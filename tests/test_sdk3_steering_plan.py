import json
from pathlib import Path
import tempfile
import unittest

from bigbench.sdk3_steering_contract import live_limits, modeled_activity


class RuntimeContract(unittest.TestCase):
    def test_effective_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            values = {'memory.max':'10737418240', 'memory.swap.max':'0',
                      'cpu.max':'200000 100000', 'pids.max':'128'}
            for name, value in values.items():
                (path/name).write_text(value)
            self.assertEqual(live_limits(path), values)
            for name, value in values.items():
                (path/name).write_text('max' if name!='cpu.max' else 'max 100000')
                with self.assertRaises(ValueError):
                    live_limits(path)
                (path/name).write_text(value)

    def test_counts_qualify_after_owned_progress_and_preserve_uncertainty(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertEqual(modeled_activity(folder, {'start_attempted':False})['inference_bounds'], [0,0])
            self.assertEqual(modeled_activity(folder, {'start_attempted':True})['inference_bounds'], [0,600])
            (folder/'native-child.json').write_text(json.dumps({'pid':31, 'returncode':0}))
            (folder/'model-lifecycle.json').write_text(json.dumps({'pid':31,'model_process_bounds':[1,1],
                                                                    'inference_bounds':[32,33]}))
            self.assertEqual(modeled_activity(folder, {'start_attempted':True})['inference_bounds'], [32,33])
            self.assertEqual(modeled_activity(folder, {'start_attempted':True,'ownership_unresolved':True})['inference_bounds'], [32,600])


if __name__=='__main__':
    unittest.main()
