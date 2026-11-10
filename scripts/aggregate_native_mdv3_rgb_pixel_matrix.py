"""Aggregate four real original-PSSM official MD-V3 CPU RGB pixel-probe jobs.

Each job's image bytes and frame/model hashes must be independently verified,
not blindly trusted through a hand-authored GitHub Actions summary JSON.
A successful diagnostic is *not* the uninstrumented original repeatability.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.aggregate_original_mdv3_current_recheck import (
    SEEDS,SCENARIOS,MODEL_SHA256,
)
from scripts.compare_native_mdv3_rgb_pixels import evaluate_native_rgb_pixel_pair


def aggregate_native_rgb_pixel_matrix(root:Path) -> dict:
    cases=[]
    for seed in SEEDS:
        for scene in SCENARIOS:
            directory=root/f"seed-{seed}"/scene
            if not directory.is_dir():
                raise ValueError(f"missing independent native pixel sample {directory}")
            original=json.loads((directory/"raw_rgb_pixel_comparison.json").read_text(
                encoding="utf-8"
            ))
            # Re-decompress and verify EVERY original raw RGB frame in each
            # two-process artifact, re-check per-frame source SHA and pixel
            # metrics, and independently regenerate first-difference mask.
            computed=evaluate_native_rgb_pixel_pair(directory,save_masks=True)
            if computed!=original:
                raise ValueError(f"native RGB raw pixels differ from saved summary: {directory}")
            if (computed["seed"]!=seed or computed["scenario"]!=scene
                or computed["official_md_v3_model_sha256"]!=MODEL_SHA256
                or computed["independent_native_onnx_process_count"]!=2
                or computed["actual_onnx_steps_per_process"]!=12
                or computed["original_native_964x604_rgb_pairs_per_process_captured"]!=6
                or computed["status"] not in (
                    "FIRST_SOURCE_RGB_PIXEL_MISMATCH_MEASURED",
                    "SOURCE_RGB_BIT_EXACT_IN_12_STEPS",
                )
                or computed["model_scoring_allowed"] is not False
                or computed["real_vehicle_testing"] is not False
                or computed["gpu_shadow_texel_or_unique_causality_proven"] is not False):
                raise ValueError("invalid official native source RGB pixel diagnosis")
            first=computed["first_raw_source_diff_step"]
            first_fields={
                kind:(next((row for row in computed["pixel_metrics"][kind]
                            if row["step"]==first),None) if first else None)
                for kind in ("road","wide")
            }
            cases.append({
                "seed":seed,"scenario":scene,
                "status":computed["status"],
                "first_source_rgb_mismatch_step":first,
                "first_actual_onnx_new_img_mismatch_step":computed[
                    "source_to_onnx_first_divergence"][
                        "first_actual_onnx_new_img_mismatch_step"],
                "prior_step_virtual_pose_and_action_and_recurrent_equal":
                    computed["prior_step_virtual_pose_and_action_and_recurrent_equal"],
                "first_source_mismatch_pixel_detail":first_fields,
                "first_difference_binary_mask":computed["first_difference_binary_mask"],
                "instrumented_strict_status":computed[
                    "strict_native_repeat_status_in_instrumented_runs"],
            })
    count=sum(x["status"]=="FIRST_SOURCE_RGB_PIXEL_MISMATCH_MEASURED"
              for x in cases)
    return {
        "status":"STAGE7_FOUR_SCENE_CPU_RGB_PIXEL_DIAGNOSTICS_VALIDATED",
        "official_md_v3_sha256":MODEL_SHA256,
        "real_original_pssm_native_processes":len(cases)*2,
        "per_process_original_onnx_new_image_steps":12,
        "first_six_native_road_wide_rgb_pairs_retained_per_process":True,
        "cases_with_source_rgb_pixel_mismatch_measured":count,
        "cases_total":len(cases),
        "per_case":cases,
        "additional_cpu_memory_retention_may_affect_renderer_timing":True,
        "original_uninstrumented_strict_repeatability_proven":False,
        "shadow_depth_or_hdr_pixel_cause_proven":False,
        "model_scoring_allowed":False,
        "real_vehicle_testing":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description="four real original-MD-V3 native pixel archives")
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    result=aggregate_native_rgb_pixel_matrix(args.root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,
                                    allow_nan=False)+"\n",encoding="utf-8")
    print("STAGE7_NATIVE_PIXEL_MATRIX",json.dumps({
        "cases":result["cases_total"],
        "measured_source_pixel_mismatches":
            result["cases_with_source_rgb_pixel_mismatch_measured"],
        "first_differences":[{
            "seed":x["seed"],"scene":x["scenario"],
            "first":x["first_source_rgb_mismatch_step"],
            "native_road_pixels":(
                x["first_source_mismatch_pixel_detail"]["road"]["changed_pixel_count"]
                if x["first_source_mismatch_pixel_detail"]["road"] else None
            ),
            "native_wide_pixels":(
                x["first_source_mismatch_pixel_detail"]["wide"]["changed_pixel_count"]
                if x["first_source_mismatch_pixel_detail"]["wide"] else None
            ),
        } for x in result["per_case"]],
        "warning":"diagnostic data validity != original model repeatability",
    },ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
