"""Synthetic contract tests ONLY; these do not execute a 768MB official ONNX."""
import copy
import unittest

import numpy as np

from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
from scripts.native_mdv3_repeat_trial import recurrent_receipt


def native_receipt(process, steps=3):
    rows=[]
    for i in range(steps):
        rows.append({
            "time_s":(i+1)*.05,
            "world_x_m":float(i+1),"world_y_m":.1,
            "heading_rad":.01,"speed_mps":8.,
            "desired_curvature_1pm":.02,
            "desired_acceleration_mps2":-.2,
            "road_frame_sha256":f"road-{i}",
            "wide_frame_sha256":f"wide-{i}",
            "new_img_sha256":f"i420-{i}",
            "raw_model_action":[.12,-.2],
            "raw_action_sha256":f"action-{i}",
            "state_after_step_sha256":f"state-{i}",
        })
    return {
        "status":"DIAGNOSTIC_EXECUTED",
        "model_sha256":"a"*64,
        "scenario":"s_curve_left_right","seed":20261109,
        "requested_steps":steps,"completed_steps":steps,"initial_fraction":.12,
        "camera_capture_mode":"native_MetaDrive_perceive_sequential_per_step",
        "process_uuid":f"distinct-{process}","process_id":100+process,
        "camera_convergence_attempts":0,"camera_pixel_tolerance":0,
        "camera_image_interpolation_or_replay":False,
        "gpu_hdr_extraction":False,"pssm_update_preserved":True,
        "actual_onnx_image_feed_sha_captured_per_step":True,
        "raw_action_and_recurrent_sha_captured_per_step":True,
        "real_vehicle_testing":False,"model_scoring_allowed":False,
        "frames":rows,
    }


class OfficialNativeRepeatContracts(unittest.TestCase):
    def test_exact_equal_is_only_native_short_gate(self):
        a,b=native_receipt(1),native_receipt(2)
        d=compare_fresh_trials(a,b)
        self.assertTrue(d["exact_repeated_execution_gate_passed"])
        self.assertEqual(d["status"],"STRICT_NATIVE_ONNX_REPEAT_MATCH")
        self.assertFalse(d["official_model_driving_performance_ranked"])

    def test_first_differing_input_cannot_be_masked_by_small_delta(self):
        a,b=native_receipt(1),native_receipt(2)
        b["frames"][1]["new_img_sha256"]="different"
        b["frames"][2]["world_y_m"]+=1e-8
        d=compare_fresh_trials(a,b)
        self.assertEqual(d["status"],"STRICT_NATIVE_ONNX_REPEAT_MISMATCH")
        self.assertEqual(d["first_diverging_step"],2)
        self.assertFalse(d["actual_onnx_new_img_sha256_match"])
        self.assertGreater(d["max_xy_position_delta_m"],0)

    def test_recurrent_state_mismatch_even_if_rgb_identical(self):
        a,b=native_receipt(1),native_receipt(2)
        b["frames"][1]["state_after_step_sha256"]="changed"
        d=compare_fresh_trials(a,b)
        self.assertTrue(d["camera_rgb_frames_match"])
        self.assertFalse(d["exact_repeated_execution_gate_passed"])

    def test_independent_process_and_untouched_renderer_required(self):
        a,b=native_receipt(1),native_receipt(2)
        b["process_uuid"]=a["process_uuid"]
        with self.assertRaises(ValueError):compare_fresh_trials(a,b)
        b=native_receipt(2)
        b["pssm_update_preserved"]=False
        with self.assertRaises(ValueError):compare_fresh_trials(a,b)
        b=native_receipt(2)
        b["camera_convergence_attempts"]=6
        with self.assertRaises(ValueError):compare_fresh_trials(a,b)

    def test_failed_or_unmatched_report_cannot_be_a_pass(self):
        a,b=native_receipt(1),native_receipt(2)
        b["status"]="FAILED_OR_INCOMPLETE"
        with self.assertRaises(ValueError):compare_fresh_trials(a,b)
        b=native_receipt(2)
        b["seed"]=20261110
        with self.assertRaises(ValueError):compare_fresh_trials(a,b)
        b=native_receipt(2)
        del b["frames"][0]["new_img_sha256"]
        with self.assertRaises(ValueError):compare_fresh_trials(a,b)

    def test_recurring_state_digest_contains_exact_bytes(self):
        a=recurrent_receipt({"h":np.ones((2,3),dtype=np.float32)})
        b=recurrent_receipt({"h":np.ones((2,3),dtype=np.float32)})
        c=recurrent_receipt({"h":np.ones((2,3),dtype=np.float64)})
        d=recurrent_receipt({"h":np.zeros((2,3),dtype=np.float32)})
        self.assertEqual(a,b)
        self.assertNotEqual(a,c)
        self.assertNotEqual(a,d)
        with self.assertRaises(ValueError):recurrent_receipt({})


if __name__=="__main__":
    unittest.main()
