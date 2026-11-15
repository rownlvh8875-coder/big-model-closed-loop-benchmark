import copy,importlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from tests.panda_sdk_dispatch_support import cpu_library
ROOT=Path(__file__).resolve().parents[1]
class ProbeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.probe=importlib.import_module('scripts.panda_sdk_dispatch_probe');cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.target=cpu_library(cls.root/'cpu');cls.identity=cls.probe.build_probe(cls.root/'probe')
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'tmp'):cls.tmp.cleanup()
 def run_probe(self,mode=0):
  code='''import ctypes,json,os,sys
sdk=ctypes.CDLL(sys.argv[1],mode=os.RTLD_NOW|os.RTLD_LOCAL)
p=ctypes.CDLL(sys.argv[2],mode=os.RTLD_NOW|os.RTLD_LOCAL)
f=p.probe_run;f.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t];f.restype=ctypes.c_int
buf=ctypes.create_string_buffer(65536);result=f(sdk._handle,int(sys.argv[3]),buf,len(buf));print(json.dumps(dict(returned=result,report=json.loads(buf.value))))
'''
  p=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(self.target),self.identity['path'],str(mode)],capture_output=True,text=True,check=True,timeout=15);return json.loads(p.stdout)
 def test_real_wrappers_replay_and_live_deletion_lifetimes(self):
  result=self.run_probe();self.assertEqual(result['returned'],0);r=result['report'];self.probe.validate_probe(r)
  self.assertEqual(r['original_calls'],22);self.assertEqual(r['sizes'],[2640344,2320]);self.assertEqual(r['pack_snapshots'],[42,0,77,0,0]);self.assertEqual(r['lifecycle'],[2,1,1,0,3,0]);self.assertEqual(r['finish'],0);self.assertEqual(r['pbo_resets'],1);self.assertEqual(r['live'],0);self.assertTrue(all(r[k] for k in ('args_ok','errno_ok','returns_ok','guards_ok')));self.assertEqual(r['bootstrap'],r['replayed']);self.assertGreater(r['bootstrap'],4);self.assertFalse(r['native_admitted'])
 def test_failed_original_switch_does_not_mutate_current_cache(self):
  r=self.run_probe(1)['report'];self.assertEqual(r['failed_switch_preserved'],1);self.assertEqual(r['finish'],0);self.assertEqual(r['pack_snapshots'],[42,0,77,0,0]);self.assertEqual(r['original_calls'],23)
 def test_downstream_error_cannot_be_promoted_to_pass(self):
  r=self.run_probe(2);self.assertNotEqual(r['returned'],0);self.assertNotEqual(r['report']['finish'],0)
  with self.assertRaises(ValueError):self.probe.validate_probe(r['report'])
 def test_guard_or_missing_forwarding_and_forged_admission_reject(self):
  r=self.run_probe()['report']
  for field,value in [('guards_ok',0),('original_calls',21),('native_admitted',True),('pack_snapshots',[42,42,77,0,0]),('lifecycle',[2,1,2,0,3,0])]:
   q=copy.deepcopy(r);q[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):self.probe.validate_probe(q)
 def test_binary_profile_mismatch_is_rejected(self):
  raw=Path(self.identity['path']).read_bytes();self.assertEqual(self.identity['nbytes'],len(raw));self.assertEqual(self.identity['profile'],self.probe.executable_profile(raw))
  with self.assertRaises(ValueError):self.probe.executable_profile(b'not ELF')
 def test_false_tool_or_input_stability_is_rejected(self):
  r=self.identity
  for field in ('tool_profiles_unchanged','project_inputs_unchanged'):
   q=copy.deepcopy(r);q[field]=False
   with self.assertRaises(ValueError):self.probe.validate_identity(q)
 def test_compiler_receives_no_repository_token(self):
  from unittest import mock
  original=self.probe.cpu.run_command
  def guarded(command,cwd,env,*args,**kwargs):
   self.assertFalse('GH_TOKEN' in env,'compiler token boundary');return original(command,cwd,env,*args,**kwargs)
  with mock.patch.dict('os.environ',{'GH_TOKEN':'unit-token-never-forward'}),mock.patch.object(self.probe.cpu,'run_command',side_effect=guarded):self.probe.build_probe(self.root/'no-secret-probe')
 def test_forwarded_argument_or_return_trace_mismatch_rejects(self):
  r=self.run_probe()['report']
  for index,column,value in [(0,1,99),(1,2,8),(5,1,2),(16,6,0)]:
   q=copy.deepcopy(r);q['trace'][index][column]=value
   with self.subTest(index=index,column=column),self.assertRaises(ValueError):self.probe.validate_probe(q)
if __name__=='__main__':unittest.main()
