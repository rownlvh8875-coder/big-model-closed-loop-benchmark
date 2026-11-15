"""Closed receipt/ZIP fixtures; dictionaries never authenticate remote origin."""
import copy,json,tempfile,unittest,zipfile
from pathlib import Path
try:from scripts import accept_panda_sdk_image as c
except ImportError:c=None
class AcceptanceBoundaryTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(c,'authenticated image consumer missing')
 def receipt(self):
  return dict(schema='panda-sdk-actions-image-production-v1',status='COPY_ONLY_SDK_IMAGE_BYTES_VERIFIED_NATIVE_BLOCKED',request_id=c.a.ID,source_sha='a'*40,activation_sha='b'*40,run_id=200,request_sha256='c'*64,sdk_sha256=c.a.SDK_SHA,sdk_nbytes=c.a.SDK_SIZE,containers_started=0,new_native_runs=0,official_model_calls=0,native_admitted=False,stage7_complete=False,installed_entries=44232,installed_manifest_sha256='d'*64,owned_stopped_container_removed=True,archive=dict(image_tar_sha256='e'*64,image_tar_nbytes=100,config_digest='sha256:'+'f'*64))
 def test_receipt_cannot_promote_metadata_into_external_or_native_authority(self):
  r=self.receipt();v=c.validate_receipt(r,'a'*40,'b'*40,200,'c'*64,'d'*64);self.assertFalse(v['external_origin_authenticated']);self.assertFalse(v['native_admitted'])
  for k,v in [('native_admitted',True),('containers_started',True),('run_id',201),('source_sha','e'*40),('sdk_sha256','0'*64),('status','READY'),('owned_stopped_container_removed',False)]:
   with self.subTest(k=k),self.assertRaises(ValueError):c.validate_receipt(dict(r,**{k:v}),'a'*40,'b'*40,200,'c'*64,'d'*64)
 def test_closed_bundle_crc_members_paths_and_existing_output_preserve(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);z=p/'carrier.zip'
   with zipfile.ZipFile(z,'w') as f:
    for n,v in [('image.tar',b'CPU data only'),('preparation.json',b'{}'),('installed-files.json',b'{}')]:f.writestr(n,v)
   c.extract_carrier(z,p/'good');self.assertEqual((p/'good/image.tar').read_bytes(),b'CPU data only')
   with self.assertRaises(ValueError):c.extract_carrier(z,p/'good')
   with zipfile.ZipFile(z,'a') as f:f.writestr('../outside',b'CPU')
   with self.assertRaises(ValueError):c.extract_carrier(z,p/'bad')
 def test_existing_acceptance_output_rejects_before_network(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t);(out/'keep').write_bytes(b'previous')
   with self.assertRaises(ValueError):c.accept_image('a'*40,'b'*40,200,out)
   self.assertEqual((out/'keep').read_bytes(),b'previous')
if __name__=='__main__':unittest.main()
