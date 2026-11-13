"""Source/API/resource/launch fixtures only; no network, Docker or package execution."""
import copy
import json
from pathlib import Path
import unittest
try:
 from scripts import engine_clock_image_preparation as prepare
except ImportError:prepare=None
from test_engine_clock_image_archive import launch_fixture
ROOT=Path(__file__).resolve().parent.parent
GIB=1024**3

class ImagePreparationTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(prepare,'source-qualified one-use image controller missing')
 def request(self,role='prepare'):
  cfg=prepare.ROLES[role]
  return {'schema':'engine-clock-image-operation-request-v1','role':role,'request_id':cfg['request_id'],'repository':prepare.REPOSITORY,'branch':cfg['branch'],'reviewed_source_branch':prepare.SOURCE_BRANCH,'reviewed_source_sha':'1'*40,'output_directory':cfg['output'],'workflow_path':cfg['workflow'],'source_closure':{p:'0'*64 for p in prepare.source_paths(ROOT)},'source_ci':[{'run_id':11,'event':'push'},{'run_id':12,'event':'pull_request'}],'input_lock_sha256':prepare.INPUT_SHA,'renderer_lock_sha256':prepare.RENDERER_SHA,'python_layout_sha256':prepare.LAYOUT_SHA,'effective_lock_sha256':prepare.EFFECTIVE_SHA,'budget':copy.deepcopy(prepare.BUDGETS[role]),'permissions':copy.deepcopy(prepare.PERMISSIONS[role]),'image_evidence':None if role=='prepare' else {'fixture':'not-accepted-until-typed'}}
 def test_closed_request_roles_limits_permissions_and_source_set(self):
  r=self.request();self.assertEqual(r,prepare.validate_request(r,'prepare',ROOT))
  for key,value in [('extra',True),('branch','main'),('input_lock_sha256','2'*64),('source_closure',{}),('image_evidence',{'fixture':'bad'})]:
   bad=copy.deepcopy(r);bad[key]=value
   with self.assertRaisesRegex(ValueError,'^IMAGE_REQUEST_REJECTED$'):prepare.validate_request(bad,'prepare',ROOT)
  bad=copy.deepcopy(r);bad['permissions']['native_engine']=True
  with self.assertRaisesRegex(ValueError,'^IMAGE_REQUEST_REJECTED$'):prepare.validate_request(bad,'prepare',ROOT)
  bad=copy.deepcopy(r);bad['budget']['docker_builds']=2
  with self.assertRaisesRegex(ValueError,'^IMAGE_REQUEST_REJECTED$'):prepare.validate_request(bad,'prepare',ROOT)
 def test_activation_is_exact_single_parent_request_only_and_regular(self):
  r=self.request();cfg=prepare.ROLES['prepare'];change=b'A\0'+cfg['request_path'].encode()+b'\0';prepare.validate_activation(r,'2'*40,['1'*40],change,'100644',cfg['branch'])
  for parents,delta,mode,branch in [(['3'*40],change,'100644',cfg['branch']),(['1'*40,'3'*40],change,'100644',cfg['branch']),(['1'*40],b'M\0scripts/owned.py\0','100644',cfg['branch']),(['1'*40],change,'120000',cfg['branch']),(['1'*40],change,'100644','main')]:
   with self.assertRaisesRegex(ValueError,'^IMAGE_CONTEXT_REJECTED$'):prepare.validate_activation(r,'2'*40,parents,delta,mode,branch)
 def proofs(self,r):
  rows=[]
  for ci in r['source_ci']:
   rid=ci['run_id'];rows.append({'run':{'id':rid,'head_sha':'1'*40,'head_branch':prepare.SOURCE_BRANCH,'event':ci['event'],'path':'.github/workflows/ci.yml','run_attempt':1,'status':'completed','conclusion':'success','repository':{'full_name':prepare.REPOSITORY}},'jobs':{'total_count':2,'jobs':[{'name':n,'run_id':rid,'status':'completed','conclusion':'success'} for n in ('synthetic-unit','onnx-interface-test')]},'artifacts':{'total_count':0,'artifacts':[]}})
  return rows
 def test_exact_head_source_ci_semantics_required_not_only_hash_shape(self):
  r=self.request();proofs=self.proofs(r);prepare.validate_source_ci(r,proofs)
  for key,value in [('head_sha','2'*40),('run_attempt',True),('run_attempt',2),('conclusion','failure')]:
   bad=copy.deepcopy(proofs);bad[0]['run'][key]=value
   with self.assertRaisesRegex(ValueError,'^IMAGE_SOURCE_CI_REJECTED$'):prepare.validate_source_ci(r,bad)
 def live(self,r):
  cfg=prepare.ROLES['prepare'];context={'run_id':111,'head_sha':'2'*40,'repository':prepare.REPOSITORY,'event':'push','attempt':1};run={'id':111,'head_sha':'2'*40,'head_branch':cfg['branch'],'workflow_id':222,'path':cfg['workflow'],'event':'push','run_attempt':1,'status':'in_progress','conclusion':None,'repository':{'full_name':prepare.REPOSITORY}};workflow={'id':222,'path':cfg['workflow'],'state':'active'};unique={'total_count':1,'workflow_runs':[copy.deepcopy(run)]};return context,run,workflow,unique
 def test_live_api_owner_workflow_unique_run_and_attempt_cannot_be_env_only(self):
  r=self.request();context,run,wf,unique=self.live(r);result=prepare.validate_live_run(r,context,run,wf,unique);self.assertFalse(result['external_api_origin_authenticated'])
  for key,value in [('head_sha','3'*40),('head_branch','main'),('run_attempt',True),('event','workflow_dispatch')]:
   bad=copy.deepcopy(run);bad[key]=value
   with self.assertRaisesRegex(ValueError,'^IMAGE_CONTEXT_REJECTED$'):prepare.validate_live_run(r,context,bad,wf,unique)
  bad=copy.deepcopy(unique);bad['total_count']=2
  with self.assertRaisesRegex(ValueError,'^IMAGE_CONTEXT_REJECTED$'):prepare.validate_live_run(r,context,run,wf,bad)
 def test_shared_storage_is_counted_once_and_unsupported_capacity_rejects(self):
  r=prepare.storage_union([{'label':'archive','st_dev':1,'free_bytes':20*GIB},{'label':'docker','st_dev':1,'free_bytes':21*GIB}]);self.assertEqual(20*GIB,r['free_union_bytes']);self.assertEqual(1,r['filesystem_count'])
  r=prepare.storage_union([{'label':'archive','st_dev':1,'free_bytes':10*GIB},{'label':'docker','st_dev':2,'free_bytes':10*GIB}]);self.assertEqual(20*GIB,r['free_union_bytes']);self.assertEqual(2,r['filesystem_count'])
  for rows in [[{'label':'archive','st_dev':1,'free_bytes':15*GIB},{'label':'docker','st_dev':1,'free_bytes':15*GIB}],[{'label':'archive','st_dev':1,'free_bytes':2*GIB},{'label':'docker','st_dev':2,'free_bytes':30*GIB}]]:
   with self.assertRaisesRegex(ValueError,'^IMAGE_STORAGE_REJECTED$'):prepare.storage_union(rows)
 def test_raw_launch_metadata_is_validated_before_any_public_projection(self):
  cid='sha256:'+'4'*64;nonce='a'*32;clean=launch_fixture(cid,nonce);h={'ReadonlyRootfs':True,'NetworkMode':'none','Privileged':False,'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],'PidMode':'','IpcMode':'private','PidsLimit':128,'Memory':2147483648,'NanoCpus':2000000000,'Devices':[],'DeviceRequests':None,'Binds':None,'Tmpfs':clean['tmpfs']}
  raw={'Id':clean['container_id'],'Image':cid,'HostConfig':h,'Mounts':[],'Config':{'Entrypoint':clean['entrypoint'],'Cmd':clean['command'],'User':'0:0','WorkingDir':'/','Env':[k+'='+v for k,v in clean['env'].items()],'Labels':clean['labels']}}
  expected={'config_digest':cid,'request_id':'image-20261114-01','command':clean['command']};result=prepare.normalize_launch(raw,expected,nonce);self.assertEqual(cid,result['image_id'])
  bad=copy.deepcopy(raw);bad['Config']['Env'].append('GH_TOKEN=SECRET_SENTINEL')
  with self.assertRaisesRegex(ValueError,'^IMAGE_LAUNCH_REJECTED$') as got:prepare.normalize_launch(bad,expected,nonce)
  self.assertNotIn('SECRET',str(got.exception))
 def test_api_commit_compare_rejects_any_extra_change_even_with_expected_parent(self):
  r=self.request();head='2'*40;calls=[]
  comparison={'status':'ahead','ahead_by':1,'behind_by':0,'total_commits':1,'base_commit':{'sha':'1'*40},'merge_base_commit':{'sha':'1'*40},'commits':[{'sha':head}],'files':[{'filename':prepare.ROLES['prepare']['request_path'],'status':'added'}]}
  class API:
   def get_json(self,endpoint,name):
    calls.append(endpoint)
    return {'sha':head,'parents':[{'sha':'1'*40}],'tree':{'sha':'3'*40}} if endpoint.startswith('git/') else comparison
  prepare.authenticate_delta(API(),r,head,'3'*40);self.assertEqual(2,len(calls))
  comparison['files'].append({'filename':'scripts/changed.py','status':'modified'})
  with self.assertRaisesRegex(ValueError,'^IMAGE_CONTEXT_REJECTED$'):prepare.authenticate_delta(API(),r,head,'3'*40)
 def test_redactor_handles_actual_secrets_proxy_userinfo_and_signed_queries(self):
  redact=prepare.make_redactor({'GH_TOKEN':'SECRET_SENTINEL_VALUE','HTTPS_PROXY':'https://user:password@proxy.invalid'})
  safe=redact(b'SECRET_SENTINEL_VALUE https://user:password@proxy.invalid https://owned.blob.core.windows.net/path?sig=SECRET_SIG')
  self.assertNotIn(b'SECRET',safe);self.assertNotIn(b'password',safe)
 def test_owned_pipeline_composes_stage_build_candidate_and_archive_without_live_tools(self):
  import tempfile,hashlib
  from test_engine_clock_image_archive import make_save
  from scripts import engine_clock_runtime_inventory as core
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);work=root/'execution';work.mkdir();fake=root/'fixture';fake.mkdir();tar,cid,config=make_save(fake);calls=[];host={'fixture':'owned host'}
   manifest={'schema':'installed-files-v1','roots':list(core.BASE_ROOTS),'runtime_exclusions':list(core.RUNTIME_EXCLUSIONS),'entries':[]};raw=core._canonical(manifest)
   renderer=json.loads((ROOT/prepare.RENDERER_PATH).read_bytes());wanted={r['name']:r['version'] for r in renderer['wheels']}
   class Engine:
    def __init__(self):self.host=host;self.profile={'fixture':'owned engine'}
    def load_base(self,*args):calls.append('load')
    def build(self,*args):calls.append('build');return {'config_digest':cid,'rootfs_diff_ids':config['rootfs']['diff_ids'],'platform':'linux/amd64'}
    def collect(self,*args,**kwargs):calls.append('collect');return {'manifest_raw':raw,'summary':{'status':'CANDIDATE_INSTALLED_MANIFEST_COLLECTED','complete':True,'canonical_manifest_sha256':hashlib.sha256(raw).hexdigest(),'host':host,'prefix':{'status':'PREFIX_LAYOUT_AND_OBSERVATION_MATCH'},'version_evidence':{'python':'3.11.18','installed_distributions':wanted,'cv2_imported':False,'renderer_packages_imported':False,'ort_installed':False},'native_admission':False,'official_model_calls':0},'launch':{'fixture':'owned launch'}}
    def save(self,image,path):calls.append('save');path.write_bytes(tar.read_bytes())
   stage=lambda *args:{'context':root,'base_archive':tar,'base_config_digest':'sha256:'+'4'*64,'base_diff_ids':['sha256:'+'5'*64],'recipe_sha256':'6'*64,'renderer':renderer}
   r=self.request();ctx={'activation_sha':'2'*40,'source_sha':'1'*40,'run_id':111,'workflow_id':222,'request_sha256':'3'*64,'source_closure_verified':True}
   result=prepare.prepare_image(r,ctx,work,engine=Engine(),stage=stage);self.assertEqual(['load','build','collect','save'],calls);self.assertEqual('IMAGE_CANDIDATE_PREPARED',result['status']);self.assertFalse(result['native_admission']);self.assertEqual({'image.tar','preparation.json','installed-files.json'},{p.name for p in (root/'image').iterdir()})
 def test_owned_pipeline_failure_never_retries_or_reaches_collection(self):
  import tempfile
  calls=[]
  class Engine:
   def load_base(self,*args):calls.append('load')
   def build(self,*args):calls.append('build');raise ValueError('owned failure')
  with tempfile.TemporaryDirectory() as tmp:
   work=Path(tmp)/'execution';work.mkdir()
   stage=lambda *args:{'context':work,'base_archive':work/'base','base_config_digest':'sha256:'+'4'*64,'base_diff_ids':['sha256:'+'5'*64],'recipe_sha256':'6'*64}
   with self.assertRaises(ValueError):prepare.prepare_image(self.request(),{'activation_sha':'2'*40,'source_sha':'1'*40},work,engine=Engine(),stage=stage)
   self.assertEqual(['load','build'],calls)
 def test_cli_on_this_host_stops_before_network_or_docker(self):
  from unittest.mock import patch
  with patch.object(prepare,'run_operation',side_effect=AssertionError('live action forbidden')):
   self.assertEqual(1,prepare.main(['--run','--role','prepare']))

if __name__=='__main__':unittest.main()
