"""Fail-closed, three-independent-process PSSM/chase camera pose lag A-B.

Uninstrumented controller-free MetaDrive input path, CPU callback telemetry
and *explicitly changed* virtual main-scene camera arm are not interchangeable.
The injected camera arm is a SIM-only causal falsification test and is never a
replacement input for a native ONNX driving-model benchmark.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median

from bigbench.pssm_chase_pose_trace import (
    assess_pose_events,position_distance_m,
)
from scripts.native_pssm_chase_pose_trial import (
    ARMS,CAPTURES,INTERVENTION_DELTA_M,INTERVENTION_FRAMES,
)


def compare_pose_arms(reports:dict[str,dict]) -> dict:
    if set(reports)!=set(ARMS):
        raise ValueError("all three independent MetaDrive evidence arms required")
    ref=reports["boundary_control"]
    same=("seed","scenario","fraction","world_pose","capture","frames",
          "warmup","mode","taskmgr_calls_per_pair_from_original_code")
    summary={}
    for name in ARMS:
        value=reports[name]
        if (value.get("arm")!=name or
                value.get("status")!="OBSERVED_NATIVE_PSSM_CHASE_CAMERA_BOUNDARIES"):
            raise ValueError(f"{name}: native test incomplete/inconclusive")
        if any(value.get(key)!=ref.get(key) for key in same):
            raise ValueError(f"{name}: unequal scene, pose, camera sampling or clock")
        if value["capture"] not in CAPTURES or (
                value["mode"],value["taskmgr_calls_per_pair_from_original_code"]
            ) != CAPTURES[value["capture"]]:
            raise ValueError(f"{name}: wrong original camera/callback schedule")
        for key in ("registered_tasks_unchanged","panda_global_frame_deltas_match",
                    "panda_clock_finite","controlled_intervention_identity_valid",
                    "callback_evidence_complete"):
            if value.get(key) is not True:
                raise ValueError(f"{name}: missing native task/clock/intervention validity")
        if (value.get("native_gpu_hdr_extract_calls") !=0 or
                value.get("onnx_inference_executed") is not False or
                value.get("model_scoring_allowed") or value.get("real_vehicle_testing")):
            raise ValueError("GPU extraction/model scoring/physical vehicle forbidden")
        if any(value.get("plus_2m_pose_response",{}).get(k) is not True
               for k in ("road","wide")):
            raise ValueError(f"{name}: native RGB stale-buffer positive control failed")
        if (value["registered_tasks_before"]!=value["registered_tasks_after"]
                or value["registered_tasks_before"]!=ref["registered_tasks_before"]):
            raise ValueError(f"{name}: task registry was altered")
        timings=value.get("timeline",[])
        if len(timings)!=value["frames"]:
            raise ValueError(f"{name}: missing original camera frame receipts")
        if any(t.get("panda_global_frame_count_delta") !=
               value["taskmgr_calls_per_pair_from_original_code"] for t in timings):
            raise ValueError(f"{name}: unexpected Panda frame count")
        expected_profile=name!="boundary_control"
        expected_perturbed=name=="virtual_x_intervention"
        if value.get("callback_trace_instrumented") is not expected_profile:
            raise ValueError(f"{name}: CPU profiler arm mislabeled")
        if value.get("original_main_camera_state_deliberately_modified") is not expected_perturbed:
            raise ValueError(f"{name}: the camera intervention scope was misstated")
        if value.get("virtual_offset_intervention_frames_zero_based") != (
                list(INTERVENTION_FRAMES) if expected_perturbed else []):
            raise ValueError(f"{name}: wrong deliberate camera pose intervention frames")
        if value.get("virtual_offset_m_requested")!= (
                INTERVENTION_DELTA_M if expected_perturbed else 0):
            raise ValueError(f"{name}: wrong virtual camera perturbation displacement")
        if expected_profile:
            valid_ticks=[]
            for row in timings:
                raw=row.get("raw_python_call_return_events")
                if not isinstance(raw,list) or not raw:
                    raise ValueError(f"{name}: original raw callback entry/exit missing")
                tick=assess_pose_events(
                    raw,expected_ticks=value["taskmgr_calls_per_pair_from_original_code"]
                )
                stored=row.get("exact_python_callback_event_receipt")
                if stored!=tick:
                    raise ValueError(f"{name}: callback pose/MVP evidence was modified")
                valid_ticks.extend(tick["per_taskmgr_tick"])
        else:
            valid_ticks=[]
            if any(t.get("raw_python_call_return_events") or
                   t.get("exact_python_callback_event_receipt")
                   for t in timings):
                raise ValueError("unprofiled arm cannot have invented callbacks")

        offsets=[]
        first_tick_results=[]
        for row in timings:
            intervention=row.get("controlled_virtual_main_camera_offset")
            should_intervene=expected_perturbed and row["frame_index_zero_based"] in INTERVENTION_FRAMES
            if bool(intervention)!=should_intervene:
                raise ValueError(f"{name}: wrong intervention location")
            if should_intervene:
                if (intervention.get("virtual_intervention") !=
                        "MAIN_SCENE_CAMERA_X_OFFSET_BEFORE_TASK_TICK"):
                    raise ValueError("camera perturbation not explicitly identified")
                if abs(intervention.get("measured_delta_x_m",0)-INTERVENTION_DELTA_M)>1e-5:
                    raise ValueError("2m virtual camera displacement positive control failed")
                if (intervention.get("intervened_camera_world_pose") !=
                        row.get("camera_pose_before_task_tick")):
                    raise ValueError("captured PSSM call saw untracked perturbation state")
                if (intervention.get("original_camera_world_pose") !=
                        row.get("camera_pose_before_optional_intervention")):
                    raise ValueError("intervention world pose before-camera mismatch")
                offsets.append(row["frame_index_zero_based"])
                if not expected_profile:
                    raise ValueError("virtual intervention requires actual callback observation")
                tick=row["exact_python_callback_event_receipt"]["per_taskmgr_tick"][0]
                pssm_injected_distance=position_distance_m(
                    tick["pssm_entry_camera"],intervention["intervened_camera_world_pose"]
                )
                pssm_to_chase=position_distance_m(
                    tick["pssm_entry_camera"],tick["chase_exit_camera"]
                )
                first_tick_results.append({
                    "frame_index_zero_based":row["frame_index_zero_based"],
                    "pssm_entry_matched_imposed_virtual_camera_pose":
                        pssm_injected_distance <= 1e-5,
                    "pssm_entry_from_injected_pose_error_m":pssm_injected_distance,
                    "pssm_entry_vs_chase_exit_position_difference_m":pssm_to_chase,
                    "chase_moved_camera_on_injected_tick":
                        tick["camera_moved_during_chase_callback_m"]>1e-6,
                    "pssm_mvp_updated_in_injected_tick":
                        tick["pssm_mvp_changed_during_pssm_callback"],
                    "mvp_unchanged_during_chase":
                        not tick["pssm_mvp_changed_during_chase_callback"],
                })
        if expected_perturbed and len(offsets)!=len(INTERVENTION_FRAMES):
            raise ValueError("controlled intervention frame count incomplete")
        if expected_profile and len(valid_ticks)!=len(timings)*value["taskmgr_calls_per_pair_from_original_code"]:
            raise ValueError("actual profiler callback tick count incomplete")
        source={}
        for kind in ("road","wide"):
            receipt=value["raw_source_rgb"][kind]
            if len(receipt["all_frame_sha256"])!=value["frames"]:
                raise ValueError(f"{name}: missing raw native RGB time series")
            source[kind]={
                "post_warmup_unique_sha":receipt["post_warmup_unique_sha256"],
                "max_changed_pixels_post_warmup":
                    receipt["max_changed_pixels_post_warmup"],
            }
        i420=value["onnx_image_tensor_i420"]
        if len(i420["all_frame_sha256"])!=value["frames"]:
            raise ValueError(f"{name}: incomplete native new_img I420 receipt")
        capture_ns=[x["capture_elapsed_wall_ns"] for x in timings]
        if any(type(x) is not int or x<=0 for x in capture_ns):
            raise ValueError(f"{name}: missing CPU execution time")
        summary[name]={
            "callbacks_observed":len(valid_ticks),
            "pssm_before_chase_callback_count":
                sum(bool(x["pssm_precedes_chase_on_cpu"]) for x in valid_ticks),
            "pssm_mvp_update_during_callback_count":
                sum(x["pssm_mvp_changed_during_pssm_callback"] for x in valid_ticks),
            "chase_moved_camera_count":
                sum(x["camera_moved_during_chase_callback_m"]>0 for x in valid_ticks),
            "pssm_entry_pose_differs_from_chase_exit_count":
                sum(x["camera_pose_difference_between_pssm_entry_and_chase_exit_m"]>0
                    for x in valid_ticks),
            "median_capture_wall_ms":float(median(capture_ns)/1e6),
            "raw_source_rgb":source,
            "i420_post_warmup_unique_sha":i420["post_warmup_unique_sha256"],
            "controlled_intervention_first_tick_results":first_tick_results,
        }
    first=ref["onnx_image_tensor_i420"]["all_frame_sha256"]
    compare={}
    for name in ("boundary_observed","virtual_x_intervention"):
        second=reports[name]["onnx_image_tensor_i420"]["all_frame_sha256"]
        compare[name]={
            "cross_process_matched_i420_frames":
                sum(a==b for a,b in zip(first,second)),
            "cross_process_bit_exact_all":first==second,
        }
    return {
        "status":"NATIVE_PSSM_CHASE_CAMERA_POSE_CALLBACK_EVIDENCE_RECORDED",
        "seed":ref["seed"],"scenario":ref["scenario"],"capture":ref["capture"],
        "arm_metrics":summary,
        "independent_process_i420_control_comparisons":compare,
        "controlled_virtual_camera_perturbation_is_original_renderer_equivalent":False,
        "CPU_profile_intrudes_on_scheduler_timing":True,
        "specific_PSSM_shadow_depth_or_shader_bug_proven":False,
        "actual_callback_order_alone_proves_previous_frame_lag":False,
        "native_onnx_closed_loop_repeatability_proven":False,
        "real_vehicle_testing":False,"model_scoring_allowed":False,
        "warning":(
            "Observed main-camera pose during a PSSM CPU callback is not "
            "GPU shadow-map rendering proof. Deliberately displacing the virtual "
            "main camera changes scene state, and CPU profiling changes timing."
        ),
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="Compare 3 independent Panda camera pose arms")
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args(argv)
    reports={
        arm:json.loads((a.root/(arm+".json")).read_text(encoding="utf-8"))
        for arm in ARMS
    }
    result=compare_pose_arms(reports)
    (a.root/"pose_boundary_comparison.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8"
    )
    print("PSSM_CHASE_POSE_A_B",json.dumps({
        "status":result["status"],"seed":result["seed"],
        "scenario":result["scenario"],"capture":result["capture"],
        "metrics":{
            name:{
                "ticks":row["callbacks_observed"],
                "pssm_first":row["pssm_before_chase_callback_count"],
                "chase_moved":row["chase_moved_camera_count"],
                "mvp_changed":row["pssm_mvp_update_during_callback_count"],
                "i420_unique":row["i420_post_warmup_unique_sha"],
                "virtual_interventions":row["controlled_intervention_first_tick_results"],
            } for name,row in result["arm_metrics"].items()
        }
    },ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
