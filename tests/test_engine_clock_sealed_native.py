"""Admission and bounded process fixtures; never import a renderer or call Docker."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
try:
    from scripts import engine_clock_sealed_native as n
except ImportError:
    n = None

ROOT = Path(__file__).resolve().parents[1]


class SealedNativeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(n, 'new sealed native protocol is absent')

    def request(self):
        return dict(schema='engine-clock-sealed-native-request-v1', request_id=n.ID,
                    repository=n.REPOSITORY, branch=n.BRANCH, workflow_path=n.WORKFLOW,
                    reviewed_source_branch=n.SOURCE_BRANCH, reviewed_source_sha='1'*40,
                    source_closure={p:'0'*64 for p in n.source_paths(ROOT)},
                    source_ci=[dict(event='push',run_id=11),dict(event='pull_request',run_id=12)],
                    budget=copy.deepcopy(n.BUDGET), native_budget=copy.deepcopy(n.NATIVE_BUDGET),
                    image_evidence=n.image_evidence(ROOT), official_model_calls=0, ort_sessions=0)

    def test_request_rejects_extra_native_allowance_and_incomplete_source(self):
        request=self.request();self.assertEqual(request,n.validate_request(request,ROOT))
        for key,value in [('source_closure',{}),('official_model_calls',1),('ort_sessions',True),('branch','main'),('extra',0)]:
            bad=copy.deepcopy(request);bad[key]=value
            with self.assertRaises(ValueError):n.validate_request(bad,ROOT)
        bad=copy.deepcopy(request);bad['native_budget']['providers']=2
        with self.assertRaises(ValueError):n.validate_request(bad,ROOT)
        bad=copy.deepcopy(request);bad['image_evidence']['expected']['artifact_id']=1
        with self.assertRaises(ValueError):n.validate_request(bad,ROOT)

    def test_source_union_includes_application_identity_and_image_authority(self):
        paths=n.source_paths(ROOT)
        self.assertTrue({'bigbench/metadrive_camera.py','scripts/engine_clock_native.py',
                         'scripts/engine_clock_runtime_contract.py','scripts/engine_clock_runtime_inventory.py',
                         'scripts/engine_clock_sealed_native_container.py',n.WORKFLOW,
                         'docs/evidence/engine-clock-sealed-image-06/installed-files.json'}<=paths)
        self.assertGreater(len(paths),79)

    def test_activation_rejects_reused_merged_or_modified_request(self):
        r=self.request();delta=b'A\0'+n.REQUEST.encode()+b'\0'
        n.validate_activation(r,'2'*40,['1'*40],delta,'100644',n.BRANCH)
        for parents,changes,mode,branch in [(['1'*40,'3'*40],delta,'100644',n.BRANCH),(['3'*40],delta,'100644',n.BRANCH),(['1'*40],b'M\0'+n.REQUEST.encode()+b'\0','100644',n.BRANCH),(['1'*40],delta,'120000',n.BRANCH),(['1'*40],delta,'100644','main')]:
            with self.assertRaises(ValueError):n.validate_activation(r,'2'*40,parents,changes,mode,branch)

    def ci(self):
        return [dict(run=dict(id=rid,head_sha='1'*40,head_branch=n.SOURCE_BRANCH,event=event,path='.github/workflows/ci.yml',run_attempt=1,status='completed',conclusion='success',repository=dict(full_name=n.REPOSITORY)),jobs=dict(total_count=2,jobs=[dict(name=name,run_id=rid,status='completed',conclusion='success') for name in ('synthetic-unit','onnx-interface-test')]),artifacts=dict(total_count=0,artifacts=[])) for rid,event in [(11,'push'),(12,'pull_request')]]

    def test_ci_is_exact_source_and_both_named_terminal_jobs(self):
        r=self.request();proofs=self.ci();n.validate_source_ci(r,proofs)
        for field,value in [('head_sha','3'*40),('head_branch','main'),('run_attempt',True),('conclusion','failure')]:
            bad=copy.deepcopy(proofs);bad[0]['run'][field]=value
            with self.assertRaises(ValueError):n.validate_source_ci(r,bad)
        bad=copy.deepcopy(proofs);bad[1]['jobs']['jobs'][0]['name']='different'
        with self.assertRaises(ValueError):n.validate_source_ci(r,bad)

    def test_live_run_is_unique_current_push_attempt(self):
        r=self.request();ctx=dict(repository=n.REPOSITORY,event='push',attempt=1,run_id=111,head_sha='2'*40)
        run=dict(id=111,head_sha='2'*40,head_branch=n.BRANCH,workflow_id=222,path=n.WORKFLOW,event='push',run_attempt=1,status='in_progress',repository=dict(full_name=n.REPOSITORY))
        wf=dict(id=222,path=n.WORKFLOW,state='active');unique=dict(total_count=1,workflow_runs=[run])
        n.validate_live(r,ctx,run,wf,unique)
        for field,value in [('run_attempt',2),('head_sha','3'*40),('head_branch','main')]:
            bad=copy.deepcopy(run);bad[field]=value
            with self.assertRaises(ValueError):n.validate_live(r,ctx,bad,wf,unique)
        with self.assertRaises(ValueError):n.validate_live(r,ctx,run,wf,dict(total_count=2,workflow_runs=[run,run]))

    def test_environment_rejects_unregistered_loader_and_locale(self):
        profile=n.environment_profile();self.assertEqual('C.UTF-8',profile['LC_ALL'])
        self.assertEqual(profile,n.check_environment(profile,'parent'))
        for name,value in [('LD_LIBRARY_PATH','/host'),('GALLIUM_DRIVER','llvmpipe'),('LC_ALL','C'),('GH_TOKEN','secret-value')]:
            bad=dict(profile);bad[name]=value
            with self.assertRaises(ValueError):n.check_environment(bad,'parent')
        child=dict(profile,FIRST_DIVERGENCE_TRIAL_FD='10',MESA_SHADER_CACHE_DIR='/work/cache/case_00')
        self.assertEqual(profile,n.check_environment(child,'child'))
        child['MESA_SHADER_CACHE_DIR']='/host'
        with self.assertRaises(ValueError):n.check_environment(child,'child')

    def permit(self):
        return dict(schema='engine-clock-sealed-native-permit-v1',parent_pid=23,
                    parent_uuid='a'*32,process_group=37,nonce='b'*64,binding_sha256='c'*64,
                    identity_sha256='d'*64)

    def test_permit_requires_live_ancestor_group_nonce_and_binding(self):
        p=self.permit();facts=dict(ancestors=[36,23,1],group=37,nonce='b'*64,binding_sha='c'*64,identity_sha='d'*64)
        n.validate_permit(p,**facts)
        for key,value in [('ancestors',[36,1]),('group',38),('nonce','e'*64),('binding_sha','f'*64),('identity_sha','e'*64)]:
            bad=dict(facts);bad[key]=value
            with self.assertRaises(ValueError):n.validate_permit(p,**bad)

    def test_container_pid1_is_valid_only_when_actual_live_ancestor(self):
        p=self.permit();p['parent_pid']=1
        n.validate_permit(p,ancestors=[36,1],group=37,nonce='b'*64,binding_sha='c'*64,identity_sha='d'*64)
        with self.assertRaises(ValueError):n.validate_permit(p,ancestors=[36,2],group=37,nonce='b'*64,binding_sha='c'*64,identity_sha='d'*64)

    def test_real_one_use_fifo_eof_is_consumed_and_replay_fd_is_closed(self):
        import fcntl,os
        from unittest.mock import patch
        from scripts import engine_clock_sealed_native_container as c
        permit=self.permit();permit.update(parent_pid=os.getppid(),process_group=os.getpgid(0))
        readfd,writefd=os.pipe();high=fcntl.fcntl(readfd,fcntl.F_DUPFD_CLOEXEC,10);os.close(readfd)
        os.write(writefd,json.dumps(permit).encode());os.close(writefd)
        with patch.dict(os.environ,{'FIRST_DIVERGENCE_TRIAL_FD':str(high)}):
            got=c.consume_fd('b'*64,'c'*64,'d'*64)
            self.assertEqual(permit,got)
            self.assertNotIn('FIRST_DIVERGENCE_TRIAL_FD',os.environ)
        with self.assertRaises(OSError):os.fstat(high)

    def test_refused_prestart_never_starts_native_container(self):
        try:from scripts import engine_clock_sealed_native_run as runner
        except ImportError:runner=None
        self.assertIsNotNone(runner,'outer authenticated native controller absent')
        calls=[]
        class Engine:
            from time import perf_counter
            deadline=perf_counter()+1800
            host=json.loads((ROOT/(n.AUTH+'root-acceptance.json')).read_bytes())['host']
            profile=json.loads((ROOT/(n.AUTH+'root-acceptance.json')).read_bytes())['engine']
            def once(self,name):calls.append(name)
            def call(self,args,**kwargs):
                calls.append(args[0]);self.assert_create(args);return {'_stdout':b'b'*64+b'\n'}
            def assert_create(self,args):
                if args[0]!='create':raise AssertionError('native start before stopped-container proof')
            def copied_tree(self,*args):
                from time import perf_counter
                if self.deadline>perf_counter()+180:raise AssertionError('prestart copies have no shared 180s deadline')
                raise ValueError('real prestart rejection fixture')
            def terminate(self,cid):calls.append('terminate');return {'stopped_state_established':True}
        receipt=json.loads((ROOT/(n.AUTH+'preparation.json')).read_bytes())
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,'prestart rejection'):
                runner.launch_canary(Engine(),{'config_digest':receipt['config_digest']},self.request(),
                    {'request_sha256':'a'*64},receipt,(ROOT/(n.AUTH+'installed-files.json')).read_bytes(),Path(td),ROOT)
        self.assertNotIn('start',calls);self.assertIn('terminate',calls)

    def test_source_bytes_are_verified_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'a').write_bytes(b'hello')
            n.verify_sources(root,{'a':'2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'})
            (root/'a').write_bytes(b'changed')
            with self.assertRaises(ValueError):n.verify_sources(root,{'a':'2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'})
            (root/'a').unlink();(root/'a').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):n.verify_sources(root,{'a':'0'*64})

    def test_unregistered_invocation_cannot_reach_native_imports(self):
        import subprocess,sys
        result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/engine_clock_sealed_native_container.py'),'parent'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
        self.assertEqual(1,result.returncode)
        self.assertIn(b'SEALED_NATIVE_REJECTED',result.stdout)
        self.assertNotIn(b'No module named',result.stderr)

    def test_identity_keeps_strict_actual_host_and_full_environment(self):
        receipt=json.loads((ROOT/(n.AUTH+'preparation.json')).read_bytes())
        actual=json.loads((ROOT/(n.AUTH+'root-acceptance.json')).read_bytes())
        expected=n.image_evidence(ROOT)['expected']
        identity=n.make_identity(receipt,expected,actual['host'],actual['engine'])
        changed=copy.deepcopy(actual['host']);changed['release']='different-kernel'
        second=n.make_identity(receipt,expected,changed,actual['engine'])
        self.assertNotEqual(identity['core_sha256'],second['core_sha256'])
        self.assertEqual(14078483374,identity['core']['image']['artifact_id'])
        self.assertNotIn('ImageVersion',identity['core']['host'])

    def launch(self):
        env=[k+'='+v for k,v in n.environment_profile().items()]
        mounts=[dict(Type='bind',Source=src,Destination=dst,RW=rw,Propagation='rprivate') for src,dst,rw in [('/host/repo','/work/repo',False),('/host/binding','/work/binding',False),('/host/output','/work/output',True),('/host/cache','/work/cache',True)]]
        mounts.append(dict(Type='tmpfs',Source='',Destination='/tmp',RW=True))
        host=dict(ReadonlyRootfs=True,NetworkMode='none',Privileged=False,CapDrop=['ALL'],CapAdd=None,SecurityOpt=['no-new-privileges'],PidMode='',IpcMode='private',PidsLimit=128,Memory=2147483648,NanoCpus=2000000000,Devices=[],DeviceRequests=None,Binds=None,Tmpfs={'/tmp':'rw,nosuid,nodev,noexec,size=67108864,mode=0700'},GroupAdd=None,ExtraHosts=None,PortBindings={})
        cfg=dict(Env=env,Entrypoint=['/opt/venv/bin/python'],Cmd=['-I','-S','-B','/work/repo/scripts/engine_clock_sealed_native_container.py','parent'],User='0:0',WorkingDir='/work/repo',Hostname='stage7-sealed-native',Tty=False,OpenStdin=False,Labels={'stage7.request':n.ID,'stage7.nonce':'a'*32,'stage7.source':'1'*40,'org.opencontainers.image.version':'24.04'})
        return dict(Id='b'*64,Image='sha256:'+'c'*64,HostConfig=host,Config=cfg,Mounts=mounts)

    def test_launch_refuses_writable_source_host_display_devices_and_secrets(self):
        raw=self.launch();routes=dict(repo='/host/repo',binding='/host/binding',output='/host/output',cache='/host/cache')
        expected=dict(config_digest='sha256:'+'c'*64,source_sha='1'*40,nonce='a'*32)
        checked=n.validate_launch(raw,routes,expected);self.assertTrue(checked['validated'])
        bad=copy.deepcopy(raw);bad['Mounts'][0]['RW']=True
        with self.assertRaises(ValueError):n.validate_launch(bad,routes,expected)
        bad=copy.deepcopy(raw);bad['Mounts'].append(dict(Type='bind',Source='/tmp/.X11-unix',Destination='/tmp/.X11-unix',RW=False))
        with self.assertRaises(ValueError):n.validate_launch(bad,routes,expected)
        bad=copy.deepcopy(raw);bad['HostConfig']['Devices']=[dict(PathOnHost='/dev/dri')]
        with self.assertRaises(ValueError):n.validate_launch(bad,routes,expected)
        bad=copy.deepcopy(raw);bad['Config']['Env'].append('GH_TOKEN=secret-value')
        with self.assertRaises(ValueError):n.validate_launch(bad,routes,expected)


if __name__=='__main__':unittest.main()
