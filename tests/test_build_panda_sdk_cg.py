import json,os,sys,tempfile,unittest
from pathlib import Path
from scripts import build_panda_sdk_cg as b
class BuildTests(unittest.TestCase):
 def test_cg_command_and_dependency_closure(self):
  cmd=b.build_command(Path('/src'),Path('/private'),Path('/new'),'/usr/bin/python3')
  for flag in ['--nothing','--use-nvidiacg','--nvidiacg-incdir','--nvidiacg-libdir','--cggl-incdir','--cggl-libdir','--no-python']:self.assertIn(flag,cmd)
  self.assertEqual(cmd[cmd.index('--threads')+1],'2');env=b.build_environment(Path('/private'));self.assertEqual(env['RPM_OPT_FLAGS'],'-D_GLIBCXX_USE_CXX11_ABI=0 -MD');self.assertEqual(env['CC'],'/usr/bin/gcc-13');self.assertNotIn('GH_TOKEN',env);self.assertNotIn('CFLAGS',env)
  b.verify_compile(['g++','-D_GLIBCXX_USE_CXX11_ABI=0','-MD','-c','a.cxx'])
  for flags in [[],['-MD'],['-MD','-D_GLIBCXX_USE_CXX11_ABI=1'],['-MD','-D_GLIBCXX_USE_CXX11_ABI=0','-D_GLIBCXX_USE_CXX11_ABI=0']]:
   with self.assertRaises(ValueError):b.verify_compile(flags)
 def test_owned_failed_spawn_and_timeout_retained(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);r=b.run_owned(['/no/such/compiler'],root,{},root/'spawn',1);self.assertEqual(r['status'],'SPAWN_FAILED');self.assertIsNone(r['returncode']);self.assertTrue((root/'spawn/command.json').exists())
   r=b.run_owned([sys.executable,'-B','-c','import time;print("started",flush=True);time.sleep(10)'],root,{},root/'timeout',.2);self.assertEqual(r['status'],'TIMEOUT');self.assertTrue(r['owned_group_reaped']);self.assertIn(b'started',(root/'timeout/stdout.log').read_bytes())
 def test_stream_limits_and_nonzero_command_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);r=b.run_owned([sys.executable,'-B','-c','import sys;print("bad",file=sys.stderr);sys.exit(3)'],root,{},root/'bad',2);self.assertEqual(r['returncode'],3);self.assertEqual(r['status'],'EXITED');self.assertTrue(r['streams_complete'])
   r=b.run_owned([sys.executable,'-B','-c','import sys;sys.stdout.write("x"*1000000)'],root,{},root/'large',2,stream_limit=100);self.assertEqual(r['status'],'OUTPUT_LIMIT');self.assertLessEqual((root/'large/stdout.log').stat().st_size,100)
 def test_local_target_build_rejected_before_start_with_receipt(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with self.assertRaises(ValueError):b.build(root,{},root/'out',{})
   r=json.loads((root/'out/receipt.json').read_text());self.assertEqual(r['build_start_attempts'],0);self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['target_execution'])
 def test_compile_only_layout_arguments(self):
  cmd=b.layout_command(Path('/inc'),Path('/private'),Path('/obj'),'/usr/bin/g++-13');self.assertIn('-c',cmd);self.assertIn('-fno-access-control',cmd);self.assertIn('-Wno-invalid-'+'offsetof',cmd);self.assertNotIn('-shared',cmd);self.assertEqual(cmd[-1],'/obj')
 def test_missing_tools_and_changed_record_fail(self):
  with self.assertRaises(ValueError):b.measure_tools({'cc':'/missing/compiler'})
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'tool';p.write_text('old');row=b.record(p);p.write_text('new')
   with self.assertRaises(ValueError):b.verify_records({str(p):row})
if __name__=='__main__':unittest.main()

class InputClosureTests(unittest.TestCase):
 def test_private_alias_and_unregistered_gl_header_reject(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'real').write_text('kept');(root/'alias').symlink_to('real');before=b.private_tree(root);(root/'alias').unlink();(root/'alias').symlink_to('/usr/include/stdio.h')
   with self.assertRaises(ValueError):b.private_tree(root)
   self.assertIn('alias',before)
  for name in ['/usr/include/GL/gl.h','/usr/include/Cg/cg.h','/usr/include/X11/Xlib.h','/usr/include/x86_64-linux-gnu/X11/XlibConf.h']:
   with self.assertRaises(ValueError):b.validate_declared_headers([dict(path=name,origin='host')])
  b.validate_declared_headers([dict(path='/private/usr/include/GL/gl.h',origin='private'),dict(path='/usr/include/stdio.h',origin='host')])

class CompileOnlyCpuTests(unittest.TestCase):
 def test_handwritten_cpu_object_is_data_and_never_executed(self):
  import shutil,struct
  compiler=shutil.which('g++')
  if compiler is None:self.skipTest('host C++ compiler unavailable')
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);src=root/'layout.cxx';obj=root/'layout.o';src.write_text('struct Toy { private: int value; };\nextern "C" __attribute__((used,section(".panda_cg_layout"))) const unsigned long long toy_layout[]={sizeof(Toy),__builtin_offsetof(Toy,value)};\n')
   cmd=[compiler,'-fno-access-control','-Wno-invalid-'+'offsetof','-c',str(src),'-o',str(obj)];r=b.run_owned(cmd,root,{'PATH':'/usr/bin:/bin'},root/'compile',15);self.assertEqual(r['returncode'],0);self.assertEqual(struct.unpack_from('<H',obj.read_bytes(),16)[0],1);self.assertIn(b'.panda_cg_layout',obj.read_bytes());self.assertFalse((root/'a.out').exists())

class FailedToolProfileTests(unittest.TestCase):
 def test_failed_tool_preflight_retains_partial_identity_record(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'profile.json'
   with self.assertRaises(ValueError):b.measure_tools({'cc':'/missing/compiler'},out=p)
   r=json.loads(p.read_text());self.assertEqual(r['status'],'FAILED');self.assertEqual(r['tools']['cc'],'/missing/compiler');self.assertIn('failure',r)
