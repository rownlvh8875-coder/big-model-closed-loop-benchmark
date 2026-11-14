"""Pure new campaign admission/archive fixtures; no native renderer or Docker."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile
try:
    from scripts import engine_clock_sealed_abba as n
    from scripts import engine_clock_sealed_abba_acceptance as a
except ImportError:
    n = a = None
ROOT = Path(__file__).resolve().parents[1]


class SealedAbbaProtocolTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(n, 'new sealed C/ABBA admission missing')
        self.assertIsNotNone(a, 'authenticated C archive boundary missing')

    def acceptance(self):
        return dict(canary_head_sha='2'*40, source_sha='1'*40, run_id=21,
                    workflow_id=31, job_id=41, artifact_id=51,
                    artifact_name=n.ARTIFACT, artifact_size_bytes=1234,
                    artifact_sha256='a'*64, root_raw_accepted=True,
                    fresh_raw_review_accepted=True)

    def request(self, mode='canary'):
        return dict(schema=n.REQUEST_SCHEMA, mode=mode,
                    acceptance=None if mode=='canary' else self.acceptance(),
                    request_id=n.ID, repository=n.REPOSITORY, branch=n.BRANCH,
                    workflow_path=n.WORKFLOW, reviewed_source_branch=n.SOURCE_BRANCH,
                    reviewed_source_sha='1'*40, source_closure={p:'0'*64 for p in n.source_paths(ROOT)},
                    source_ci=[dict(event='push',run_id=11),dict(event='pull_request',run_id=12)],
                    budget=copy.deepcopy(n.BUDGET), native_budget=n.native_budget(mode),
                    image_evidence=n.image_evidence(ROOT), official_model_calls=0, ort_sessions=0)

    def test_exact_modes_budgets_and_no_old_canary_acceptance(self):
        self.assertEqual([(True,0)],n.schedule('canary'))
        self.assertEqual([(False,0),(True,0),(True,1),(False,1)],n.schedule('abba'))
        self.assertEqual((1,6,144),(n.native_budget('canary')['providers'],n.native_budget('canary')['capture_pairs'],n.native_budget('canary')['observer_getters']))
        self.assertEqual((4,24,384,10,5),(n.native_budget('abba')['providers'],n.native_budget('abba')['capture_pairs'],n.native_budget('abba')['observer_getters'],n.native_budget('abba')['maps_snapshots'],n.native_budget('abba')['module_origin_snapshots']))
        for mode in ('canary','abba'):
            good=self.request(mode);self.assertEqual(good,n.validate_request(good,ROOT))
            for key,value in [('native_budget',{}),('mode','old06'),('official_model_calls',1),('ort_sessions',True)]:
                bad=copy.deepcopy(good);bad[key]=value
                with self.assertRaises(ValueError):n.validate_request(bad,ROOT)
        for field,value in [('root_raw_accepted',False),('fresh_raw_review_accepted',1),('source_sha','9'*40),('canary_head_sha','1'*40),('artifact_name','engine-clock-sealed-native-20261114-06')]:
            bad=self.request('abba');bad['acceptance'][field]=value
            with self.assertRaises(ValueError):n.validate_request(bad,ROOT)

    def test_activations_are_sole_request_and_direct_parent(self):
        for mode,parent,head,delta in [('canary','1'*40,'2'*40,b'A'),('abba','2'*40,'3'*40,b'M')]:
            request=self.request(mode);changes=delta+b'\0'+n.REQUEST.encode()+b'\0'
            n.validate_activation(request,head,[parent],changes,'100644',n.BRANCH)
            for parents,diff in [(['9'*40],changes),([parent,'9'*40],changes),([parent],changes+b'A\0scripts/injected.py\0'),([parent],b'D\0'+n.REQUEST.encode()+b'\0')]:
                with self.assertRaises(ValueError):n.validate_activation(request,head,parents,diff,'100644',n.BRANCH)

    def test_live_history_rejects_repeated_or_failed_canary(self):
        ctx=dict(repository=n.REPOSITORY,event='push',attempt=1,run_id=22,head_sha='3'*40)
        current=dict(id=22,head_sha='3'*40,head_branch=n.BRANCH,workflow_id=31,path=n.WORKFLOW,event='push',run_attempt=1,status='in_progress',repository=dict(full_name=n.REPOSITORY))
        prior=dict(current,id=21,head_sha='2'*40,status='completed',conclusion='success')
        wf=dict(id=31,path=n.WORKFLOW,state='active')
        history=dict(total_count=2,workflow_runs=[current,prior])
        n.validate_live(self.request('abba'),ctx,current,wf,history)
        for change in [dict(run_attempt=2),dict(conclusion='failure'),dict(head_sha='8'*40)]:
            bad=copy.deepcopy(history);bad['workflow_runs'][1].update(change)
            with self.assertRaises(ValueError):n.validate_live(self.request('abba'),ctx,current,wf,bad)
        bad=copy.deepcopy(history);bad['workflow_runs'].append(prior);bad['total_count']=3
        with self.assertRaises(ValueError):n.validate_live(self.request('abba'),ctx,current,wf,bad)

    def test_identity_difference_keeps_every_field_and_type(self):
        base=dict(installed=dict(host=dict(release='kernel',cpu_flags=['a','b']),engine=dict(docker_server='28'),configuration=dict(env='x',memory=4294967296)),host_details=dict(affinity_ids=[0,1],memory_total_bytes=8*1024**3))
        self.assertEqual([],n.identity_difference(base,copy.deepcopy(base)))
        for change,path in [(lambda b:b['installed']['host'].update(release='other'),'installed.host.release'),(lambda b:b['host_details'].update(affinity_ids=[1,2]),'host_details.affinity_ids'),(lambda b:b['host_details'].update(memory_total_bytes=9*1024**3),'host_details.memory_total_bytes'),(lambda b:b['installed']['configuration'].update(memory=True),'installed.configuration.memory')]:
            bad=copy.deepcopy(base);change(bad)
            self.assertTrue(any(r['path'].startswith(path) for r in n.identity_difference(base,bad)))
        bad=copy.deepcopy(base);bad['extra']=0
        self.assertTrue(n.identity_difference(base,bad))

    def api_proofs(self):
        accepted=self.acceptance()
        run=dict(id=21,head_sha='2'*40,head_branch=n.BRANCH,workflow_id=31,path=n.WORKFLOW,event='push',run_attempt=1,status='completed',conclusion='success',repository=dict(id=7,full_name=n.REPOSITORY))
        jobs=dict(total_count=1,jobs=[dict(id=41,run_id=21,name='campaign',status='completed',conclusion='success',head_sha='2'*40,run_attempt=1)])
        artifact=dict(id=51,name=n.ARTIFACT,expired=False,size_in_bytes=1234,digest='sha256:'+'a'*64,workflow_run=dict(id=21,head_sha='2'*40,head_branch=n.BRANCH,repository_id=7))
        return accepted,run,jobs,artifact

    def test_canary_external_api_identity_is_not_flags_alone(self):
        proof=self.api_proofs();a.validate_accepted_api(*proof,workflow_id=31)
        for index,key,value in [(1,'head_sha','9'*40),(1,'conclusion','failure'),(1,'run_attempt',2),(2,'total_count',2),(3,'digest','sha256:'+'b'*64),(3,'expired',True),(3,'size_in_bytes',1235)]:
            bad=copy.deepcopy(proof);bad[index][key]=value
            with self.assertRaises(ValueError):a.validate_accepted_api(*bad,workflow_id=31)
        bad=copy.deepcopy(proof);bad[2]['jobs'][0]['id']=42
        with self.assertRaises(ValueError):a.validate_accepted_api(*bad,workflow_id=31)

    def test_archive_all_bytes_checked_and_only_data_selected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);archive=root/'original.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('output/case_00/case.json','{}')
                z.writestr('output/case_00/capture_01/raw_road.png',b'png-data')
                z.writestr('docker/copied-python.tar',b'not-executed')
            report=a.audit_archive(archive,root/'selected')
            self.assertEqual(3,report['members']);self.assertEqual(2,report['selected_members'])
            self.assertEqual(b'png-data',(root/'selected/output/case_00/capture_01/raw_road.png').read_bytes())
            self.assertFalse((root/'selected/docker').exists())

    def test_archive_traversal_duplicate_symlink_and_oversize_reject(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for i,names in enumerate([['../escape'],['/absolute'],['output//alias'],['x/../escape'],['output/x','output/x']]):
                archive=root/('bad'+str(i)+'.zip')
                with warnings.catch_warnings(),zipfile.ZipFile(archive,'w') as z:
                    warnings.simplefilter('ignore',UserWarning)
                    for name in names:z.writestr(name,b'x')
                with self.assertRaises(ValueError):a.audit_archive(archive,root/('out'+str(i)))
            archive=root/'link.zip'
            with zipfile.ZipFile(archive,'w') as z:
                info=zipfile.ZipInfo('output/link');info.create_system=3;info.external_attr=0o120777<<16
                z.writestr(info,'/etc/passwd')
            with self.assertRaises(ValueError):a.audit_archive(archive,root/'linkout')
            archive=root/'cap.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('output/a',b'x'*100)
            with self.assertRaises(ValueError):a.audit_archive(archive,root/'capout',total_limit=99)

    def test_transport_uses_bounded_existing_download_api(self):
        accepted,run,jobs,artifact=self.api_proofs()
        request=self.request('abba')
        with tempfile.TemporaryDirectory() as td:
            class Client:
                def get_json(self,endpoint,name):
                    if endpoint=='actions/runs/21':return run
                    if endpoint=='actions/runs/21/jobs?per_page=100':return jobs
                    if endpoint=='actions/artifacts/51':return artifact
                    raise AssertionError(endpoint)
                def download(self,url,path,*,nbytes,sha256,kind):
                    if not(url=='https://api.github.com/repos/'+n.REPOSITORY+'/actions/artifacts/51/zip' and nbytes==1234 and sha256=='a'*64 and kind=='artifact'):
                        raise AssertionError('unbounded or unauthenticated artifact route')
                    Path(path).write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                a.authenticate_canary(Client(),request,dict(workflow_id=31),Path(td))


if __name__=='__main__':unittest.main()
