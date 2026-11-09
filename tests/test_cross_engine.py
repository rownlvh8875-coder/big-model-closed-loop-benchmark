"""Cross-renderer test doubles; not independent CARLA rendering evidence."""
import unittest
from bigbench.cross_engine import (
    EngineReceipt,LandmarkMeasurement,CrossEngineError,compare_engine_landmarks,
)


def fake(engine, *, offset=0., real=True, scenario='same-map'):
    return EngineReceipt(engine,'test-build',scenario,'ideal-pinhole-512x256',
                         tuple(LandmarkMeasurement('L'+str(i),100+i+offset,150+i)
                               for i in range(8)),real)


class CrossEngineContractTests(unittest.TestCase):
    def test_distinct_engine_and_same_geometry_can_be_evaluated(self):
        report=compare_engine_landmarks(fake('metadrive'),fake('carla',offset=.2))
        self.assertEqual(report['matched_landmarks'],8)
        self.assertEqual(report['status'],'CROSS_ENGINE_LANDMARK_GATE_PASS')
        self.assertFalse(report['model_scoring_allowed'])

    def test_identical_engine_is_not_independent(self):
        with self.assertRaises(CrossEngineError):
            compare_engine_landmarks(fake('metadrive'),fake('metadrive'))

    def test_missing_real_renderer_receipt_fails(self):
        with self.assertRaises(CrossEngineError):
            compare_engine_landmarks(fake('metadrive',real=False),fake('carla'))

    def test_mismatch_and_wrong_scenario_are_visible(self):
        self.assertEqual(compare_engine_landmarks(fake('metadrive'),fake('carla',offset=20))['status'],
                         'CROSS_ENGINE_LANDMARK_MISMATCH')
        with self.assertRaises(CrossEngineError):
            compare_engine_landmarks(fake('metadrive'),fake('carla',scenario='different'))


if __name__=='__main__':unittest.main()
