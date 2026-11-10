"""Fixed-world-pose native MetaDrive 0.4.3 PSSM A/B over genuine curve/ramp maps.

SIM ONLY. The RGB image stream is measured without any HDR GPU extraction,
image smoothing, convergence/re-capture, ONNX policy, or vehicle control.
Bit-identical/no-drift is an observation, not a model-performance PASS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from bigbench.curved_lane_scenarios import (
    SCENARIOS, select_native_curve_lanes, world_camera_pose,
)
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.render_causality import (
    raw_rgb_frame, summarize_frame_sequence, summarize_readback_groups,
)
from bigbench.task_ablation import remove_visual_scene_task
from scripts.metadrive_render_causality import (
    _packed_summary, _scene_snapshot, capture_with_readback, source_model_frames,
)

CONDITIONS = {"baseline": None, "shadow_off": "PSSM.update"}
ALLOWED_FRACTIONS = (0.12, 0.28)


def scenario_pose(provider: Any, scenario: str, fraction: float, height_m: float) -> tuple:
    """Derive camera coordinates from the NATIVE selected lane, never fake pixels."""
    if scenario not in SCENARIOS or fraction not in ALLOWED_FRACTIONS:
        raise ValueError("unapproved native scene or lane fraction")
    lanes = select_native_curve_lanes(provider.env.current_map, SCENARIOS[scenario])
    if not lanes:
        raise RuntimeError("no native lane suitable for pose placement")
    # A short ramp can require a small look-back to make its painted roadway visible.
    lookback_m = 4.0 if scenario in ("in_ramp", "out_ramp") else 0.0
    x, y, z, h = world_camera_pose(
        lanes[0], fraction, height_m=height_m, lookback_m=lookback_m,
    )
    return ((x, y, z), (h, 0.0, 0.0))


def take_scene_series(*, scenario: str, seed: int, fraction: float,
                      height_m: float, condition: str,
                      frames: int = 9, warmup: int = 2) -> dict:
    if scenario not in SCENARIOS or condition not in CONDITIONS:
        raise ValueError("unsupported native scenario/condition")
    if type(seed) is not int or type(frames) is not int or not 6 <= frames <= 24:
        raise ValueError("bounded integer seed/frames required")
    if type(warmup) is not int or not 0 <= warmup < frames - 1:
        raise ValueError("invalid warmup")
    if not 0.75 <= height_m <= 2.0:
        raise ValueError("virtual camera height outside experiment")
    provider = NativeMetaDriveProvider(
        seed=seed, map_config=SCENARIOS[scenario].map_config(),
    )
    try:
        if CONDITIONS[condition]:
            ablation = remove_visual_scene_task(provider.env.engine.taskMgr, CONDITIONS[condition])
        else:
            ablation = None
        from metadrive.constants import CamMask
        provider.env.vehicle.origin.hide(CamMask.RgbCam)
        pose = scenario_pose(provider, scenario, fraction, height_m)
        before = _scene_snapshot(provider)
        source = {"road": [], "wide": []}
        model = {"road": [], "wide": []}
        cpu_reads = {"road": [], "wide": []}
        tensor_frames = []
        for i in range(frames):
            images, repeated = capture_with_readback(
                provider, mode="task_step_pair", pose=pose, repeat_reads=3,
            )
            model_pair, packed = source_model_frames(provider, images)
            for kind in ("road", "wide"):
                source[kind].append(raw_rgb_frame(images[kind]))
                model[kind].append(model_pair[kind])
                cpu_reads[kind].append([raw_rgb_frame(array) for array in repeated[kind]])
            tensor_frames.append(packed)
        after = _scene_snapshot(provider)
        shifted = ((pose[0][0] + 2.0, pose[0][1], pose[0][2]), pose[1])
        shifted_rgb, _ = capture_with_readback(
            provider, mode="task_step_pair", pose=shifted, repeat_reads=3,
        )
        positive = {
            kind: raw_rgb_frame(shifted_rgb[kind]).sha256 != source[kind][-1].sha256
            for kind in ("road", "wide")
        }
        cpu_summary = {kind: summarize_readback_groups(v) for kind, v in cpu_reads.items()}
        state_unchanged = (
            before["visual_ego_position_xyz"] == after["visual_ego_position_xyz"]
            and before["visual_ego_heading_pitch_roll"] ==
                after["visual_ego_heading_pitch_roll"]
        )
        valid = (
            all(positive.values()) and state_unchanged
            and all(v["readback_bit_exact"] for v in cpu_summary.values())
        )
        return {
            "status": "OBSERVED_NATIVE_SCENE" if valid else "INCONCLUSIVE_NATIVE_SCENE",
            "seed": seed, "scenario": scenario, "fraction": fraction,
            "camera_height_m": height_m, "world_pose": pose,
            "condition": condition, "ablation": ablation,
            "scene_visibility": "ego_hidden", "capture_mode": "task_step_pair",
            "frames": frames, "warmup": warmup,
            "source_rgb": {
                kind: summarize_frame_sequence(v, warmup=warmup)
                for kind, v in source.items()
            },
            "model_rgb": {
                kind: summarize_frame_sequence(v, warmup=warmup)
                for kind, v in model.items()
            },
            "i420": _packed_summary(tensor_frames, warmup=warmup),
            "cpu_readback": cpu_summary,
            "pose_shift_positive_control": positive,
            "visual_ego_transform_unchanged": state_unchanged,
            "gpu_texture_extract_calls": 0,
            "multiple_captures_per_model_input": False,
            "real_vehicle_testing": False, "model_scoring_allowed": False,
            "cd210_fallback": False,
            "warning": "Still a fixed virtual camera; not a moving ONNX feedback test",
        }
    finally:
        provider.close()


def compare_ablation(baseline: dict, shadow_off: dict) -> dict:
    fields = (
        "seed", "scenario", "fraction", "camera_height_m", "world_pose",
        "frames", "warmup", "scene_visibility", "capture_mode",
    )
    for name, record in (("baseline", baseline), ("shadow_off", shadow_off)):
        if record.get("status") != "OBSERVED_NATIVE_SCENE":
            raise ValueError(f"{name}: missing native camera positive control")
        if record.get("condition") != name or record["gpu_texture_extract_calls"] != 0:
            raise ValueError(f"{name}: untrusted native trace configuration")
        if record["model_scoring_allowed"] or record["real_vehicle_testing"]:
            raise ValueError("no real vehicle or model performance claims")
        if not all(record["pose_shift_positive_control"].values()):
            raise ValueError("stale pose-control image")
    if any(baseline[f] != shadow_off[f] for f in fields):
        raise ValueError("A/B native scenes are not comparable")
    if baseline.get("ablation") is not None:
        raise ValueError("baseline must preserve all scene tasks")
    if shadow_off.get("ablation", {}).get("ablation") != "PSSM.update":
        raise ValueError("shadow_off must remove exactly PSSM.update")
    def compact(record):
        return {
            "source_unique_road": record["source_rgb"]["road"]["post_warmup_unique_sha256"],
            "source_unique_wide": record["source_rgb"]["wide"]["post_warmup_unique_sha256"],
            "model_unique_road": record["model_rgb"]["road"]["post_warmup_unique_sha256"],
            "model_unique_wide": record["model_rgb"]["wide"]["post_warmup_unique_sha256"],
            "i420_unique": record["i420"]["after_warmup_unique_sha256"],
            "i420_bit_exact_post_warmup": record["i420"]["after_warmup_bit_exact"],
            "i420_max_changed_elements": record["i420"]["max_changed_tensor_elements_after_warmup"],
        }
    return {
        "status": "MULTISCENE_NATIVE_ABLATION_OBSERVED_NO_CAUSE_PROVEN",
        "seed": baseline["seed"], "scenario": baseline["scenario"],
        "fraction": baseline["fraction"], "camera_height_m": baseline["camera_height_m"],
        "baseline": compact(baseline), "shadow_off": compact(shadow_off),
        "same_render_semantics_unproven": True,
        "native_onnx_closed_loop_pass": False,
        "model_scoring_allowed": False, "real_vehicle_testing": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="MetaDrive curve/ramp scene A/B (SIM ONLY)")
    p.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--fraction", type=float, choices=ALLOWED_FRACTIONS, required=True)
    p.add_argument("--height", type=float, default=1.22)
    p.add_argument("--condition", choices=sorted(CONDITIONS), required=True)
    p.add_argument("--frames", type=int, default=9)
    p.add_argument("--warmup", type=int, default=2)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = take_scene_series(
            scenario=args.scenario, seed=args.seed, fraction=args.fraction,
            height_m=args.height, condition=args.condition,
            frames=args.frames, warmup=args.warmup,
        )
    except Exception as exc:
        result = {
            "status": "ERROR", "scenario": args.scenario, "seed": args.seed,
            "fraction": args.fraction, "condition": args.condition,
            "error": f"{type(exc).__name__}: {exc}",
            "real_vehicle_testing": False, "model_scoring_allowed": False,
        }
    args.out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print("MULTISCENE_NATIVE_ABLATION", args.scenario, args.seed,
          args.fraction, args.condition, result["status"], flush=True)
    return 0 if result["status"] == "OBSERVED_NATIVE_SCENE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
