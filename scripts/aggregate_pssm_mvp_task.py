"""Fail-closed independent-Panda-context aggregation of PSSM matrix/clock data.

Only diagnostic measurements are compared. Fixed non-real-time clock, GPU
graphics-only and PSSM-off arms change execution/rendering semantics and are
never used for official driving-model quality scores.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.native_pssm_mvp_task_trace import CONDITIONS


def aggregate_shadow_mvp(reports: dict[str,dict]) -> dict:
    if set(reports) != set(CONDITIONS):
        raise ValueError("all four fresh Panda native conditions required")
    baseline = reports["paired_baseline"]
    match = ("seed","scenario","fraction","world_pose",
             "fixed_virtual_clock","frames","warmup")
    outcomes = {}
    for name, record in reports.items():
        mode, removed, global_delta, task_calls = CONDITIONS[name]
        if record.get("status") != "OBSERVED_NATIVE_PSSM_MVP_TASK_TIMING":
            raise ValueError(f"{name}: missing valid native MVP/positive-control receipt")
        if any(record.get(k)!=baseline.get(k) for k in match):
            raise ValueError(f"{name}: mismatched scene/seed/camera/clock")
        if (record.get("condition")!=name or record.get("mode")!=mode or
                record.get("removed_task")!=removed):
            raise ValueError(f"{name}: invalid PSSM/renderer experimental identity")
        if record.get("pssm_shadow_atlas_gpu_readback_performed") is not False:
            raise ValueError(f"{name}: intrusive GPU texture extraction forbidden")
        if (record.get("onnx_inference_executed") is not False or
                record.get("model_scoring_allowed") or record.get("real_vehicle_testing")):
            raise ValueError(f"{name}: model/real-car claims forbidden")
        if record.get("registered_tasks_unchanged") is not True:
            raise ValueError(f"{name}: Panda task registry changed mid-run")
        if record.get("expected_global_frame_delta_per_camera_pair")!=global_delta:
            raise ValueError(f"{name}: global frame count contract changed")
        if record.get("taskmgr_calls_from_code_not_global_clock")!=task_calls:
            raise ValueError(f"{name}: taskMgr call path mislabeled")
        if record.get("global_frame_deltas_match") is not True:
            raise ValueError(f"{name}: global frame counter mismatch")
        if record.get("clock_values_finite") is not True:
            raise ValueError(f"{name}: nonfinite clock")
        if any(record.get("plus_2m_camera_pose_response",{}).get(k) is not True
               for k in ("road","wide")):
            raise ValueError(f"{name}: stale camera is a false stability proof")
        if record.get("mvp_post_warmup",{}).get("status")!="OBSERVED_NUMERIC_MVP_SEQUENCE":
            raise ValueError(f"{name}: missing numeric PSSM matrix values")
        if record["mvp_post_warmup"].get("frame_count") != record["frames"]:
            raise ValueError(f"{name}: truncated PSSM matrix sequence")
        if len(record.get("per_frame_before_after_and_intra_pair",[])) != record["frames"]:
            raise ValueError(f"{name}: incomplete render/clock time series")
        if record["mvp_post_warmup"].get("not_a_gpu_shadow_map_capture") is not True:
            raise ValueError(f"{name}: GPU shadow atlas misidentified as numeric matrix")
        registration = record.get("task_registry_sort_metadata_only_not_execution_proof",[])
        names=[x["name"] for x in registration]
        if "igLoop" not in names or ("PSSM.update" in names) != (removed is None):
            raise ValueError(f"{name}: wrong PSSM/graphics engine task registration")
        if removed:
            receipt=record.get("ablation_receipt") or {}
            if receipt.get("ablation")!="PSSM.update" or receipt.get("graphics_igLoop_preserved") is not True:
                raise ValueError(f"{name}: shadow disablement not proven")
        elif record.get("ablation_receipt") is not None:
            raise ValueError(f"{name}: baseline PSSM unexpectedly removed")
        if any(x["observed_global_frame_delta"]!=global_delta
               for x in record["per_frame_before_after_and_intra_pair"]):
            raise ValueError(f"{name}: per-frame clock evidence inconsistent")
        raw = record["raw_source_rgb"]
        outputs={
            k: {
                "unique_sha_after_warmup": raw[k]["post_warmup_unique_sha256"],
                "max_changed_pixels": raw[k]["max_changed_pixels_post_warmup"],
                "first_diverging_index": raw[k]["first_divergence_frame_index_zero_based"],
                "mvp_raw_association": record["pssm_vs_raw_rgb_associations"][k]["classification"],
            }
            for k in ("road","wide")
        }
        outcomes[name]={
            "mode":mode,"removed_task":removed,
            "mvp_post_warmup_unique_sha256":
                record["mvp_post_warmup"]["post_warmup_unique_mvp_sha256"],
            "mvp_first_diverging_index":
                record["mvp_post_warmup"]["first_changed_frame_index_zero_based"],
            "mvp_max_numeric_delta":
                record["mvp_post_warmup"]["max_absolute_numeric_matrix_delta_post_warmup"],
            "mvp_max_changed_elements":
                record["mvp_post_warmup"]["max_changed_matrix_elements_post_warmup"],
            "mvp_changed_during_camera_pair_count":
                sum(bool(x["mvp_changed_during_pair"]) for x in
                    record["per_frame_before_after_and_intra_pair"]),
            "main_camera_changed_during_pair_count":
                sum(bool(x["main_camera_moved_after_tick"]) for x in
                    record["per_frame_before_after_and_intra_pair"]),
            "light_pose_changed_during_pair_count":
                sum(bool(x["light_pose_moved_after_tick"]) for x in
                    record["per_frame_before_after_and_intra_pair"]),
            "road_wide_source_rgb":outputs,
            "post_warmup_unique_i420_sha256":
                record["onnx_i420"]["post_warmup_unique_sha256"],
            "global_frame_increments_from_actual_clock":global_delta,
            "taskMgr_step_calls_from_inspected_python_code":task_calls,
            "task_sort_metadata_is_not_actual_execution_trace":True,
        }
    return {
        "status":"PSSM_MVP_TASK_CLOCK_NATIVE_OBSERVATIONS_RECORDED",
        "seed":baseline["seed"],"scenario":baseline["scenario"],
        "fraction":baseline["fraction"],
        "fixed_virtual_clock":baseline["fixed_virtual_clock"],
        "observed_arms":outcomes,
        "specific_shadow_shader_causality_proven":False,
        "fixed_clock_equivalent_to_default_renderer_proven":False,
        "official_onnx_closed_loop_repeatability_proven":False,
        "model_scoring_allowed":False,"real_vehicle_testing":False,
        "warning": (
            "PSSM MVP is a CPU matrix receipt, NOT GPU shadow-map content. "
            "Reading it and task metadata can change wall-clock scheduling. "
            "Registration sort hints are NOT an execution-order trace."
        ),
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args(argv)
    reports={
        name:json.loads((a.root/(name+".json")).read_text(encoding="utf-8"))
        for name in CONDITIONS
    }
    result=aggregate_shadow_mvp(reports)
    (a.root/"mvp_task_clock_comparison.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8",
    )
    print("NATIVE_PSSM_MVP_AGGREGATE",json.dumps({
        "status":result["status"],"seed":result["seed"],
        "scenario":result["scenario"],"fixed_clock":result["fixed_virtual_clock"],
        "conditions":{
            k:{
                "mvp_unique":x["mvp_post_warmup_unique_sha256"],
                "i420_unique":x["post_warmup_unique_i420_sha256"],
                "raw_road_change_max":x["road_wide_source_rgb"]["road"]["max_changed_pixels"],
                "raw_wide_change_max":x["road_wide_source_rgb"]["wide"]["max_changed_pixels"],
            } for k,x in result["observed_arms"].items()
        },
    },ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
