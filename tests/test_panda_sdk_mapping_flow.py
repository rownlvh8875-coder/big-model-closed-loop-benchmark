"""CPU fake Docker and in-memory APIs, never start a real container locally."""
import base64,copy,hashlib,json,os,tempfile,time,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
try:
 from scripts import run_panda_sdk_mapping_canary as host
 from scripts import accept_panda_sdk_mapping_canary as consumer
 from scripts import panda_sdk_mapping_carrier as carrier
except ImportError:host=consumer=carrier=None
class MappingFlowTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(host,'new one-use hosted mapping path required')
 def fake(self,root):
  p=root/'cpu-docker';p.write_text('#!/usr/bin/python3\nimport os,sys\nassert sys.argv[1]=="--host=unix:///var/run/docker.sock"\nassert not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN","LD_PRELOAD","DOCKER_HOST"))\nprint("CPU only")\n');p.chmod(0o755);return p
 def docker(self,root):
  with patch.dict(os.environ,{'GH_TOKEN':'CPU','GITHUB_TOKEN':'CPU','LD_PRELOAD':'unset','DOCKER_HOST':'foreign'}):return host.MappingDocker(self.fake(root),root/'docker',time.monotonic()+10,root/'binding','a'*64,'b'*32,root/'image.tar')
 def test_unregistered_entry_cannot_create_output_or_load(self):
  with patch.dict(os.environ,{},clear=True),self.assertRaises(ValueError):host.run_canary()
 def test_fixed_create_is_readonly_unprivileged_and_forbidden_args_reject(self):
  with tempfile.TemporaryDirectory() as t:
   d=self.docker(Path(t));args=d.create_argv();self.assertIn('--read-only',args);self.assertIn('65534:65534',args);self.assertIn('--security-opt=no-new-privileges',args);self.assertIn('805306368',args);self.assertNotIn('--privileged',args);d.validate_args(args)
   for bad in [['run','x'],['build','x'],['push','x'],['exec','x'],args+['--privileged'],['start','--attach','c'*64]]:
    with self.assertRaises(ValueError):d.validate_args(bad)
 def test_one_start_latch_persists_before_child_and_rejects_repeat(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);d=self.docker(root);d.bind('c'*64);d.call(['start','--attach','c'*64]);self.assertTrue(d.consumed);self.assertTrue((root/'mapping-window-consumed.json').is_file())
   with self.assertRaises(ValueError):d.call(['start','--attach','c'*64])
 def test_cpu_boundary_drops_tokens_and_uses_pinned_endpoint(self):
  with tempfile.TemporaryDirectory() as t:
   d=self.docker(Path(t));self.assertEqual(d.call(['version','--format','{{json .Server}}']).strip(),'CPU only')
 def test_closed_small_carrier_crc_paths_members_and_existing_outputs(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);z=root/'proof.zip'
   with zipfile.ZipFile(z,'w') as f:
    for n in ['canary.json','runtime.json','execution.json']:f.writestr(n,b'{}')
   carrier.extract_carrier(z,root/'accepted');self.assertEqual((root/'accepted/runtime.json').read_bytes(),b'{}')
   with self.assertRaises(ValueError):carrier.extract_carrier(z,root/'accepted')
   with zipfile.ZipFile(z,'a') as f:f.writestr('../outside',b'CPU')
   with self.assertRaises(ValueError):carrier.extract_carrier(z,root/'bad')
 def test_job_failure_is_retained_failure_not_success_authority(self):
  a=host.a;run=dict(id=201,head_sha='b'*40,head_branch=a.BRANCH,status='completed',conclusion='failure');jobs=dict(total_count=1,jobs=[dict(id=401,run_id=201,run_attempt=1,head_sha='b'*40,head_branch=a.BRANCH,name='canary',status='completed',conclusion='failure')]);self.assertEqual(a.validate_production_job(run,jobs),401)
  with self.assertRaises(ValueError):a.validate_production_job(dict(run,conclusion='success'),jobs)
 def test_existing_consumer_output_preserved_before_network(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t);(out/'keep').write_bytes(b'old')
   with patch.object(consumer,'Client') as client,self.assertRaises(ValueError):consumer.accept_canary('a'*40,'b'*40,201,out)
   client.assert_not_called();self.assertEqual((out/'keep').read_bytes(),b'old')
 def test_receipt_dictionary_alone_cannot_authenticate_failed_window(self):
  a=host.a;c=dict(schema='panda-sdk-mapping-canary-v1',source_sha='a'*40,activation_sha='b'*40,run_id=201,request_sha256='c'*64,sdk_sha256=a.SDK_SHA,image_sha256=a.IMAGE_SHA,native_admitted=False,scientific_native_runs=0,stage7_complete=False,mapping_window_consumed=True,start_attempts=1,status='MAPPING_ONLY_CANARY_FAILED');r=consumer.validate_result(c,{}, {},'a'*40,'b'*40,201,'c'*64);self.assertFalse(r['external_origin_authenticated']);self.assertFalse(r['canary_passed']);self.assertFalse(r['native_admitted'])
 def test_complete_memory_api_checks_job_before_proof_download(self):
  a=host.a;request=a.request_template('a'*40,[dict(event='push',run_id=101),dict(event='pull_request',run_id=102)],a.ROOT);raw=json.dumps(request).encode();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();run=dict(id=201,head_sha='b'*40,head_branch=a.BRANCH,event='push',run_attempt=1,status='completed',conclusion='success',path=a.WORKFLOW,workflow_id=301,repository=dict(full_name=a.REPO,id=a.REPO_ID),head_repository=dict(full_name=a.REPO,id=a.REPO_ID),actor=dict(login=a.OWNER));commit=dict(sha='b'*40,parents=[dict(sha='a'*40)],commit=dict(tree=dict(sha='1'*40)));delta=dict(status='ahead',ahead_by=1,total_commits=1,commits=[dict(sha='b'*40)],files=[dict(filename=a.REQUEST,status='added',sha=blob)]);trees={'1'*40:[dict(path='docs',type='tree',mode='040000',sha='2'*40)],'2'*40:[dict(path='requests',type='tree',mode='040000',sha='3'*40)],'3'*40:[dict(path=Path(a.REQUEST).name,type='blob',mode='100644',sha=blob)]}
  class DownloadGate(Exception):pass
  for valid in (True,False):
   visited=[];downloads=[]
   class MemoryClient:
    def __init__(self,out,**kw):self.out=out;out.mkdir()
    def get_json(self,path,name):
     visited.append(path)
     if path.startswith('commits/'):v=commit
     elif path.startswith('compare/'):v=delta
     elif path.startswith('git/trees/'):v=dict(tree=trees[path.rsplit('/',1)[1]])
     elif path.startswith('git/blobs/'):v=dict(encoding='base64',size=len(raw),content=base64.b64encode(raw).decode())
     elif path.startswith('actions/workflows/'):v=dict(total_count=1,workflow_runs=[run]) if '/runs?' in path else dict(id=301,path=a.WORKFLOW,state='active')
     else:
      parts=path.split('/');rid=int(parts[2]);suffix=parts[3] if len(parts)>3 else ''
      if rid==201:
       if not suffix:v=run
       elif suffix=='jobs':v=dict(total_count=1,jobs=[dict(id=401,run_id=201,run_attempt=1,head_sha='b'*40 if valid else 'c'*40,head_branch=a.BRANCH,name='canary',status='completed',conclusion='success')])
       else:v=dict(total_count=1,artifacts=[dict(id=501,name=a.ARTIFACT,size_in_bytes=100,digest='sha256:'+'e'*64,expired=False,workflow_run=dict(id=201,head_sha='b'*40,head_branch=a.BRANCH,repository_id=a.REPO_ID,head_repository_id=a.REPO_ID))])
      elif suffix=='jobs':v=dict(total_count=2,jobs=[dict(name=n,run_id=rid,status='completed',conclusion='success') for n in ['synthetic-unit','onnx-interface-test']])
      elif suffix=='artifacts':v=dict(total_count=0,artifacts=[])
      else:v=dict(id=rid,head_sha='a'*40,head_branch=a.SOURCE_BRANCH,event='push' if rid==101 else 'pull_request',workflow_id=411705464,path='.github/workflows/ci.yml',run_attempt=1,status='completed',conclusion='success',repository=dict(full_name=a.REPO))
     with (self.out/name).open('xb') as f:f.write(json.dumps(v).encode())
     return v
    def download(self,*args,**kw):downloads.append(True);raise DownloadGate()
   with tempfile.TemporaryDirectory() as t,patch.object(consumer,'Client',MemoryClient),patch.dict(os.environ,{'GH_TOKEN':'CPU-synthetic-token'}):
    out=Path(t)/'new'
    with self.assertRaises(DownloadGate if valid else ValueError):consumer.accept_canary('a'*40,'b'*40,201,out)
    self.assertIn('actions/runs/201/jobs',visited);self.assertEqual(len(downloads),1 if valid else 0);self.assertFalse(json.loads((out/'acceptance.json').read_text())['actions_output_origin_authenticated'])
 def test_timed_out_start_exports_binary_partial_stdout_without_success(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);tool=root/'cpu-docker';tool.write_text('#!/usr/bin/python3\nimport os,time\nos.write(1,b"PARTIAL_RUNTIME_EVIDENCE\\xff\\n")\ntime.sleep(5)\n');tool.chmod(0o755);d=host.MappingDocker(tool,root/'docker',time.monotonic()+10,root/'binding','a'*64,'b'*32,root/'image.tar');d.bind('c'*64);bundle=root/'bundle';bundle.mkdir()
   with self.assertRaises(ValueError):d.call(['start','--attach','c'*64],timeout=.15)
   host.preserve_failed_start(d,bundle);r=json.loads((bundle/'runtime.json').read_text());raw=base64.b64decode(r['captured_stdout']['base64']);self.assertEqual(raw,b'PARTIAL_RUNTIME_EVIDENCE\xff\n');self.assertEqual(r['captured_stdout']['sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(r['capture']['status'],'TIMEOUT');self.assertTrue(d.consumed);self.assertFalse(r['runtime_semantics_validated']);self.assertFalse(r['native_admitted'])
   z=root/'proof.zip'
   with zipfile.ZipFile(z,'w') as f:
    f.write(bundle/'runtime.json','runtime.json');f.writestr('canary.json',b'{"status":"MAPPING_ONLY_CANARY_FAILED"}');f.writestr('execution.json',b'{}')
   carrier.extract_carrier(z,root/'exported');self.assertEqual(json.loads((root/'exported/runtime.json').read_text())['captured_stdout'],r['captured_stdout'])
 def test_maximum_failed_stdout_and_stderr_fit_closed_carrier_limits(self):
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);prefix=root/'capture';prefix.mkdir();raw=b'\0\xff'*(4*1024**2);(prefix/'stdout.bin').write_bytes(raw);(prefix/'stderr.bin').write_bytes(b'e'*(128*1024));bundle=root/'bundle';bundle.mkdir();fake=SimpleNamespace(last_start_capture=dict(prefix=str(prefix),process=dict(status='OUTPUT_LIMIT',streams_complete=False)));host.preserve_failed_start(fake,bundle);self.assertLess((bundle/'runtime.json').stat().st_size,12*1024**2);z=root/'max.zip'
   with zipfile.ZipFile(z,'w') as f:
    f.write(bundle/'runtime.json','runtime.json');f.writestr('canary.json',b'{}');f.writestr('execution.json',b'{}')
   carrier.extract_carrier(z,root/'received');r=json.loads((root/'received/runtime.json').read_text());self.assertEqual(hashlib.sha256(base64.b64decode(r['captured_stdout']['base64'])).hexdigest(),hashlib.sha256(raw).hexdigest());self.assertFalse(r['runtime_semantics_validated'])
if __name__=='__main__':unittest.main()
