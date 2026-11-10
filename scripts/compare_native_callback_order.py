"""Validate and compare original-Panda task scheduling with profiler A/B.

Measured Python callback execution order is not inferred from registration sort.
The profiler is not a renderer repair and introduces CPU overhead.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median

from scripts.native_callback_order_trial import CAPTURE_MODES
from bigbench.native_callback_profiler import summarize_callback_pair


def compare_profiled_control(control: dict, profile: dict) -> dict:
    for role, report, required_status in (
        ("unprofiled", control, "OBSERVED_NATIVE_CALLBACK_CONTROL"),
        ("profiled", profile, "OBSERVED_NATIVE_CALLBACK_ORDER"),
    ):
        if report.get("status")!=required_status or report.get("arm")!=role:
            raise ValueError(f"{role}: no completed native execution")
        if (report.get("gpu_hdr_or_depth_extract_calls") != 0
                or report.get("task_registration_modified") is not False):
            raise ValueError(f"{role}: raw renderer/task semantics were modified")
        if report.get("onnx_model_inference_executed") is not False:
            raise ValueError("this is not an ONNX test")
        if report.get("model_scoring_allowed") or report.get("real_vehicle_testing"):
            raise ValueError("no real-world or driving quality result allowed")
        if report.get("task_registration_unchanged") is not True:
            raise ValueError(f"{role}: Panda task registry changed")
        if report.get("global_frame_count_delta_telemetry_correct") is not True:
            raise ValueError(f"{role}: unexpected Panda global clock count")
        if not all(report.get("plus_2m_road_and_wide_response",{}).get(k)
                   for k in ("road","wide")):
            raise ValueError(f"{role}: stale RGB positive control")
        if len(report.get("clock_and_capture_wall_time",[])) != report.get("frames"):
            raise ValueError(f"{role}: missing capture steps")
        if any(type(row.get("capture_elapsed_cpu_wall_ns")) is not int or
               row["capture_elapsed_cpu_wall_ns"] <= 0
               for row in report["clock_and_capture_wall_time"]):
            raise ValueError(f"{role}: capture monotonic time missing")
        if report.get("cpu_profiler_timing_overhead_possible") is not (role=="profiled"):
            raise ValueError(f"{role}: profiler identity mislabeled")
    match=("scenario","seed","fraction","world_pose","capture",
           "capture_mode_in_upstream","frames","warmup",
           "taskmgr_step_calls_from_source")
    if any(control.get(k) != profile.get(k) for k in match):
        raise ValueError("unprofiled and profiled worlds use different conditions")
    capture=control["capture"]
    if capture not in CAPTURE_MODES:
        raise ValueError("unknown camera render schedule")
    if CAPTURE_MODES[capture] != (
        control["capture_mode_in_upstream"],
        control["taskmgr_step_calls_from_source"]
    ):
        raise ValueError("wrong source-verified task call count")
    if control["native_task_registration_before"] != profile["native_task_registration_before"]:
        raise ValueError("different Panda scene task registrations")
    if control["actual_python_callback_order"] is not None:
        raise ValueError("unprofiled control must not claim to observe callback order")
    if control.get("per_frame_callback_receipts"):
        raise ValueError("unprofiled must not produce made-up callback events")
    summary=profile.get("actual_python_callback_order")
    if (not isinstance(summary,dict) or
            summary.get("status") != "EXACT_PYTHON_CALLBACK_CALL_SEQUENCE_RECORDED"):
        raise ValueError("missing directly observed callback order")
    expected=profile["frames"]*profile["taskmgr_step_calls_from_source"]
    if summary.get("observed_taskmgr_ticks") != expected:
        raise ValueError("callback count differs from actual taskMgr capture calls")
    if summary.get("task_registration_modified") is not False:
        raise ValueError("callback tracing replaced registered task objects")
    if len(profile.get("per_frame_callback_receipts",[])) != profile["frames"]:
        raise ValueError("incomplete per-tick Python profiler data")
    # Reconstruct actual frequencies from each raw Python entry/exit event:
    # a copied prefilled summary alone cannot establish execution order.
    reconstructed=Counter()
    for receipt in profile["per_frame_callback_receipts"]:
        raw=receipt.get("raw_call_return_events")
        if not isinstance(raw,list):
            raise ValueError("actual callback profiling events missing")
        verified=summarize_callback_pair(
            raw,profile["taskmgr_step_calls_from_source"]
        )
        if verified["per_taskmgr_step_callback_call_order"] != receipt.get(
                "per_taskmgr_step_callback_call_order"):
            raise ValueError("recorded order differs from the raw call/return events")
        for order in verified["per_taskmgr_step_callback_call_order"]:
            reconstructed[" BEFORE ".join(order)]+=1
    orders=summary.get("order_frequencies",{})
    if dict(reconstructed)!=orders:
        raise ValueError("profiler summary does not match actual Python callback events")
    if not orders or sum(orders.values()) != expected:
        raise ValueError("missing or inconsistent actual callback order frequency")
    valid_orders={
        "PSSM.update BEFORE MainCamera._chase_task",
        "MainCamera._chase_task BEFORE PSSM.update",
    }
    if not set(orders) <= valid_orders:
        raise ValueError("unknown or duplicate actual Python callback pattern")
    frames=profile["frames"]
    source_metrics={}
    for kind in ("road","wide"):
        a=control["source_rgb"][kind]
        b=profile["source_rgb"][kind]
        ha,hb=a["all_frame_sha256"],b["all_frame_sha256"]
        if len(ha)!=frames or len(hb)!=frames:
            raise ValueError("raw MetaDrive image time series absent")
        source_metrics[kind]={
            "unprofiled_post_warmup_unique_sha":a["post_warmup_unique_sha256"],
            "profiled_post_warmup_unique_sha":b["post_warmup_unique_sha256"],
            "unprofiled_max_changed_pixels":a["max_changed_pixels_post_warmup"],
            "profiled_max_changed_pixels":b["max_changed_pixels_post_warmup"],
            "cross_independent_process_equal_frame_count":sum(x==y for x,y in zip(ha,hb)),
            "first_unmatched_cross_process_frame_zero_based":next(
                (i for i,(x,y) in enumerate(zip(ha,hb)) if x!=y),None
            ),
        }
    ia=control["model_i420"]["all_frame_sha256"]
    ib=profile["model_i420"]["all_frame_sha256"]
    if len(ia)!=frames or len(ib)!=frames:
        raise ValueError("model I420 image sequence missing")
    timing={}
    for role,x in (("unprofiled",control),("profiled",profile)):
        t=[row["capture_elapsed_cpu_wall_ns"] for row in x["clock_and_capture_wall_time"]]
        timing[role+"_median_capture_wall_ms"] = float(median(t)/1e6)
    return {
        "status": "NATIVE_PYTHON_CALLBACK_ORDER_AND_PROFILE_CONTROL_OBSERVED",
        "scenario":control["scenario"],"seed":control["seed"],
        "camera_capture":capture,"frames":frames,
        "registered_sort_task_metadata":control["native_task_registration_before"],
        "task_objects_not_replaced_or_reordered":True,
        "actual_profiled_callback_order_frequencies":orders,
        "same_callback_order_across_profiled_ticks":summary["all_ticks_same_callback_order"],
        "actual_profiled_taskmgr_tick_count":expected,
        "native_source_rgb_impact":source_metrics,
        "unprofiled_i420_post_warmup_unique_sha":control["model_i420"]["post_warmup_unique_sha256"],
        "profiled_i420_post_warmup_unique_sha":profile["model_i420"]["post_warmup_unique_sha256"],
        "independent_process_exact_i420_frames":sum(x==y for x,y in zip(ia,ib)),
        "first_unmatched_independent_i420_frame_zero_based":next(
            (i for i,(x,y) in enumerate(zip(ia,ib)) if x!=y),None
        ),
        "capture_wall_time_observation_not_causal":timing,
        "profile_hook_introduces_cpu_overhead":True,
        "profiled_equals_unprofiled_render_semantics_proven":False,
        "task_callback_order_equals_gpu_render_pass_order":False,
        "model_scoring_allowed":False,
        "real_vehicle_testing":False,
        "official_onnx_native_repeatability_proven":False,
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="Paired native call trace controls")
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args(argv)
    control=json.loads((a.root/"unprofiled.json").read_text(encoding="utf-8"))
    profile=json.loads((a.root/"profiled.json").read_text(encoding="utf-8"))
    result=compare_profiled_control(control,profile)
    (a.root/"callback_order_comparison.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8",
    )
    print("META_NATIVE_PYTHON_CALLBACK_ORDER",json.dumps({
        "seed":result["seed"],"scenario":result["scenario"],
        "capture":result["camera_capture"],
        "actual_order":result["actual_profiled_callback_order_frequencies"],
        "source_road":result["native_source_rgb_impact"]["road"],
        "source_wide":result["native_source_rgb_impact"]["wide"],
        "matched_i420_frames":result["independent_process_exact_i420_frames"],
    },ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
