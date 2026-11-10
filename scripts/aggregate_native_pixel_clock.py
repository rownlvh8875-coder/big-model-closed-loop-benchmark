"""Compare fresh native pixel/clock reports without calling anything a model PASS."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


SCHEDULES = {
    "perceive_baseline": ("perceive_sequential", "baseline", 2),
    "task_baseline": ("task_step_pair", "baseline", 1),
    "graphics_baseline": ("graphics_frame_pair", "baseline", 0),
    "task_shadow_off": ("task_step_pair", "shadow_off", 1),
}


def compare_pixel_clock_conditions(reports: dict[str, dict]) -> dict:
    if set(reports) != set(SCHEDULES):
        raise ValueError("all four independently initialized native schedule receipts required")
    first = reports["task_baseline"]
    match_fields = ("seed", "scenario", "fraction", "camera_pose", "frames", "warmup")
    summary = {}
    for label, (mode, ablation, ticks) in SCHEDULES.items():
        report = reports[label]
        if report.get("status") != "OBSERVED_NATIVE_PIXEL_CLOCK":
            raise ValueError(f"{label}: missing native positive control or clock measurement")
        if (report.get("mode") != mode or report.get("ablation") != ablation):
            raise ValueError(f"{label}: wrong task/render condition")
        if any(report.get(field) != first.get(field) for field in match_fields):
            raise ValueError(f"{label}: not the same native scene and camera pose")
        if report.get("gpu_texture_extract_calls") != 0 or report.get("onnx_inference_used") is not False:
            raise ValueError(f"{label}: invasive GPU extraction or model scoring prohibited")
        if report.get("real_vehicle_testing") or report.get("model_scoring_allowed"):
            raise ValueError("real vehicle or model scoring must remain disabled")
        if not all(report["camera_plus_2m_positive"][camera] for camera in ("road", "wide")):
            raise ValueError(f"{label}: stale image may be mistaken for deterministic frame")
        if (report.get("expected_taskMgr_frame_count_delta_per_pair") != ticks
                or report.get("all_taskMgr_clock_deltas_as_expected") is not True):
            raise ValueError(f"{label}: task scheduler ticks were not observed as expected")
        observed = report.get("clock_timeline", [])
        if len(observed) != report["frames"]:
            raise ValueError(f"{label}: missing per-frame clock receipts")
        if any(t.get("global_clock_frame_count_delta") != ticks for t in observed):
            raise ValueError(f"{label}: inconsistent frame-clock delta")
        if report.get("pssm_task_identity_correct") is not True:
            raise ValueError(f"{label}: incorrect PSSM task identity")
        if ablation == "shadow_off":
            a = report.get("ablation_receipt") or {}
            if a.get("ablation") != "PSSM.update" or a.get("graphics_igLoop_preserved") is not True:
                raise ValueError(f"{label}: disabling shadow task not proven")
        elif report.get("ablation_receipt") is not None:
            raise ValueError(f"{label}: baseline must not disable tasks")
        if report.get("cpu_readbacks_bit_exact_without_new_render") is not True:
            raise ValueError(f"{label}: same completed GPU frame CPU copies changed")

        source = {}
        model = {}
        for camera in ("road", "wide"):
            a, b = report["source_rgb"][camera], report["model_rgb"][camera]
            if len(a["all_frame_sha256"]) != report["frames"]:
                raise ValueError(f"{label}: raw frames missing")
            if len(b["all_frame_sha256"]) != report["frames"]:
                raise ValueError(f"{label}: model warped frames missing")
            source[camera] = {
                "unique_sha_after_warmup": a["post_warmup_unique_sha256"],
                "first_divergence_frame_index_zero_based":
                    a["first_divergence_frame_index_zero_based"],
                "max_changed_pixels_after_warmup": a["max_changed_pixels_post_warmup"],
                "first_changed_pixel_examples": next(
                    (row["changed_pixel_examples"]
                     for row in a["per_frame_vs_first_post_warmup"]
                     if row["changed_pixels"] > 0), []
                ),
                "first_changed_bbox_xyxy_inclusive": next(
                    (row["bounding_box_xyxy_inclusive"]
                     for row in a["per_frame_vs_first_post_warmup"]
                     if row["changed_pixels"] > 0), None
                ),
            }
            model[camera] = {
                "unique_sha_after_warmup": b["post_warmup_unique_sha256"],
                "max_changed_pixels_after_warmup": b["max_changed_pixels_post_warmup"],
            }
        i420 = report["onnx_i420"]
        if len(i420["all_frame_sha256"]) != report["frames"]:
            raise ValueError(f"{label}: I420 frame count missing")
        summary[label] = {
            "mode": mode, "ablation": ablation,
            "measured_taskMgr_frame_ticks_per_pair": ticks,
            "raw_sensor_rgb": source,
            "warped_model_rgb": model,
            "i420_unique_sha_after_warmup": i420["post_warmup_unique_sha256"],
            "i420_max_changed_elements_after_warmup":
                i420["max_changed_elements_post_warmup"],
            "first_i420_changed_element_indices": next(
                (row["first_changed_indices_camera_plane_row_col"]
                 for row in i420["per_frame_vs_first_post_warmup"]
                 if row["changed_elements"] > 0), None
            ),
            "post_warmup_i420_bit_exact": i420["bit_exact_after_warmup"],
            "clock_observed_real_time_deltas_s": [
                row["real_time_delta_s"] for row in observed],
        }
    return {
        "status": "NATIVE_PIXEL_CLOCK_TASK_CORRELATIONS_RECORDED",
        "seed": first["seed"], "scenario": first["scenario"],
        "fraction": first["fraction"], "frames": first["frames"],
        "conditions": summary,
        "same_render_semantics_proven": False,
        "specific_shader_or_task_cause_proven": False,
        "model_closed_loop_reproducibility_proven": False,
        "real_vehicle_testing": False, "model_scoring_allowed": False,
        "warning": (
            "Comparing taskMgr.step, sequential perceive, graphicsFrame-only and "
            "shadow-task removal changes camera timing/render semantics. "
            "Pixel/clock associations do not identify a unique root cause."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    reports = {label: json.loads((args.root / (label + ".json")).read_text(
        encoding="utf-8")) for label in SCHEDULES}
    result = compare_pixel_clock_conditions(reports)
    (args.root / "pixel_clock_comparison.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print("NATIVE_PIXEL_CLOCK_COMPARE", json.dumps({
        "status": result["status"], "seed": result["seed"],
        "scenario": result["scenario"], "mode_summaries": {
            name: {
                "i420_unique": item["i420_unique_sha_after_warmup"],
                "raw_pixel_change_max": {
                    k: v["max_changed_pixels_after_warmup"]
                    for k,v in item["raw_sensor_rgb"].items()
                },
            } for name,item in result["conditions"].items()
        },
    }, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
