import copy,importlib,json,tempfile,unittest
from pathlib import Path
from tests.panda_sdk_dispatch_support import cpu_library
from scripts import panda_sdk_dispatch_probe as probe
class RuntimeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.runtime=importlib.import_module('scripts.panda_sdk_dispatch_runtime');cls.profile=importlib.import_module('scripts.panda_sdk_dispatch_profile');cls.policy=importlib.import_module('scripts.panda_sdk_dispatch_policy');cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.lib=cpu_library(cls.root/'cpu');cls.q=probe.build_probe(cls.root/'probe');cls.p=cls.profile.make_profile(cls.lib.read_bytes(),fixture=True)
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'tmp'):cls.tmp.cleanup()
 def test_owned_real_cpu_code_and_integrated_probe(self):
  r=self.runtime.run_window(self.lib,self.p,probe_identity=self.q,fixture=True);self.runtime.validate_window(self.p,r);self.assertEqual(r['status'],'SELECTED_DISPATCH_ABI_OBSERVED');self.assertEqual(r['child']['probe']['original_calls'],22);self.assertTrue(r['before']['code']['process_code_verified']);self.assertTrue(r['probe_before']['code']['process_code_verified']);self.assertEqual(r['child']['probe_invocations'],1);self.assertFalse(r['image_and_probe_membership_verified']);self.assertFalse(r['native_admitted'])
 def test_wrong_probe_file_and_alias_are_rejected_before_loading(self):
  q=copy.deepcopy(self.q);q['sha256']='0'*64
  with self.assertRaises(ValueError):self.runtime.run_window(self.lib,self.p,probe_identity=q,fixture=True)
  alias=self.root/'alias.so'
  if not alias.exists():alias.symlink_to(self.q['path'])
  q=copy.deepcopy(self.q);q['path']=str(alias)
  with self.assertRaises(ValueError):self.runtime.run_window(self.lib,self.p,probe_identity=q,fixture=True)
 def test_production_sdk_cannot_enter_fixture_or_local_actual_mode(self):
  data=(self.policy.ROOT/self.policy.SDK).read_bytes();p=self.profile.make_profile(data)
  with self.assertRaises(ValueError):self.runtime.run_window(self.policy.ROOT/self.policy.SDK,p,probe_identity=self.q,fixture=True)
  with self.assertRaises(ValueError):self.runtime.run_window(self.lib,self.p,probe_identity=self.q,fixture=False)
 def test_tampered_parent_code_wrapper_address_and_source_fail_closed(self):
  r=self.runtime.run_window(self.lib,self.p,probe_identity=self.q,fixture=True)
  for kind in ('nonce','sdkcode','probecode','wrapper','original','count'):
   q=copy.deepcopy(r)
   if kind=='nonce':q['child']['nonce']='0'*32
   elif kind=='sdkcode':q['after']['code']['ranges']['sdk_text_1']['sha256']='0'*64
   elif kind=='probecode':next(iter(q['probe_after']['code']['ranges'].values()))['sha256']='0'*64
   elif kind=='wrapper':q['child']['probe']['wrappers'][0]=1
   elif kind=='original':q['child']['probe']['originals'][0]=1
   else:q['child']['probe_invocations']=2
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.runtime.validate_window(self.p,q)
 def test_timeout_keeps_failed_owned_process_evidence(self):
  with self.assertRaises(self.runtime.WindowFailure) as caught:self.runtime.run_window(self.lib,self.p,probe_identity=self.q,fixture=True,timeout=.001)
  self.assertEqual(caught.exception.receipt['status'],'FAILED');self.assertFalse(caught.exception.receipt['native_admitted'])
 def test_new_request_rejects_consumed_mapping_scope_and_changed_budget(self):
  a=self.policy;request=a.request_template('a'*40,[dict(event='push',run_id=1),dict(event='pull_request',run_id=2)],a.ROOT);a.validate_request(request,a.ROOT)
  for kind in ('request_id','permissions','budget','mapping_pin'):
   q=copy.deepcopy(request)
   if kind=='request_id':q[kind]='panda-sdk-mapping-20261115-01'
   elif kind=='permissions':q[kind]['render']=True
   elif kind=='budget':q[kind]['probe_loads']=2
   else:q['mapping_acceptance_sha256']='0'*64
   with self.subTest(kind=kind),self.assertRaises(ValueError):a.validate_request(q,a.ROOT)
 def test_failed_real_probe_keeps_return_and_structured_report(self):
  import shutil
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);native=root/'native';shutil.copytree(self.policy.ROOT/'native/panda_sdk_routes_v2',native);p=native/'panda_cache_adapter.cxx';text=p.read_text();self.assertIn('return error(d)?-1:0;',text);p.write_text(text.replace('return error(d)?-1:0;','return -1;'));lib=cpu_library(root/'cpu',native);profile=self.profile.make_profile(lib.read_bytes(),fixture=True)
   with self.assertRaises(self.runtime.WindowFailure) as caught:self.runtime.run_window(lib,profile,probe_identity=self.q,fixture=True)
   r=caught.exception.receipt;self.assertEqual(r['child']['probe_returned'],-17);self.assertEqual(r['child']['probe']['finish'],-1);self.assertEqual(r['child']['probe']['original_calls'],22);self.assertFalse(r['native_admitted'])
if __name__=='__main__':unittest.main()
