"""Unit test doubles only; native terminal observations require Xvfb/MetaDrive CI."""
import unittest
from scripts.metadrive_terminal_hdr import CONDITIONS, compare_terminals


def fake_case(name):
    readback = name != "baseline_no_gpu"
    summaries = {
        k: {"bit_exact_after_warmup": False,
            "per_frame_vs_first": [{"first_sha256": "a", "second_sha256": "a"},
                                   {"first_sha256": "a", "second_sha256": "b"}]}
        for k in ("road", "wide")
    }
    texture = {"road_hdr": {"sha256": "a"}, "wide_hdr": {"sha256": "b"},
               "pssm_depth": {"sha256": "c"}}
    return {
        "status": "OBSERVED_TERMINAL_GPU_SAMPLE" if readback
                  else "OBSERVED_NO_GPU_CONTROL",
        "condition": name, "seed": 20261109, "pose_id": "origin",
        "pose": [[0, 0, 1.22], [-90, 0, 0]],
        "frames": 6, "warmup": 2,
        "scene": "ego_hidden", "capture_mode": "task_step_pair",
        "ablation": CONDITIONS[name]["ablation"],
        "pose_positive_before_gpu_extraction": {"road": True, "wide": True},
        "camera_rgb": summaries,
        "onnx_i420": {"after_warmup_bit_exact": False,
                      "after_warmup_unique_sha256": 2},
        "terminal_gpu_receipts": texture if readback else {},
        "real_vehicle_testing": False, "model_scoring_allowed": False,
    }


class TerminalHdrContractTests(unittest.TestCase):
    def test_three_conditions_create_non_scoring_summary(self):
        rows = {name: fake_case(name) for name in CONDITIONS}
        x = compare_terminals(rows)
        self.assertEqual(x["status"], "TERMINAL_ONLY_GPU_MEASUREMENTS_RECORDED")
        self.assertFalse(x["model_scoring_allowed"])
        self.assertFalse(x["native_onnx_closed_loop_pass"])
        self.assertTrue(x["base_vs_terminal_process_delta_receipts_identical"]["road"])

    def test_incomplete_probe_report_blocks_aggregation(self):
        rows = {name: fake_case(name) for name in CONDITIONS}
        rows["baseline_terminal"]["status"] = "INCONCLUSIVE_TERMINAL_SNAPSHOT"
        with self.assertRaises(ValueError):
            compare_terminals(rows)

    def test_mismatched_frames_blocks_aggregation(self):
        rows = {name: fake_case(name) for name in CONDITIONS}
        rows["shadow_off_terminal"]["frames"] = 4
        with self.assertRaises(ValueError):
            compare_terminals(rows)

    def test_real_vehicle_flag_blocks_aggregation(self):
        rows = {name: fake_case(name) for name in CONDITIONS}
        rows["shadow_off_terminal"]["real_vehicle_testing"] = True
        with self.assertRaises(ValueError):
            compare_terminals(rows)


if __name__ == "__main__":
    unittest.main()
