"""Synthetic-only comparison fixtures, never native simulator evidence."""
import copy
import unittest

from bigbench.pssm_chase_pose_trace import assess_pose_events
from scripts.aggregate_pssm_chase_pose import compare_pose_arms
from scripts.native_pssm_chase_pose_trial import (
    INTERVENTION_FRAMES, INTERVENTION_DELTA_M,
)
from bigbench.pssm_mvp_trace import exact_mvp_receipt


def pose(x):
    return {"xyz_m":[float(x),0.,1.22],"hpr_deg":[0.,0.,0.]}


def original_tick(t0=10, before=0., after=0., mvp_before=0., mvp_after=1.):
    def one(n):
        mat=[[float(i==j) for j in range(4)] for i in range(4)]
        mat[0][2]=float(n)
        return exact_mvp_receipt([mat])
    m0=one(mvp_before)
    m1=one(mvp_after)
    def ev(kind,action,time,world,mvp):
        return {
            "event":action,"callback":kind,"perf_counter_ns":time,
            "main_camera_world_pose":pose(world),
            "pssm_mvp_cpu_sha256":mvp["all_f64_sha256"],
            "pssm_mvp_numeric":mvp,
            "chase_run_task_flag":True if kind=="MainCamera._chase_task" else None,
        }
    return [
        ev("PSSM.update","call",t0,before,m0),
        ev("PSSM.update","return",t0+10,before,m1),
        ev("MainCamera._chase_task","call",t0+20,before,m1),
        ev("MainCamera._chase_task","return",t0+30,after,m1),
    ]


def arm_report(arm):
    frames=8
    virtual=arm=="virtual_x_intervention"
    profiled=arm!="boundary_control"
    timeline=[]
    for i in range(frames):
        active=virtual and i in INTERVENTION_FRAMES
        injected_pose=pose(2. if active else 0.)
        before=pose(0.)
        events=original_tick(
            t0=100+i*100,
            before=2. if active else 0.,
            after=0.,
            mvp_before=float(i),
            mvp_after=float(i+1),
        ) if profiled else []
        receipt=assess_pose_events(events,expected_ticks=1) if profiled else None
        injection={
            "virtual_intervention":"MAIN_SCENE_CAMERA_X_OFFSET_BEFORE_TASK_TICK",
            "original_camera_world_pose":before,
            "intervened_camera_world_pose":injected_pose,
            "measured_delta_x_m":INTERVENTION_DELTA_M,
            "requested_delta_x_m":INTERVENTION_DELTA_M,
        } if active else None
        timeline.append({
            "frame_index_zero_based":i,
            "camera_pose_before_optional_intervention":before,
            "camera_pose_before_task_tick":injected_pose,
            "camera_pose_after_task_tick":pose(0.),
            "mvp_sha_before_tick":"before",
            "mvp_sha_after_tick":"after",
            "controlled_virtual_main_camera_offset":injection,
            "start_clock":{"frame_count":i},"end_clock":{"frame_count":i+1},
            "panda_global_frame_count_delta":1,
            "capture_elapsed_wall_ns":1000000+i,
            "exact_python_callback_event_receipt":receipt,
            "raw_python_call_return_events":events,
        })
    frame_hashes=[f"frame-{i}" for i in range(frames)]
    camera={
        "all_frame_sha256":frame_hashes,
        "post_warmup_unique_sha256":6,
        "max_changed_pixels_post_warmup":3,
    }
    keys={"source":camera}
    return {
        "status":"OBSERVED_NATIVE_PSSM_CHASE_CAMERA_BOUNDARIES",
        "seed":20261109,"scenario":"s_curve_left_right",
        "fraction":.12,"world_pose":[[1.,2.,1.22],[0.,0.,0.]],
        "capture":"paired","arm":arm,"frames":frames,"warmup":2,
        "mode":"task_step_pair","taskmgr_calls_per_pair_from_original_code":1,
        "registered_tasks_before":[
            {"name":"PSSM.update","sort":0,"chain":"default"},
            {"name":"update main chase camera","sort":0,"chain":"default"},
            {"name":"igLoop","sort":50,"chain":"default"},
        ],
        "registered_tasks_after":[
            {"name":"PSSM.update","sort":0,"chain":"default"},
            {"name":"update main chase camera","sort":0,"chain":"default"},
            {"name":"igLoop","sort":50,"chain":"default"},
        ],
        "registered_tasks_unchanged":True,
        "callback_trace_instrumented":profiled,
        "original_main_camera_state_deliberately_modified":virtual,
        "virtual_offset_intervention_frames_zero_based":
            list(INTERVENTION_FRAMES) if virtual else [],
        "virtual_offset_m_requested":INTERVENTION_DELTA_M if virtual else 0,
        "timeline":timeline,
        "raw_source_rgb":{"road":copy.deepcopy(camera),
                          "wide":copy.deepcopy(camera)},
        "onnx_image_tensor_i420":{
            "all_frame_sha256":frame_hashes,
            "post_warmup_unique_sha256":6,
        },
        "plus_2m_pose_response":{"road":True,"wide":True},
        "panda_global_frame_deltas_match":True,"panda_clock_finite":True,
        "controlled_intervention_identity_valid":True,
        "callback_evidence_complete":True,
        "native_gpu_hdr_extract_calls":0,
        "real_vehicle_testing":False,"model_scoring_allowed":False,
        "onnx_inference_executed":False,"cd210_fallback":False,
    }


class IndependentNativePoseABContracts(unittest.TestCase):
    def setUp(self):
        self.data={name:arm_report(name) for name in (
            "boundary_control","boundary_observed","virtual_x_intervention"
        )}

    def test_real_panda_evidence_schema_never_claims_model_quality(self):
        value=compare_pose_arms(self.data)
        self.assertEqual(value["status"],
            "NATIVE_PSSM_CHASE_CAMERA_POSE_CALLBACK_EVIDENCE_RECORDED")
        self.assertFalse(value["native_onnx_closed_loop_repeatability_proven"])
        self.assertFalse(value["specific_PSSM_shadow_depth_or_shader_bug_proven"])
        self.assertEqual(
            value["arm_metrics"]["virtual_x_intervention"]
                 ["pssm_before_chase_callback_count"],8)
        tests=value["arm_metrics"]["virtual_x_intervention"][
            "controlled_intervention_first_tick_results"]
        self.assertEqual(len(tests),2)
        self.assertTrue(all(x["pssm_entry_matched_imposed_virtual_camera_pose"] for x in tests))
        self.assertTrue(all(x["chase_moved_camera_on_injected_tick"] for x in tests))

    def test_missing_model_pose_and_intervention_controls_fail(self):
        del self.data["boundary_control"]
        with self.assertRaises(ValueError):
            compare_pose_arms(self.data)
        self.setUp()
        self.data["virtual_x_intervention"]["timeline"][3][
            "controlled_virtual_main_camera_offset"]["measured_delta_x_m"]=3.
        with self.assertRaises(ValueError):
            compare_pose_arms(self.data)

    def test_corrupted_raw_python_events_fail(self):
        self.data["boundary_observed"]["timeline"][2][
            "raw_python_call_return_events"][0]["callback"]="faked"
        with self.assertRaises(Exception):
            compare_pose_arms(self.data)

    def test_original_control_profiler_is_not_permitted(self):
        self.data["boundary_control"]["callback_trace_instrumented"]=True
        with self.assertRaises(ValueError):
            compare_pose_arms(self.data)

    def test_pssm_task_deletion_is_rejected(self):
        self.data["virtual_x_intervention"]["registered_tasks_after"].pop()
        with self.assertRaises(ValueError):
            compare_pose_arms(self.data)


if __name__=="__main__":
    unittest.main()
