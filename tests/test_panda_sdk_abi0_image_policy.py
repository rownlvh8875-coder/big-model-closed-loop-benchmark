"""New03 policy with committed DATA and synthetic APIs; no target execution."""
import copy,json,tempfile,unittest
from pathlib import Path
try:from scripts import panda_sdk_abi0_image_policy as a
except ImportError:a=None
class Abi0ImagePolicyTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(a,'new ABI0 image policy required')
 def request(self):return a.request_template('a'*40,[dict(event='push',run_id=101),dict(event='pull_request',run_id=102)],a.ROOT)
 def live(self):
  run=dict(id=201,head_sha='b'*40,head_branch=a.BRANCH,event='push',run_attempt=1,status='completed',conclusion='success',path=a.WORKFLOW,workflow_id=301,repository=dict(full_name=a.REPO,id=a.REPO_ID),head_repository=dict(full_name=a.REPO,id=a.REPO_ID),actor=dict(login=a.OWNER));ctx=dict(repository=a.REPO,head_sha='b'*40,run_id=201,attempt=1,event='push',actor=a.OWNER);return ctx,run,dict(id=301,path=a.WORKFLOW,state='active'),dict(total_count=1,workflow_runs=[run])
 def jobs(self,run):return dict(total_count=1,jobs=[dict(id=401,run_id=run['id'],run_attempt=1,head_sha=run['head_sha'],head_branch=a.BRANCH,name='produce',status='completed',conclusion='success')])
 def test_new_request_rejects_old_sdk_request_and_privilege_drift(self):
  r=self.request();a.validate_request(r,a.ROOT)
  from scripts import panda_sdk_image_auth as old
  with self.assertRaises(ValueError):a.validate_request(old.request_template('a'*40,r['source_ci'],a.ROOT),a.ROOT)
  for k,v in [('sdk_sha256',old.SDK_SHA),('sdk_nbytes',old.SDK_SIZE),('branch',old.BRANCH),('permissions',dict(native=True)),('source_ci',[dict(event='push',run_id=True),dict(event='pull_request',run_id=102)])]:
   with self.subTest(k=k),self.assertRaises(ValueError):a.validate_request(dict(r,**{k:v}),a.ROOT)
  r['source_closure'][a.SDK]='0'*64
  with self.assertRaises(ValueError):a.validate_request(r,a.ROOT)
 def test_real_prerequisite_pins_and_provider_profile_reject_tampering(self):
  p=a.prerequisite(a.ROOT);self.assertEqual(p['candidate_sha256'],a.SDK_SHA);self.assertEqual(len(p['root_symbol_availability']['provider_records']),21)
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);q=root/a.HANDOFF;q.parent.mkdir(parents=True);q.write_bytes((a.ROOT/a.HANDOFF).read_bytes()+b'\n')
   with self.assertRaisesRegex(ValueError,'handoff pin'):a.prerequisite(root)
 def test_request_only_activation_single_parent_and_regular_mode(self):
  r=self.request();head='b'*40;commit=dict(sha=head,parents=[dict(sha=r['source_sha'])]);delta=dict(status='ahead',ahead_by=1,total_commits=1,commits=[dict(sha=head)],files=[dict(filename=a.REQUEST,status='added',sha='c'*40)]);a.validate_activation(r,head,commit,delta,'100644')
  for d,mode in [(dict(delta,files=delta['files']+[dict(filename='other',status='added')]),'100644'),(delta,'120000'),(dict(delta,ahead_by=2),'100644')]:
   with self.assertRaises(ValueError):a.validate_activation(r,head,commit,d,mode)
 def test_source_ci_requires_exact_pair_jobs_attempt_and_no_artifacts(self):
  r=self.request();proof=[]
  for row in r['source_ci']:
   rid=row['run_id'];proof.append(dict(run=dict(id=rid,head_sha=r['source_sha'],head_branch=a.SOURCE_BRANCH,event=row['event'],path='.github/workflows/ci.yml',workflow_id=411705464,run_attempt=1,status='completed',conclusion='success',repository=dict(full_name=a.REPO)),jobs=dict(total_count=2,jobs=[dict(name=n,run_id=rid,status='completed',conclusion='success') for n in ('synthetic-unit','onnx-interface-test')]),artifacts=dict(total_count=0,artifacts=[])))
  a.validate_ci(r,proof)
  for key,value in [('run_attempt',2),('head_branch','feature/panda-sdk-image-auth-v1')]:
   bad=copy.deepcopy(proof);bad[0]['run'][key]=value
   with self.assertRaises(ValueError):a.validate_ci(r,bad)
 def test_producer_run_is_new_branch_workflow_and_unique_attempt(self):
  ctx,run,w,listing=self.live();r=self.request();a.validate_run(r,ctx,run,w,listing,completed=True)
  for k,v in [('head_branch','prepare/panda-sdk-image-20261115-02'),('run_attempt',2),('event','workflow_dispatch'),('actor',dict(login='foreign'))]:
   with self.assertRaises(ValueError):a.validate_run(r,ctx,dict(run,**{k:v}),w,listing,completed=True)
  with self.assertRaises(ValueError):a.validate_run(r,ctx,run,w,dict(total_count=2,workflow_runs=[run,run]),completed=True)
 def test_exact_production_job_required_with_strict_types(self):
  _,run,_,_=self.live();jobs=self.jobs(run);self.assertEqual(a.validate_production_job(run,jobs),401)
  for k,v in [('id',True),('run_id',202),('run_attempt',True),('head_sha','c'*40),('head_branch','main'),('name','other'),('conclusion','failure'),('status','in_progress')]:
   bad=copy.deepcopy(jobs);bad['jobs'][0][k]=v
   with self.subTest(k=k),self.assertRaises(ValueError):a.validate_production_job(run,bad)
  for bad in [dict(total_count=True,jobs=jobs['jobs']),dict(total_count=2,jobs=jobs['jobs']*2),dict(total_count=0,jobs=[])]:
   with self.assertRaises(ValueError):a.validate_production_job(run,bad)
 def test_inventory_changes_only_sdk_and_preserves_all_providers(self):
  m=a.expected_inventory(a.ROOT);old=json.loads((a.ROOT/a.INVENTORY).read_text());self.assertEqual(len(m['entries']),44232);changes=[(x,y) for x,y in zip(old['entries'],m['entries']) if x!=y];self.assertEqual(len(changes),1);self.assertEqual(changes[0][1]['sha256'],a.SDK_SHA);self.assertEqual(changes[0][1]['nbytes'],992200);rows={r['path']:r for r in m['entries']}
  for path,v in a.prerequisite(a.ROOT)['root_symbol_availability']['provider_records'].items():self.assertEqual((rows[path]['sha256'],rows[path]['nbytes'],rows[path]['mode']),(v['sha256'],v['nbytes'],v['image_mode']))
 def test_workflow_has_unique_filter_pinned_actions_and_no_start_or_dispatch(self):
  s=(a.ROOT/a.WORKFLOW).read_text();self.assertIn("branches: ['"+a.BRANCH+"']",s);self.assertIn('scripts/produce_panda_sdk_abi0_image.py --run',s);self.assertIn('persist-credentials: false',s);self.assertNotIn('workflow_dispatch',s);self.assertNotIn('docker run',s);self.assertNotIn('id-token: write',s)
if __name__=='__main__':unittest.main()
