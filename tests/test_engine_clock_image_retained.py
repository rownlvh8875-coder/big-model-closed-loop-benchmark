"""Owned archives and fake API errors only; no network, Docker or payload execution."""
import hashlib,json,tempfile,time,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
try:from scripts import engine_clock_image_staging_v2 as v
except ImportError:v=None
class RetainedTests(unittest.TestCase):
 def test_closed_registered_members_are_copied_and_changed_member_rejects(self):
  self.assertIsNotNone(v)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);z=root/'owned.zip';data=b'owned deb bytes';sha=hashlib.sha256(data).hexdigest()
   row={'filename':'owned.deb','member':'context/debs/owned.deb','nbytes':len(data),'sha256':sha};descriptor={'members':[row],'member_count':1,'member_bytes':len(data)}
   packages=[{'filename':'pool/main/owned.deb','nbytes':len(data),'sha256':sha}]
   with zipfile.ZipFile(z,'w') as out:out.writestr(row['member'],data);out.writestr('result.json','{"fixture":true}')
   dest=root/'good';dest.mkdir();r=v.extract_retained_debs(z,dest,descriptor,packages);self.assertEqual(data,(dest/'owned.deb').read_bytes());self.assertEqual(1,r['member_count'])
   with zipfile.ZipFile(z,'w') as out:out.writestr(row['member'],b'substituted')
   dest=root/'bad';dest.mkdir()
   with self.assertRaisesRegex(ValueError,'^IMAGE_RETAINED_INPUTS_REJECTED$'):v.extract_retained_debs(z,dest,descriptor,packages)
 def test_duplicate_traversal_or_unregistered_selected_filename_rejects(self):
  self.assertIsNotNone(v)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);z=root/'owned.zip';row={'filename':'owned.deb','member':'../owned.deb','nbytes':1,'sha256':hashlib.sha256(b'x').hexdigest()}
   with zipfile.ZipFile(z,'w') as out:out.writestr('../owned.deb',b'x')
   dest=root/'dest';dest.mkdir()
   with self.assertRaisesRegex(ValueError,'^IMAGE_RETAINED_INPUTS_REJECTED$'):v.extract_retained_debs(z,dest,{'members':[row],'member_count':1,'member_bytes':1},[{'filename':'pool/owned.deb','nbytes':1,'sha256':row['sha256']}])
 def test_failure_status_public_url_and_partial_facts_persist_without_secret_text(self):
  self.assertIsNotNone(v)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);c=v.RetainedClient(root,repository='owner/repo',token='SECRET_SENTINEL',deadline=time.monotonic()+10)
   def fail(*args,**kw):c.errors.append({'stage':'payload','http_status':503});raise ValueError('SECRET_SENTINEL proxy-password')
   with patch.object(v.transport.Client,'download',side_effect=fail):
    with self.assertRaises(ValueError):c.download('https://files.pythonhosted.org/owned?sig=SECRET_QUERY',root/'payload',nbytes=1,sha256='0'*64,kind='public')
   raw=(root/'failure-events.jsonl').read_bytes();self.assertNotIn(b'SECRET',raw);self.assertNotIn(b'proxy-password',raw);row=json.loads(raw);self.assertEqual(503,row['http_status']);self.assertEqual('https://files.pythonhosted.org/owned',row['public_url'])
 def test_wrong_old_run_attempt_rejects_before_any_artifact_download(self):
  self.assertIsNotNone(v)
  from unittest.mock import Mock
  descriptor={'run_id':11,'activation_sha':'1'*40,'workflow_id':22,'branch':'old/consumed','workflow_path':'.github/workflows/old.yml','run_conclusion':'failure','repository':'owner/repo','job_name':'prepare'}
  client=Mock();client.get_json.return_value={'id':11,'head_sha':'1'*40,'head_branch':'old/consumed','event':'push','run_attempt':2,'workflow_id':22,'path':'.github/workflows/old.yml','status':'completed','conclusion':'failure','repository':{'full_name':'owner/repo'}}
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaisesRegex(ValueError,'^IMAGE_STAGING_REJECTED$'):v.download_retained_debs(client,Path(tmp),Path(tmp),descriptor,[])
  client.download.assert_not_called()
 def test_v2_controller_changes_only_registration_and_retained_client_wiring(self):
  import ast
  from scripts import engine_clock_image_preparation_v2 as p
  root=Path(__file__).resolve().parent.parent
  old=ast.parse((root/'scripts/engine_clock_image_preparation.py').read_text());new=ast.parse((root/'scripts/engine_clock_image_preparation_v2.py').read_text())
  old_functions={n.name:ast.dump(n,include_attributes=False) for n in old.body if isinstance(n,ast.FunctionDef)}
  new_functions={n.name:ast.dump(n,include_attributes=False) for n in new.body if isinstance(n,ast.FunctionDef)}
  self.assertEqual(set(old_functions),set(new_functions))
  for name in old_functions:
   if name!='run_operation':self.assertEqual(old_functions[name],new_functions[name],name)
  self.assertEqual(p.BUDGETS['prepare']['download_seconds'],900);self.assertEqual(p.BUDGETS['prepare']['docker_builds'],1);self.assertFalse(p.PERMISSIONS['prepare']['native_engine'])
 def test_v2_identity_and_real_retained_lock_are_explicit(self):
  self.assertIsNotNone(v)
  from scripts import engine_clock_image_preparation_v2 as p
  self.assertEqual('image-20261114-02',p.ROLES['prepare']['request_id']);self.assertEqual('prepare/engine-clock-sealed-image-v2',p.SOURCE_BRANCH)
  lock=Path(__file__).resolve().parent.parent/v.RETAINED_LOCK;raw=lock.read_bytes();self.assertEqual(v.RETAINED_SHA,hashlib.sha256(raw).hexdigest());value=json.loads(raw);self.assertEqual(166,value['member_count']);self.assertEqual(74460858,value['member_bytes'])
if __name__=='__main__':unittest.main()
