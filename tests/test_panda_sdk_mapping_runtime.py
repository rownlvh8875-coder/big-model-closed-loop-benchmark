"""Owned handwritten CPU .so only; no Panda/SDK target loads locally."""
import copy,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
try:
 from scripts import panda_sdk_mapping_runtime as runtime
 from scripts import panda_sdk_mapping_profile as profile
except ImportError:runtime=profile=None
C='''#include <stdint.h>
#include <errno.h>
#include <stdio.h>
__attribute__((constructor)) static void notice(void){fputs("CPU-owned\\n",stderr);}
struct stats{uint32_t configured,closed,error,pad;uint64_t forwarded,resolutions,paths,events;};
unsigned long pca_context_size(void){return SIZE;}
unsigned long rc_context_size(void){return 2320;}
int psd_source_idle(void *a,void*b){return -1;}
int psd_get_stats(struct stats *p){if(!p)return -1;*p=(struct stats){0};BAD return 0;}
'''
class MappingRuntimeTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(runtime,'owned mapping parent/child required')
 def fixture(self,root,size=2640344,bad=''):
  src=root/'fixture.c';src.write_text(C.replace('SIZE',str(size)).replace('BAD',bad));lib=root/'libmapping_fixture.so';subprocess.run(['/usr/bin/gcc','-shared','-fPIC','-O2',str(src),'-o',str(lib)],check=True,capture_output=True,timeout=15);raw=lib.read_bytes();p=profile.make_profile((profile.ROOT/profile.SDK).read_bytes());p.update(sdk_sha256=hashlib.sha256(raw).hexdigest(),sdk_nbytes=len(raw),functions=profile.export_ranges(raw));return lib,p
 def test_real_owned_process_maps_and_five_typed_calls(self):
  with tempfile.TemporaryDirectory() as t:
   lib,p=self.fixture(Path(t));r=runtime.run_window(lib,p,fixture=True);self.assertEqual(r['status'],'SELECTED_MAPPING_ABI_OBSERVED');self.assertEqual(len(r['child']['calls']),5);self.assertEqual(r['before']['code']['pid'],r['after']['code']['pid']);self.assertTrue(r['before']['code']['process_code_verified']);self.assertFalse(r['image_membership_verified']);self.assertFalse(r['native_admitted']);self.assertFalse(r['external_origin_authenticated'])
 def test_wrong_file_identity_rejects_before_child_loading(self):
  with tempfile.TemporaryDirectory() as t:
   lib,p=self.fixture(Path(t));p['sdk_sha256']='0'*64
   with self.assertRaises(ValueError):runtime.run_window(lib,p,fixture=True)
 def test_wrong_return_errno_and_guard_writes_reject(self):
  for size,bad in [(2640345,''),(2640344,'errno=99;'),(2640344,'((unsigned char*)p)[48]=0;')]:
   with self.subTest(size=size,bad=bad),tempfile.TemporaryDirectory() as t:
    lib,p=self.fixture(Path(t),size,bad)
    with self.assertRaises(ValueError):runtime.run_window(lib,p,fixture=True)
 def test_forged_nonce_or_process_and_changed_code_proof_reject(self):
  with tempfile.TemporaryDirectory() as t:
   lib,p=self.fixture(Path(t));r=runtime.run_window(lib,p,fixture=True)
   for mutate in ['nonce','pid','range']:
    bad=copy.deepcopy(r)
    if mutate=='nonce':bad['child']['nonce']='0'*32
    elif mutate=='pid':bad['after']['code']['pid']+=1
    else:bad['after']['code']['ranges']['pca_context_size']['sha256']='0'*64
    with self.assertRaises(ValueError):runtime.validate_window(p,bad)
 def test_timeout_and_unregistered_production_context_are_closed(self):
  with tempfile.TemporaryDirectory() as t:
   lib,p=self.fixture(Path(t))
   with self.assertRaises(ValueError):runtime.run_window(lib,p,fixture=True,timeout=.001)
   with self.assertRaises(ValueError):runtime.run_window(lib,p,fixture=False)
 def test_cpu_fixture_mode_cannot_load_actual_sdk(self):
  p=profile.make_profile((profile.ROOT/profile.SDK).read_bytes())
  with self.assertRaises(ValueError):runtime.run_window(profile.ROOT/profile.SDK,p,fixture=True)
 def test_failed_abi_validation_retains_child_logs_and_exit_status(self):
  with tempfile.TemporaryDirectory() as t:
   lib,p=self.fixture(Path(t),2640345)
   with self.assertRaises(runtime.WindowFailure) as caught:runtime.run_window(lib,p,fixture=True)
   r=caught.exception.receipt;self.assertEqual(r['status'],'FAILED');self.assertIn('CPU-owned',r['stderr']['text']);self.assertIsInstance(r['child_returncode'],int);self.assertFalse(r['native_admitted'])
 def test_runtime_namespace_caps_mount_and_cgroup_contract(self):
  host={k:k+':[1]' for k in ['pid','net','mnt']};f=dict(pid=1,uid=65534,gid=65534,cap_eff=0,cap_bnd=0,no_new_privs=1,seccomp=2,namespaces={k:k+':[2]' for k in host},mounts={p:['ro'] for p in ['/','/work/repo','/work/binding']},pids_max=32,cpu_quota=100000,cpu_period=100000);f['mounts']['/tmp']=['rw','nosuid','nodev','noexec'];runtime.check_context(f,host)
  for name,value in [('uid',0),('cap_eff',1),('no_new_privs',0),('pids_max',99),('cpu_quota',200000),('namespaces',host),('mounts',{'/':['rw']})]:
   with self.assertRaises(ValueError):runtime.check_context(dict(f,**{name:value}),host)
if __name__=='__main__':unittest.main()
