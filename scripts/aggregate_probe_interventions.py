"""Fail-closed summary of individual GPU extraction interventions.

CI success means ONLY that a causal diagnostic was recorded. It does not mean
native renderer reproducibility or model driving performance was validated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROBES = ("none", "pssm_depth", "road_hdr", "wide_hdr", "all")


def aggregate_interventions(reports: dict[str, dict]) -> dict:
    if set(reports) != set(PROBES):
        raise ValueError("must observe all five independent probe modes")
    ref = reports["none"]
    required = ("seed", "pose_id", "pose", "frames", "warmup", "scene",
                "capture_mode", "ablation", "removed_task")
    if ref["status"] != "OBSERVED_SELECTIVE_PROBE":
        raise ValueError("no-GPU control must be responsive before and after")
    observations = {}
    for mode, row in reports.items():
        if any(row[k] != ref[k] for k in required) or row.get("probe_stage") != mode:
            raise ValueError(f"{mode}: unmatched native condition or incorrect probe")
        if row["real_vehicle_testing"] or row["model_scoring_allowed"]:
            raise ValueError("vehicle/model scoring not permitted")
        if row.get("ablation") != "baseline" or row.get("removed_task") is not None:
            raise ValueError("readback study must not remove scene tasks")
        if not row.get("required_probe_buffers_available"):
            raise ValueError(f"{mode}: required GPU texture or matrix unavailable")
        before = row["before_gpu_probe_pose_positive_control"]
        after = row["pose_shift_positive_control"]
        if not all(before.get(k, False) for k in ("road", "wide")):
            raise ValueError(f"{mode}: camera movement invalid before probe")
        if after.get("road") != after.get("wide"):
            raise ValueError(f"{mode}: inconsistent two-camera response")
        observed_response = all(after[k] for k in ("road", "wide"))
        expected = ("OBSERVED_BUFFER_CHAIN" if mode == "all" and observed_response
                    else "OBSERVED_SELECTIVE_PROBE" if observed_response
                    else "GPU_PROBE_INTERVENTION_OBSERVED")
        if row["status"] != expected:
            raise ValueError(f"{mode}: status contradicts measured response")
        if mode == "none" and not observed_response:
            raise ValueError("no-GPU control lost camera response")
        observations[mode] = {
            "post_probe_camera_response": observed_response,
            "camera_response_lost": not observed_response,
            "observed_report_status": row["status"],
            "raw_road_unique_sha256_after_warmup":
                row["stages"]["road_rgb"]["unique_sha256_after_warmup"],
            "raw_wide_unique_sha256_after_warmup":
                row["stages"]["wide_rgb"]["unique_sha256_after_warmup"],
            "i420_unique_sha256_after_warmup":
                row["stages"]["onnx_i420"]["unique_sha256_after_warmup"],
        }
    return {
        "status": "GPU_READBACK_INTERVENTION_ISOLATION_OBSERVED",
        "seed": ref["seed"], "pose_id": ref["pose_id"],
        "readback_probe_effects": observations,
        "observed_probe_modes_causing_response_loss": [
            k for k, v in observations.items() if v["camera_response_lost"]],
        "cause_and_untouched_render_equivalence_unproven": True,
        "real_vehicle_testing": False, "model_scoring_allowed": False,
        "official_onnx_closed_loop_repeatability_validated": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    args = p.parse_args(argv)
    reports = {mode: json.loads((args.root / (mode + ".json")).read_text(encoding="utf-8"))
               for mode in PROBES}
    out = aggregate_interventions(reports)
    (args.root / "probe_intervention_summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    print("NATIVE_GPU_PROBE_INTERVENTION_SUMMARY",
          json.dumps({"seed": out["seed"], "response_lost_when_probing":
                      out["observed_probe_modes_causing_response_loss"],
                      "classification": out["status"]}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
