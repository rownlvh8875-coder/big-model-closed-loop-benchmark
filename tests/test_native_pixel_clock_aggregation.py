"""Schema-only test doubles; cannot certify actual native MetaDrive rendering."""
import copy
import unittest

from scripts.aggregate_native_pixel_clock import (
    SCHEDULES, compare_pixel_clock_conditions,
)


def report_for(key):
    mode, ablation, ticks, task_calls = SCHEDULES[key]
    images = {
        "all_frame_sha256": ["a", "b", "c", "c", "d", "d"],
        "post_warmup_unique_sha256": 2,
        "max_changed_pixels_post_warmup": 1,
        "first_divergence_frame_index_zero_based": 4,
        "per_frame_vs_first_post_warmup": [
            {"changed_pixels": 0, "changed_pixel_examples": [],
             "bounding_box_xyxy_inclusive": None},
            {"changed_pixels": 0, "changed_pixel_examples": [],
             "bounding_box_xyxy_inclusive": None},
            {"changed_pixels": 1,
             "changed_pixel_examples": [{"x": 3, "y": 4,
                                         "first_rgb": [0, 0, 0],
                                         "second_rgb": [1, 0, 0]}],
             "bounding_box_xyxy_inclusive": [3, 4, 3, 4]},
            {"changed_pixels": 1, "changed_pixel_examples": [],
             "bounding_box_xyxy_inclusive": [3, 4, 3, 4]},
        ],
    }
    i420 = {
        "all_frame_sha256": ["0", "0", "1", "1", "2", "2"],
        "post_warmup_unique_sha256": 2,
        "max_changed_elements_post_warmup": 1,
        "bit_exact_after_warmup": False,
        "per_frame_vs_first_post_warmup": [
            {"changed_elements": 0,
             "first_changed_indices_camera_plane_row_col": None},
            {"changed_elements": 0,
             "first_changed_indices_camera_plane_row_col": None},
            {"changed_elements": 1,
             "first_changed_indices_camera_plane_row_col": [1, 5, 7, 8]},
            {"changed_elements": 1,
             "first_changed_indices_camera_plane_row_col": [1, 5, 7, 8]},
        ],
    }
    return {
        "status": "OBSERVED_NATIVE_PIXEL_CLOCK",
        "seed": 20261109, "scenario": "s_curve_left_right",
        "fraction": .12, "camera_pose": [[0, 0, 1.22], [-90, 0, 0]],
        "frames": 6, "warmup": 2, "mode": mode, "ablation": ablation,
        "source_rgb": {"road": copy.deepcopy(images),
                       "wide": copy.deepcopy(images)},
        "model_rgb": {"road": copy.deepcopy(images),
                      "wide": copy.deepcopy(images)},
        "onnx_i420": i420,
        "clock_timeline": [{"global_clock_frame_count_delta": ticks,
                            "real_time_delta_s": .01} for _ in range(6)],
        "expected_panda_global_frame_count_delta_per_pair": ticks,
        "all_panda_frame_count_deltas_as_expected": True,
        "task_manager_step_invocations_from_capture_call_path": task_calls,
        "global_frame_counter_cannot_identify_task_manager_execution": True,
        "pssm_task_identity_correct": True,
        "cpu_readbacks_bit_exact_without_new_render": True,
        "camera_plus_2m_positive": {"road": True, "wide": True},
        "ablation_receipt": (
            {"ablation": "PSSM.update", "graphics_igLoop_preserved": True}
            if ablation == "shadow_off" else None),
        "gpu_texture_extract_calls": 0, "onnx_inference_used": False,
        "model_scoring_allowed": False, "real_vehicle_testing": False,
    }


class NativePixelClockAggregationTests(unittest.TestCase):
    def setUp(self):
        self.rows = {name: report_for(name) for name in SCHEDULES}

    def test_all_four_conditions_valid_not_driving_scores(self):
        result = compare_pixel_clock_conditions(self.rows)
        self.assertEqual(result["status"], "NATIVE_PIXEL_CLOCK_TASK_CORRELATIONS_RECORDED")
        self.assertFalse(result["specific_shader_or_task_cause_proven"])
        self.assertFalse(result["model_closed_loop_reproducibility_proven"])
        self.assertEqual(result["conditions"]["perceive_baseline"]
                         ["measured_panda_frame_count_delta_per_pair"], 2)
        self.assertEqual(result["conditions"]["graphics_baseline"]
                         ["measured_panda_frame_count_delta_per_pair"], 1)
        self.assertEqual(result["conditions"]["graphics_baseline"]
                         ["taskMgr_steps_per_pair_from_call_path"], 0)
        self.assertEqual(result["conditions"]["task_baseline"]
                         ["raw_sensor_rgb"]["road"]["first_changed_bbox_xyxy_inclusive"],
                         [3, 4, 3, 4])

    def test_stale_frame_would_fail(self):
        self.rows["graphics_baseline"]["camera_plus_2m_positive"]["road"] = False
        with self.assertRaises(ValueError):
            compare_pixel_clock_conditions(self.rows)

    def test_task_identity_and_clock_are_fail_closed(self):
        self.rows["task_shadow_off"]["ablation_receipt"] = None
        with self.assertRaises(ValueError):
            compare_pixel_clock_conditions(self.rows)
        self.rows["task_shadow_off"] = report_for("task_shadow_off")
        self.rows["perceive_baseline"]["clock_timeline"][0][
            "global_clock_frame_count_delta"] = 1
        with self.assertRaises(ValueError):
            compare_pixel_clock_conditions(self.rows)

    def test_missing_or_unmatched_process_evidence_fails(self):
        del self.rows["graphics_baseline"]
        with self.assertRaises(ValueError):
            compare_pixel_clock_conditions(self.rows)
        self.rows["graphics_baseline"] = report_for("graphics_baseline")
        self.rows["graphics_baseline"]["seed"] = 20261110
        with self.assertRaises(ValueError):
            compare_pixel_clock_conditions(self.rows)


if __name__ == "__main__":
    unittest.main()
