"""New image boundaries using handwritten CPU children and memory-only HTTP."""
import base64,copy,hashlib,io,json,os,tempfile,unittest,urllib.parse
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
try:
 from scripts import accept_panda_sdk_abi0_image as c
 from scripts import produce_panda_sdk_abi0_image as p
except ImportError:c=p=None
class Abi0ImageFlowTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(c,'new ABI0 producer/consumer required')
 def receipt(self):return dict(schema='panda-sdk-abi0-actions-image-production-v1',status='COPY_ONLY_SDK_IMAGE_BYTES_VERIFIED_NATIVE_BLOCKED',request_id=c.a.ID,source_sha='a'*40,activation_sha='b'*40,run_id=201,request_sha256='c'*64,sdk_sha256=c.a.SDK_SHA,sdk_nbytes=c.a.SDK_SIZE,containers_started=0,new_native_runs=0,official_model_calls=0,native_admitted=False,stage7_complete=False,installed_entries=44232,installed_manifest_sha256='d'*64,owned_stopped_container_removed=True,archive=dict(image_tar_sha256='e'*64,image_tar_nbytes=100,config_digest='sha256:'+'f'*64))
 def test_receipt_is_semantics_only_and_old_sdk_native_flags_reject(self):
  r=self.receipt();v=c.validate_receipt(r,'a'*40,'b'*40,201,'c'*64,'d'*64);self.assertFalse(v['external_origin_authenticated']);self.assertFalse(v['native_admitted'])
  for k,v in [('sdk_sha256','3e9fa983023cb1f30b08a2bc650d0803686bef032a2c5d7a5700e1d3ad60553b'),('native_admitted',True),('containers_started',True),('owned_stopped_container_removed',False),('source_sha','0'*40)]:
   with self.assertRaises(ValueError):c.validate_receipt(dict(r,**{k:v}),'a'*40,'b'*40,201,'c'*64,'d'*64)
 def test_producer_context_gate_precedes_any_action(self):
  with patch.dict(os.environ,{},clear=True),self.assertRaises(ValueError):p.run_production()
 def test_real_cpu_child_filters_credentials_and_rejects_payload_commands(self):
  from tests.test_panda_sdk_image_producer import ProducerBoundaryTests
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);child=ProducerBoundaryTests().child(root)
   with patch.dict(os.environ,{'DOCKER_CONFIG':'cpu-config','GH_TOKEN':'cpu-secret','LD_PRELOAD':'unset','DOCKER_HOST':'foreign'}):docker=p.DockerData(child,root/'logs',__import__('time').monotonic()+8)
   self.assertEqual(docker.call(['version'],timeout=2).strip(),'CPU only')
   for args in [['run','x'],['start','x'],['exec','x'],['pull','x'],['push','x'],['rm','--force','x']]:
    with self.assertRaises(ValueError):docker.call(args)
 def test_existing_output_is_preserved_before_network(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t);(out/'keep').write_bytes(b'old')
   with patch.object(c,'Client') as net,self.assertRaises(ValueError):c.accept_image('a'*40,'b'*40,201,out)
   net.assert_not_called();self.assertEqual((out/'keep').read_bytes(),b'old')
 def test_local_space_reserves_carrier_image_and_audit_before_download(self):
  required=200+384*1024**2
  with patch.object(c.shutil,'disk_usage',return_value=SimpleNamespace(free=required-1)),self.assertRaisesRegex(ValueError,'local space'):c.require_local_space(100,Path('/tmp'))
  with patch.object(c.shutil,'disk_usage',return_value=SimpleNamespace(free=required)):self.assertEqual(c.require_local_space(100,Path('/tmp')),required)
 def memory_flow(self,valid_job):
  from scripts.engine_clock_image_transport import Client
  from tests.test_panda_sdk_abi0_image_policy import Abi0ImagePolicyTests
  a=c.a;r=a.request_template('a'*40,[dict(event='push',run_id=101),dict(event='pull_request',run_id=102)],a.ROOT);raw=json.dumps(r).encode();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();ctx,run,workflow,listing=Abi0ImagePolicyTests().live();jobs=Abi0ImagePolicyTests().jobs(run)
  if not valid_job:jobs['jobs'][0]['head_sha']='0'*40
  commit=dict(sha='b'*40,parents=[dict(sha='a'*40)],commit=dict(tree=dict(sha='1'*40)));delta=dict(status='ahead',ahead_by=1,total_commits=1,commits=[dict(sha='b'*40)],files=[dict(filename=a.REQUEST,status='added',sha=blob)]);trees={'1'*40:[dict(path='docs',type='tree',mode='040000',sha='2'*40)],'2'*40:[dict(path='requests',type='tree',mode='040000',sha='3'*40)],'3'*40:[dict(path=Path(a.REQUEST).name,type='blob',mode='100644',sha=blob)]};visited=[]
  class Response(io.BytesIO):status=200;headers={}
  class Opener:
   def open(self,request,timeout):
    path=urllib.parse.urlsplit(request.full_url).path.split('/'+a.REPO+'/',1)[1];visited.append(path)
    if path.startswith('commits/'):value=commit
    elif path.startswith('compare/'):value=delta
    elif path.startswith('git/trees/'):value=dict(tree=trees[path.rsplit('/',1)[1]])
    elif path.startswith('git/blobs/'):value=dict(encoding='base64',size=len(raw),content=base64.b64encode(raw).decode())
    elif path.startswith('actions/workflows/'):value=listing if path.endswith('/runs') else workflow
    elif path.startswith('actions/runs/'):
     parts=path.split('/');rid=int(parts[2]);suffix=parts[3] if len(parts)>3 else ''
     if rid==201:
      if not suffix:value=run
      elif suffix=='jobs':value=jobs
      else:value=dict(total_count=2,artifacts=[dict(id=400+i,name=n,digest='sha256:'+'e'*64,size_in_bytes=100,expired=False,workflow_run=dict(id=201,head_sha='b'*40,head_branch=a.BRANCH,repository_id=a.REPO_ID,head_repository_id=a.REPO_ID)) for i,n in enumerate((a.ARTIFACT,a.ARTIFACT+'-execution'))])
     elif suffix=='jobs':value=dict(total_count=2,jobs=[dict(name=n,run_id=rid,status='completed',conclusion='success') for n in ('synthetic-unit','onnx-interface-test')])
     elif suffix=='artifacts':value=dict(total_count=0,artifacts=[])
     else:value=dict(id=rid,head_sha='a'*40,head_branch=a.SOURCE_BRANCH,event='push' if rid==101 else 'pull_request',path='.github/workflows/ci.yml',workflow_id=411705464,run_attempt=1,status='completed',conclusion='success',repository=dict(full_name=a.REPO))
    else:raise AssertionError(path)
    return Response(json.dumps(value).encode())
  class DownloadGate(Exception):pass
  def client(*args,**kw):return Client(*args,**kw,opener=Opener())
  with tempfile.TemporaryDirectory() as t,patch.object(c,'Client',side_effect=client),patch.object(Client,'download',side_effect=DownloadGate) as download,patch.dict(os.environ,{'GH_TOKEN':'synthetic-cpu-token'}):
   out=Path(t)/'out'
   with self.assertRaises(DownloadGate if valid_job else ValueError):c.accept_image('a'*40,'b'*40,201,out)
   self.assertIn('actions/runs/201/jobs',visited);self.assertEqual(download.call_count,1 if valid_job else 0);self.assertFalse(json.loads((out/'acceptance.json').read_text())['actions_output_origin_authenticated'])
 def test_full_memory_api_flow_reaches_download_after_exact_job(self):self.memory_flow(True)
 def test_foreign_production_job_blocks_carrier_download(self):self.memory_flow(False)
 def test_provider_drift_blocks_even_when_root_symbols_are_available(self):
  report=copy.deepcopy(c.a.prerequisite(c.a.ROOT)['root_symbol_availability']);c.verify_provider_profile(report)
  next(iter(report['provider_records'].values()))['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'provider profile'):c.verify_provider_profile(report)
 def test_actual_extracted_root_sdk_must_match_handoff_before_symbol_graph(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);bad=root/'bad.elf.data';bad.write_bytes(b'CPU wrong SDK');row=dict(data_path=str(bad));reader=SimpleNamespace(collect=lambda paths:{c.image_data.LIB:row})
   with patch.object(c.image_data,'SelectedImage',return_value=reader),patch.object(c.image_data,'provider_graph') as graph,self.assertRaisesRegex(ValueError,'installed SDK bytes'):
    c.audit_installed_root(root/'unused-image',{},c.a.expected_inventory(c.a.ROOT),root/'audit')
   graph.assert_not_called();self.assertEqual(json.loads((root/'audit/audit.json').read_text())['status'],'FAILED')
if __name__=='__main__':unittest.main()
