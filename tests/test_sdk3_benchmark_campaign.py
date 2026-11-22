import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from bigbench import benchmark_dashboard
from bigbench import benchmark_results
from bigbench.first_divergence import source_snapshot
from bigbench.longitudinal_world import scenario
from bigbench.sdk3_longitudinal import run_longitudinal_benchmark
from bigbench.kinematics import ModelAction
from scripts import sdk3_sidewalk_full_s
from tests.test_native_longitudinal import FakeCamera, FakePolicy


class Sdk3CampaignTests(unittest.TestCase):
    def test_comparison_keeps_the_historical_source_pin_registry_valid(self):
        try:
            snapshot = source_snapshot()
        except ValueError as error:
            self.fail(str(error))
        self.assertIn('bigbench/native_longitudinal.py', snapshot)
        self.assertIn('bigbench/dashboard.py', snapshot)

    def test_light_speed_2_resolves_a_distinct_pinned_contract(self):
        self.assertTrue(hasattr(sdk3_sidewalk_full_s, 'official_model_spec'))
        official_model_spec = sdk3_sidewalk_full_s.official_model_spec
        first, _ = official_model_spec('md-v3')
        second, frame = official_model_spec('light-speed-2')

        self.assertNotEqual(first, second)
        self.assertEqual(second.name, 'light-speed-2.json')
        self.assertEqual(frame, 'model-frd')
        with self.assertRaises(ValueError):
            official_model_spec('n16')

    def test_longitudinal_candidate_stops_at_first_nonpositive_gap(self):
        class DrivingPolicy(FakePolicy):
            def step(self, observation):
                return ModelAction(curvature_1pm=0.0, acceleration_mps2=2.0)

        events = []
        report = run_longitudinal_benchmark(
            DrivingPolicy(), scenario('lead_brake'), FakeCamera(), steps=400,
            progress=events.append,
        )

        self.assertEqual(report['termination'], 'LEAD_GAP_NONPOSITIVE')
        self.assertLess(report['steps_completed'], 400)
        self.assertLessEqual(report['trace'][-1]['gap_m'], 0)
        self.assertTrue(all(row['gap_m'] > 0 for row in report['trace'][:-1]))
        self.assertEqual(events[-1]['status'], 'STEP_COMMITTED')

    def test_benchmark_dashboard_preserves_failed_and_pending_verdicts(self):
        self.assertTrue(hasattr(benchmark_dashboard, 'render_benchmark_dashboard'))
        report = {
            'lateral': [{
                'seed': 20261109, 'scenario': 's_curve_left_right', 'comparable': None,
                'models': {
                    'md-v3': {'traversal_passed': False, 'strict_repeat_passed': True,
                              'runs': [{'outcome':'LANE_INTRUSION', 'steps':298, 'intrusion_m':.003}]},
                    'light-speed-2': {'traversal_passed':None, 'strict_repeat_passed':None, 'runs':[]},
                },
            }],
            'longitudinal': [],
        }
        html = benchmark_dashboard.render_benchmark_dashboard(report)

        self.assertIn('LANE_INTRUSION', html)
        self.assertIn('298', html)
        self.assertIn('미판정', html)
        self.assertIn('Light Speed 2', html)

    def test_model_receipt_cannot_borrow_a_camera_gate_with_another_first_frame(self):
        self.assertTrue(hasattr(benchmark_results,'verify_camera_admission'))
        doc = dict(geometry=['lane'],intrinsics={'road':'lens'},driver={'renderer':'llvmpipe'},
                   input_variant='source_yuv_nearest_even')
        first = dict(source_sha256={'road':'a','wide':'b'},canvas_sha256=['c','d'],
                     actual_tensor_sha256='e')
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/'camera-admission.json'
            path.write_text(json.dumps(dict(doc,rows=[dict(first,actual_tensor_sha256='other')])))
            with self.assertRaisesRegex(ValueError,'qualified first'):
                benchmark_results.verify_camera_admission(path,doc,first)


if __name__ == '__main__':
    unittest.main()
