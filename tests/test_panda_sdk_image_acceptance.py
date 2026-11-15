"""Closed receipt/ZIP fixtures; dictionaries never authenticate remote origin."""
import copy,json,os,tempfile,unittest,zipfile
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

class ReviewRegressionTests(unittest.TestCase):
 def test_full_offline_consumer_reaches_download_with_distinct_evidence(self):
  import base64,hashlib,io,urllib.parse
  from unittest.mock import patch
  from scripts.engine_clock_image_transport import Client
  from tests.test_panda_sdk_image_auth import SourceImagePolicyTests
  r=c.a.request_template('a'*40,[dict(event='push',run_id=101),dict(event='pull_request',run_id=102)],c.a.ROOT);raw=json.dumps(r).encode();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();ctx,run,workflow,listing=SourceImagePolicyTests().live(True)
  commit=dict(sha='b'*40,parents=[dict(sha='a'*40)],commit=dict(tree=dict(sha='1'*40)))
  delta=dict(status='ahead',ahead_by=1,total_commits=1,commits=[dict(sha='b'*40)],files=[dict(filename=c.a.REQUEST,status='added',sha=blob)])
  trees={'1'*40:[dict(path='docs',type='tree',mode='040000',sha='2'*40)],'2'*40:[dict(path='requests',type='tree',mode='040000',sha='3'*40)],'3'*40:[dict(path=Path(c.a.REQUEST).name,type='blob',mode='100644',sha=blob)]}
  class Response(io.BytesIO):
   status=200;headers={}
  class MemoryOpener:
   def open(self,req,timeout):
    path=urllib.parse.urlsplit(req.full_url).path.split('/'+c.a.REPO+'/',1)[1]
    if path.startswith('commits/'):v=commit
    elif path.startswith('compare/'):v=delta
    elif path.startswith('git/trees/'):v=dict(tree=trees[path.rsplit('/',1)[1]])
    elif path.startswith('git/blobs/'):v=dict(encoding='base64',size=len(raw),content=base64.b64encode(raw).decode())
    elif path.startswith('actions/workflows/'):
     v=listing if path.endswith('/runs') else workflow
    elif path.startswith('actions/runs/'):
     parts=path.split('/');rid=int(parts[2]);suffix=parts[3] if len(parts)>3 else ''
     if rid==201:
      if not suffix:v=run
      else:v=dict(total_count=2,artifacts=[dict(id=400+i,name=n,digest='sha256:'+'e'*64,size_in_bytes=100,expired=False,workflow_run=dict(id=201,head_sha='b'*40,head_branch=c.a.BRANCH,repository_id=c.a.REPO_ID,head_repository_id=c.a.REPO_ID)) for i,n in enumerate((c.a.ARTIFACT,c.a.ARTIFACT+'-execution'))])
     elif suffix=='jobs':v=dict(total_count=2,jobs=[dict(name=n,run_id=rid,status='completed',conclusion='success') for n in ('synthetic-unit','onnx-interface-test')])
     elif suffix=='artifacts':v=dict(total_count=0,artifacts=[])
     else:v=dict(id=rid,head_sha='a'*40,head_branch=c.a.SOURCE_BRANCH,event='push' if rid==101 else 'pull_request',path='.github/workflows/ci.yml',workflow_id=411705464,run_attempt=1,status='completed',conclusion='success',repository=dict(full_name=c.a.REPO))
    else:raise AssertionError(path)
    return Response(json.dumps(v).encode())
  class DownloadGate(Exception):pass
  def client(*args,**kw):return Client(*args,**kw,opener=MemoryOpener())
  with tempfile.TemporaryDirectory() as t,patch.object(c,'Client',side_effect=client),patch.object(Client,'download',side_effect=DownloadGate),patch.dict(os.environ,{'GH_TOKEN':'synthetic-cpu-token'}):
   out=Path(t)/'new'
   with self.assertRaises(DownloadGate):c.accept_image('a'*40,'b'*40,201,out)
   self.assertFalse(json.loads((out/'acceptance.json').read_text())['actions_output_origin_authenticated'])
 def test_many_zip_entries_reject_before_stdlib_directory_allocation(self):
  from unittest.mock import patch
  calls=[];original=zipfile.ZipFile._RealGetContents
  def counted(z):calls.append(True);return original(z)
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);z=root/'many.zip'
   with zipfile.ZipFile(z,'w') as f:
    for i in range(10000):f.writestr(str(i),b'')
   with patch.object(zipfile.ZipFile,'_RealGetContents',counted),self.assertRaises(ValueError):c.extract_carrier(z,root/'bad')
   self.assertEqual(calls,[])
 def test_bad_metadata_and_unsupported_decoder_reject_before_zip_parse(self):
  from unittest.mock import patch
  for case in ('extra','comment','bzip2'):
   with self.subTest(case=case),tempfile.TemporaryDirectory() as t:
    root=Path(t);z=root/'bad.zip'
    with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_BZIP2 if case=='bzip2' else zipfile.ZIP_STORED) as f:
     for n in ('image.tar','preparation.json','installed-files.json'):f.writestr(n,b'CPU')
     if case=='comment':f.comment=b'x'*60000
    if case=='extra':
     with zipfile.ZipFile(z,'a') as f:
      x=zipfile.ZipInfo('unexpected');x.extra=b'\xff\xff'+(50000).to_bytes(2,'little')+b'x'*50000;f.writestr(x,b'CPU')
    calls=[];original=zipfile.ZipFile._RealGetContents
    def counted(f):calls.append(True);return original(f)
    with patch.object(zipfile.ZipFile,'_RealGetContents',counted),self.assertRaises(ValueError):c.extract_carrier(z,root/'out')
    self.assertEqual(calls,[])
 def test_extraction_absolute_deadline_interrupts_parser(self):
  import time
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);z=root/'good.zip'
   with zipfile.ZipFile(z,'w') as f:
    for n in ('image.tar','preparation.json','installed-files.json'):f.writestr(n,b'CPU')
   started=time.monotonic()
   with patch.object(zipfile.ZipFile,'_RealGetContents',side_effect=lambda _:time.sleep(1)),self.assertRaises(ValueError):c.extract_carrier(z,root/'late',deadline=time.monotonic()+.05)
   self.assertLess(time.monotonic()-started,.8)
 def test_valid_zip64_and_crc_rejection(self):
  import struct
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);z=root/'good.zip'
   with zipfile.ZipFile(z,'w') as f:
    for n in ('image.tar','preparation.json','installed-files.json'):f.writestr(n,b'CPU')
   raw=z.read_bytes();off=raw.rfind(b'PK\x05\x06');e=struct.unpack('<4s4H2LH',raw[off:]);record=struct.pack('<4sQ2H2L4Q',b'PK\x06\x06',44,45,45,0,0,3,3,e[5],e[6]);loc=struct.pack('<4sLQL',b'PK\x06\x07',0,off,1);end=struct.pack('<4s4H2LH',b'PK\x05\x06',0,0,65535,65535,0xffffffff,0xffffffff,0);z.write_bytes(raw[:off]+record+loc+end);c.extract_carrier(z,root/'valid64')
   raw=bytearray(raw);pos=30+len('image.tar');raw[pos]^=1;z.write_bytes(raw)
   with self.assertRaises(ValueError):c.extract_carrier(z,root/'crc')
