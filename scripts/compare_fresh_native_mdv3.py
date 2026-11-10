"""Fail-closed independent-process official ONNX native-frame reproducibility.

A successful GitHub Actions diagnostic may legitimately report a FAILED strict
repeatability gate: capturing true disagreement is NOT an ONNX model ranking.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROWS=(
    "time_s", "world_x_m", "world_y_m", "heading_rad", "speed_mps",
    "source_road_rgb_sha256", "source_wide_rgb_sha256",
    "desired_curvature_1pm", "desired_acceleration_mps2",
    "road_frame_sha256", "wide_frame_sha256", "new_img_sha256",
    "raw_model_action", "raw_action_sha256", "state_after_step_sha256",
)
MATCH_FIELDS=(
    "model_sha256", "scenario", "seed", "requested_steps",
    "completed_steps", "initial_fraction", "camera_capture_mode",
)


def compare_fresh_trials(a: dict, b: dict) -> dict:
    for label, item in (("first",a),("second",b)):
        if item.get("status")!="DIAGNOSTIC_EXECUTED":
            raise ValueError(f"{label} native ONNX trial not completed")
        if item.get("model_scoring_allowed") or item.get("real_vehicle_testing"):
            raise ValueError("model ranking/vehicle controls may not be enabled")
        if item.get("camera_convergence_attempts") != 0 or item.get("camera_pixel_tolerance") != 0:
            raise ValueError("camera convergence/tolerance invalidates original input condition")
        if item.get("camera_image_interpolation_or_replay") is not False:
            raise ValueError("recorded-frame substitution or interpolation prohibited")
        if item.get("gpu_hdr_extraction") is not False or item.get("pssm_update_preserved") is not True:
            raise ValueError("native scene/render semantics changed")
        if not item.get("actual_onnx_image_feed_sha_captured_per_step"):
            raise ValueError("model new_img SHA evidence missing")
        if item.get("native_source_964x604_rgb_sha_captured_per_step") is not True:
            raise ValueError("native source camera RGB evidence missing")
        if not item.get("raw_action_and_recurrent_sha_captured_per_step"):
            raise ValueError("action or recurrent output evidence missing")
        if len(item.get("frames",[]))!=item.get("requested_steps"):
            raise ValueError("incomplete camera/input step receipts")
    if any(a.get(k)!=b.get(k) for k in MATCH_FIELDS):
        raise ValueError("repeat model/scenario/seed/native capture schedule differs")
    if a.get("process_uuid")==b.get("process_uuid") or not a.get("process_uuid") or not b.get("process_uuid"):
        raise ValueError("two independent Python inference process IDs required")
    if a.get("process_id")==b.get("process_id"):
        raise ValueError("ONNX processes must be distinct")
    discrepancies=[]
    distances=[]
    headings=[]
    for step,(left,right) in enumerate(zip(a["frames"],b["frames"]),1):
        if any(field not in left or field not in right for field in ROWS):
            raise ValueError(f"step {step} has missing evidence fields")
        for record in (left,right):
            if any(not isinstance(record[k],(int,float)) or not math.isfinite(record[k])
                   for k in ("time_s","world_x_m","world_y_m","heading_rad","speed_mps")):
                raise ValueError(f"step {step} nonfinite pose or time")
            if not isinstance(record["raw_model_action"],list) or not record["raw_model_action"]:
                raise ValueError(f"step {step} raw model action not recorded")
        delta_m=math.hypot(left["world_x_m"]-right["world_x_m"],
                           left["world_y_m"]-right["world_y_m"])
        distances.append(delta_m)
        headings.append(abs(left["heading_rad"]-right["heading_rad"]))
        differences=[name for name in ROWS if left[name]!=right[name]]
        if differences:
            discrepancies.append({"step":step,"differing_fields":differences,
                                  "pose_delta_m":delta_m})
    exact=not discrepancies
    source_exact=all("source_road_rgb_sha256" not in row["differing_fields"] and
                     "source_wide_rgb_sha256" not in row["differing_fields"]
                     for row in discrepancies)
    model_canvas_exact=all("road_frame_sha256" not in row["differing_fields"] and
                           "wide_frame_sha256" not in row["differing_fields"]
                           for row in discrepancies)
    camera_exact=source_exact and model_canvas_exact
    tensor_exact=all("new_img_sha256" not in row["differing_fields"]
                     for row in discrepancies)
    first_fields=discrepancies[0]["differing_fields"] if discrepancies else []
    first_boundary=(
        "NATIVE_964x604_RGB" if any(f in first_fields for f in
                                      ("source_road_rgb_sha256","source_wide_rgb_sha256"))
        else "WARPED_512x256_RGB" if any(f in first_fields for f in
                                            ("road_frame_sha256","wide_frame_sha256"))
        else "ACTUAL_I420_NEW_IMG" if "new_img_sha256" in first_fields
        else "ONNX_ACTION_OR_RECURRENT" if any(f in first_fields for f in
                                ("raw_action_sha256","state_after_step_sha256"))
        else "POSE_OR_TIME_ONLY" if first_fields else None
    )
    return {
        "status": "STRICT_NATIVE_ONNX_REPEAT_MATCH" if exact
                  else "STRICT_NATIVE_ONNX_REPEAT_MISMATCH",
        "exact_repeated_execution_gate_passed":exact,
        "compare_rule":"bit-exact native raw 964x604, warped 512x256, actual I420 new_img feed, raw actions, recurrent states, virtual pose and time",
        "scenario":a["scenario"],"seed":a["seed"],
        "steps":a["requested_steps"],"initial_fraction":a["initial_fraction"],
        "camera_rgb_frames_match":camera_exact,
        "source_native_rgb_frames_match":source_exact,
        "warped_model_rgb_frames_match":model_canvas_exact,
        "actual_onnx_new_img_sha256_match":tensor_exact,
        "first_observed_mismatch_boundary":first_boundary,
        "max_xy_position_delta_m":max(distances),
        "max_heading_delta_rad":max(headings),
        "first_diverging_step":discrepancies[0]["step"] if discrepancies else None,
        "mismatches":discrepancies,
        "first_process_uuid":a["process_uuid"],
        "second_process_uuid":b["process_uuid"],
        "model_sha256":a["model_sha256"],
        "no_tolerance_or_pixel_rewriting":True,
        "scene_pssm_not_disabled":True,
        "official_model_driving_performance_ranked":False,
        "real_vehicle_testing":False,"cd210_fallback":False,
        "model_scoring_allowed":False,
        "diagnostic_capture_complete":True,
        "warning":"Strict repeatability in this short native environment is not camera fidelity, safety, long-run, cross-engine or model ranking proof",
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="Compare two fresh process MD-V3 ONNX receipts")
    p.add_argument("--root",type=Path,required=True)
    args=p.parse_args(argv)
    first=json.loads((args.root/"run_0.json").read_text(encoding="utf-8"))
    second=json.loads((args.root/"run_1.json").read_text(encoding="utf-8"))
    verdict=compare_fresh_trials(first,second)
    (args.root/"strict_native_repeat_verdict.json").write_text(
        json.dumps(verdict,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8")
    print("STRICT_MDV3_INDEPENDENT_NATIVE_REPEAT",json.dumps({
        "status":verdict["status"],"scenario":verdict["scenario"],
        "seed":verdict["seed"],"first_diverging_step":verdict["first_diverging_step"],
        "max_xy_position_delta_m":verdict["max_xy_position_delta_m"],
        "camera_frames_match":verdict["camera_rgb_frames_match"],
        "source_rgb_match":verdict["source_native_rgb_frames_match"],
        "model_canvas_rgb_match":verdict["warped_model_rgb_frames_match"],
        "first_boundary":verdict["first_observed_mismatch_boundary"],
        "new_img_match":verdict["actual_onnx_new_img_sha256_match"],
    },ensure_ascii=False),flush=True)
    # Reporting a genuine mismatch is a successful *diagnostic*, NOT a gate PASS.
    return 0


if __name__=="__main__":
    raise SystemExit(main())
