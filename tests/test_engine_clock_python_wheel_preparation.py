"""Local context/command/provenance fixtures; never resolve or download packages."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
try:
 from scripts import engine_clock_python_wheel_preparation as b
except ImportError:b=None
ROOT=Path(__file__).resolve().parent.parent

class WheelPreparationTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(b,'one-use wheel closure operator missing')
 def request(self):
  cis=[]
  for rid,event in ((111,'push'),(112,'pull_request')):
   cis.append({'run_id':rid,'event':event,'proofs':{kind:{'path':b.PREFLIGHT+'/source-'+str(rid)+'-'+kind+'.json','nbytes':2,'sha256':'0'*64} for kind in ('run','jobs','artifacts')}})
  return {'schema':'python-wheel-closure-request-v1','request_id':b.REQUEST_ID,'repository':b.REPOSITORY,'branch':b.BRANCH,'reviewed_source_branch':b.SOURCE_BRANCH,'reviewed_source_sha':'1'*40,
          'output_directory':b.OUTPUT,'tool':b.TOOL,'target':b.TARGET,'budget':b.BUDGET,'permissions':b.PERMISSIONS,
          'root_requirements':b.expected_roots(ROOT),'local_inputs':b.LOCAL_INPUTS,'source_closure':{p:'0'*64 for p in b.CLOSURE},'source_ci':cis}
 def test_closed_request_caps_permissions_and_local_pin_binding(self):
  req=self.request();self.assertEqual(req,b.validate_request(req,ROOT))
  for key,bad in [('request_id','python-lock-20261113-01'),('extra','SECRET'),('budget',{**b.BUDGET,'pip_downloads':2}),('permissions',{**b.PERMISSIONS,'source_execution':True}),('local_inputs',[]),('source_closure',{})]:
   r=copy.deepcopy(req);r[key]=bad
   with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):b.validate_request(r,ROOT)
  r=copy.deepcopy(req);r['source_ci'][0]['proofs']['run']['path']='../SECRET'
  with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):b.validate_request(r,ROOT)
 def test_exact_request_only_sole_parent_activation(self):
  req=self.request();b.validate_activation(req,'2'*40,['1'*40],b'A\0'+b.REQUEST_PATH.encode()+b'\0','100644')
  for parent,changes,mode in [(['3'*40],b'A\0'+b.REQUEST_PATH.encode()+b'\0','100644'),(['1'*40,'3'*40],b'A\0'+b.REQUEST_PATH.encode()+b'\0','100644'),(['1'*40],b'M\0SECRET\0','100644'),(['1'*40],b'A\0'+b.REQUEST_PATH.encode()+b'\0','120000')]:
   with self.assertRaisesRegex(ValueError,'^INVALID_ACTIVATION$'):b.validate_activation(req,'2'*40,parent,changes,mode)
 def ci(self,req):
  result=[]
  for row in req['source_ci']:
   rid=row['run_id'];result.append({'run':{'id':rid,'head_sha':req['reviewed_source_sha'],'head_branch':b.SOURCE_BRANCH,'event':row['event'],'path':'.github/workflows/ci.yml','run_attempt':1,'status':'completed','conclusion':'success','repository':{'full_name':b.REPOSITORY}},
    'jobs':{'total_count':2,'jobs':[{'run_id':rid,'name':name,'status':'completed','conclusion':'success'} for name in ('synthetic-unit','onnx-interface-test')]},'artifacts':{'total_count':0,'artifacts':[]}})
  return result
 def test_actual_ci_semantics_not_only_digest_syntax(self):
  req=self.request();proofs=self.ci(req);b.validate_ci(req,proofs)
  for object_name,key,bad in [('run','head_sha','3'*40),('run','run_attempt',2),('run','run_attempt',True),('run','conclusion','failure'),('artifacts','total_count',1)]:
   v=copy.deepcopy(proofs);v[0][object_name][key]=bad
   with self.assertRaisesRegex(ValueError,'^INVALID_SOURCE_CI$'):b.validate_ci(req,v)
 def test_only_binary_download_exact_target_roots_and_public_index(self):
  req=self.request();cmd=b.pip_argv(ROOT,req,Path('/tmp/owned-fixture'))
  self.assertIn('download',cmd);self.assertNotIn('install',cmd);self.assertIn('--only-binary=:all:',cmd);self.assertIn('--no-cache-dir',cmd);self.assertIn('3.11.18',cmd);self.assertIn('https://pypi.org/simple',cmd);self.assertIn('onnxruntime>=1.19',cmd)
  self.assertEqual(1,cmd.count('download'));self.assertNotIn('--no-deps',cmd)
  for row in b.LOCAL_INPUTS:self.assertIn(str(ROOT/row['path']),cmd)
 def test_prior_genuine_inputs_authenticate_without_new_execution(self):
  facts=b.validate_input_provenance(ROOT);self.assertEqual({'metadrive-headless','progressbar'},set(facts));self.assertEqual('6d700c40ef5826211c7fa03701fc0bd9131a93f40e170963cff507c622ee3dd1',facts['progressbar']['sha256'])
 def test_tree_meter_never_follows_links(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'plain').write_bytes(b'abc');self.assertEqual(3,b._tree_bytes(root));(root/'link').symlink_to('/SECRET_SENTINEL')
   with self.assertRaisesRegex(ValueError,'^UNSAFE_OPERATION_TREE$'):b._tree_bytes(root)
 def test_publisher_transport_fixture_retains_exact_bytes_without_network(self):
  raw=b'{"info":{"name":"sample","version":"1"},"urls":[]}'
  class Response:
   status=200
   def __init__(self):self.data=raw
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def geturl(self):return 'https://pypi.org/pypi/sample/1/json'
   def read(self,n):data=self.data[:n];self.data=self.data[n:];return data
  class Opener:
   def open(self,request,timeout):return Response()
  with tempfile.TemporaryDirectory() as tmp,patch.object(b.urllib.request,'build_opener',return_value=Opener()):
   path=Path(tmp)/'metadata.json';data,receipt=b._release('sample','1',path,b.time.monotonic()+10)
   self.assertEqual(raw,path.read_bytes());self.assertEqual('sample',data['info']['name']);self.assertEqual(hashlib.sha256(raw).hexdigest(),receipt['sha256']);self.assertTrue(receipt['tls_default_context_verified'])
 def test_owned_child_failure_is_retained_and_never_retried(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'tmp').mkdir();receipt={}
   with self.assertRaisesRegex(ValueError,'^BINARY_WHEEL_DOWNLOAD_FAILED$'):b._run_pip([sys.executable,'-I','-S','-B','-c','print("owned fixture");raise SystemExit(3)'],root,receipt)
   self.assertEqual(1,receipt['pip_invocations']);self.assertEqual(3,receipt['pip_exit_code']);self.assertIn(b'owned fixture',(root/'pip.log').read_bytes())
 def test_failed_preparation_consumes_marker_before_network(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);req=self.request()
   with patch.object(b,'authenticate',return_value={'activation_sha':'2'*40}),patch.object(b,'validate_input_provenance',side_effect=ValueError('INVALID_LOCAL_PROVENANCE')),patch.object(b.subprocess,'Popen',side_effect=AssertionError('network after input failure')):
    result=b.run_preparation(root,req);self.assertTrue(result['request_consumed']);self.assertFalse(result['python_wheel_inputs_ready']);self.assertEqual(0,result['pip_invocations']);self.assertTrue((root/b.OUTPUT/'attempt.json').is_file())
    with self.assertRaisesRegex(ValueError,'^OUTPUT_EXISTS$'):b.run_preparation(root,req)

 def test_bad_context_or_existing_operation_stops_before_pip(self):
  req=self.request()
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   with patch.object(b,'authenticate',side_effect=ValueError('INVALID_LOCAL_CONTEXT')),patch.object(b.subprocess,'Popen',side_effect=AssertionError('pip before context')):
    with self.assertRaisesRegex(ValueError,'^INVALID_LOCAL_CONTEXT$'):b.run_preparation(root,req)
   out=root/b.OUTPUT;out.mkdir(parents=True);(out/'attempt.json').write_bytes(b'preserved')
   with patch.object(b,'authenticate',return_value={}),patch.object(b.subprocess,'Popen',side_effect=AssertionError('consumed retry')):
    with self.assertRaisesRegex(ValueError,'^OUTPUT_EXISTS$'):b.run_preparation(root,req)
   self.assertEqual(b'preserved',(out/'attempt.json').read_bytes())

 def test_multi_wheel_aggregate_caps_block_before_second_payload_open(self):
  from test_engine_clock_python_wheel_closure import make_wheel
  import zipfile
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);paths=[make_wheel(root,name=n) for n in ('first','second')]
   first,second=[b.wheel.inspect_wheel(p) for p in paths]
   with zipfile.ZipFile(paths[1]) as archive:first_payload=archive.infolist()[0].file_size
   limits={'max_total_archive_bytes':first['nbytes']+second['nbytes']-1,
           'max_decoded_bytes':first['decoded_bytes']+first_payload-1,
           'max_members':first['member_count']+second['member_count']-1}
   original=zipfile.ZipFile.open
   for key,cap in limits.items():
    opened=[]
    def observe(archive,member,*args,**kwargs):
     opened.append(member.filename if isinstance(member,zipfile.ZipInfo) else member)
     return original(archive,member,*args,**kwargs)
    with self.subTest(cap=key),patch.dict(b.BUDGET,{key:cap}),patch.object(zipfile.ZipFile,'open',observe):
     with self.assertRaisesRegex(ValueError,'^WHEEL_SET_LIMIT$'):b.audit_wheels(paths,deadline=b.time.perf_counter()+10)
     self.assertEqual(first['member_count'],len(opened),'second wheel payload must remain unopened')

if __name__=='__main__':unittest.main()
