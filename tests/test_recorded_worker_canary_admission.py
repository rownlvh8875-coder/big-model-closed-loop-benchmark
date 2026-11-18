"""Portable admission/archive regressions; fixtures are never native evidence."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from bigbench import recorded_worker_canary as c
from scripts import run_recorded_worker_canary as host


class AdmissionTests(unittest.TestCase):
    def good(self):
        source='a'*40;head='b'*40
        manifest={'scripts/example.py':'c'*64}
        request=dict(schema='recorded-worker-camera-canary-request-v1',active=True,mode=c.MODE,
            limits=dict(c.LIMITS),case=dict(seed=c.CASE[0],scenario=c.CASE[1]),source=source,
            push_ci=12,pr_ci=13,source_map=manifest)
        context=dict(attempt=1,event='push',branch=c.BRANCH,env_head=head,head=head,
            parents=[source],delta=['M\t'+c.REQUEST],repository='rownlvh8875-coder/big-model-closed-loop-benchmark',run_id='987')
        ci={}
        for event,runid in (('push',12),('pull_request',13)):
            ci[event]=dict(run=dict(id=runid,head_sha=source,head_branch=host.FEATURE,event=event,workflow_id=411705464,
                run_attempt=1,conclusion='success',status='completed',head_repository=dict(full_name=context['repository'])),
                jobs=dict(total_count=2,jobs=[dict(name=n,conclusion='success',status='completed') for n in ('synthetic-unit','onnx-interface-test')]),
                artifacts=dict(total_count=0,artifacts=[]))
        return request,context,manifest,ci

    def test_only_exact_request_source_and_four_ci_jobs_are_admitted(self):
        r,x,m,ci=self.good()
        self.assertEqual(host.validate_admission(r,x,manifest=m,ci=ci)['source'],r['source'])
        for changes in ({'attempt':2},{'event':'workflow_dispatch'},{'branch':host.FEATURE},{'env_head':'c'*40},
                        {'parents':[]},{'parents':[r['source'],'d'*40]},{'delta':['M\tbigbench/image_adapter.py']},
                        {'run_id':None},{'head':'g'*40}):
            bad=dict(x,**changes)
            with self.subTest(context=changes),self.assertRaises(ValueError):host.validate_admission(r,bad,manifest=m,ci=ci)
        for changes in ({'mode':'OFFICIAL_MODEL'},{'active':False},{'limits':dict(c.LIMITS,official_models=1)},
                        {'limits':dict(c.LIMITS,official_models=False)},{'source_map':{}},{'source':'z'*40}):
            with self.subTest(request=changes),self.assertRaises(ValueError):host.validate_admission(dict(r,**changes),x,manifest=m,ci=ci)
        for mutate in (lambda d:d['push']['run'].update(head_sha='d'*40),
                       lambda d:d['pull_request']['run'].update(run_attempt=2),
                       lambda d:d['push']['run'].update(workflow_id=123),
                       lambda d:d['push']['run']['head_repository'].update(full_name='fork/repo'),
                       lambda d:d['push']['jobs']['jobs'][0].update(conclusion='failure'),
                       lambda d:d['pull_request']['artifacts'].update(total_count=1)):
            bad=copy.deepcopy(ci);mutate(bad)
            with self.assertRaises(ValueError):host.validate_admission(r,x,manifest=m,ci=bad)

    def test_mounted_source_map_cannot_omit_change_or_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'source.py';path.write_bytes(b'original')
            mapping={'source.py':hashlib.sha256(b'original').hexdigest()}
            c.check_source_map(root,mapping)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):c.check_source_map(root,mapping)
            for name in ('../source.py','/source.py','C:/source.py','a\\b.py'):
                with self.assertRaises(ValueError):c.check_source_map(root,{name:'a'*64})
            if os.name!='nt':
                path.unlink();outside=root/'outside';outside.write_bytes(b'original');path.symlink_to(outside)
                with self.assertRaises(ValueError):c.check_source_map(root,mapping)

    def test_inactive_workflow_is_branch_path_scoped_and_has_no_model_phase(self):
        text=(host.ROOT/c.WORKFLOW).read_text()
        self.assertIn("branches: ['"+c.BRANCH+"']",text)
        self.assertIn("paths: ['"+c.REQUEST+"']",text)
        self.assertNotIn('workflow_dispatch',text)
        self.assertNotIn('model-deps',text)
        self.assertIn('if: always()',text)
        request=json.loads((host.ROOT/c.REQUEST).read_text())
        # On feature/source CI this placeholder must never be active.
        if os.environ.get('GITHUB_REF_NAME')!=c.BRANCH:self.assertIs(request['active'],False)


class ArchiveTests(unittest.TestCase):
    def archive(self,root,members):
        path=root/'artifact.zip'
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,data in members:z.writestr(name,data)
        return path,hashlib.sha256(path.read_bytes()).hexdigest()

    def test_digest_namespace_symlinks_duplicate_conflicts_and_extent_rejected(self):
        for members in ([('../escape',b'x')],[('/escape',b'x')],[('a\\b',b'x')],[('C:/escape',b'x')],
                        [('a',b'x'),('a',b'y')],[('a',b'x'),('a/b',b'y')],[('a/b',b'y'),('a',b'x')]):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);path,digest=self.archive(root,members)
                with self.assertRaises(ValueError):c.extract_archive(path,root/'out',expected_sha256=digest)
                self.assertFalse((root/'out').exists())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
            path,digest=self.archive(root,[(info,b'target')])
            with self.assertRaises(ValueError):c.extract_archive(path,root/'out',expected_sha256=digest)
            path,digest=self.archive(root,[('oversize',b'0'*(16*1024**2+1))])
            with self.assertRaises(ValueError):c.extract_archive(path,root/'out',expected_sha256=digest)
            path,digest=self.archive(root,[('receipt.json',b'{}')])
            with self.assertRaises(ValueError):c.extract_archive(path,root/'out',expected_sha256='0'*64)
            out=c.extract_archive(path,root/'out',expected_sha256=digest)
            self.assertEqual((out/'receipt.json').read_bytes(),b'{}')
            with self.assertRaises(ValueError):c.extract_archive(path,out,expected_sha256=digest)

    @unittest.skipUnless(sys.platform=='linux','Docker command builder uses Linux runtime helpers')
    def test_model_mounts_forbidden_and_only_new_canary_entry_used(self):
        argv=host.canary_command('fixture',Path('/repo'),Path('/sdk'),Path('/out'),['--source','a'*40],owner='a'*32)
        self.assertIn(host.ENTRY,argv)
        self.assertNotIn('/model.onnx',str(argv))
        self.assertIn('--read-only',argv)
        self.assertIn('none',argv)
        for key in ('model','deps'):
            with self.assertRaises(ValueError):host.canary_command('x',Path('/r'),Path('/s'),Path('/o'),[],owner='b'*32,**{key:Path('/bad')})


@unittest.skipUnless(sys.platform=='linux','native bundle has Linux Docker receipts')
class NativeBundleTests(unittest.TestCase):
    def build(self,root):
        from tests.test_recorded_worker_canary import CanaryTests
        from scripts import panda_sdk3_runtime as pins
        from bigbench.full_s_recorded_worker import _read_receipt
        from bigbench.full_s_failure_capture import verify_recording
        native=root/'native';native.mkdir()
        fixture=CanaryTests();fixture.setUp();fixture.fixture(native/'observed-trial')
        # Explicit CPU fixture with named native primitives for pure replay only.
        recording=native/'observed-trial/recording'
        report=json.loads((recording/'report.json').read_text())
        for row in report['geometry']:
            row['lane_class']='metadrive.component.lane.'+('circular_lane.CircularLane' if row['shape']['kind']=='circular' else 'straight_lane.StraightLane')
        raw=(json.dumps(report,indent=2)+'\n').encode();previous=(recording/'report.json').stat().st_size
        (recording/'report.json').write_bytes(raw)
        manifest=json.loads((recording/'manifest.json').read_text());manifest.update(report_sha256=hashlib.sha256(raw).hexdigest())
        manifest['payload_and_report_bytes']+=len(raw)-previous
        (recording/'manifest.json').write_text(json.dumps(manifest))
        trial=_read_receipt(native/'observed-trial/recorded-trial.json',4*1024**2)
        trial['driver']=dict(renderer='llvmpipe CPU_UNIT_FIXTURE_ONLY',vendor='fixture',version='fixture')
        trial['recording_verification']=verify_recording(recording)
        (native/'observed-trial/recorded-trial.json').write_text(json.dumps(trial))
        request,context,mapping,ci=AdmissionTests().good()
        mapping={'scripts/run_recorded_worker_canary.py':hashlib.sha256((host.ROOT/'scripts/run_recorded_worker_canary.py').read_bytes()).hexdigest()}
        request['source_map']=mapping
        auth=host.validate_admission(request,context,manifest=mapping,ci=ci)
        launch=dict(parent_pid=trial['parent_pid'],nonce=trial['nonce'],seed=c.CASE[0],scenario=c.CASE[1],
            mode=c.MODE,source=auth['source'],activation=auth['activation'],run_id=auth['run_id'],limits=c.LIMITS)
        stats=dict(returned=0,guards_ok=True,values={k:0 for k in c.STAT_FIELDS})
        top=dict(launch,protocol='recorded-camera-canary-native-v1',status='CAMERA_RECORDER_CANARY_RECORDED',pid=trial['pid'],
            source_map_sha256=c.check_source_map(host.ROOT,mapping),parent_admission_checked=True,
            sdk_sha256=pins.SDK_SHA,core_sha256=pins.CORE_SHA,load_order='core-first',panda_version='1.10.13',
            source_stats_before=stats,source_stats_after=stats,zero_model_audit=dict(weight_open_attempts=0,ort_import_attempts=0),
            onnxruntime_loaded=False,official_model_processes=0,official_inferences=0,capture_count_bounds=[2,2],sensor_perceive_bounds=[4,4],
            fixture_policy_audit_bounds=[2,2],policy_data=trial['policy_data'],graph_feed_attested=False,
            server_returncode=0,child_finalized_before_server_stop=True,**{k:False for k in c.FALSE_FLAGS})
        cid='f'*64;label='d'*32
        command=host.canary_command('fixture',Path('/repo'),Path('/sdk'),Path('/out'),
            ['--source',auth['source'],'--activation',auth['activation'],'--run-id',auth['run_id']],owner=label)
        files={'authentication.json':auth,'native/report.json':top,'native/launch.json':launch,
            'native/native-child.json':dict(spawn_attempted=True,pid=trial['pid'],returncode=0,server_returncode=0),
            'native/container.json':dict(name='fixture',id=cid,image=pins.IMAGE,ownership_label=label,
                effective_limits=dict(Memory=10*1024**3,MemorySwap=10*1024**3,NanoCpus=2_000_000_000,
                    PidsLimit=128,ReadonlyRootfs=True,NetworkMode='none',IpcMode='private')),
            'native/command.json':dict(argv=command,ownership_label=label),
            'native/execution.json':dict(status='EXIT_OBSERVED',returncode=0,failure=None,container_id=cid,
                create_attempted=True,start_attempted=True,owned_container_removed=True,ownership_unresolved=False,cleanup_failure=None,
                stopped_state=dict(Running=False,Pid=0,OOMKilled=False,ExitCode=0))}
        for path,value in files.items():(root/path).write_text(json.dumps(value))
        return files

    def test_all_parent_source_cleanup_and_command_associations_are_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.build(root)
            self.assertTrue(c.validate_native_bundle(root)['camera_recorder_canary_passed'])
            self.assertFalse(c.validate_native_bundle(root)['origin_authenticated'])
            for name,changes in (
                ('native/report.json',{'nonce':'b'*32}),('native/launch.json',{'parent_pid':100}),
                ('native/native-child.json',{'pid':1}),('native/report.json',{'source':'c'*40}),
                ('native/report.json',{'official_inferences':1}),('native/report.json',{'sdk_sha256':'a'*64}),
                ('native/report.json',{'child_finalized_before_server_stop':False}),
                ('native/execution.json',{'owned_container_removed':False}),
                ('native/container.json',{'image':'sha256:'+'0'*64}),
                ('native/report.json',{'zero_model_audit':dict(weight_open_attempts=1,ort_import_attempts=0)})):
                path=root/name;original=path.read_bytes();data=json.loads(original);data.update(changes);path.write_text(json.dumps(data))
                with self.subTest(name=name,changes=changes),self.assertRaises(ValueError):c.validate_native_bundle(root)
                path.write_bytes(original)
            path=root/'native/command.json';data=json.loads(path.read_text());data['argv'].insert(-1,'--model-trial');path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):c.validate_native_bundle(root)


if __name__=='__main__':unittest.main()
