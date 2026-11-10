"""Synthetic validations of results schema; never counted as native evidence."""
import unittest
from scripts.aggregate_probe_interventions import PROBES, aggregate_interventions


def make_report(probe, post=True):
    stages = {name: {"unique_sha256_after_warmup": 2}
              for name in ("road_rgb", "wide_rgb", "onnx_i420")}
    return {
        "status": ("OBSERVED_BUFFER_CHAIN" if probe == "all" and post else
                   "OBSERVED_SELECTIVE_PROBE" if post else
                   "GPU_PROBE_INTERVENTION_OBSERVED"),
        "probe_stage": probe, "required_probe_buffers_available": True,
        "seed": 20261109, "pose_id": "origin",
        "pose": [[0, 0, 1.22], [-90, 0, 0]],
        "frames": 6, "warmup": 2,
        "scene": "ego_hidden", "capture_mode": "task_step_pair",
        "ablation": "baseline", "removed_task": None,
        "before_gpu_probe_pose_positive_control": {"road": True, "wide": True},
        "pose_shift_positive_control": {"road": post, "wide": post},
        "real_vehicle_testing": False, "model_scoring_allowed": False,
        "stages": stages,
    }


class InterventionContracts(unittest.TestCase):
    def test_probe_influence_is_diagnostic_only(self):
        records = {probe: make_report(probe, post=(probe == "none"))
                   for probe in PROBES}
        out = aggregate_interventions(records)
        self.assertIn("pssm_depth", out["observed_probe_modes_causing_response_loss"])
        self.assertFalse(out["official_onnx_closed_loop_repeatability_validated"])
        self.assertFalse(out["model_scoring_allowed"])

    def test_no_gpu_control_must_respond(self):
        records = {probe: make_report(probe, post=False) for probe in PROBES}
        with self.assertRaises(ValueError):
            aggregate_interventions(records)

    def test_missing_readback_is_not_success(self):
        records = {probe: make_report(probe) for probe in PROBES}
        records["road_hdr"]["required_probe_buffers_available"] = False
        with self.assertRaises(ValueError):
            aggregate_interventions(records)

    def test_wrong_seed_fails(self):
        records = {probe: make_report(probe) for probe in PROBES}
        records["wide_hdr"]["seed"] = 20261110
        with self.assertRaises(ValueError):
            aggregate_interventions(records)


if __name__ == "__main__":
    unittest.main()
