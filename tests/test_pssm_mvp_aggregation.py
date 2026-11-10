"""Schema-only contract tests. No Panda3D renderer, no real MD-V3 inference."""
import copy
import unittest

from scripts.aggregate_pssm_mvp_task import aggregate_shadow_mvp
from scripts.native_pssm_mvp_task_trace import CONDITIONS


def report(name):
    mode, removed, frame_delta, calls = CONDITIONS[name]
    task_names = ["igLoop","update main chase camera"]
    if not removed:
        task_names.append("PSSM.update")
    rows=[
        {"index_zero_based":i, "observed_global_frame_delta":frame_delta,
         "mvp_changed_during_pair":i>2,
         "main_camera_moved_after_tick":False,
         "light_pose_moved_after_tick":False}
        for i in range(6)
    ]
    raw={"post_warmup_unique_sha256":2,
         "max_changed_pixels_post_warmup":3,
         "first_divergence_frame_index_zero_based":4}
    return {
        "status":"OBSERVED_NATIVE_PSSM_MVP_TASK_TIMING",
        "seed":20261109,"scenario":"s_curve_left_right",
        "fraction":0.12,"world_pose":[[1.,2.,1.22],[0.,0.,0.]],
        "fixed_virtual_clock":False,"frames":6,"warmup":2,
        "condition":name,"mode":mode,"removed_task":removed,
        "ablation_receipt":({"ablation":"PSSM.update",
                             "graphics_igLoop_preserved":True} if removed else None),
        "pssm_shadow_atlas_gpu_readback_performed":False,
        "registered_tasks_unchanged":True,
        "expected_global_frame_delta_per_camera_pair":frame_delta,
        "global_frame_deltas_match":True,
        "taskmgr_calls_from_code_not_global_clock":calls,
        "clock_values_finite":True,"plus_2m_camera_pose_response":{
            "road":True,"wide":True},
        "mvp_post_warmup":{
            "status":"OBSERVED_NUMERIC_MVP_SEQUENCE",
            "frame_count":6,
            "post_warmup_unique_mvp_sha256":2,
            "first_changed_frame_index_zero_based":4,
            "max_absolute_numeric_matrix_delta_post_warmup":0.1,
            "max_changed_matrix_elements_post_warmup":1,
            "not_a_gpu_shadow_map_capture":True,
        },
        "per_frame_before_after_and_intra_pair":rows,
        "task_registry_sort_metadata_only_not_execution_proof":[
            {"name":n,"sort":0,"chain":"default"} for n in task_names
        ],
        "raw_source_rgb":{"road":copy.deepcopy(raw),"wide":copy.deepcopy(raw)},
        "pssm_vs_raw_rgb_associations":{
            k:{"classification":"BOTH_MVP_AND_RGB_CHANGED",
               "pssm_causality_proven":False,
               "model_scoring_allowed":False}
            for k in ("road","wide")
        },
        "onnx_i420":{"post_warmup_unique_sha256":2},
        "onnx_inference_executed":False,"model_scoring_allowed":False,
        "real_vehicle_testing":False,
    }


class IndependentShadowMVPTests(unittest.TestCase):
    def setUp(self):
        self.records={name:report(name) for name in CONDITIONS}

    def test_valid_diagnostic_never_authorizes_driving_rank(self):
        z=aggregate_shadow_mvp(self.records)
        self.assertEqual(z["status"],"PSSM_MVP_TASK_CLOCK_NATIVE_OBSERVATIONS_RECORDED")
        self.assertFalse(z["official_onnx_closed_loop_repeatability_proven"])
        self.assertFalse(z["specific_shadow_shader_causality_proven"])
        self.assertEqual(z["observed_arms"]["graphics_only"]
                         ["taskMgr_step_calls_from_inspected_python_code"],0)
        self.assertEqual(z["observed_arms"]["graphics_only"]
                         ["global_frame_increments_from_actual_clock"],1)

    def test_stale_pose_and_cpu_gpu_probe_rejected(self):
        self.records["graphics_only"]["plus_2m_camera_pose_response"]["wide"]=False
        with self.assertRaises(ValueError):aggregate_shadow_mvp(self.records)
        self.records["graphics_only"]=report("graphics_only")
        self.records["graphics_only"]["pssm_shadow_atlas_gpu_readback_performed"]=True
        with self.assertRaises(ValueError):aggregate_shadow_mvp(self.records)

    def test_wrong_shadow_removed_task_rejected(self):
        self.records["paired_pssm_off"]["ablation_receipt"]={"ablation":"igLoop"}
        with self.assertRaises(ValueError):aggregate_shadow_mvp(self.records)

    def test_missing_matrix_or_clock_rejected(self):
        self.records["paired_baseline"]["mvp_post_warmup"]["status"]="UNAVAILABLE"
        with self.assertRaises(ValueError):aggregate_shadow_mvp(self.records)
        self.records["paired_baseline"]=report("paired_baseline")
        self.records["paired_baseline"]["per_frame_before_after_and_intra_pair"][0][
            "observed_global_frame_delta"]=0
        with self.assertRaises(ValueError):aggregate_shadow_mvp(self.records)

    def test_mismatched_scene_or_virtual_clock_rejected(self):
        self.records["graphics_only"]["fixed_virtual_clock"]=True
        with self.assertRaises(ValueError):aggregate_shadow_mvp(self.records)
        self.records["graphics_only"]=report("graphics_only")
        self.records["graphics_only"]["scenario"]="s_curve_right_left"
        with self.assertRaises(ValueError):aggregate_shadow_mvp(self.records)


if __name__=="__main__":
    unittest.main()
