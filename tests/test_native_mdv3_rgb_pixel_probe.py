"""Synthetic-only contract tests; these DO NOT run MetaDrive or official ONNX."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from scripts.aggregate_original_mdv3_current_recheck import MODEL_SHA256
from scripts.compare_native_mdv3_rgb_pixels import (
    read_capture_manifest,read_verified_pixels,evaluate_native_rgb_pixel_pair,
    summarize_pixel_difference,
)
from scripts.native_mdv3_rgb_pixel_capture import (
    BoundedNativeRGBCapture,SHAPE,MAX_CAPTURE_STEPS,
)


def fake_trial(root:Path,pid:int,changed_step:int|None=None,
               changed_camera:str="wide"):
    observer=BoundedNativeRGBCapture()
    frames=[]
    for i in range(1,13):
        rgb={"road":np.full(SHAPE,30,dtype=np.uint8),
             "wide":np.full(SHAPE,70,dtype=np.uint8)}
        if i==changed_step:
            rgb[changed_camera][5,7,1]=99
        digest={k:sha256(v.tobytes(order="C")).hexdigest() for k,v in rgb.items()}
        observer.record_native_rgb(rgb,digest)
        frames.append({
            "time_s":i*.05,"world_x_m":float(i),
            "world_y_m":0.,"heading_rad":0.,
            "speed_mps":8.,"desired_curvature_1pm":.01,
            "desired_acceleration_mps2":.0,
            "source_road_rgb_sha256":digest["road"],
            "source_wide_rgb_sha256":digest["wide"],
            "road_frame_sha256":f"warped-road-{i}",
            "wide_frame_sha256":f"warped-wide-{i}",
            "new_img_sha256":f"model-feed-{i}",
            "raw_model_action":[.01,.0],
            "raw_action_sha256":f"model-action-{i}",
            "state_after_step_sha256":f"recurrent-{i}",
        })
    report={
        "status":"DIAGNOSTIC_EXECUTED",
        "model_sha256":MODEL_SHA256,
        "scenario":"s_curve_left_right","seed":20261109,
        "requested_steps":12,"completed_steps":12,"initial_fraction":.12,
        "camera_capture_mode":"native_MetaDrive_perceive_sequential_per_step",
        "process_uuid":f"fake-{pid}","process_id":pid,
        "camera_convergence_attempts":0,"camera_pixel_tolerance":0,
        "camera_image_interpolation_or_replay":False,
        "gpu_hdr_extraction":False,"pssm_update_preserved":True,
        "actual_onnx_image_feed_sha_captured_per_step":True,
        "native_source_964x604_rgb_sha_captured_per_step":True,
        "raw_action_and_recurrent_sha_captured_per_step":True,
        "trial_evidence":"ORIGINAL_PSSM_WITH_OPT_IN_CPU_RGB_RETENTION_PROBE",
        "real_vehicle_testing":False,"model_scoring_allowed":False,
        "frames":frames,
    }
    directory=root/f"rgb_run_{0 if pid==100 else 1}"
    report["raw_rgb_pixel_audit"]=observer.save_after_episode(directory,report)
    (root/f"run_{0 if pid==100 else 1}.json").write_text(
        json.dumps(report,allow_nan=False),encoding="utf-8"
    )
    return report


class Stage7SourceRGBPixelProbeTests(unittest.TestCase):
    def test_pixel_metrics_are_exact_and_bounds_are_inclusive(self):
        a=np.zeros((6,8,3),dtype=np.uint8)
        b=a.copy()
        b[1,2,0]=1
        b[4,5,2]=8
        result=summarize_pixel_difference(a,b)
        self.assertFalse(result["bit_exact"])
        self.assertEqual(result["changed_pixel_count"],2)
        self.assertEqual(result["changed_channel_values"],2)
        self.assertEqual(result["maximum_absolute_channel_delta"],8)
        self.assertEqual(result["bounding_box_xyxy_inclusive"],[2,1,5,4])
        self.assertEqual(result["first_12_changed_xy"],[[2,1],[5,4]])
        self.assertEqual(sum(map(sum,result[
            "changed_pixel_counts_grid_4x4_top_left_to_bottom_right"])),2)
        self.assertTrue(summarize_pixel_difference(a,a)["bit_exact"])

    def test_reject_invalid_shape_or_range_for_pixel_metrics(self):
        with self.assertRaises(ValueError):
            summarize_pixel_difference(np.zeros((3,4),dtype=np.uint8),
                                       np.zeros((3,4),dtype=np.uint8))
        with self.assertRaises(ValueError):
            summarize_pixel_difference(np.zeros((3,4,3),dtype=np.uint8),
                                       np.zeros((3,5,3),dtype=np.uint8))
        with self.assertRaises(ValueError):
            BoundedNativeRGBCapture(7)

    def test_archived_native_pixels_match_sha_and_first_difference(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            a=fake_trial(root,100)
            b=fake_trial(root,200,changed_step=2,changed_camera="wide")
            result=evaluate_native_rgb_pixel_pair(root,save_masks=True)
            self.assertEqual(result["status"],"FIRST_SOURCE_RGB_PIXEL_MISMATCH_MEASURED")
            self.assertEqual(result["first_raw_source_diff_step"],2)
            self.assertEqual(result["first_pixel_measured_mismatch_step"],2)
            self.assertEqual(result["pixel_metrics"]["wide"][1]["changed_pixel_count"],1)
            self.assertEqual(result["pixel_metrics"]["wide"][1][
                "bounding_box_xyxy_inclusive"],[7,5,7,5])
            self.assertEqual(result["pixel_metrics"]["road"][1]["changed_pixel_count"],0)
            self.assertEqual(result["source_to_onnx_first_divergence"][
                "source_vs_onnx_first_divergence_classification"],
                "SOURCE_RGB_DIFF_WITH_NO_ONNX_FEED_DIFF_IN_12_STEPS")
            self.assertTrue((root/result["first_difference_binary_mask"]).is_file())
            self.assertFalse(result["all_four_original_uninstrumented_strict_gate_passed"])
            manifest=read_capture_manifest(root/"rgb_run_1",b)
            self.assertEqual(len(manifest["images"]),MAX_CAPTURE_STEPS*2)
            # zlib stream trailing bytes must not be silently accepted.
            artifact=root/"rgb_run_1"/"step-01-road.rgb.zlib"
            artifact.write_bytes(artifact.read_bytes()+b"tampering")
            with self.assertRaises(ValueError):
                read_verified_pixels(root/"rgb_run_1",manifest["images"][0])

    def test_late_mismatch_is_inconclusive_not_false_early_pixel_proof(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            fake_trial(root,100)
            fake_trial(root,200,changed_step=8,changed_camera="road")
            result=evaluate_native_rgb_pixel_pair(root,save_masks=False)
            self.assertEqual(result["status"],
                "INCONCLUSIVE_FIRST_SOURCE_MISMATCH_OUTSIDE_CAPTURE_WINDOW")
            self.assertEqual(result["first_raw_source_diff_step"],8)
            self.assertIsNone(result["first_pixel_measured_mismatch_step"])

    def test_manifest_must_match_original_inference_source_sha(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            report=fake_trial(root,100)
            manifest=root/"rgb_run_0"/"manifest.json"
            data=json.loads(manifest.read_text())
            data["images"][0]["sha256"]="00"*32
            manifest.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                read_capture_manifest(root/"rgb_run_0",report)


if __name__=="__main__":
    unittest.main()
