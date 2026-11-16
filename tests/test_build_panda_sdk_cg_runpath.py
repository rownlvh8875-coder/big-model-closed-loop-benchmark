import json,os,shlex,subprocess,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import build_panda_sdk_cg_runpath as b
from scripts import build_panda_sdk_cg_eigen as previous
from scripts.panda_sdk_link_elf import inspect_elf

class RunpathBuilderTests(unittest.TestCase):
 def test_exact_quoted_origin_environment(self):
  expected=previous.build_environment(Path('/private'));expected['LDFLAGS']="-Wl,-z,defs -Wl,--enable-new-dtags,-rpath,'$ORIGIN'"
  self.assertEqual(b.build_environment(Path('/private')),expected);self.assertEqual(b.contract()['future']['ldflags'],expected['LDFLAGS'])
  for bad in ['', '-Wl,-z,defs', expected['LDFLAGS'].replace("'$ORIGIN'",'$ORIGIN'),expected['LDFLAGS'].replace('$ORIGIN','/tmp'),expected['LDFLAGS']+' -Wl,--disable-new-dtags']:
   with self.assertRaises(ValueError):b.validate_environment(dict(expected,LDFLAGS=bad),Path('/private'))
 def test_cpu_link_emits_runpath_with_origin_unset_and_spoofed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'handwritten.c';source.write_text('int handwritten_fixture(void){return 7;}\n')
   for index,origin in enumerate(['','EXPANSION_SENTINEL']):
    target=root/('fixture'+str(index)+'.so');env=b.build_environment(root);env['ORIGIN']=origin
    command='/usr/bin/gcc -shared -fPIC '+shlex.quote(str(source))+' -o '+shlex.quote(str(target))+' '+env['LDFLAGS']
    subprocess.run(['/bin/sh','-c',command],env=env,capture_output=True,check=True);metadata=inspect_elf(target.read_bytes());self.assertEqual(metadata['runpath'],'$ORIGIN');self.assertIsNone(metadata['rpath'])
 def test_actual_link_argv_and_output_cardinality(self):
  out=Path('/cpu/build');commands=[]
  for filename in ['libpandagl.so','libpanda.so.1.10']:
   commands.append([b.TOOLS['cxx'],'-shared','-o',str(out/'sdk/lib'/filename),'handwritten.o','-Wl,-z,defs','-Wl,--enable-new-dtags,-rpath,$ORIGIN'])
  text='\n'.join(shlex.join(command) for command in commands);found=b.capture_link_commands(text,out);self.assertEqual(found,dict(candidate=commands[0],build_panda=commands[1]))
  for mutate in [lambda v:v+['-Wl,--disable-new-dtags'],lambda v:v+['-Wl,-rpath,/tmp'],lambda v:v+['-Xlinker','--rpath=/tmp'],lambda v:v+['@response'],lambda v:v+['-Wl,-z,defs'],lambda v:[x.replace('$ORIGIN','${ORIGIN}') for x in v],lambda v:[x.replace('$ORIGIN','$ORIGIN:/tmp') for x in v],lambda v:[x for x in v if x!='-shared']]:
   with self.assertRaises(ValueError):b.validate_link_command(mutate(commands[0]),out/'sdk/lib/libpandagl.so')
  for bad in [text+'\n'+shlex.join(commands[0]),shlex.join(commands[0])]:
   with self.assertRaises(ValueError):b.capture_link_commands(bad,out)
 def test_v3_guard_deadline_and_failed_command_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with patch.object(previous,'build',side_effect=AssertionError('old build called')),patch.object(previous,'compile_layout',side_effect=AssertionError('old layout called')):
    with self.assertRaises(ValueError):b.build(root,{}, {},root/'blocked',{})
   receipt=json.loads((root/'blocked/receipt.json').read_text());self.assertEqual(receipt['build_start_attempts'],0);self.assertFalse(receipt['target_execution'])
   with patch.object(b,'action_context'),patch.object(b,'verify_tools'):
    with self.assertRaises(ValueError):b.compile_layout(root,dict(root=str(root)),root/'deadline',dict(tools=b.TOOLS),deadline=time.monotonic()-1)
   receipt=json.loads((root/'deadline/receipt.json').read_text());self.assertEqual(receipt['command']['status'],'NOT_STARTED_DEADLINE');self.assertTrue(receipt['command']['owned_group_reaped'])
   with patch.object(b,'action_context'),patch.object(b,'verify_tools'),patch.object(b,'layout_command',return_value=['/no/compiler']):
    with self.assertRaises(ValueError):b.compile_layout(root,dict(root=str(root)),root/'spawn',dict(tools=b.TOOLS))
   receipt=json.loads((root/'spawn/receipt.json').read_text());self.assertEqual(receipt['command']['status'],'SPAWN_FAILED');self.assertTrue(receipt['command']['owned_group_reaped'])
 def test_action_context_rejects_v2_and_attempt_two(self):
  env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='rownlvh8875-coder/big-model-closed-loop-benchmark',GITHUB_REF_NAME=b.BRANCH,GITHUB_RUN_ATTEMPT='1')
  with patch.object(b,'ROOT',Path('/home/runner/work/cpu')),patch.dict(os.environ,env,clear=True):
   b.action_context()
   for change in [dict(GITHUB_REF_NAME=previous.BRANCH),dict(GITHUB_RUN_ATTEMPT='2'),dict(GITHUB_ACTIONS='false')]:
    with patch.dict(os.environ,change):
     with self.assertRaises(ValueError):b.action_context()
 def test_real_handwritten_descriptor_uses_own_lifecycle(self):
  from scripts import panda_sdk_cg_eigen_layout as literal
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'toy.cxx';words=[literal.MAGIC,2,8,0,1,88,104,848,3984,0x670,0x688,0x68c,1,1,16,16]
   source.write_text('\n'.join('#define '+k+' '+v for k,v in dict(HAVE_CG='1',HAVE_EIGEN='1',HAVE_X11='1',LINMATH_ALIGN='1',MEMORY_HOOK_ALIGNMENT='16').items())+'\n__attribute__((used,section(".panda_cg_layout_v2"))) const unsigned long long data[]={'+','.join(map(str,words))+'};\n__attribute__((constructor)) static void inert(){}\n')
   def cmd(include,private,out,cxx):return [cxx,'-std=gnu++11','-D_GLIBCXX_USE_CXX11_ABI=0','-MD','-c',str(source),'-o',str(out)]
   with patch.object(b,'action_context'),patch.object(b,'verify_tools'),patch.object(b,'layout_command',side_effect=cmd),patch.object(previous,'compile_layout',side_effect=AssertionError('old layout')):
    r=b.compile_layout(root,dict(root=str(root)),root/'layout',dict(tools=dict(cxx='/usr/bin/g++')))
   self.assertEqual(literal.verify_pair(Path(r['object']).read_bytes(),Path(r['descriptor']).read_bytes())['vector_alignment'],16);self.assertFalse(r['target_execution'])

if __name__=='__main__':unittest.main()
