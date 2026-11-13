"""Owned complete-payload fixtures and fake API only; no external operations."""
import hashlib,json,tempfile,time,unittest,zipfile
from pathlib import Path
from unittest.mock import Mock
from scripts import engine_clock_image_staging_v3 as s

class CompletePayloadTests(unittest.TestCase):
 def fixture(self,root):
  p=root/'bundle.zip';raw=b'owned data'
  with zipfile.ZipFile(p,'w') as z:z.writestr('context/debs/owned.deb',raw);z.writestr('result.json','{}')
  sha=hashlib.sha256(raw).hexdigest();descriptor={'members':[{'path':'context/debs/owned.deb','nbytes':len(raw),'sha256':sha}],'member_count':1,'member_bytes':len(raw),'artifact_zip_nbytes':p.stat().st_size,'artifact_zip_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  return p,descriptor,{'context/debs/owned.deb':{'nbytes':len(raw),'sha256':sha}}
 def test_whole_carrier_and_selected_registered_bytes_are_verified(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p,d,e=self.fixture(root);work=root/'work';work.mkdir();r=s.copy_bundle(p,work,d,e,deadline=time.perf_counter()+10)
   self.assertEqual(1,r['member_count']);self.assertEqual(b'owned data',(work/'context/debs/owned.deb').read_bytes());self.assertFalse((work/'result.json').exists())
 def test_wrong_carrier_or_registered_member_hash_rejects(self):
  for carrier in (True,False):
   with self.subTest(carrier=carrier),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);p,d,e=self.fixture(root);work=root/'work';work.mkdir()
    if carrier:d['artifact_zip_sha256']='0'*64
    else:
     d['members'][0]['sha256']='0'*64;e['context/debs/owned.deb']['sha256']='0'*64
    with self.assertRaisesRegex(ValueError,'^IMAGE_PAYLOADS_REJECTED$'):s.copy_bundle(p,work,d,e,deadline=time.perf_counter()+10)
 def test_source_pins_close_all249_real_registered_payloads(self):
  from scripts import engine_clock_image_preparation_v3 as p
  root=Path(__file__).resolve().parent.parent;d=json.loads((root/s.PAYLOAD_LOCK).read_bytes());full=json.loads((root/p.INPUT_PATH).read_bytes());renderer=json.loads((root/p.RENDERER_PATH).read_bytes());expected=s.expected_payloads(full,renderer)
  self.assertEqual(s.PAYLOAD_SHA,hashlib.sha256((root/s.PAYLOAD_LOCK).read_bytes()).hexdigest());self.assertEqual(249,len(expected));self.assertEqual(712506101,sum(r['nbytes'] for r in expected.values()))
  self.assertEqual({r['path']:{'nbytes':r['nbytes'],'sha256':r['sha256']} for r in d['members']},expected)
 def test_complete_failed_run_api_bindings_precede_one_download(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);d={'run_id':11,'workflow_id':22,'activation_sha':'1'*40,'branch':'old/failed','workflow_path':'.github/workflows/old.yml','run_conclusion':'failure','repository':'owner/repo','job_name':'prepare','artifact_id':33,'artifact_name':'payload','artifact_zip_nbytes':100,'artifact_zip_sha256':'2'*64}
   run={'id':11,'head_sha':'1'*40,'head_branch':d['branch'],'event':'push','run_attempt':1,'workflow_id':22,'path':d['workflow_path'],'status':'completed','conclusion':'failure','repository':{'full_name':'owner/repo'}}
   jobs={'total_count':1,'jobs':[{'run_id':11,'name':'prepare','status':'completed','conclusion':'failure'}]};unique={'total_count':1,'workflow_runs':[{'id':11,'head_sha':'1'*40,'run_attempt':1}]};art={'id':33,'name':'payload','expired':False,'workflow_run':{'id':11,'head_sha':'1'*40},'digest':'sha256:'+'2'*64,'size_in_bytes':100}
   client=Mock();client.get_json.side_effect=[run,jobs,unique,art]
   path=s.acquire_bundle(client,root,d);self.assertEqual(root/'retained-original-execution.zip',path);client.download.assert_called_once()
   client.reset_mock();art['digest']='sha256:'+'3'*64;client.get_json.side_effect=[run,jobs,unique,art]
   with self.assertRaisesRegex(ValueError,'^IMAGE_PAYLOADS_REJECTED$'):s.acquire_bundle(client,root,d)
   client.download.assert_not_called()
if __name__=='__main__':unittest.main()
