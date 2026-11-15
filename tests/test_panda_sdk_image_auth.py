"""Synthetic API metadata and committed DATA inputs; no Docker/native calls."""
import copy,json,tempfile,unittest
from pathlib import Path
try:from scripts import panda_sdk_image_auth as a
except ImportError:a=None
class SourceImagePolicyTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(a,'source-bound image policy missing')
 def request(self):return a.request_template('a'*40,[dict(event='push',run_id=101),dict(event='pull_request',run_id=102)],a.ROOT)
 def test_request_closes_inputs_permissions_types_and_real_source_hashes(self):
  r=self.request();a.validate_request(r,a.ROOT)
  for key,value in [('sdk_sha256','0'*64),('branch','main'),('permissions',dict(native=True)),('source_ci',[dict(event='push',run_id=True),dict(event='pull_request',run_id=102)]),('budget',dict(total_seconds=True))]:
   with self.subTest(key=key),self.assertRaises(ValueError):a.validate_request(dict(r,**{key:value}),a.ROOT)
  bad=copy.deepcopy(r);bad['source_closure'][next(iter(bad['source_closure']))]='0'*64
  with self.assertRaises(ValueError):a.validate_request(bad,a.ROOT)
 def test_activation_only_new_regular_request_single_parent(self):
  r=self.request();head='b'*40;c=dict(sha=head,parents=[dict(sha=r['source_sha'])]);delta=dict(status='ahead',ahead_by=1,total_commits=1,commits=[dict(sha=head)],files=[dict(filename=a.REQUEST,status='added',sha='c'*40)])
  a.validate_activation(r,head,c,delta,'100644')
  for change,mode in [(dict(delta,files=delta['files']+[dict(filename='extra',status='added')]),'100644'),(delta,'120000'),(dict(delta,ahead_by=2),'100644')]:
   with self.assertRaises(ValueError):a.validate_activation(r,head,c,change,mode)
 def live(self,completed=False):
  ctx=dict(repository=a.REPO,head_sha='b'*40,run_id=201,attempt=1,event='push',actor=a.OWNER)
  run=dict(id=201,head_sha='b'*40,head_branch=a.BRANCH,event='push',run_attempt=1,status='completed' if completed else 'in_progress',conclusion='success' if completed else None,path=a.WORKFLOW,workflow_id=301,repository=dict(full_name=a.REPO,id=a.REPO_ID),head_repository=dict(full_name=a.REPO,id=a.REPO_ID),actor=dict(login=a.OWNER))
  return ctx,run,dict(id=301,path=a.WORKFLOW,state='active'),dict(total_count=1,workflow_runs=[run])
 def test_live_replay_foreign_owner_workflow_or_ambiguous_run_reject(self):
  r=self.request();ctx,run,w,l=self.live();a.validate_run(r,ctx,run,w,l)
  for key,value in [('run_attempt',2),('head_branch','main'),('head_sha','d'*40),('event','workflow_dispatch'),('actor',dict(login='foreign'))]:
   with self.subTest(key=key),self.assertRaises(ValueError):a.validate_run(r,ctx,dict(run,**{key:value}),w,l)
  with self.assertRaises(ValueError):a.validate_run(r,ctx,run,w,dict(total_count=2,workflow_runs=[run,run]))
 def test_exact_two_ci_runs_jobs_attempt_and_no_artifacts(self):
  r=self.request();proof=[]
  for x in r['source_ci']:
   rid=x['run_id'];proof.append(dict(run=dict(id=rid,head_sha=r['source_sha'],head_branch=a.SOURCE_BRANCH,event=x['event'],path='.github/workflows/ci.yml',workflow_id=411705464,run_attempt=1,status='completed',conclusion='success',repository=dict(full_name=a.REPO)),jobs=dict(total_count=2,jobs=[dict(name=n,run_id=rid,status='completed',conclusion='success') for n in ('synthetic-unit','onnx-interface-test')]),artifacts=dict(total_count=0,artifacts=[])))
  a.validate_ci(r,proof);bad=copy.deepcopy(proof);bad[0]['artifacts']=dict(total_count=1,artifacts=[{}])
  with self.assertRaises(ValueError):a.validate_ci(r,bad)
  with self.assertRaises(ValueError):a.validate_ci(r,proof*2)
 def test_artifacts_bind_zip_digest_run_and_no_foreign_or_expired(self):
  _,run,_,_=self.live(True);rows=[]
  for i,n in enumerate((a.ARTIFACT,a.ARTIFACT+'-execution')):rows.append(dict(id=400+i,name=n,digest='sha256:'+'e'*64,size_in_bytes=100,expired=False,workflow_run=dict(id=run['id'],head_sha=run['head_sha'],head_branch=a.BRANCH,repository_id=a.REPO_ID,head_repository_id=a.REPO_ID)))
  listing=dict(total_count=2,artifacts=rows);self.assertEqual(len(a.validate_artifacts(run,listing)),2)
  for key,value in [('expired',True),('digest',None),('size_in_bytes',True),('name','foreign')]:
   bad=copy.deepcopy(listing);bad['artifacts'][0][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):a.validate_artifacts(run,bad)
 def test_real_expected_inventory_replaces_only_sdk_and_keeps_scope(self):
  m=a.expected_inventory(a.ROOT);old=json.loads((a.ROOT/a.INVENTORY).read_text());changes=[(x,y) for x,y in zip(old['entries'],m['entries']) if x!=y];self.assertEqual(len(m['entries']),44232);self.assertEqual(len(changes),1);self.assertEqual(changes[0][1]['sha256'],a.SDK_SHA);self.assertEqual(m['roots'],old['roots'])
 def test_duplicate_json_fields_cannot_override_closed_policy(self):
  with self.assertRaises(ValueError):a.parse(b'{"native":false,"native":true}')
if __name__=='__main__':unittest.main()
