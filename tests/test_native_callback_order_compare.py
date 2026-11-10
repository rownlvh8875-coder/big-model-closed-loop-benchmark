"""Mock-only tests, never mistaken for original 0.4.3 native run evidence."""
import copy
import unittest

from bigbench.native_callback_profiler import (
    summarize_callback_pair, summarize_callback_sequence,
)
from scripts.compare_native_callback_order import compare_profiled_control


def event_rows():
    return [
      {"event":"call","callback":"PSSM.update","perf_counter_ns":1},
      {"event":"return","callback":"PSSM.update","perf_counter_ns":2},
      {"event":"call","callback":"MainCamera._chase_task","perf_counter_ns":3},
      {"event":"return","callback":"MainCamera._chase_task","perf_counter_ns":4},
    ]


def fake_report(role="unprofiled"):
    frame_count=6
    events=event_rows()
    receipts=[]
    if role=="profiled":
        for _ in range(frame_count):
            x=summarize_callback_pair(copy.deepcopy(events),1)
            x["raw_call_return_events"]=copy.deepcopy(events)
            receipts.append(x)
        summary=summarize_callback_sequence(receipts,expected_steps=1)
    else:
        summary=None
    source={"all_frame_sha256":[f"rgb-{i}" for i in range(frame_count)],
            "post_warmup_unique_sha256":4,"max_changed_pixels_post_warmup":3}
    return {
        "status":"OBSERVED_NATIVE_CALLBACK_CONTROL" if role=="unprofiled"
                 else "OBSERVED_NATIVE_CALLBACK_ORDER",
        "arm":role,"seed":20261109,"scenario":"s_curve_left_right",
        "fraction":0.12,"world_pose":[[1.0,2.0,1.22],[0.0,0.0,0.0]],
        "capture":"paired","capture_mode_in_upstream":"task_step_pair",
        "frames":frame_count,"warmup":2,"taskmgr_step_calls_from_source":1,
        "gpu_hdr_or_depth_extract_calls":0,"task_registration_modified":False,
        "onnx_model_inference_executed":False,
        "model_scoring_allowed":False,"real_vehicle_testing":False,
        "task_registration_unchanged":True,
        "global_frame_count_delta_telemetry_correct":True,
        "cpu_profiler_timing_overhead_possible":role=="profiled",
        "plus_2m_road_and_wide_response":{"road":True,"wide":True},
        "clock_and_capture_wall_time":[
            {"capture_elapsed_cpu_wall_ns":10000+i} for i in range(frame_count)
        ],
        "native_task_registration_before":[
            {"name":"PSSM.update","sort":0,"chain":"default"},
            {"name":"update main chase camera","sort":0,"chain":"default"},
            {"name":"igLoop","sort":50,"chain":"default"},
        ],
        "actual_python_callback_order":summary,
        "per_frame_callback_receipts":receipts,
        "source_rgb":{"road":copy.deepcopy(source),"wide":copy.deepcopy(source)},
        "model_i420":{
            "all_frame_sha256":[f"i420-{i}" for i in range(frame_count)],
            "post_warmup_unique_sha256":4
        },
    }


class ObservedCallbackOrderABContracts(unittest.TestCase):
    def test_comparative_report_is_not_renderer_fix(self):
        x=compare_profiled_control(fake_report(),fake_report("profiled"))
        self.assertEqual(x["status"],
             "NATIVE_PYTHON_CALLBACK_ORDER_AND_PROFILE_CONTROL_OBSERVED")
        self.assertEqual(x["actual_profiled_callback_order_frequencies"],
             {"PSSM.update BEFORE MainCamera._chase_task":6})
        self.assertFalse(x["profiled_equals_unprofiled_render_semantics_proven"])
        self.assertFalse(x["official_onnx_native_repeatability_proven"])
        self.assertTrue(x["profile_hook_introduces_cpu_overhead"])

    def test_missing_or_swapped_task_calls_are_rejected(self):
        a,b=fake_report(),fake_report("profiled")
        b["actual_python_callback_order"]["observed_taskmgr_ticks"]=5
        with self.assertRaises(ValueError):compare_profiled_control(a,b)
        b=fake_report("profiled")
        b["actual_python_callback_order"]["order_frequencies"]={
            "MainCamera._chase_task BEFORE PSSM.update":6
        }
        with self.assertRaises(ValueError):compare_profiled_control(a,b)

    def test_wrong_task_registry_or_camera_positive_fails(self):
        a,b=fake_report(),fake_report("profiled")
        b["native_task_registration_before"][1]["sort"]=5
        with self.assertRaises(ValueError):compare_profiled_control(a,b)
        b=fake_report("profiled")
        a["plus_2m_road_and_wide_response"]["wide"]=False
        with self.assertRaises(ValueError):compare_profiled_control(a,b)

    def test_raw_event_falsification_fails_even_with_correct_summary(self):
        a,b=fake_report(),fake_report("profiled")
        b["per_frame_callback_receipts"][1]["raw_call_return_events"][0]["callback"] = "unrelated"
        with self.assertRaises(Exception):compare_profiled_control(a,b)

    def test_cpu_profiler_must_be_disabled_in_original_control(self):
        a,b=fake_report(),fake_report("profiled")
        a["cpu_profiler_timing_overhead_possible"]=True
        with self.assertRaises(ValueError):compare_profiled_control(a,b)


if __name__ == "__main__":
    unittest.main()
