"""Native envelope CPU doubles only, never evidence of an actual model/session."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from bigbench import recorded_official_execution as c
from bigbench.full_s_recorded_worker import _read_receipt
from scripts import run_recorded_official as h
from tests import test_recorded_official as admission_tests

@unittest.skipUnless(sys.platform=='linux','frozen native-body orchestration fixtures are Linux-only')
class BundleTests(unittest.TestCase):
    def build(self,root,kind='complete'):
        from tests.test_full_s_recorded_receiver import trial_fixture
        from scripts import panda_sdk3_runtime as pins
        from bigbench import recorded_official_dependencies as d
        native=root/'native';native.mkdir()
        trial_fixture(native/'observed-trial',kind)
        trial=_read_receipt(native/'observed-trial/recorded-trial.json',4*1024**2)
        life=_read_receipt(native/'observed-trial/recorded-trial-lifecycle.json')
        r,x,m,ci=admission_tests.AdmissionTests().good();m={'bigbench/recorded_official_execution.py':hashlib.sha256((c.ROOT/'bigbench/recorded_official_execution.py').read_bytes()).hexdigest()};r['source_map']=m
        self.mapping=m
        auth=h.validate_admission(r,x,manifest=m,ci=ci,**admission_tests.AdmissionTests().external(r,x,m,ci))
        desc=dict(protocol='recorded-official-installed-dependencies-v1',declaration_sha256=d.DECLARATION_SHA,versions=d.VERSIONS,files={'module.py':dict(nbytes=1,sha256='a'*64)})
        self.write(root/'model-dependencies.json',desc);self.write(native/'model-dependencies.json',desc)
        dep=hashlib.sha256((root/'model-dependencies.json').read_bytes()).hexdigest()
        launch=dict(parent_pid=trial['parent_pid'],nonce=trial['nonce'],seed=c.CASE[0],scenario=c.CASE[1],mode=c.MODE,source=auth['source'],activation=auth['activation'],run_id=auth['run_id'],approval=r['approval_sha'],limits=c.LIMITS,dependencies_sha256=dep)
        stats=dict(returned=0,guards_ok=True,values={k:0 for k in c.STAT_FIELDS})
        rc=0 if kind=='complete' else 1
        top=dict(launch,protocol='recorded-official-native-v1',status='OFFICIAL_RECORDED_DIAGNOSTIC_RETURNED' if rc==0 else 'FAILED',pid=trial['pid'],
            source_map_sha256=c.check_source_map(c.ROOT,m),parent_admission_checked=True,sdk_sha256=pins.SDK_SHA,core_sha256=pins.CORE_SHA,load_order='core-first',panda_version='1.10.13',
            source_stats_before=stats,source_stats_after=stats,server_returncode=0,child_finalized_before_server_stop=True,failure=None if rc==0 else 'TrialFailure: fixture',container_hostname='f'*12,
            recorded_trial_sha256=hashlib.sha256((native/'observed-trial/recorded-trial.json').read_bytes()).hexdigest(),dependencies=dict(versions=d.VERSIONS,declaration_sha256=d.DECLARATION_SHA,file_count=1),model_sha256=pins.MODEL_SHA,model_nbytes=768750198,
            **c.activity_bounds(life),**{k:False for k in c.FALSE_FLAGS})
        child=dict(pid=trial['pid'],spawn_attempted=True,returncode=rc,server_returncode=0,failure=None)
        self.write(native/'report.json',top);self.write(native/'launch.json',launch);self.write(native/'native-child.json',child)
        final=dict(protocol='recorded-official-parent-completion-v1',status='NATIVE_CHILD_REAPED',failure=None,returncode=rc,
            **{k:top[k] for k in ('pid','parent_pid','nonce','source','activation','run_id','approval','mode','container_hostname')},
            native_child_sha256=hashlib.sha256((native/'native-child.json').read_bytes()).hexdigest(),report_sha256=hashlib.sha256((native/'report.json').read_bytes()).hexdigest())
        self.write(native/'parent-completion.json',final)
        label='d'*32;cid='f'*64;name='recorded-official-'+auth['run_id']
        argv=h.official_command(name,Path('/repo'),Path('/sdk'),Path('/out'),['--source',auth['source'],'--activation',auth['activation'],'--run-id',auth['run_id'],'--approval',r['approval_sha'],'--dependencies-sha256',dep],owner=label,model=Path('/model'),deps=Path('/deps'))
        self.write(native/'command.json',dict(argv=argv,ownership_label=label))
        self.write(native/'container.json',dict(id=cid,name=name,image=pins.IMAGE,ownership_label=label,effective_limits=dict(Memory=10*1024**3,MemorySwap=10*1024**3,NanoCpus=2000000000,PidsLimit=128,ReadonlyRootfs=True,NetworkMode='none',IpcMode='private')))
        self.write(native/'execution.json',dict(status='EXIT_OBSERVED',returncode=rc,failure=None,stopped_state=dict(Running=False,Pid=0,OOMKilled=False,ExitCode=rc),create_attempted=True,start_attempted=True,container_id=cid,ownership_unresolved=False,owned_container_removed=True,cleanup_failure=None))
        self.write(root/'evidence-handoff.json',dict(protocol='recorded-worker-evidence-handoff-v1',status='EVIDENCE_HANDED_TO_RUNNER',native_dir='/out',uid=1001,gid=1001,writer_uid=65534,writer_gid=65534,symlinks_followed=False,container_removed=True,argv=['sudo','-n','chown','-R','--no-dereference','--from=65534:65534','1001:1001','--','/out']))
        self.write(root/'authentication.json',auth)
        pages=[dict(total_count=1,workflow_runs=[dict(id=int(auth['run_id']),workflow_id=98765,status='in_progress')])]
        for stage in ('before-staging','before-container'):self.write(root/('public-activity-'+stage+'.json'),dict(pages=pages))
    def write(self,path,data):path.write_text(json.dumps(data,indent=2)+'\n')
    def verify(self,root):
        report=root/'native/observed-trial/recording/report.json'
        with patch.object(h,'source_manifest',return_value=self.mapping):return c.validate_native_bundle(root,qualified=_read_receipt(report,16*1024**2) if report.exists() else None)
    def test_complete_and_failed_original_bodies_keep_distinct_status_and_bounds(self):
        for kind,status in (('complete','COMPLETE_DIAGNOSTIC'),('graph','PARTIAL_DIAGNOSTIC'),('constructor','INCOMPLETE_EVIDENCE')):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.build(root,kind)
                result=self.verify(root)
                self.assertEqual(result['status'],status);self.assertFalse(result['native_execution_authenticated'])
                self.assertEqual(result['official_model_process_bounds'],[0,1] if kind=='constructor' else [1,1])
    def test_envelope_changes_and_canary_session_cannot_borrow_model_authentication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.build(root)
            changes=(('native/report.json',{'official_model_process_bounds':[0,0]}),('native/launch.json',{'mode':'CAMERA_ONLY_NO_GRAPH'}),
                ('native/parent-completion.json',{'report_sha256':'e'*64}),('native/container.json',{'image':'other'}),
                ('native/execution.json',{'owned_container_removed':False}),('native/model-dependencies.json',{'versions':{}}),
                ('evidence-handoff.json',{'symlinks_followed':True}))
            for name,delta in changes:
                path=root/name;raw=path.read_bytes();value=json.loads(raw);value.update(delta);self.write(path,value)
                with self.subTest(name=name),self.assertRaises(ValueError):self.verify(root)
                path.write_bytes(raw)
    def test_missing_final_receipts_preserve_lifecycle_bounds_without_native_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.build(root,'graph')
            for name in ('report.json','parent-completion.json'):(root/'native'/name).unlink()
            result=self.verify(root)
            self.assertEqual(result['status'],'INCOMPLETE_EVIDENCE');self.assertEqual(result['official_inference_bounds'],[1,2])
            self.assertFalse(result['native_execution_authenticated'])

if __name__=='__main__':unittest.main()
