"""One terminal-only PSSM/HDR GPU snapshot AFTER an otherwise unprobed frame series.

Experimental virtual MetaDrive 0.4.3 only; diagnostic, not a model score.
Never call GPU extractTextureData until the LAST completed frame is frozen
into independent CPU RGB/I420 bytes. No post-snapshot render or pose movement.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.render_causality import raw_rgb_frame, summarize_frame_sequence
from bigbench.task_ablation import remove_visual_scene_task
from scripts.metadrive_render_causality import (
    WORLD_POSE, _packed_summary, _scene_snapshot, capture_with_readback,
    read_cpu_texture, source_model_frames,
)
from scripts.metadrive_hdr_trace import gpu_readback, pssm_matrix_receipt, POSES


CONDITIONS = {
    "baseline_no_gpu": {"ablation": None, "terminal_probe": False},
    "baseline_terminal": {"ablation": None, "terminal_probe": True},
    "shadow_off_terminal": {"ablation": "PSSM.update", "terminal_probe": True},
}
GPU_STAGES = ("pssm_mvp", "pssm_depth", "road_hdr", "wide_hdr")


def snapshot(seed: int, pose_id: str, frames: int, warmup: int, condition: str) -> dict:
    if condition not in CONDITIONS or pose_id not in POSES:
        raise ValueError("unknown condition or pose")
    if type(frames) is not int or not 4 <= frames <= 12 or not 0 <= warmup <= frames - 2:
        raise ValueError("require bounded native frames/warmup")
    provider = NativeMetaDriveProvider(seed=seed)
    try:
        engine = provider.env.engine
        cfg = CONDITIONS[condition]
        ablation_receipt = (remove_visual_scene_task(engine.taskMgr, cfg["ablation"])
                            if cfg["ablation"] else None)
        from metadrive.constants import CamMask
        provider.env.vehicle.origin.hide(CamMask.RgbCam)
        pose = POSES[pose_id]
        moved = ((pose[0][0] + 2.0, pose[0][1], pose[0][2]), pose[1])
        # One pre-experiment spatial positive control for EACH independent process.
        # No GPU extraction at any point before or during the frame series.
        ref, _ = capture_with_readback(provider, mode="task_step_pair", pose=pose)
        ctrl, _ = capture_with_readback(provider, mode="task_step_pair", pose=moved)
        positive = {
            kind: raw_rgb_frame(ref[kind]).sha256 != raw_rgb_frame(ctrl[kind]).sha256
            for kind in ("road", "wide")
        }
        before = _scene_snapshot(provider)
        raw_frames = {"road": [], "wide": []}
        model_frames = {"road": [], "wide": []}
        tensors = []
        for _ in range(frames):
            raw, group = capture_with_readback(
                provider, mode="task_step_pair", pose=pose, repeat_reads=3)
            if not all(all(np.array_equal(values[0], item) for item in values[1:])
                       for values in group.values()):
                raise RuntimeError("same-frame RGB readback diverged")
            model, packed = source_model_frames(provider, raw)
            for kind in ("road", "wide"):
                raw_frames[kind].append(raw_rgb_frame(raw[kind]))
                model_frames[kind].append(model[kind])
            tensors.append(packed)
        end = _scene_snapshot(provider)
        # All image and I420 frames were snapshotted before the FIRST GPU extract.
        per_raw = {k: summarize_frame_sequence(v, warmup=warmup)
                   for k, v in raw_frames.items()}
        per_model = {k: summarize_frame_sequence(v, warmup=warmup)
                     for k, v in model_frames.items()}
        per_i420 = _packed_summary(tensors, warmup)
        receipt = {}
        rgb_unchanged_after_probe = {"road": None, "wide": None}
        if cfg["terminal_probe"]:
            pssm = getattr(engine, "pssm", None)
            receipt["pssm_mvp"] = pssm_matrix_receipt(engine)[0]
            receipt["pssm_depth"] = gpu_readback(
                engine, "pssm_depth", getattr(pssm, "depth_tex", None),
                pssm.buffer.getGsg() if pssm is not None and pssm.buffer is not None else None)[0]
            for kind in ("road", "wide"):
                sensor = engine.sensors["bigbench_" + kind]
                receipt[kind + "_hdr"] = gpu_readback(
                    engine, kind + "_hdr", getattr(sensor, "scene_tex", None),
                    sensor.buffer.getGsg())[0]
                # No graphics/task tick; detect unexpected changes to FINAL RAM
                # RGB texture caused by terminal GPU extraction itself.
                after = read_cpu_texture(sensor, provider.source_width, provider.source_height)
                rgb_unchanged_after_probe[kind] = (
                    raw_rgb_frame(after).sha256 == raw_frames[kind][-1].sha256
                )
        else:
            receipt = {name: {"status": "SKIPPED_NO_GPU_CONTROL"} for name in GPU_STAGES}
        buffers = (all(receipt[k]["status"] == "EXTRACTED" for k in GPU_STAGES)
                   if cfg["terminal_probe"] else True)
        identical_post = (all(v is True for v in rgb_unchanged_after_probe.values())
                          if cfg["terminal_probe"] else True)
        state_ok = (
            before["visual_ego_position_xyz"] == end["visual_ego_position_xyz"]
            and before["visual_ego_heading_pitch_roll"] == end["visual_ego_heading_pitch_roll"]
        )
        status = (
            "INCONCLUSIVE_TERMINAL_SNAPSHOT" if not (
                all(positive.values()) and buffers and identical_post and state_ok)
            else "OBSERVED_TERMINAL_GPU_SAMPLE" if cfg["terminal_probe"]
            else "OBSERVED_NO_GPU_CONTROL"
        )
        return {
            "status": status,
            "seed": seed, "pose_id": pose_id, "pose": pose,
            "condition": condition, "ablation": cfg["ablation"],
            "ablation_receipt": ablation_receipt,
            "frames": frames, "warmup": warmup, "scene": "ego_hidden",
            "capture_mode": "task_step_pair",
            "gpu_extraction_before_or_during_frame_series": False,
            "terminal_gpu_extraction_after_all_rgb_snapshots": bool(cfg["terminal_probe"]),
            "terminal_gpu_receipts": receipt,
            "same_tick_final_rgb_unchanged_after_terminal_probe": rgb_unchanged_after_probe,
            "pose_positive_before_gpu_extraction": positive,
            "cpu_rgb_readback_without_extra_render_bit_exact": True,
            "camera_rgb": per_raw, "model_rgb": per_model, "onnx_i420": per_i420,
            "registered_tasks": before["registered_task_names"],
            "visual_ego_transform_unchanged": state_ok,
            "gpu_readback_interferes_with_later_frames_unmeasured_here": True,
            "full_native_render_equivalence_not_proven": True,
            "model_scoring_allowed": False, "real_vehicle_testing": False,
            "official_onnx_closed_loop_repeatability_validated": False,
        }
    finally:
        provider.close()


def compare_terminals(reports: dict[str, dict]) -> dict:
    if set(reports) != set(CONDITIONS):
        raise ValueError("three matched terminal/no-GPU conditions required")
    base = reports["baseline_no_gpu"]
    fixed = ("seed", "pose_id", "pose", "frames", "warmup", "scene", "capture_mode")
    for name, report in reports.items():
        expected = ("OBSERVED_NO_GPU_CONTROL" if name == "baseline_no_gpu"
                    else "OBSERVED_TERMINAL_GPU_SAMPLE")
        if report.get("status") != expected or report.get("condition") != name:
            raise ValueError(f"{name}: missing positive control or GPU receipt")
        if any(report[k] != base[k] for k in fixed):
            raise ValueError(f"{name}: unmatched experiment")
        if report.get("ablation") != CONDITIONS[name]["ablation"]:
            raise ValueError(f"{name}: task mismatch")
        if not all(report["pose_positive_before_gpu_extraction"].values()):
            raise ValueError(f"{name}: stale camera before experiment")
        if report["real_vehicle_testing"] or report["model_scoring_allowed"]:
            raise ValueError("model/vehicle scoring forbidden")
    baseline_probe = reports["baseline_terminal"]
    shadow_probe = reports["shadow_off_terminal"]
    temporal = {
        name: {
            "raw_rgb_bit_exact_after_warmup": {
                k: report["camera_rgb"][k]["bit_exact_after_warmup"]
                for k in ("road", "wide")
            },
            "i420_bit_exact_after_warmup":
                report["onnx_i420"]["after_warmup_bit_exact"],
            "i420_unique_hashes_after_warmup":
                report["onnx_i420"]["after_warmup_unique_sha256"],
        }
        for name, report in reports.items()
    }
    baseline_vs_control = {
        kind: (base["camera_rgb"][kind]["per_frame_vs_first"] ==
               baseline_probe["camera_rgb"][kind]["per_frame_vs_first"])
        for kind in ("road", "wide")
    }
    hdr = {
        kind: {
            "baseline_terminal_sha256":
                baseline_probe["terminal_gpu_receipts"][kind]["sha256"],
            "shadow_off_terminal_sha256":
                shadow_probe["terminal_gpu_receipts"][kind]["sha256"],
            "same_byte_hash_at_final_frame":
                baseline_probe["terminal_gpu_receipts"][kind]["sha256"] ==
                shadow_probe["terminal_gpu_receipts"][kind]["sha256"],
        }
        for kind in ("road_hdr", "wide_hdr", "pssm_depth")
    }
    return {
        "status": "TERMINAL_ONLY_GPU_MEASUREMENTS_RECORDED",
        "seed": base["seed"], "pose_id": base["pose_id"],
        "frames": base["frames"],
        "pre_terminal_frame_series": temporal,
        "base_vs_terminal_process_delta_receipts_identical": baseline_vs_control,
        "final_gpu_texture_sha256": hdr,
        "single_terminal_texture_capture_only_not_a_time_series": True,
        "altered_shadow_scene_not_model_input_equivalence": True,
        "model_scoring_allowed": False,
        "real_vehicle_testing": False,
        "native_onnx_closed_loop_pass": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Terminal-only MetaDrive PSSM/HDR diagnostic")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20261109)
    p.add_argument("--pose-id", choices=sorted(POSES), default="origin")
    p.add_argument("--frames", type=int, default=6)
    p.add_argument("--warmup", type=int, default=2)
    p.add_argument("--condition", choices=sorted(CONDITIONS), required=True)
    args = p.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = snapshot(args.seed, args.pose_id, args.frames, args.warmup, args.condition)
    except Exception as exc:
        result = {"status": "ERROR", "condition": args.condition,
                  "seed": args.seed, "pose_id": args.pose_id,
                  "error": f"{type(exc).__name__}: {exc}",
                  "real_vehicle_testing": False, "model_scoring_allowed": False}
    args.out.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)+"\n",
                        encoding="utf-8")
    print("TERMINAL_HDR_RESULT", args.condition, result["status"], flush=True)
    return 0 if result["status"] in ("OBSERVED_NO_GPU_CONTROL", "OBSERVED_TERMINAL_GPU_SAMPLE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
