from pathlib import Path
from types import SimpleNamespace
import subprocess,sys,tempfile,unittest
try:from scripts import sdk3_four_validation_native as n
except ImportError:n=None
class NativeBoundaryContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(n,'owned four-validation native entry missing')
 def test_cold_help_has_no_optional_runtime_import(self):
  r=subprocess.run([sys.executable,'-I','-S','-B',n.__file__,'--help'],capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,0,r.stderr)
 def test_probe_and_model_child_commands_keep_exact_entry_case_and_owner(self):
  for model in (False,True):
   a=SimpleNamespace(out='/out/case',nonce='a'*32,seed=20261109,scenario='s_curve_left_right',model_trial=model);cmd=n.owned_child_command(a,123);self.assertIn('--owned-child',cmd);self.assertEqual(cmd[cmd.index('--server-owner')+1],'123');self.assertIn('--model-trial' if model else '--probe',cmd);self.assertEqual(cmd[4],str(Path(n.__file__).resolve()));self.assertFalse(any('drawtrace' in x or 'full-rgb' in x for x in cmd))
 def test_probe_launch_gets_fresh_nonce_and_owned_child_cannot_rebind_it(self):
  a=SimpleNamespace(nonce='0'*32,owned_child=False,model_pair=False);n.prepare_nonce(a);self.assertEqual(len(a.nonce),32);self.assertNotEqual(a.nonce,'0'*32)
  child=SimpleNamespace(nonce='0'*32,owned_child=True,model_pair=False)
  with self.assertRaises(ValueError):n.prepare_nonce(child)
 def test_invalid_case_cannot_start_child_or_create_output(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'must-not-exist';r=subprocess.run([sys.executable,'-I','-S','-B',n.__file__,'--probe','--out',str(out),'--seed','1','--scenario','s_curve_left_right'],capture_output=True,text=True,timeout=10);self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
