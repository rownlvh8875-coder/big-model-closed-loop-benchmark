"""Fake HTTP responses only; no network requests or image/package execution."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
import urllib.error
from email.message import Message
try:
 from scripts import engine_clock_image_transport as transport
except ImportError:transport=None
class Response:
 status=200
 def __init__(self,data):self.data=io.BytesIO(data);self.headers={'Content-Length':str(len(data))}
 def __enter__(self):return self
 def __exit__(self,*args):self.data.close()
 def read(self,n):return self.data.read(n)
 def geturl(self):return 'unused-fixture'
class ImageTransportTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(transport,'bounded image input transport missing')
 def client(self,root,opener,**kwargs):return transport.Client(root,repository='owner/repo',token='SECRET_SENTINEL',deadline=time.monotonic()+5,max_requests=10,max_payload_bytes=1024,opener=opener,**kwargs)
 def test_exact_bytes_and_hash_are_kept_once_with_measured_receipt(self):
  calls=[]
  class Opener:
   def open(self,req,timeout):calls.append(req.full_url);return Response(b'owned')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);c=self.client(root,Opener());p=root/'wheel.whl';r=c.download('https://files.pythonhosted.org/packages/owned.whl',p,nbytes=5,sha256=hashlib.sha256(b'owned').hexdigest(),kind='public');self.assertEqual(b'owned',p.read_bytes());self.assertEqual(1,len(calls));self.assertEqual(5,r['nbytes'])
   with self.assertRaises(ValueError):c.download('https://files.pythonhosted.org/packages/owned.whl',p,nbytes=5,sha256=r['sha256'],kind='public')
   self.assertEqual(1,len(calls))
 def test_bad_hash_keeps_partial_and_never_retries(self):
  calls=[]
  class Opener:
   def open(self,req,timeout):calls.append(1);return Response(b'owned')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);c=self.client(root,Opener())
   with self.assertRaisesRegex(ValueError,'^IMAGE_TRANSPORT_REJECTED$'):c.download('https://files.pythonhosted.org/packages/owned.whl',root/'x',nbytes=5,sha256='0'*64,kind='public')
   self.assertEqual(1,len(calls));self.assertEqual(b'owned',(root/'x.partial').read_bytes());self.assertFalse((root/'x').exists())
 def test_artifact_redirect_drops_auth_and_never_persists_signed_query(self):
  calls=[]
  class Opener:
   def open(self,req,timeout):
    calls.append(req)
    if len(calls)==1:
     headers=Message();headers['Location']='https://owned.blob.core.windows.net/artifact?sig=SECRET_SENTINEL'
     raise urllib.error.HTTPError(req.full_url,302,'owned redirect',headers,None)
    return Response(b'owned')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);c=self.client(root,Opener());r=c.download('https://api.github.com/repos/owner/repo/actions/artifacts/1/zip',root/'x',nbytes=5,sha256=hashlib.sha256(b'owned').hexdigest(),kind='artifact')
   self.assertEqual('Bearer SECRET_SENTINEL',calls[0].get_header('Authorization'));self.assertIsNone(calls[1].get_header('Authorization'));self.assertNotIn('SECRET_SENTINEL',json.dumps(r));self.assertNotIn('sig=',json.dumps(r))
 def test_non_https_redirect_and_expired_deadline_stop_before_extra_request(self):
  class Opener:
   def __init__(self):self.calls=0
   def open(self,req,timeout):
    self.calls+=1;headers=Message();headers['Location']='file:///SECRET';raise urllib.error.HTTPError(req.full_url,302,'owned',headers,None)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);opener=Opener();c=self.client(root,opener)
   with self.assertRaisesRegex(ValueError,'^IMAGE_TRANSPORT_REJECTED$'):c.download('https://api.github.com/repos/owner/repo/actions/artifacts/1/zip',root/'x',nbytes=5,sha256='0'*64,kind='artifact')
   self.assertEqual(1,opener.calls);c.deadline=0
   with self.assertRaisesRegex(ValueError,'^IMAGE_TRANSPORT_REJECTED$'):c.get_json('actions/runs/1','run.json')
   self.assertEqual(1,opener.calls)

if __name__=='__main__':unittest.main()
