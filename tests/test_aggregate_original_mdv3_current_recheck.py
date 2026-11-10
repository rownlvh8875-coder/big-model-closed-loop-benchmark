"""Synthetic-only unit test fixtures, NOT actual official ONNX execution."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.aggregate_original_mdv3_current_recheck import (
    aggregate_original_mdv3,MODEL_SHA256,SCENARIOS,SEEDS,STEPS,
)
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials


def mock_trial(seed,scenario,pid):
    frames=[]
    for i in range(STEPS):
        frames.append({
            "time_s":(i+1)*.05,"world_x_m":float(i),"world_y_m":0.,
            "heading_rad":0.0,"speed_mps":8.,
            "source_road_rgb_sha256":f"road-raw-{i}",
            "source_wide_rgb_sha256":f"wide-raw-{i}",
            "desired_curvature_1pm":0.01,
            "desired_acceleration_mps2":0.0,
            "road_frame_sha256":f"warped-road-{i}",
            "wide_frame_sha256":f"warped-wide-{i}",
            "new_img_sha256":f"actual-feed-{i}",
            "raw_model_action":[.1,.0],
            "raw_action_sha256":f"action-{i}",
            "state_after_step_sha256":f"recurrent-{i}",
        })
    return {
        "status":"DIAGNOSTIC_EXECUTED",
        "model_sha256":MODEL_SHA256,
        "scenario":scenario,"seed":seed,
        "requested_steps":STEPS,"completed_steps":STEPS,
        "initial_fraction":.12,
        "camera_capture_mode":"native_MetaDrive_perceive_sequential_per_step",
        "process_uuid":f"separate-{seed}-{scenario}-{pid}",
        "process_id":pid,
        "camera_convergence_attempts":0,
        "camera_pixel_tolerance":0,
        "camera_image_interpolation_or_replay":False,
        "gpu_hdr_extraction":False,"pssm_update_preserved":True,
        "actual_onnx_image_feed_sha_captured_per_step":True,
        "native_source_964x604_rgb_sha_captured_per_step":True,
        "raw_action_and_recurrent_sha_captured_per_step":True,
        "model_scoring_allowed":False,"real_vehicle_testing":False,
        "frames":frames,
    }


class StrictOriginalMDV3AggregateTests(unittest.TestCase):
    def setUp(self):
        self.t=TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        for seed in SEEDS:
            for scene in SCENARIOS:
                folder=self.root/f"seed-{seed}"/scene
                folder.mkdir(parents=True)
                a=mock_trial(seed,scene,100)
                b=mock_trial(seed,scene,200)
                if seed==20261110 and scene=="s_curve_right_left":
                    b["frames"][2]["source_wide_rgb_sha256"]="modified-original-sensor"
                verdict=compare_fresh_trials(a,b)
                for name,data in (
                    ("run_0.json",a),("run_1.json",b),
                    ("strict_native_repeat_verdict.json",verdict)
                ):
                    (folder/name).write_text(json.dumps(data))

    def test_strict_mismatch_survives_successful_diagnostic(self):
        result=aggregate_original_mdv3(self.root)
        self.assertEqual(result["strict_gate_pass_count"],3)
        self.assertEqual(result["strict_gate_total"],4)
        self.assertFalse(result["all_four_cases_strict_native_gate_passed"])
        self.assertEqual(result["total_independent_native_onnx_processes"],8)
        self.assertEqual(result["actual_onnx_new_image_steps_across_all_processes"],96)
        self.assertFalse(result["model_scoring_allowed"])
        self.assertEqual(result["per_seed_scene"][3]["first_observed_mismatch_boundary"],
                         "NATIVE_964x604_RGB")

    def test_mismatched_model_sha_never_accepted(self):
        path=self.root/"seed-20261109"/"s_curve_left_right"/"run_0.json"
        data=json.loads(path.read_text())
        data["model_sha256"]="0"*64
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            aggregate_original_mdv3(self.root)

    def test_fabricated_pass_verdict_rejected(self):
        path=self.root/"seed-20261110"/"s_curve_right_left"/"strict_native_repeat_verdict.json"
        d=json.loads(path.read_text())
        d["exact_repeated_execution_gate_passed"]=True
        path.write_text(json.dumps(d))
        with self.assertRaises(ValueError):
            aggregate_original_mdv3(self.root)

    def test_camera_replay_or_pssm_off_is_invalid(self):
        path=self.root/"seed-20261109"/"s_curve_left_right"/"run_1.json"
        d=json.loads(path.read_text())
        d["camera_image_interpolation_or_replay"]=True
        path.write_text(json.dumps(d))
        with self.assertRaises(ValueError):
            aggregate_original_mdv3(self.root)

    def test_missing_original_second_process_is_invalid(self):
        path=self.root/"seed-20261109"/"s_curve_right_left"/"run_1.json"
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            aggregate_original_mdv3(self.root)


if __name__=="__main__":
    unittest.main()
