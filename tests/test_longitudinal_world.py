"""Synthetic longitudinal evaluation math, not real ONNX or road evidence."""
from __future__ import annotations

import unittest
from bigbench.longitudinal_world import (
    LeadEvent, LongitudinalContractError, LongitudinalScenario,
    run_longitudinal_actions,scenario
)


class LongitudinalTests(unittest.TestCase):
    def test_braking_lead_gap_and_jerk_are_deterministic(self):
        sc=scenario('lead_brake')
        a=[0]*40+[-2]*60
        x=run_longitudinal_actions(sc,a)
        y=run_longitudinal_actions(sc,a)
        self.assertEqual(x,y)
        self.assertEqual(x['sample_count'],100)
        self.assertIsNotNone(x['minimum_gap_m'])
        self.assertFalse(x['model_scoring_allowed'])
        self.assertGreaterEqual(x['max_abs_jerk_mps3'],0)

    def test_cut_in_visibility_is_exact_and_cannot_create_early_ttc(self):
        run=run_longitudinal_actions(scenario('cut_in'),[0]*60)
        self.assertFalse(run['rows'][0]['lead_visible'])
        self.assertIsNone(run['rows'][0]['gap_m'])
        self.assertFalse(run['rows'][39]['lead_visible'])
        self.assertTrue(run['rows'][40]['lead_visible'])
        self.assertIsNotNone(run['rows'][40]['gap_m'])

    def test_lead_stop_go_remains_nonnegative(self):
        run=run_longitudinal_actions(scenario('stop_go'),[0]*200)
        self.assertTrue(all(v['lead_speed_mps']>=0 for v in run['rows']))
        self.assertEqual(run['status'],'SYNTHETIC_LONGITUDINAL_METRIC_DIAGNOSTIC')

    def test_invalid_commands_fail_no_silent_clipping(self):
        for a in ([float('nan')],[float('inf')],[100]):
            with self.assertRaises(LongitudinalContractError):
                run_longitudinal_actions(scenario('lead_brake'),a)
        with self.assertRaises(LongitudinalContractError):
            run_longitudinal_actions(scenario('lead_brake'),[0],dt_s=0)
        with self.assertRaises(LongitudinalContractError):
            scenario('unknown')
        with self.assertRaises(LongitudinalContractError):
            LongitudinalScenario('stop_go',10,10,10,(LeadEvent(1,0),LeadEvent(.5,-1)))

if __name__=='__main__':
    unittest.main()
