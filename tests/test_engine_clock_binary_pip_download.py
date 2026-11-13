"""Pip source/origin gate fixtures; no real package preparation or network."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
try:
 from scripts import engine_clock_binary_pip_download as b
except ImportError:b=None

class BinaryGateTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(b,'binary-only preparation gate missing')
 def link(self,**kwargs):
  return SimpleNamespace(is_wheel=True,is_file=False,url_without_fragment='https://files.pythonhosted.org/packages/x/pkg-1-py3-none-any.whl',filename='pkg-1-py3-none-any.whl',**kwargs)
 def test_public_wheel_allowed_source_vcs_and_other_origin_rejected(self):
  gate=b.Gate(Path('/fixture'))
  gate.check(SimpleNamespace(link=self.link()))
  for values in ({'is_wheel':False},{'url_without_fragment':'https://SECRET@files.pythonhosted.org/pkg-1-py3-none-any.whl'},{'url_without_fragment':'https://evil.invalid/pkg-1-py3-none-any.whl'}):
   link=self.link()
   for k,v in values.items():setattr(link,k,v)
   with self.assertRaisesRegex(ValueError,'^WHEEL_ONLY_[A-Z_]+$'):gate.check(SimpleNamespace(link=link))
  self.assertEqual(3,len(gate.facts['rejections']))
 def test_only_registered_local_inputs_allowed(self):
  root=Path('/fixture');gate=b.Gate(root)
  for rel in b.LOCAL_RELATIVE:
   p=str(root/rel);link=self.link();link.is_file=True;link.file_path=p;link.url_without_fragment=Path(p).as_uri();link.filename=Path(p).name;gate.check(SimpleNamespace(link=link))
  link=self.link();link.is_file=True;link.file_path='/SECRET.whl';link.url_without_fragment='file:///SECRET.whl'
  with self.assertRaisesRegex(ValueError,'^WHEEL_ONLY_LOCAL_INPUT_REJECTED$'):gate.check(SimpleNamespace(link=link))
 def test_wrappers_block_before_original_and_restore_all_methods(self):
  calls=[]
  class Preparer:
   def prepare_linked_requirement(self,req,*args,**kwargs):calls.append('linked');return 7
   def prepare_linked_requirements_more(self,reqs,*args,**kwargs):calls.append('batch');return 8
   def prepare_editable_requirement(self,req,*args,**kwargs):calls.append('editable');return 9
  originals={k:Preparer.__dict__[k] for k in ('prepare_linked_requirement','prepare_linked_requirements_more','prepare_editable_requirement')};gate=b.Gate(Path('/fixture'));good=SimpleNamespace(link=self.link());bad=SimpleNamespace(link=SimpleNamespace(is_wheel=False))
  with b.protect(Preparer,gate):
   p=Preparer();self.assertEqual(7,p.prepare_linked_requirement(good));self.assertEqual(8,p.prepare_linked_requirements_more([good]))
   for fn,args in ((p.prepare_linked_requirement,(bad,)),(p.prepare_linked_requirements_more,([bad],)),(p.prepare_editable_requirement,(good,))):
    with self.assertRaises(ValueError):fn(*args)
  self.assertEqual(['linked','batch'],calls)
  for k,v in originals.items():self.assertIs(v,Preparer.__dict__[k])
  self.assertTrue(gate.facts['gate_restored'])
 def test_restore_on_callback_exception(self):
  class Preparer:
   def prepare_linked_requirement(self,*args):raise RuntimeError('owned')
   def prepare_linked_requirements_more(self,*args):pass
   def prepare_editable_requirement(self,*args):pass
  old=Preparer.prepare_linked_requirement;gate=b.Gate(Path('/fixture'))
  with self.assertRaises(RuntimeError):
   with b.protect(Preparer,gate):Preparer().prepare_linked_requirement(SimpleNamespace(link=self.link()))
  self.assertIs(old,Preparer.prepare_linked_requirement);self.assertTrue(gate.facts['gate_restored'])
 def test_real_download_option_parser_validates_without_editable_option(self):
  from scripts import engine_clock_python_wheel_preparation as op
  root=Path(__file__).resolve().parent.parent;out=root/op.OUTPUT
  cmd=op.pip_argv(root,{'root_requirements':op.expected_roots(root)},out)
  b.validate_cli(cmd[cmd.index('--')+1:],out)
 def test_real_trusted_pip_reads_owned_wheel_with_gate_without_network(self):
  from test_engine_clock_python_wheel_closure import make_wheel
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=make_wheel(root);dest=root/'dest';dest.mkdir();repo=Path(__file__).resolve().parent.parent
   script="""import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from scripts.engine_clock_binary_pip_download import Gate,protect
from pip._internal.cli.main import main
from pip._internal.operations.prepare import RequirementPreparer
root=Path(sys.argv[2]);gate=Gate(root);gate.local.add(sys.argv[3])
with protect(RequirementPreparer,gate):code=main(['--isolated','--disable-pip-version-check','--no-input','--no-cache-dir','download','--no-index','--no-deps','--only-binary=:all:','--dest',sys.argv[4],sys.argv[3]])
print(json.dumps({'code':code,'facts':gate.facts}))
"""
   result=subprocess.run([sys.executable,'-I','-B','-c',script,str(repo),str(root),str(path),str(dest)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=True)
   facts=json.loads(result.stdout.decode().splitlines()[-1]);self.assertEqual(0,facts['code']);self.assertTrue(facts['facts']['gate_restored']);self.assertGreater(facts['facts']['requirements_checked'],0);self.assertTrue((dest/path.name).is_file())
 def test_real_pip_source_candidate_blocked_before_owned_setup_runs(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source';source.mkdir();(source/'setup.py').write_text('from pathlib import Path\nPath(__file__).with_name("SOURCE_EXECUTED").write_text("unexpected")\nraise RuntimeError("owned fixture")\n');dest=root/'dest';dest.mkdir();repo=Path(__file__).resolve().parent.parent
   script="""import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from scripts.engine_clock_binary_pip_download import Gate,protect
from pip._internal.cli.main import main
from pip._internal.operations.prepare import RequirementPreparer
gate=Gate(Path(sys.argv[2]))
with protect(RequirementPreparer,gate):code=main(['--isolated','--disable-pip-version-check','--no-input','--no-cache-dir','download','--no-index','--no-deps','--only-binary=:all:','--dest',sys.argv[4],sys.argv[3]])
print(json.dumps({'code':code,'facts':gate.facts}))
"""
   result=subprocess.run([sys.executable,'-I','-B','-c',script,str(repo),str(root),str(source),str(dest)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=True)
   facts=json.loads(result.stdout.decode().splitlines()[-1]);self.assertNotEqual(0,facts['code']);self.assertIn('WHEEL_ONLY_SOURCE_REJECTED',facts['facts']['rejections']);self.assertFalse((source/'SOURCE_EXECUTED').exists());self.assertTrue(facts['facts']['gate_restored'])

 def test_parent_and_child_registered_inputs_stay_identical(self):
  from scripts import engine_clock_python_wheel_preparation as op
  self.assertEqual(set(b.LOCAL_RELATIVE),{r['path'] for r in op.LOCAL_INPUTS})

if __name__=='__main__':unittest.main()
