"""Owned Docker-save/API/launch fixtures only; no Docker, network or payload execution."""
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import tarfile
try:
 from scripts import engine_clock_image_archive as a
except ImportError:a=None
TAG='stage7-engine-clock:image-20261114-01'
def rawjson(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def tarbytes(entries):
 buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode='w',format=tarfile.PAX_FORMAT) as out:
  for path,value in entries:
   info=tarfile.TarInfo(path);info.mode=0o644
   if isinstance(value,tuple):info.type=tarfile.SYMTYPE;info.linkname=value[0];out.addfile(info)
   else:info.size=len(value);out.addfile(info,io.BytesIO(value))
 return buf.getvalue()
def make_save(root,*,layout='legacy',layers=None,config_patch=None,manifest_patch=None,extra=None,reverse=False):
 layers=layers or [tarbytes([('usr/lib/owned-fixture',b'never execute')]),tarbytes([('opt/python/owned',b'stdlib fixture')])]
 config={'architecture':'amd64','os':'linux','rootfs':{'type':'layers','diff_ids':['sha256:'+sha(v) for v in layers]},'config':{'Env':['PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','LIBGL_ALWAYS_SOFTWARE=1','PYOPENGL_PLATFORM=glx','OMP_NUM_THREADS=2'],'Entrypoint':['/opt/venv/bin/python'],'Cmd':['-I','-S','-B','/usr/local/libexec/stage7/scripts/engine_clock_image_inventory.py','--candidate'],'User':'0:0','WorkingDir':'/'}}
 if config_patch:config.update(config_patch)
 c=rawjson(config);cid='sha256:'+sha(c);entries=[]
 if layout=='legacy':
  cp=sha(c)+'.json';lp=[sha(v)+'/layer.tar' for v in layers];entries=[(cp,c),*zip(lp,layers)]
 else:
  cp='blobs/sha256/'+sha(c);zipped=[gzip.compress(v,mtime=0) for v in layers];lp=['blobs/sha256/'+sha(v) for v in zipped];entries=[(cp,c),*zip(lp,zipped)]
  im={'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json','config':{'mediaType':'application/vnd.oci.image.config.v1+json','digest':cid,'size':len(c)},'layers':[{'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip','digest':'sha256:'+sha(v),'size':len(v)} for v in zipped]};imraw=rawjson(im);ip='blobs/sha256/'+sha(imraw);entries.extend([(ip,imraw),('oci-layout',rawjson({'imageLayoutVersion':'1.0.0'})),('index.json',rawjson({'schemaVersion':2,'manifests':[{'mediaType':'application/vnd.oci.image.manifest.v1+json','digest':'sha256:'+sha(imraw),'size':len(imraw),'platform':{'os':'linux','architecture':'amd64'},'annotations':{'org.opencontainers.image.ref.name':TAG}}]}))])
 manifest=[{'Config':cp,'RepoTags':[TAG],'Layers':list(reversed(lp)) if reverse else lp}]
 if manifest_patch:manifest_patch(manifest)
 entries.append(('manifest.json',rawjson(manifest)))
 if extra:entries.extend(extra)
 p=root/'image.tar';p.write_bytes(tarbytes(entries));return p,cid,config

def launch_fixture(cid,nonce='a'*32):
 return {'container_id':'b'*64,'image_id':cid,'read_only_rootfs':True,'network_mode':'none','privileged':False,'cap_drop':['ALL'],'security_opt':['no-new-privileges'],'pid_mode':'','ipc_mode':'private','pids_limit':128,'memory_bytes':2147483648,'nano_cpus':2000000000,'devices':[],'device_requests':[],'binds':[],'mounts':[],'tmpfs':{'/tmp':'rw,nosuid,nodev,noexec,size=67108864,mode=0700'},'entrypoint':['/opt/venv/bin/python'],'command':['-I','-S','-B','/usr/local/libexec/stage7/scripts/engine_clock_image_inventory.py','--candidate'],'user':'0:0','working_dir':'/','env':{'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','LIBGL_ALWAYS_SOFTWARE':'1','PYOPENGL_PLATFORM':'glx','OMP_NUM_THREADS':'2'},'labels':{'stage7.request':'image-20261114-01','stage7.nonce':nonce},'unknown_env_count':0}

class ImageArchiveTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(a,'bounded image archive/API/launch verifier missing')
 def inspect(self,path):return a.inspect_save_archive(path,expected_tag=TAG,deadline=time.perf_counter()+10)
 def test_owned_legacy_save_binds_actual_config_and_ordered_diffids_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   p,cid,c=make_save(Path(tmp));r=self.inspect(p);self.assertEqual('DOCKER_SAVE_STRUCTURE_VERIFIED',r['status']);self.assertEqual(cid,r['config_digest']);self.assertEqual(c['rootfs']['diff_ids'],r['rootfs_diff_ids']);self.assertEqual('linux/amd64',r['platform']);self.assertEqual(sha(p.read_bytes()),r['image_tar_sha256']);self.assertFalse(r['native_admission']);self.assertFalse(r['installed_runtime_verified'])
 def test_owned_oci_sidecar_layout_is_cross_bound_without_registry_claim(self):
  with tempfile.TemporaryDirectory() as tmp:
   p,cid,c=make_save(Path(tmp),layout='oci');r=self.inspect(p);self.assertEqual(cid,r['config_digest']);self.assertEqual(c['rootfs']['diff_ids'],r['rootfs_diff_ids']);self.assertEqual('docker-save-oci-layout',r['archive_layout']);self.assertNotIn('registry_manifest_digest',r)
 def test_wrong_platform_diffid_order_tag_or_multiple_images_reject(self):
  cases=[{'config_patch':{'architecture':'arm64'}},{'config_patch':{'rootfs':{'type':'layers','diff_ids':['sha256:'+'0'*64]*2}}},{'reverse':True},{'manifest_patch':lambda rows:rows[0].update(RepoTags=['mutable:other'])},{'manifest_patch':lambda rows:rows.append(copy.deepcopy(rows[0]))}]
  for kwargs in cases:
   with self.subTest(case=kwargs),tempfile.TemporaryDirectory() as tmp:
    p,_,_=make_save(Path(tmp),**kwargs)
    with self.assertRaisesRegex(ValueError,'^IMAGE_ARCHIVE_REJECTED$'):self.inspect(p)
 def test_extra_payload_unsafe_outer_and_layer_paths_or_links_reject(self):
  cases=[{'extra':[('unexpected',b'SECRET_SENTINEL')]},{'extra':[('../escape',b'bad')]},{'layers':[tarbytes([('../escape',b'bad')])]},{'layers':[tarbytes([('usr/link',('../../escape',))])]}]
  for kwargs in cases:
   with self.subTest(case=kwargs),tempfile.TemporaryDirectory() as tmp:
    p,_,_=make_save(Path(tmp),**kwargs)
    with self.assertRaisesRegex(ValueError,'^IMAGE_ARCHIVE_REJECTED$'):self.inspect(p)
 def test_archive_and_aggregate_layer_caps_and_deadline_prevent_success(self):
  with tempfile.TemporaryDirectory() as tmp:
   p,_,_=make_save(Path(tmp))
   for key,value in [('MAX_ARCHIVE_BYTES',p.stat().st_size-1),('MAX_LAYER_BYTES',10239),('MAX_JSON_BYTES',16)]:
    with self.subTest(cap=key),patch.object(a,key,value):
     with self.assertRaisesRegex(ValueError,'^IMAGE_ARCHIVE_REJECTED$'):self.inspect(p)
   with self.assertRaisesRegex(ValueError,'^IMAGE_ARCHIVE_REJECTED$'):a.inspect_save_archive(p,expected_tag=TAG,deadline=0)
 def test_nonzero_outer_tail_or_truncated_member_rejects(self):
  with tempfile.TemporaryDirectory() as tmp:
   p,_,_=make_save(Path(tmp));original=p.read_bytes()
   for corrupted in (original+b'SECRET_TRAILING_DATA'+b'\0'*(512-20),original[:1000]):
    p.write_bytes(corrupted)
    with self.assertRaisesRegex(ValueError,'^IMAGE_ARCHIVE_REJECTED$'):self.inspect(p)
 def test_layer_member_limit_is_shared_across_all_layers(self):
  with tempfile.TemporaryDirectory() as tmp:
   p,_,_=make_save(Path(tmp))
   with patch.object(a,'MAX_LAYER_MEMBERS',1):
    with self.assertRaisesRegex(ValueError,'^IMAGE_ARCHIVE_REJECTED$'):self.inspect(p)
 def test_symlink_or_hardlinked_outer_input_rejects(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p,_,_=make_save(root);link=root/'link.tar';link.symlink_to(p)
   with self.assertRaisesRegex(ValueError,'^IMAGE_ARCHIVE_REJECTED$'):self.inspect(link)
   import os
   os.link(p,root/'hard.tar')
   with self.assertRaisesRegex(ValueError,'^IMAGE_ARCHIVE_REJECTED$'):self.inspect(p)
 def test_semantic_api_binding_is_not_external_authentication_by_itself(self):
  with tempfile.TemporaryDirectory() as tmp:
   p,cid,c=make_save(Path(tmp));ar=self.inspect(p)
   expected={'repository':'owner/repo','run_id':111,'workflow_id':222,'workflow_path':'.github/workflows/prep.yml','activation_sha':'c'*40,'source_sha':'d'*40,'branch':'prepare/one-use','request_id':'image-20261114-01','artifact_id':333,'artifact_name':'sealed-image','artifact_zip_sha256':'e'*64,'artifact_zip_nbytes':1234,'image_tag':TAG,'lock_sha256':'f'*64,'recipe_sha256':'1'*64,'installed_files_sha256':'2'*64,'execution_artifact_name':'execution'}
   receipt={'schema':'engine-clock-image-candidate-v1','status':'IMAGE_CANDIDATE_PREPARED','request_id':expected['request_id'],'activation_sha':expected['activation_sha'],'source_sha':expected['source_sha'],'image_tar_sha256':ar['image_tar_sha256'],'image_tar_nbytes':p.stat().st_size,'config_digest':cid,'rootfs_diff_ids':c['rootfs']['diff_ids'],'platform':'linux/amd64','lock_sha256':expected['lock_sha256'],'recipe_sha256':expected['recipe_sha256'],'installed_files_sha256':expected['installed_files_sha256'],'native_admission':False,'official_model_calls':0}
   api={'run':{'id':111,'workflow_id':222,'path':expected['workflow_path'],'head_sha':expected['activation_sha'],'head_branch':expected['branch'],'event':'push','run_attempt':1,'status':'completed','conclusion':'success','repository':{'full_name':'owner/repo'}},'workflow':{'id':222,'path':expected['workflow_path'],'state':'active'},'jobs':{'total_count':1,'jobs':[{'run_id':111,'name':'prepare','status':'completed','conclusion':'success'}]},'artifacts':{'total_count':2,'artifacts':[{'id':333,'name':'sealed-image','expired':False,'size_in_bytes':1234,'digest':'sha256:'+'e'*64,'workflow_run':{'id':111,'head_sha':'c'*40}},{'id':334,'name':'execution','expired':False,'workflow_run':{'id':111,'head_sha':'c'*40}}]},'unique_runs':{'total_count':1,'workflow_runs':[{'id':111,'head_sha':'c'*40,'head_branch':'prepare/one-use','run_attempt':1}]}}
   r=a.validate_preparation(receipt,api,p,expected=expected);self.assertEqual('PREPARATION_METADATA_AND_ARCHIVE_MATCH',r['status']);self.assertFalse(r['external_api_origin_authenticated']);self.assertFalse(r['native_admission'])
   for where,key,bad in [('run','run_attempt',True),('run','head_sha','9'*40),('run','conclusion','failure'),('workflow','path','other.yml')]:
    altered=copy.deepcopy(api);altered[where][key]=bad
    with self.assertRaisesRegex(ValueError,'^IMAGE_PREPARATION_REJECTED$'):a.validate_preparation(receipt,altered,p,expected=expected)
 def test_actual_launch_configuration_and_nonce_required_without_secret_echo(self):
  cid='sha256:'+'3'*64;nonce='a'*32;actual=launch_fixture(cid,nonce);expected={'config_digest':cid,'request_id':'image-20261114-01','command':actual['command']}
  r=a.validate_launch(actual,expected,nonce);self.assertEqual('CLOSED_IMAGE_LAUNCH_METADATA_MATCH',r['status']);self.assertFalse(r['native_admission'])
  cases=[{'image_id':'sha256:'+'4'*64},{'read_only_rootfs':False},{'network_mode':'host'},{'binds':['/SECRET_TOKEN:/opt/python']},{'devices':[{'PathOnHost':'/SECRET_TOKEN'}]},{'unknown_env_count':1},{'env':{**actual['env'],'HTTPS_PROXY':'https://SECRET_TOKEN@proxy.invalid'}},{'labels':{**actual['labels'],'stage7.nonce':'5'*32}}]
  for bad in cases:
   with self.subTest(fields=sorted(bad)):
    with self.assertRaisesRegex(ValueError,'^IMAGE_LAUNCH_REJECTED$') as got:a.validate_launch({**actual,**bad},expected,nonce)
    self.assertNotIn('SECRET_TOKEN',str(got.exception))

if __name__=='__main__':unittest.main()
