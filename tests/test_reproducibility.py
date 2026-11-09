"""Reproducible synthetic trial registration and repeated-run tests."""
import copy
import unittest

from bigbench.reproducibility import (
    RepeatSpec, ReproducibilityError, canonical_digest, planned_trials,
    compare_repeat_receipts,
)


class ReproducibilityTests(unittest.TestCase):
    def test_planned_trial_matrix_never_claims_executed(self):
        spec=RepeatSpec('a'*64,'s_curve_left_right',(11,22,33),(8.,12.),200)
        a=planned_trials(spec)
        b=planned_trials(spec)
        self.assertEqual(a,b)
        self.assertEqual(a['trial_count_planned'],6)
        self.assertEqual(a['status'],'PLAN_ONLY_NO_TRIALS_EXECUTED')
        self.assertFalse(a['model_scoring_allowed'])

    def test_repeated_receipts_compare_frame_timing_and_hashes(self):
        x={'model_sha256':'a'*64,'scenario':'s_curve_left_right','seed':11,
           'requested_steps':2,'completed_steps':2,'status':'DIAGNOSTIC_EXECUTED',
           'frames':[{'time_s':.05,'world_x_m':1.,'world_y_m':.1,
                      'road_frame_sha256':'r1','wide_frame_sha256':'w1'},
                     {'time_s':.1,'world_x_m':2.,'world_y_m':.1,
                      'road_frame_sha256':'r2','wide_frame_sha256':'w2'}]}
        y=copy.deepcopy(x)
        self.assertEqual(compare_repeat_receipts(x,y)['status'],'SYNTHETIC_REPEATED_DIAGNOSTIC_MATCH')
        y['frames'][1]['world_y_m']+=1.
        self.assertEqual(compare_repeat_receipts(x,y)['status'],'REPEATED_DIAGNOSTIC_MISMATCH')
        y=copy.deepcopy(x);y['frames'][1]['road_frame_sha256']='changed'
        self.assertFalse(compare_repeat_receipts(x,y)['frame_hashes_identical'])
        y=copy.deepcopy(x);y['seed']=12
        with self.assertRaises(ReproducibilityError):
            compare_repeat_receipts(x,y)

    def test_invalid_manifest_fails(self):
        with self.assertRaises(ReproducibilityError):
            RepeatSpec('bad','s', (1,),(8.,),20)
        with self.assertRaises(ReproducibilityError):
            RepeatSpec('a'*64,'s',(1,1),(8.,),20)
        with self.assertRaises(ReproducibilityError):
            RepeatSpec('a'*64,'s',(1,),(8.,),0)
        with self.assertRaises(ReproducibilityError):
            canonical_digest({'not_valid':float('nan')})


if __name__=='__main__':
    unittest.main()
