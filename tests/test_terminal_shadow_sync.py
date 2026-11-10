"""Pure fixture tests: these are NOT native GPU observations or model scores."""
from __future__ import annotations

from hashlib import sha256
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zlib

from scripts.native_terminal_shadow_sync import CONDITIONS,STAGES
from scripts.aggregate_terminal_shadow_sync import (
    _verified_stage_bytes,raw_gpu_byte_difference,aggregate_gpu_shadow,
)


def mock_report(name,root):
    injected,extra,terminal=CONDITIONS[name]
    stage_data={}
    if terminal:
        for stage in STAGES:
            raw=b"GPU_RAW_"+stage.encode("ascii")+bytes(range(64))
            output=f"{name}-{stage}.bin.zlib"
            compressed=zlib.compress(raw)
            (root/output).write_bytes(compressed)
            stage_data[stage]={
                "status":"EXTRACTED","source":stage,
                "sha256":sha256(raw).hexdigest(),
                "byte_count":len(raw),
                "metadata":{"dimensions":[2,4,1],"format":"F_dummy",
                            "component_type":"uint8"},
                "lossless_compressed_filename":output,
                "compressed_byte_count":len(compressed),
                "uncompressed_bytes_kept":len(raw),
            }
    else:
        stage_data={stage:{"status":"SKIPPED_BY_DESIGN_NO_GPU"} for stage in STAGES}
    frames=[]
    for i in range(5):
        injected_item=(
            {"measured_delta_x_m":2.0} if injected and i==4 else None
        )
        probe=({
            "post_chase_probe_mode":extra,
            "main_camera_pose_at_sort25":{"xyz_m":[0,0,1.22]},
            "camera_pose_after_sort25":{"xyz_m":[0,0,1.22]},
            "mvp_changed_by_sort25_callback":extra=="sync" and i==4,
        } if extra else None)
        frames.append({
            "frame_index_zero_based":i,
            "panda_frame_count_delta":1,
            "virtual_camera_injection":injected_item,
            "sort25_event":probe,
        })
    sample={
        "all_frame_sha256":["0","1","2","3","4"],
        "post_warmup_unique_sha256":3,
        "max_changed_pixels_post_warmup":2,
    }
    reg=[{"name":"PSSM.update","sort":0},
         {"name":"update main chase camera","sort":0},
         {"name":"igLoop","sort":50}]
    if extra:
        reg.append({"name":"bigbench_post_chase_shadow_probe","sort":25})
    return {
        "status":("OBSERVED_NATIVE_TERMINAL_SHADOW_GPU_SAMPLE"
                  if terminal else "OBSERVED_NATIVE_NO_GPU_CONTROL"),
        "condition":name,
        "seed":20261109,"scenario":"s_curve_left_right",
        "fraction":.12,"camera_pose":[[1.,2.,1.22],[0.,0.,0.]],
        "frames":5,"warmup":2,
        "injected_camera_offset_last_frame":injected,
        "post_chase_extra_task_kind":extra,
        "terminal_gpu_probe":terminal,
        "virtual_main_camera_x_offset_m":2. if injected else 0,
        "original_task_names_and_sort":reg[:3],
        "tasks_with_optional_extra_sort25":reg,
        "task_registry_unchanged_during_frames":True,
        "gpu_extraction_before_or_during_rgb_capture":False,
        "terminal_gpu_extraction_after_complete_rgb_i420":terminal,
        "gpu_stage_receipts":stage_data,
        "gpu_compressed_files":[f"{name}-{stage}.bin.zlib" for stage in STAGES]
                               if terminal else [],
        "same_tick_final_ram_rgb_unchanged_after_terminal":{
            "road":True if terminal else None,
            "wide":True if terminal else None,
        },
        "source_rgb":{"road":copy.deepcopy(sample),"wide":copy.deepcopy(sample)},
        "warped_rgb":{"road":copy.deepcopy(sample),"wide":copy.deepcopy(sample)},
        "onnx_i420":copy.deepcopy(sample),
        "final_cpu_pssm_mvp":{"status":"MVP_VALUES_CAPTURED",
                              "all_f64_sha256":"f"*64},
        "per_frame_cpu_and_extra_task":frames,
        "both_camera_plus_2m_positive":{"road":True,"wide":True},
        "post_chase_sort25_was_separately_registered":extra is not None,
        "native_onnx_inference_performed":False,
        "original_renderer_semantics_unchanged":not injected and extra is None,
        "real_vehicle_testing":False,"model_scoring_allowed":False,
        "cd210_fallback":False,
    }


class TerminalShadowContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.reports={name:mock_report(name,self.root) for name in CONDITIONS}

    def test_seven_arms_make_diagnostic_not_model_pass(self):
        out=aggregate_gpu_shadow(self.root,self.reports)
        self.assertEqual(out["status"],
                         "NATIVE_TERMINAL_GPU_SHADOW_CAUSAL_DIAGNOSTIC_OBSERVED")
        self.assertEqual(len(out["per_arm_receipts"]),7)
        self.assertEqual(len(out["gpu_raw_byte_difference_between_independent_processes"]),4)
        self.assertFalse(out["GPU_shadow_causality_proven"])
        self.assertFalse(out["official_new_frame_ONNX_repeatability_proven"])
        self.assertFalse(out["real_vehicle_testing"])

    def test_corrupted_gpu_binary_is_not_accepted(self):
        path=self.root/"offset_sync_terminal-pssm_depth.bin.zlib"
        path.write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            aggregate_gpu_shadow(self.root,self.reports)

    def test_fake_extraction_time_or_stale_frame_is_rejected(self):
        self.reports["offset_terminal"]["gpu_extraction_before_or_during_rgb_capture"]=True
        with self.assertRaises(ValueError):
            aggregate_gpu_shadow(self.root,self.reports)
        self.reports["offset_terminal"]["gpu_extraction_before_or_during_rgb_capture"]=False
        self.reports["offset_terminal"]["same_tick_final_ram_rgb_unchanged_after_terminal"]["wide"]=False
        with self.assertRaises(ValueError):
            aggregate_gpu_shadow(self.root,self.reports)

    def test_wrong_sync_sort_or_unproven_after_chase_update_rejected(self):
        self.reports["offset_sync_terminal"]["tasks_with_optional_extra_sort25"][-1]["sort"]=0
        with self.assertRaises(ValueError):
            aggregate_gpu_shadow(self.root,self.reports)
        self.reports["offset_sync_terminal"]=mock_report("offset_sync_terminal",self.root)
        self.reports["offset_sync_terminal"]["per_frame_cpu_and_extra_task"][-1][
            "sort25_event"]["mvp_changed_by_sort25_callback"]=False
        with self.assertRaises(ValueError):
            aggregate_gpu_shadow(self.root,self.reports)

    def test_byte_difference_not_equated_to_pixels(self):
        info={"metadata":{"format":"raw","dimensions":[2,2,1]}}
        a=bytes([0,1,2,3,4])
        b=bytes([0,7,2,8,4])
        d=raw_gpu_byte_difference(a,b,info,info)
        self.assertEqual(d["changed_byte_count"],2)
        self.assertEqual(d["first_12_changed_byte_offsets"],[1,3])
        self.assertTrue(d["raw_bytes_are_not_pixels"])
        different=raw_gpu_byte_difference(a,b,info,{"metadata":{"format":"other"}})
        self.assertEqual(different["status"],"INCONCLUSIVE_GPU_TEXTURE_LAYOUT_CHANGED")
        self.assertIsNone(different["bytes_equal"])

    def test_missing_trial_or_wrong_sensor_pose_rejected(self):
        del self.reports["natural_no_gpu"]
        with self.assertRaises(ValueError):
            aggregate_gpu_shadow(self.root,self.reports)
        self.reports["natural_no_gpu"]=mock_report("natural_no_gpu",self.root)
        self.reports["offset_probe_terminal"]["seed"]=20261110
        with self.assertRaises(ValueError):
            aggregate_gpu_shadow(self.root,self.reports)


if __name__=="__main__":
    unittest.main()
