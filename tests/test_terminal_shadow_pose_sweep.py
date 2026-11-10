"""Summary schema test doubles; real native MetaDrive and GPU not executed here."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.aggregate_terminal_shadow_pose_sweep import (
    SWEEP_FRACTION,SWEEP_SCENARIOS,SWEEP_SEEDS,REQUIRED_PAIRS,
    sweep_directory,summarize_terminal_pose_sweep,
)
from scripts.native_terminal_shadow_sync import CONDITIONS,STAGES


def fake_stage(count=0):
    return {
        "status":"RAW_GPU_BYTES_COMPARED_DIFFERENT_PROCESSES",
        "raw_bytes_are_not_pixels":True,
        "changed_byte_count":count,
        "bytes_equal":count==0,
    }


class SweptNativeTerminalSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for seed in SWEEP_SEEDS:
            for scenario in SWEEP_SCENARIOS:
                folder=sweep_directory(self.root,seed,scenario)
                folder.mkdir(parents=True)
                pose=[[float(seed%100),1.0,1.22],[-80.,0.,0.]]
                base={"seed":seed,"scenario":scenario,"fraction":SWEEP_FRACTION,
                      "camera_pose":pose,"status":"OBSERVED_NATIVE_NO_GPU_CONTROL",
                      "condition":"natural_no_gpu","frames":5}
                (folder/"natural_no_gpu.json").write_text(json.dumps(base))
                for name,(inj,extra,gpu) in CONDITIONS.items():
                    item={
                        **base,
                        "condition":name,
                        "status":"OBSERVED_NATIVE_TERMINAL_SHADOW_GPU_SAMPLE"
                                 if gpu else "OBSERVED_NATIVE_NO_GPU_CONTROL",
                        "injected_camera_offset_last_frame":inj,
                        "post_chase_extra_task_kind":extra,
                        "terminal_gpu_probe":gpu,
                        "gpu_extraction_before_or_during_rgb_capture":False,
                        "both_camera_plus_2m_positive":{"road":True,"wide":True},
                        "same_tick_final_ram_rgb_unchanged_after_terminal":
                            {"road":True,"wide":True},
                    }
                    (folder/(name+".json")).write_text(json.dumps(item))
                summary={
                    "status":"NATIVE_TERMINAL_GPU_SHADOW_CAUSAL_DIAGNOSTIC_OBSERVED",
                    "seed":seed,"scenario":scenario,"frames":5,
                    "GPU_shadow_causality_proven":False,
                    "official_new_frame_ONNX_repeatability_proven":False,
                    "real_vehicle_testing":False,"model_scoring_allowed":False,
                    "per_arm_receipts":{name:{"warmup_unique_i420_sha":2}
                                        for name in CONDITIONS},
                    "gpu_raw_byte_difference_between_independent_processes":{
                        pair:{stage:fake_stage(0 if stage=="pssm_depth" else 3)
                              for stage in STAGES}
                        for pair in REQUIRED_PAIRS
                    },
                }
                (folder/"shadow_gpu_comparison.json").write_text(json.dumps(summary))

    def test_eight_scene_sweep_results_no_fake_model_pass(self):
        output=summarize_terminal_pose_sweep(self.root)
        self.assertEqual(output["native_matrix_conditions"],8)
        self.assertEqual(output["independent_meta_drive_processes"],56)
        self.assertEqual(output["lane_fraction"],.28)
        self.assertFalse(output["original_renderer_md_v3_native_onnx_repeatability_proven"])
        self.assertFalse(output["model_scoring_allowed"])
        self.assertEqual(
            output["per_scene"][0]["gpu_changed_bytes_by_pair"][
                "natural_terminal VS offset_sync_terminal"]["pssm_depth"],0
        )

    def test_missing_ramp_never_counts_as_success(self):
        directory=sweep_directory(self.root,20261110,"in_ramp")
        (directory/"shadow_gpu_comparison.json").unlink()
        with self.assertRaises(FileNotFoundError):
            summarize_terminal_pose_sweep(self.root)

    def test_wrong_fraction_original_camera_rejected(self):
        file=sweep_directory(self.root,20261109,"out_ramp")/"offset_terminal.json"
        value=json.loads(file.read_text())
        value["fraction"]=0.12
        file.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            summarize_terminal_pose_sweep(self.root)

    def test_stale_camera_false_positive_rejected(self):
        file=sweep_directory(self.root,20261110,"s_curve_right_left")/"offset_sync_terminal.json"
        value=json.loads(file.read_text())
        value["both_camera_plus_2m_positive"]["road"]=False
        file.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            summarize_terminal_pose_sweep(self.root)

    def test_nonpixel_gpu_changed_bytes_contract_rejected(self):
        file=sweep_directory(self.root,20261110,"s_curve_left_right")/"shadow_gpu_comparison.json"
        d=json.loads(file.read_text())
        d["gpu_raw_byte_difference_between_independent_processes"][
            REQUIRED_PAIRS[0]]["road_hdr"]["raw_bytes_are_not_pixels"]=False
        file.write_text(json.dumps(d))
        with self.assertRaises(ValueError):
            summarize_terminal_pose_sweep(self.root)


if __name__=="__main__":
    unittest.main()
