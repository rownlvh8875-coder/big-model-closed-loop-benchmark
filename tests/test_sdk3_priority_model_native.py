from pathlib import Path
from types import SimpleNamespace
import subprocess,sys,tempfile,unittest
try:from scripts import sdk3_priority_model_native as h
except ImportError:h=None
class ModelNativeContracts(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'versioned official-model entry missing')
    def test_cold_isolated_help_needs_no_panda_ort_or_numpy(self):
        r=subprocess.run([sys.executable,'-I','-S','-B',h.__file__,'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--model-pair',r.stdout);self.assertNotIn('--full-rgb',r.stdout)
    def test_owned_command_keeps_case_nonce_and_versioned_source(self):
        a=SimpleNamespace(out='/out/run-0',nonce='a'*32,seed=20261110,scenario='s_curve_left_right');cmd=h.owned_child_command(a,123);self.assertTrue(cmd[4].endswith('sdk3_priority_model_native.py'));self.assertEqual(cmd[cmd.index('--server-owner')+1],'123');self.assertEqual(cmd[cmd.index('--seed')+1],'20261110');self.assertEqual(cmd[cmd.index('--nonce')+1],a.nonce);self.assertIn('--model-trial',cmd);self.assertNotIn('--full-rgb',cmd)
    def test_unregistered_case_fails_before_runtime_or_output_creation(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'not-created';r=subprocess.run([sys.executable,'-I','-S','-B',h.__file__,'--out',str(out),'--model-trial','--seed','1','--scenario','s_curve_left_right'],capture_output=True,text=True,timeout=15);self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists());self.assertIn('registered',r.stderr)
if __name__=='__main__':unittest.main()
