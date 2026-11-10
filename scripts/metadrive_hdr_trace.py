"""Trace MetaDrive 0.4.3 PSSM shadow depth -> HDR scene -> RGB -> I420.

Simulation diagnosis only. GPU readback is an intervention and may alter timing.
All stages are sampled after one taskMgr.step, without an additional render tick.
This module cannot certify driving model performance or real-camera equivalence.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np

from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.render_causality import raw_rgb_frame
from bigbench.task_ablation import remove_visual_scene_task
from scripts.metadrive_render_causality import (
    WORLD_POSE, _scene_snapshot, capture_with_readback, source_model_frames,
)

STAGES = ("pssm_mvp", "pssm_depth", "road_hdr", "wide_hdr",
          "road_rgb", "wide_rgb", "onnx_i420")
ABLATIONS = {
    "baseline": None,
    "shadow_disabled": "PSSM.update",
    "chase_disabled": "update main chase camera",
}
POSES = {
    "origin": WORLD_POSE,
    "shifted": ((WORLD_POSE[0][0] + 2.0, WORLD_POSE[0][1], WORLD_POSE[0][2]),
                WORLD_POSE[1]),
}


def receipt(data: bytes, name: str, metadata: dict | None = None) -> tuple[dict, bytes]:
    if not data:
        raise ValueError("empty frame does not constitute readback evidence")
    info = {"status": "EXTRACTED", "source": name,
            "sha256": sha256(data).hexdigest(), "byte_count": len(data)}
    if metadata is not None:
        info["metadata"] = metadata
    return info, bytes(data)


def missing(stage: str, error: str) -> tuple[dict, None]:
    return {"status": "UNAVAILABLE", "source": stage, "error": error}, None


def gpu_readback(engine: Any, stage: str, texture: Any, gsg: Any) -> tuple[dict, bytes | None]:
    """Extract GPU texture into RAM, without calling taskMgr or renderFrame.

    The byte layout is deliberately not interpreted as RGB8 / half-float pixels.
    """
    if texture is None or gsg is None:
        return missing(stage, "texture or GSG missing")
    try:
        if not engine.graphicsEngine.extractTextureData(texture, gsg):
            return missing(stage, "extractTextureData returned false")
        data = bytes(texture.getRamImage().getData())
        if not data or len(data) > 64 * 1024 * 1024:
            return missing(stage, "GPU texture empty or above 64 MiB readback cap")
        meta = {
            "dimensions": [int(texture.getXSize()), int(texture.getYSize()),
                           int(texture.getZSize())],
            "format": str(texture.getFormat()),
            "component_type": str(texture.getComponentType()),
            "note": "Raw Panda3D texture bytes; changed bytes are NOT changed pixels",
        }
        return receipt(data, stage, meta)
    except Exception as exc:
        return missing(stage, f"{type(exc).__name__}: {exc}")


def pssm_matrix_receipt(engine: Any) -> tuple[dict, bytes | None]:
    try:
        rows = [
            [[float(m.getCell(i, j)) for j in range(4)] for i in range(4)]
            for m in engine.pssm.camera_rig.get_mvp_array()
        ]
        if not rows:
            return missing("pssm_mvp", "no matrices in camera rig")
        data = json.dumps(rows, separators=(",", ":"), allow_nan=False).encode()
        return receipt(data, "pssm_mvp",
                       {"matrices": len(rows), "encoding": "float64 JSON cells"})
    except Exception as exc:
        return missing("pssm_mvp", f"{type(exc).__name__}: {exc}")


def summarize_stream(samples: list[tuple[dict, bytes | None]], warmup: int) -> dict:
    """Do not convert unavailable buffers or variable layouts to bit-exact."""
    if len(samples) < 2 or type(warmup) is not int or not 0 <= warmup <= len(samples) - 2:
        raise ValueError("invalid sample count or warmup")
    entries = [r for r, _ in samples]
    result = {
        "status": "INCONCLUSIVE_STAGE_UNAVAILABLE", "frames": entries,
        "warmup_frames_in_secondary_view": warmup,
        "bit_exact_all": None, "bit_exact_after_warmup": None,
    }
    if any(r.get("status") != "EXTRACTED" or data is None for r, data in samples):
        return result
    layouts = [(r["byte_count"], r.get("metadata")) for r, _ in samples]
    if len({json.dumps(l, sort_keys=True) for l in layouts}) != 1:
        result["status"] = "INCONCLUSIVE_LAYOUT_CHANGED"
        return result
    full_hashes = [r["sha256"] for r, _ in samples]
    a = np.frombuffer(samples[0][1], dtype=np.uint8)
    base = np.frombuffer(samples[warmup][1], dtype=np.uint8)
    changed_all = [int(np.count_nonzero(a != np.frombuffer(b, dtype=np.uint8)))
                   for _, b in samples]
    changed_post = [int(np.count_nonzero(base != np.frombuffer(b, dtype=np.uint8)))
                    for _, b in samples[warmup:]]
    first_offsets = []
    for _, b in samples[warmup:]:
        offsets = np.flatnonzero(base != np.frombuffer(b, dtype=np.uint8))
        if offsets.size:
            first_offsets = [int(i) for i in offsets[:12]]
            break
    result.update({
        "status": "OBSERVED_BYTES",
        "bit_exact_all": len(set(full_hashes)) == 1,
        "bit_exact_after_warmup": len(set(full_hashes[warmup:])) == 1,
        "unique_sha256_all": len(set(full_hashes)),
        "unique_sha256_after_warmup": len(set(full_hashes[warmup:])),
        "max_changed_bytes_all": max(changed_all),
        "max_changed_bytes_after_warmup": max(changed_post),
        "per_frame_changed_bytes_after_warmup": changed_post,
        "first_changed_byte_offsets_after_warmup": first_offsets,
        "changed_bytes_are_not_pixels": True,
    })
    return result


def capture_native(seed: int, pose_id: str, frames: int, warmup: int, ablation: str) -> dict:
    if pose_id not in POSES or ablation not in ABLATIONS:
        raise ValueError("unsupported seed/pose/ablation")
    if type(frames) is not int or not 4 <= frames <= 12 or not 0 <= warmup <= frames - 2:
        raise ValueError("frame/warmup outside bounded native diagnostic")
    provider = NativeMetaDriveProvider(seed=seed)
    try:
        engine = provider.env.engine
        audit = (remove_visual_scene_task(engine.taskMgr, ABLATIONS[ablation])
                 if ABLATIONS[ablation] else None)
        from metadrive.constants import CamMask
        provider.env.vehicle.origin.hide(CamMask.RgbCam)
        pose = POSES[pose_id]
        before = _scene_snapshot(provider)
        samples: dict[str, list] = {k: [] for k in STAGES}
        for index in range(frames):
            raw, cpu_groups = capture_with_readback(
                provider, mode="task_step_pair", pose=pose, repeat_reads=3)
            if not all(all(np.array_equal(xs[0], v) for v in xs[1:])
                       for xs in cpu_groups.values()):
                raise RuntimeError("same-frame repeated CPU RGB readback differed")
            _, packed = source_model_frames(provider, raw)
            pssm = getattr(engine, "pssm", None)
            samples["pssm_mvp"].append(pssm_matrix_receipt(engine))
            samples["pssm_depth"].append(gpu_readback(
                engine, "pssm_depth", getattr(pssm, "depth_tex", None),
                pssm.buffer.getGsg() if pssm is not None and pssm.buffer else None))
            for kind in ("road", "wide"):
                sensor = engine.sensors["bigbench_" + kind]
                samples[kind + "_hdr"].append(gpu_readback(
                    engine, kind + "_hdr", getattr(sensor, "scene_tex", None),
                    sensor.buffer.getGsg()))
                samples[kind + "_rgb"].append(receipt(
                    raw_rgb_frame(raw[kind]).rgb, kind + "_rgb",
                    {"shape": list(raw[kind].shape), "dtype": "uint8"}))
            samples["onnx_i420"].append(receipt(
                packed.tobytes(), "onnx_i420",
                {"shape": list(packed.shape), "dtype": str(packed.dtype)}))
            print("HDR_PSSM_FRAME", seed, pose_id, ablation, index, flush=True)

        after = _scene_snapshot(provider)
        moved = ((pose[0][0] + 2.0, pose[0][1], pose[0][2]), pose[1])
        shift, _ = capture_with_readback(provider, mode="task_step_pair", pose=moved)
        positive = {k: raw_rgb_frame(shift[k]).sha256 !=
                    samples[k + "_rgb"][-1][0]["sha256"] for k in ("road", "wide")}
        summaries = {k: summarize_stream(v, warmup) for k, v in samples.items()}
        complete = all(x["status"] == "OBSERVED_BYTES" for x in summaries.values())
        return {
            "status": ("OBSERVED_BUFFER_CHAIN" if complete and all(positive.values())
                       else "INCONCLUSIVE_NATIVE_TRACE"),
            "seed": seed, "pose_id": pose_id, "pose": pose, "ablation": ablation,
            "removed_task": ABLATIONS[ablation], "ablation_audit": audit,
            "frames": frames, "warmup": warmup,
            "scene": "ego_hidden", "capture_mode": "task_step_pair",
            "stages": summaries,
            "same_frame_cpu_readback_bit_exact": True,
            "pose_shift_positive_control": positive,
            "registered_tasks_before": before["registered_task_names"],
            "registered_tasks_after": after["registered_task_names"],
            "visual_ego_transform_unchanged": (
                before["visual_ego_position_xyz"] == after["visual_ego_position_xyz"]
                and before["visual_ego_heading_pitch_roll"] == after["visual_ego_heading_pitch_roll"]),
            "gpu_readback_may_perturb_render_timing": True,
            "render_semantics_equivalence_unproven": True,
            "real_vehicle_testing": False, "cd210_fallback": False,
            "model_scoring_allowed": False,
            "warning": "No causal sole source or native ONNX closed-loop pass proven",
        }
    finally:
        provider.close()


def compare_reports(reports: dict[str, dict]) -> dict:
    if set(reports) != set(ABLATIONS):
        raise ValueError("exact baseline/shadow/chase conditions required")
    base = reports["baseline"]
    fields = ("seed", "pose_id", "pose", "frames", "warmup", "scene", "capture_mode")
    for name, report in reports.items():
        if report["status"] != "OBSERVED_BUFFER_CHAIN":
            raise ValueError(f"{name}: native stage unavailable or control failed")
        if any(report[k] != base[k] for k in fields):
            raise ValueError(f"{name}: settings differ from baseline")
        if report["ablation"] != name or report["removed_task"] != ABLATIONS[name]:
            raise ValueError(f"{name}: unexpected task ablation")
        if report["real_vehicle_testing"] or report["model_scoring_allowed"]:
            raise ValueError("prohibited driving/vehicle scoring")
    diff = {}
    for name in ("shadow_disabled", "chase_disabled"):
        diff[name] = {}
        for stage in STAGES:
            a = base["stages"][stage]["frames"][base["warmup"]:]
            b = reports[name]["stages"][stage]["frames"][base["warmup"]:]
            count = sum(x["sha256"] == y["sha256"] for x, y in zip(a, b))
            diff[name][stage] = {
                "same_index_equal_hashes": count, "matched_frames": len(a),
                "not_render_equivalence_proof": True,
            }
    return {
        "status": "PSSM_HDR_RGB_OBSERVATIONS_ONLY",
        "seed": base["seed"], "pose_id": base["pose_id"],
        "after_warmup_bit_exact": {
            name: {stage: report["stages"][stage]["bit_exact_after_warmup"]
                   for stage in STAGES} for name, report in reports.items()},
        "between_process_same_index": diff,
        "gpu_readback_may_perturb_render_timing": True,
        "model_scoring_allowed": False, "real_vehicle_testing": False,
        "ranking_prohibited": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Native PSSM/HDR evidence (SIM ONLY)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261109)
    parser.add_argument("--pose-id", choices=sorted(POSES), default="origin")
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--ablation", choices=sorted(ABLATIONS), required=True)
    args = parser.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = capture_native(args.seed, args.pose_id, args.frames,
                                args.warmup, args.ablation)
    except Exception as exc:
        report = {
            "status": "ERROR", "seed": args.seed, "pose_id": args.pose_id,
            "ablation": args.ablation,
            "error": f"{type(exc).__name__}: {exc}",
            "model_scoring_allowed": False, "real_vehicle_testing": False,
        }
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                   allow_nan=False) + "\n", encoding="utf-8")
    print("PSSM_HDR_TRACE", report["status"], args.out, flush=True)
    return 0 if report["status"] == "OBSERVED_BUFFER_CHAIN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
