import unittest

from bigbench.curved_lane_scenarios import SCENARIOS
from bigbench import full_s_validation
from bigbench.benchmark_results import LATERAL_CASES, MODELS
from bigbench.onnx_contract import ModelContract
from bigbench.sdk3_radius45 import tight_map_config
from scripts.sdk3_sidewalk_full_s import official_model_spec


class Radius45Tests(unittest.TestCase):
    def test_tight_case_changes_only_native_curve_radii(self):
        reference = SCENARIOS['s_curve_left_right'].map_config()
        tight = tight_map_config()
        for block in reference['config'][1:]:
            self.assertEqual(block['radius'], 55.0)
            block['radius'] = 45.0
        self.assertEqual(tight, reference)

    def test_tight_case_is_registered_for_integrated_mode_only(self):
        check = getattr(full_s_validation, 'registered_case', lambda *a, **kw: False)
        self.assertTrue(check(20261109, 's_curve_left_right_radius45', integrated=True))
        self.assertFalse(check(20261110, 's_curve_left_right_radius45', integrated=True))
        self.assertFalse(check(20261109, 's_curve_left_right_radius45'))
        self.assertNotIn((20261109, 's_curve_left_right_radius45'), LATERAL_CASES)
        self.assertTrue(check(20261110, 's_curve_right_left'))

    def test_light_speed_uses_own_identity_and_explicit_body_frame(self):
        self.assertIn('light-speed', MODELS)
        path, frame = official_model_spec('light-speed')
        self.assertEqual(frame, 'model-frd')
        contract = ModelContract.load(path)
        self.assertEqual(contract.nbytes, 792305602)
        self.assertEqual(contract.sha256, '6274eb4a3f3eb7ad1ab341d222bbba2ba709b06645dbbd15ac4971d6cb22ab21')
        self.assertEqual(MODELS['light-speed'], contract.sha256)
