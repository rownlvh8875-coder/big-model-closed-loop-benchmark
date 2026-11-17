from pathlib import Path
import importlib,subprocess,sys,unittest
from scripts import run_sdk3_terrain_state as original
ROOT=Path(__file__).resolve().parents[1]
class RecoveryEntry(unittest.TestCase):
    def test_recovery_host_help_has_run_without_starting_renderer(self):
        p=ROOT/'scripts/run_sdk3_terrain_state_v2.py';r=subprocess.run([sys.executable,'-I','-B',str(p),'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--run',r.stdout)
    def test_recovery_keeps_identical_native_command_and_receipt_validator(self):
        recovery=importlib.import_module('scripts.run_sdk3_terrain_state_v2')
        args=('fixture',ROOT,Path('/fixture/sdk'),Path('/fixture/out'),['--repeat','0','--nonce','fixture']);kwargs=dict(reference=Path('/fixture/reference'),owner='fixture-owner')
        self.assertEqual(recovery.native_command(*args,**kwargs),original.native_command(*args,**kwargs));self.assertIs(recovery.validate_receipt,original.validate_receipt)
if __name__=='__main__':unittest.main()
