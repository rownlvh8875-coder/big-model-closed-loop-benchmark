import json,tempfile,unittest
from pathlib import Path
from scripts import build_panda_sdk_cg_eigen as b
class BuilderTests(unittest.TestCase):
 def test_eigen_command_and_effective_alignment(self):
  cmd=b.build_command(Path('/source'),Path('/private'),Path('/out'),'/usr/bin/python3');self.assertIn('--use-eigen',cmd);self.assertEqual(cmd[cmd.index('--eigen-incdir')+1],'/private/usr/include/eigen3');self.assertIn('--use-nvidiacg',cmd);self.assertEqual(cmd[cmd.index('--threads')+1],'2');self.assertEqual(b.build_environment(Path('/private'))['RPM_OPT_FLAGS'],'-D_GLIBCXX_USE_CXX11_ABI=0 -MD')
  generated=dict(HAVE_CG='1',HAVE_EIGEN='1',HAVE_X11='1',HAVE_PYTHON=False,STDFLOAT_DOUBLE=False,LINMATH_ALIGN='1');b.validate_generated(generated)
  with self.assertRaises(ValueError):b.validate_generated(dict(generated,HAVE_EIGEN=False))
  good={'HAVE_CG':'1','HAVE_EIGEN':'1','HAVE_X11':'1','LINMATH_ALIGN':'1','MEMORY_HOOK_ALIGNMENT':'16','_GLIBCXX_USE_CXX11_ABI':'0'};b.validate_effective(good)
  for change in [dict(LINMATH_ALIGN=None),dict(HAVE_EIGEN=None),dict(MEMORY_HOOK_ALIGNMENT='8'),dict(STDFLOAT_DOUBLE='1')]:
   x=dict(good);x.update(change)
   with self.assertRaises(ValueError):b.validate_effective(x)
 def test_host_eigen_origin_and_layout_command(self):
  for name in ['/usr/include/eigen3/Eigen/Core','/usr/local/include/Eigen/Core','/usr/include/Eigen/Core']:
   with self.assertRaises(ValueError):b.validate_declared_headers([dict(path=name,origin='host')])
  b.validate_declared_headers([dict(path='/private/usr/include/eigen3/Eigen/Core',origin='private')]);cmd=b.layout_command(Path('/include'),Path('/private'),Path('/object'),'/usr/bin/g++-13');self.assertIn('-c',cmd);self.assertIn('-I/private/usr/include/eigen3',cmd);self.assertIn('-fno-access-control',cmd);self.assertIn('panda_sdk_cg_v2/layout_contract.cxx',' '.join(cmd))
 def test_local_target_guard_and_failed_owned_process(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with self.assertRaises(ValueError):b.build(root,{}, {},root/'blocked',{})
   r=json.loads((root/'blocked/receipt.json').read_text());self.assertEqual(r['build_start_attempts'],0);self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['target_execution'])
   proc=b.run_owned(['/no/compiler'],root,{},root/'spawn',1);self.assertEqual(proc['status'],'SPAWN_FAILED');self.assertTrue(proc['owned_group_reaped'])
if __name__=='__main__':unittest.main()

class CpuDescriptorProcessTests(unittest.TestCase):
 def test_real_handwritten_parent_and_macro_dump_never_execute_target(self):
  from unittest.mock import patch
  from scripts import panda_sdk_cg_eigen_layout as literal
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'toy.cxx';words=[literal.MAGIC,2,8,0,1,88,104,848,3984,0x670,0x688,0x68c,1,1,16,16];source.write_text('\n'.join('#define '+k+' '+v for k,v in dict(HAVE_CG='1',HAVE_EIGEN='1',HAVE_X11='1',LINMATH_ALIGN='1',MEMORY_HOOK_ALIGNMENT='16').items())+'\n__attribute__((used,section(".panda_cg_layout_v2"))) const unsigned long long data[]={'+','.join(map(str,words))+'};\n__attribute__((constructor)) static void unused(){}\n')
   def command(include,private,out,cxx):return [cxx,'-std=gnu++11','-D_GLIBCXX_USE_CXX11_ABI=0','-MD','-c',str(source),'-o',str(out)]
   with patch.object(b,'action_context'),patch.object(b,'verify_tools'),patch.object(b,'layout_command',side_effect=command):r=b.compile_layout(root,dict(root=str(root)),root/'layout',dict(tools=dict(cxx='/usr/bin/g++')))
   self.assertTrue(r['effective_configuration']['vector_alignment']==16);self.assertEqual(literal.verify_pair(Path(r['object']).read_bytes(),Path(r['descriptor']).read_bytes())['offsets'],dict(vendor=0x670,major=0x688,minor=0x68c));self.assertFalse(r['target_execution']);self.assertFalse((root/'a.out').exists())
 def test_failed_layout_command_is_saved_before_raising(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with patch.object(b,'action_context'),patch.object(b,'verify_tools'):
    with self.assertRaises(ValueError):b.compile_layout(root,dict(root=str(root)),root/'layout',dict(tools=dict(cxx='/usr/bin/false')))
   r=json.loads((root/'layout/receipt.json').read_text());self.assertEqual(r['command']['returncode'],1);self.assertIn('-c',r['command']['argv']);self.assertTrue(r['command']['owned_group_reaped'])

class WholeCompileDeadlineTests(unittest.TestCase):
 def test_elapsed_sdk_budget_blocks_descriptor_before_spawn(self):
  import time
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with patch.object(b,'action_context'),patch.object(b,'verify_tools'),patch.object(b,'run_owned',side_effect=AssertionError('must not spawn')):
    with self.assertRaises(ValueError):b.compile_layout(root,dict(root=str(root)),root/'layout',dict(tools=dict(cxx='/usr/bin/false')),deadline=time.monotonic()-1)
   r=json.loads((root/'layout/receipt.json').read_text());self.assertEqual(r['command']['status'],'NOT_STARTED_DEADLINE');self.assertIsNone(r['command']['returncode']);self.assertFalse(r['target_execution'])
