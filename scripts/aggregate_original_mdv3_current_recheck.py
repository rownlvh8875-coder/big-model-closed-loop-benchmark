"""Strict original-PSSM official MD-V3 two-process new-frame verdict aggregator.

This revalidates four independent GitHub runner artifacts by calling the
existing strict comparator on each pair of actual original MetaDrive 0.4.3
new-image ONNX traces. A workflow SUCCESS is diagnostic-only: if any strict
gate fails, the complete aggregate explicitly reports 0..4 passes without
promoting that to driving quality or a completed stage seven.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.compare_fresh_native_mdv3 import compare_fresh_trials


SEEDS=(20261109,20261110)
SCENARIOS=("s_curve_left_right","s_curve_right_left")
MODEL_SHA256="35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199"
MODEL_ID="1365126a-e71e-4778-be00-8ab92dc82c09/12864/big_driving_supercombo.onnx"
STEPS=12
INITIAL_FRACTION=.12


def aggregate_original_mdv3(root:Path) -> dict:
    rows=[]
    for seed in SEEDS:
        for scenario in SCENARIOS:
            folder=root/f"seed-{seed}"/scenario
            if not folder.is_dir():
                raise ValueError(f"missing real MD-V3 native frame trial directory {folder}")
            a=json.loads((folder/"run_0.json").read_text(encoding="utf-8"))
            b=json.loads((folder/"run_1.json").read_text(encoding="utf-8"))
            original=json.loads(
                (folder/"strict_native_repeat_verdict.json").read_text(encoding="utf-8")
            )
            if any(
                item.get("model_sha256")!=MODEL_SHA256
                or item.get("seed")!=seed
                or item.get("scenario")!=scenario
                or item.get("initial_fraction")!=INITIAL_FRACTION
                or item.get("requested_steps")!=STEPS
                or item.get("completed_steps")!=STEPS
                or item.get("pssm_update_preserved") is not True
                or item.get("gpu_hdr_extraction") is not False
                or item.get("camera_pixel_tolerance") !=0
                or item.get("camera_convergence_attempts")!=0
                or item.get("camera_image_interpolation_or_replay") is not False
                or item.get("real_vehicle_testing") or item.get("model_scoring_allowed")
                for item in (a,b)
            ):
                raise ValueError(f"original MD-V3 model/renderer new-frame evidence invalid: {folder}")
            recomputed=compare_fresh_trials(a,b)
            if recomputed!=original:
                raise ValueError("native MD-V3 original signed verdict differs from raw two processes")
            if recomputed.get("scene_pssm_not_disabled") is not True:
                raise ValueError("PSSM disabled/changed by untrusted native trial")
            if recomputed.get("real_vehicle_testing") or recomputed.get("model_scoring_allowed"):
                raise ValueError("unsafe real vehicle/ONNX ranking claim")
            rows.append({
                "seed":seed,"scenario":scenario,"steps_per_process":STEPS,
                "independent_process_count":2,
                "strict_status":recomputed["status"],
                "exact_repeated_execution_gate_passed":
                    recomputed["exact_repeated_execution_gate_passed"],
                "first_diverging_step":recomputed["first_diverging_step"],
                "first_observed_mismatch_boundary":
                    recomputed["first_observed_mismatch_boundary"],
                "source_native_rgb_frames_match":
                    recomputed["source_native_rgb_frames_match"],
                "warped_model_rgb_frames_match":
                    recomputed["warped_model_rgb_frames_match"],
                "actual_onnx_new_img_sha256_match":
                    recomputed["actual_onnx_new_img_sha256_match"],
                "max_xy_position_delta_m":recomputed["max_xy_position_delta_m"],
                "full_discrepancy_receipt":recomputed["mismatches"],
            })
    if len(rows)!=len(SEEDS)*len(SCENARIOS):
        raise ValueError("four original MD-V3 independent native evaluations required")
    passed=sum(bool(x["exact_repeated_execution_gate_passed"]) for x in rows)
    return {
        "status":("ORIGINAL_MDV3_STRICT_NATIVE_4_CASES_PASS" if passed==len(rows)
                  else "ORIGINAL_MDV3_STRICT_NATIVE_GATE_NOT_PASSED"),
        "model_sha256":MODEL_SHA256,
        "official_model_id":MODEL_ID,
        "native_simulator":"MetaDrive 0.4.3 original PSSM.update",
        "total_independent_native_onnx_processes":len(rows)*2,
        "actual_onnx_new_image_steps_across_all_processes":len(rows)*2*STEPS,
        "strict_gate_pass_count":passed,
        "strict_gate_total":len(rows),
        "all_four_cases_strict_native_gate_passed":passed==len(rows),
        "per_seed_scene":rows,
        "CI_workflow_success_does_not_mean_strict_gate_passed":True,
        "model_scoring_allowed":False,
        "driving_model_performance_ranking_allowed":False,
        "real_vehicle_testing":False,
        "cd210_fallback":False,
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="Original official MD-V3 strict native repeat recheck")
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    result=aggregate_original_mdv3(args.root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(
        json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8"
    )
    print("ORIGINAL_MDV3_CURRENT_MAIN_STRICT_RECHECK",json.dumps({
        "status":result["status"],
        "pass":f'{result["strict_gate_pass_count"]}/{result["strict_gate_total"]}',
        "conditions":[{
            "seed":x["seed"],"scene":x["scenario"],
            "first_diff_step":x["first_diverging_step"],
            "first_diff_boundary":x["first_observed_mismatch_boundary"],
            "max_xy_delta_m":x["max_xy_position_delta_m"],
        } for x in result["per_seed_scene"]],
        "warning":"DIAGNOSTIC CI SUCCESS != MODEL REPEAT GATE PASS",
    },ensure_ascii=False),flush=True)
    # A real mismatch is a scientific observation, not CI test infrastructure failure.
    return 0


if __name__=="__main__":
    raise SystemExit(main())
