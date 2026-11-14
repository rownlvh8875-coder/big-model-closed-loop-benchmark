"""Synthetic CPU evidence and native/attestor boundaries; never run a renderer."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from test_engine_clock_held_abba import request,context,ROOT
try:
    from scripts import engine_clock_held_abba as n
    from scripts import engine_clock_held_abba_archive as archive
    from scripts import engine_clock_held_abba_run as run
    from scripts import engine_clock_held_abba_container as child
    from scripts import engine_clock_held_abba_attest as attest
except ImportError:archive=run=child=attest=None


def fixture(root):
    """Real synthetic PNG/I420 math; remaining witnesses explicitly fixture metadata."""
    from test_engine_clock_native import DatasetTests
    from scripts import engine_clock_held_abba_lifecycle as life
    root=Path(root);output=root/'output';output.mkdir(parents=True)
    old,cases=DatasetTests().fixture(output)
    req=request();raw=n.canonical(req);ctx=context()
    lease=life.create_lease(ctx,b'01234567-0123-4567-89ab-0123456789ab\n',100.)
    ctx['lease_sha256']=n.sha(n.canonical(lease))
    receipt=json.loads((ROOT/(n.AUTH+'preparation.json')).read_bytes())
    profile=json.loads((ROOT/(n.AUTH+'root-acceptance.json')).read_bytes())
    details=dict(affinity_ids=list(range(profile['host']['affinity_cpus'])),memory_total_bytes=8*1024**3)
    identity=n.identity_from_profiles(receipt,req['image_evidence']['expected'],profile['host'],profile['engine'],details)
    binding=dict(schema='engine-clock-held-abba-binding-v1',request=req,producer_request=req,context=ctx,
        host_lease=lease,accepted_canary=None,receipt=receipt,identity=identity,host=profile['host'],engine=profile['engine'])
    braw=n.canonical(binding);bsha=n.sha(braw)
    case=cases[0];case.update(context=ctx,source_snapshot=req['source_closure'],runtime=identity,request_sha256=n.sha(raw))
    (output/'case_00/case.json').write_bytes(n.canonical(case))
    phase=dict(schema='engine-clock-held-abba-phase-v1',status=n.recorded_status('canary'),mode='canary',
        context=ctx,identity=identity,identity_verified=True,parent_pid=old['parent_pid'],parent_uuid=old['parent_uuid'],
        binding_sha256=bsha,launches=old['launches'],comparisons=[],error=None,budget=n.BUDGET,native_budget=n.native_budget('canary'),
        elapsed_seconds=64.,official_model_calls=0,ort_sessions=0,scientific_result_promoted=False)
    def write(name,value):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(n.canonical(value))
    write('consumed-request.json',req);write('producer-request.json',req);write('source-authentication.json',ctx)
    write('host-lease.json',lease);write('binding/binding.json',binding);write('output/phase.json',phase)
    memory=dict(max_bytes=4294967296,cgroup_inode=33,events=dict(oom=0,oom_kill=0),peak_is_rss=False,non_atomic=True)
    for tag in ('parent','child-00'):
        proof=dict(identity=identity,binding_sha256=bsha,
            inventory=dict(complete=True,status='INSTALLED_FILES_MATCH',canonical_manifest_sha256=receipt['installed_files_sha256'],bytes_read=1670492280,matched_entries=44232),
            prefix=dict(status='PREFIX_LAYOUT_AND_OBSERVATION_MATCH'),memory_before=memory,
            launch_environment=n.environment_profile(),environment=dict(n.environment_profile(),LD_LIBRARY_PATH=n.CV2_LD_LIBRARY_PATH))
        if tag=='child-00':
            proof['launch_environment'].update(FIRST_DIVERGENCE_TRIAL_FD='10',MESA_SHADER_CACHE_DIR='/work/cache/case_00',DISPLAY=':99',XAUTHORITY='/tmp/xvfb-run.abc123/Xauthority')
            proof['environment']=dict(proof['launch_environment'],LD_LIBRARY_PATH=n.CV2_LD_LIBRARY_PATH)
            proof['permit']=dict(schema='engine-clock-sealed-abba-permit-v1',mode='canary',index=0,parent_pid=phase['parent_pid'],parent_uuid=phase['parent_uuid'],process_group=phase['launches'][0]['process_group'],nonce=case['nonce'],binding_sha256=bsha,identity_sha256=identity['core_sha256'])
        write('output/'+tag+'-admission.json',proof);write('output/'+tag+'-memory-after.json',memory)
        for kind,value in [('host',profile['host']),('identity',identity)]:
            write('output/'+tag+'-'+kind+'-comparison.json',dict(equal=True,differences=[],observed=value,observed_sha256=n.sha(n.canonical(value)),accepted_sha256=n.sha(n.canonical(value))))
    copies=[]
    for name in ('copied-code','copied-python','copied-executable'):
        path=root/'docker'/(name+'.tar');path.parent.mkdir(exist_ok=True);path.write_bytes(('SYNTHETIC_DATA_ONLY_'+name).encode())
        copies.append(dict(archive_sha256=n.sha(path.read_bytes()),archive_nbytes=path.stat().st_size))
    write('controller.json',dict(status=n.recorded_status('canary'),context=ctx,identity=identity,copied_trees=copies,
        phase_sha256=n.sha(n.canonical(phase)),state=dict(Status='exited',Running=False,ExitCode=0,OOMKilled=False),official_model_calls=0,ort_sessions=0,scientific_result_promoted=False))
    write('result.json',dict(status=n.recorded_status('canary'),elapsed_seconds=180.,official_model_calls=0,ort_sessions=0,scientific_result_promoted=False))
    return req,ctx,identity,lease,phase


def zip_fixture(source,path):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(Path(source).rglob('*')):
            if f.is_file():z.write(f,f.relative_to(source).as_posix())


class HeldExecutionTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(archive,'retained native/attestor execution missing')

    def test_metadata_attestor_binds_real_synthetic_archive_without_pixel_claim(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);req,ctx,identity,lease,phase=fixture(p/'raw');z=p/'synthetic.zip';zip_fixture(p/'raw',z)
            result=archive.validate_native_canary_archive(z,p/'selected',req,ctx,dict(id=51,name=n.artifact('canary'),size_in_bytes=z.stat().st_size,digest='sha256:'+n.sha(z.read_bytes())))
            self.assertEqual('CANARY_PHASE_METADATA_AUTHENTICATED',result['status'])
            self.assertFalse(result['independent_pixel_replay']);self.assertFalse(result['observed_installed_tree_here'])
            self.assertEqual(6,result['capture_pairs']);self.assertEqual(identity,result['identity'])
            effective=request('abba');effective['acceptance']['lease_sha256']=ctx['lease_sha256']
            replay=child.replay_canary(p/'selected/output',json.loads((p/'selected/output/phase.json').read_bytes()),effective)
            self.assertEqual(6,replay['capture_pairs'])

    def test_closed_provider_and_complete_inventory_are_mandatory_metadata(self):
        for target,key,value in [('output/case_00/case.json','provider_closed',False),('output/parent-admission.json','inventory',dict(complete=False))]:
            with tempfile.TemporaryDirectory() as td:
                p=Path(td);req,ctx,*_=fixture(p/'raw')
                path=p/'raw'/target;data=json.loads(path.read_bytes());data[key]=value;path.write_bytes(n.canonical(data))
                z=p/'bad.zip';zip_fixture(p/'raw',z)
                with self.assertRaises(ValueError):archive.validate_native_canary_archive(z,p/'selected',req,ctx,dict(id=51,name=n.artifact('canary'),size_in_bytes=z.stat().st_size,digest='sha256:'+n.sha(z.read_bytes())))

    def test_receipt_binds_attestor_job_phase_lease_and_source(self):
        receipt=dict(schema='engine-clock-held-canary-attestation-v1',status='CANARY_PHASE_METADATA_AUTHENTICATED',run_id=21,workflow_id=31,host_job_id=41,attestor_job_id=42,producer_head_sha='2'*40,source_sha='1'*40,artifact_id=51,artifact_sha256='a'*64,artifact_size_bytes=1234,lease_sha256='c'*64,phase_sha256='d'*64,identity_sha256='e'*64,source_closure_sha256='f'*64,producer_request_sha256='9'*64,independent_pixel_replay=False,observed_installed_tree_here=False,native_providers=0,official_model_calls=0,ort_sessions=0)
        from test_engine_clock_held_abba import approval
        checked=dict(phase_sha256='d'*64,identity=dict(core_sha256='e'*64),source_closure_sha256='f'*64,producer_request_sha256='9'*64)
        archive.validate_attestation_receipt(receipt,approval(),checked)
        for field,value in [('attestor_job_id',41),('lease_sha256','8'*64),('phase_sha256','8'*64),('independent_pixel_replay',True)]:
            bad=dict(receipt);bad[field]=value
            with self.assertRaises(ValueError):archive.validate_attestation_receipt(bad,approval(),checked)

    def test_permit_parent_uuid_must_match_completed_phase(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);req,ctx,*_=fixture(p/'raw')
            path=p/'raw/output/child-00-admission.json';data=json.loads(path.read_bytes())
            data['permit']['parent_uuid']='9'*32;path.write_bytes(n.canonical(data))
            z=p/'bad.zip';zip_fixture(p/'raw',z)
            with self.assertRaises(ValueError):
                archive.validate_native_canary_archive(z,p/'selected',req,ctx,dict(id=51,name=n.artifact('canary'),size_in_bytes=z.stat().st_size,digest='sha256:'+n.sha(z.read_bytes())))

    def test_workflow_only_canary_push_holds_native_host_and_separate_attestor(self):
        workflow=json.loads((ROOT/n.WORKFLOW).read_bytes())
        self.assertEqual(dict(branches=[n.BRANCH],paths=[n.C_REQUEST]),workflow['on']['push'])
        self.assertEqual({'push'},set(workflow['on']));self.assertEqual({'native-host','canary-attestor'},set(workflow['jobs']))
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        self.assertEqual(dict(contents='read',actions='read'),workflow['permissions'])
        host=workflow['jobs']['native-host']['steps'];att=workflow['jobs']['canary-attestor']['steps']
        self.assertLess(next(i for i,s in enumerate(host) if s.get('name')==n.C_STEP),next(i for i,s in enumerate(host) if s.get('name')==n.C_UPLOAD))
        self.assertEqual(2,sum('--canary' in s.get('run','') or '--abba' in s.get('run','') for s in host))
        self.assertFalse(any('pip ' in s.get('run','') or 'docker ' in s.get('run','') for s in att))
        for steps in (host,att):
            for step in steps:
                if 'run' in step:
                    check=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
                    self.assertEqual(0,check.returncode,check.stderr)

    def test_attestor_pending_and_failed_host_are_not_completion(self):
        from test_engine_clock_held_abba import completion
        proof=completion();jobs=proof[2]
        self.assertTrue(attest.canary_ready(jobs,context()))
        pending=copy.deepcopy(jobs);pending['jobs'][0]['steps'][1].update(status='in_progress',conclusion=None)
        self.assertFalse(attest.canary_ready(pending,context()))
        failed=copy.deepcopy(jobs);failed['jobs'][0]['steps'][0].update(status='completed',conclusion='failure')
        with self.assertRaises(ValueError):attest.canary_ready(failed,context())

    def test_prestart_proof_rejection_cannot_start_held_native_container(self):
        from time import perf_counter
        calls=[];accepted_profile=json.loads((ROOT/(n.AUTH+'root-acceptance.json')).read_bytes())
        class Engine:
            deadline=perf_counter()+2400;host=accepted_profile['host'];profile=accepted_profile['engine']
            def once(self,name):calls.append(name)
            def call(self,args,**kwargs):
                calls.append(args[0]);selftest.assertEqual('create',args[0]);return dict(_stdout=b'a'*64+b'\n')
            def copied_tree(self,*args):raise ValueError('owned stopped-container proof failure')
            def terminate(self,cid):calls.append('terminate')
        selftest=self
        receipt=json.loads((ROOT/(n.AUTH+'preparation.json')).read_bytes())
        details=dict(affinity_ids=list(range(accepted_profile['host']['affinity_cpus'])),memory_total_bytes=8*1024**3)
        with tempfile.TemporaryDirectory() as td,patch.object(n,'host_details',return_value=details):
            work=Path(td)/'canary/execution';work.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'owned stopped-container proof failure'):
                run.launch_phase(Engine(),dict(config_digest=receipt['config_digest']),request(),context(),receipt,
                    (ROOT/(n.AUTH+'installed-files.json')).read_bytes(),work,ROOT,producer=request(),lease=dict(synthetic=True))
            self.assertNotIn('start',calls);self.assertIn('terminate',calls)


if __name__=='__main__':unittest.main()
