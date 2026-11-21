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


class PostEntryWindow(unittest.TestCase):
    def test_selects_only_transition_and_bend_frames_by_input_pose(self):
        from bigbench.sdk3_steering_contract import selected_steps, validate_window
        rows=[(0,59.9),(1,59.59),(1,59.8),(2,.2),(2,.6)]
        frames=[dict(step=i,route=dict(lane_index=lane,longitudinal_m=s))
                for i,(lane,s) in enumerate(rows,1)]
        trajectory=dict(frames=frames,geometry=[{},dict(length_m=60),{}])
        steps=selected_steps(trajectory)
        self.assertEqual(steps,[4,5])
        validate_window(trajectory,steps)

    def test_evidence_ends_at_terminal_and_contains_transition(self):
        from bigbench.sdk3_steering_contract import validate_window
        frames=[dict(step=i,route=dict(lane_index=lane)) for i,lane in enumerate([0,1,2,2],1)]
        for steps in ([4], [3], [2,4], []):
            with self.assertRaises(ValueError):
                validate_window(dict(frames=frames),steps)


if __name__=='__main__':
    unittest.main()
