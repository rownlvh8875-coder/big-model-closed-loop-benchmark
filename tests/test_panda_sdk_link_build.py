"""Fixed replacement flags tested with compile-only handwritten CPU sources."""
import os,shlex,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
try:from scripts import build_panda_sdk_link as build
except ImportError:build=None
ROOT=Path(__file__).resolve().parents[1]
class LinkBuildTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(build,'versioned fixed-ABI replacement builder required')
 def test_ambient_abi_and_header_flags_cannot_override_fixed_policy(self):
  with patch.dict(os.environ,{'RPM_OPT_FLAGS':'-D_GLIBCXX_USE_CXX11_ABI=1 -include poison.h','CXXFLAGS':'-D_GLIBCXX_USE_CXX11_ABI=1','CFLAGS':'-include poison.h','CPATH':'/poison'}):env=build.build_env(ROOT/'output/stage7-panda-source-dispatch-01/sysroot')
  self.assertEqual(env['RPM_OPT_FLAGS'],'-D_GLIBCXX_USE_CXX11_ABI=0 -MD');self.assertNotIn('CXXFLAGS',env);self.assertNotIn('CFLAGS',env);self.assertNotIn('CPATH',env)
  with tempfile.TemporaryDirectory() as t:
   for compiler,ext in [('/usr/bin/gcc','c'),('/usr/bin/g++','cxx')]:
    p=Path(t)/('owned.'+ext);p.write_text('#if _GLIBCXX_USE_CXX11_ABI != 0\n#error wrong ABI\n#endif\nint owned(void){return 7;}\n');obj=p.with_suffix('.o');r=subprocess.run([compiler,*shlex.split(env['RPM_OPT_FLAGS']),'-c',str(p),'-o',str(obj)],env=env,capture_output=True,timeout=10);self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(obj.with_suffix('.d').is_file())
 def test_every_compile_requires_single_literal_abi_and_dependency_flags(self):
  good=['/usr/bin/g++','-c','-o','owned.o','-D_GLIBCXX_USE_CXX11_ABI=0','-MD','owned.cxx'];build.verify_compile_command(good)
  for cmd in [good[:4]+good[5:],good+['-D_GLIBCXX_USE_CXX11_ABI=1'],good+['-D_GLIBCXX_USE_CXX11_ABI=0'],[x for x in good if x!='-MD'],good+['-MD']]:
   with self.assertRaises(ValueError):build.verify_compile_command(cmd)
 def test_existing_build_output_is_preserved(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'keep').write_bytes(b'old')
   with self.assertRaises(ValueError):build.build(p,p,p)
   self.assertEqual((p/'keep').read_bytes(),b'old')
 def test_preprocessing_keeps_abi_and_rejects_missing_or_overridden_policy(self):
  from scripts import panda_sdk_link_coverage as coverage
  command=['/usr/bin/g++','-c','-o','x.o','-D_GLIBCXX_USE_CXX11_ABI=0','-MD','x.cxx']
  with patch.object(coverage.previous,'preprocess',return_value=(b'CPU',{})) as run:
   coverage.preprocess_recorded(command,Path('/tmp'),{},Path('/tmp/unused'))
   self.assertIn('-D_GLIBCXX_USE_CXX11_ABI=0',run.call_args.args[0]);self.assertNotIn('-MD',run.call_args.args[0])
   for bad in ([x for x in command if '_GLIBCXX_USE_CXX11_ABI' not in x],command+['-D_GLIBCXX_USE_CXX11_ABI=1']):
    with self.assertRaises(ValueError):coverage.preprocess_recorded(bad,Path('/tmp'),{},Path('/tmp/unused'))
if __name__=='__main__':unittest.main()
