from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
try:from scripts import sdk3_four_validation_runtime as r
except ImportError:r=None
from scripts import panda_sdk3_runtime as p
class RuntimeContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(r,'owned four-validation runtime missing')
 def test_probe_has_only_source_sdk_output_and_no_model_or_debug_preload(self):
  cmd=r.native_command('test',Path('/repo'),Path('/sdk'),Path('/out'),['--probe'],owner='a'*32);self.assertIn(r.ENTRY,cmd);self.assertIn('GALLIUM_DRIVER=llvmpipe',cmd);self.assertIn('LP_NUM_THREADS=2',cmd);self.assertEqual(cmd[cmd.index('--memory')+1],'10g');self.assertEqual(cmd[cmd.index('--cpus')+1],'2');self.assertEqual(cmd.count('--mount'),3);self.assertFalse(any('LD_PRELOAD' in x or 'LD_DEBUG' in x or '/model.onnx' in x for x in cmd))
 def test_model_command_has_same_profile_and_readonly_weights_deps(self):
  cmd=r.native_command('test',Path('/repo'),Path('/sdk'),Path('/out'),['--model-pair'],model=Path('/weights'),deps=Path('/deps'),owner='a'*32);self.assertEqual(cmd.count('--mount'),5);self.assertIn('type=bind,src=/weights,dst=/model.onnx,readonly',cmd);self.assertIn(p.IMAGE,cmd)
 def test_existing_unowned_container_is_never_removed(self):
  with tempfile.TemporaryDirectory() as d,patch.object(r,'inspect_container',return_value={'Id':'foreign','Config':{'Labels':{}}}),patch.object(r.subprocess,'run') as run:
   result=r.run_container('occupied',Path('/sdk'),Path(d)/'out',['--probe']);self.assertIsNotNone(result['failure']);self.assertFalse(result['create_attempted']);run.assert_not_called()
if __name__=='__main__':unittest.main()
