"""Nonintrusive native RGB changed-pixel and Panda clock tick isolation.

Every condition uses a fresh MetaDrive 0.4.3/Panda3D process in CI.
Images are copied immediately, but pixel/I420 differencing is deferred until
AFTER all camera frames, preventing image-analysis work between render ticks.
No HDR extractTextureData(), extra render, image substitution, ONNX or vehicle.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import uuid
from pathlib import Path

import numpy as np

from bigbench.curved_lane_scenarios import SCENARIOS
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.native_pixel_clock import rgb_sequence, packed_i420_sequence
from bigbench.render_causality import raw_rgb_frame
from bigbench.task_ablation import remove_visual_scene_task
from scripts.metadrive_render_causality import (
    _scene_snapshot, capture_with_readback, source_model_frames,
)
from scripts.native_scene_ablation_sweep import ALLOWED_FRACTIONS, scenario_pose


MODES = ("perceive_sequential", "task_step_pair", "graphics_frame_pair")
PANDA_FRAME_COUNT_DELTA = {
    "perceive_sequential": 2,
    "task_step_pair": 1,
    "graphics_frame_pair": 1,
}
# Documented call paths: unlike globalClock frame count, only these
# differentiate running Panda taskMgr.step() versus rendering graphics alone.
TASK_MANAGER_STEP_CALLS = {
    "perceive_sequential": 2,
    "task_step_pair": 1,
    "graphics_frame_pair": 0,
}
ABLATIONS = {"baseline": None, "shadow_off": "PSSM.update"}


def clock_receipt() -> dict:
    """Panda global clock only, no advance/step and no wall-time sleep."""
    from panda3d.core import ClockObject
    clock = ClockObject.getGlobalClock()
    return {
        "frame_count": int(clock.getFrameCount()),
        "frame_time_s": float(clock.getFrameTime()),
        "real_time_s": float(clock.getRealTime()),
        "dt_s": float(clock.getDt()),
    }


def native_pixel_clock(*, seed: int, scenario: str, fraction: float,
                       mode: str, ablation: str, frames: int = 10,
                       warmup: int = 2) -> dict:
    if (scenario not in SCENARIOS or fraction not in ALLOWED_FRACTIONS
            or mode not in MODES or ablation not in ABLATIONS):
        raise ValueError("unknown native trial configuration")
    if (type(seed) is not int or type(frames) is not int
            or not 6 <= frames <= 16 or type(warmup) is not int
            or not 0 <= warmup <= frames - 2):
        raise ValueError("invalid bounded pixel capture")
    provider = NativeMetaDriveProvider(seed=seed, map_config=SCENARIOS[scenario].map_config())
    try:
        engine = provider.env.engine
        task_report = (
            remove_visual_scene_task(engine.taskMgr, ABLATIONS[ablation])
            if ABLATIONS[ablation] else None
        )
        from metadrive.constants import CamMask
        provider.env.vehicle.origin.hide(CamMask.RgbCam)
        pose = scenario_pose(provider, scenario, fraction, 1.22)
        state_before = _scene_snapshot(provider)
        all_raw = {"road": [], "wide": []}
        clocks = []
        readback_exact = []
        for i in range(frames):
            before_tick = clock_receipt()
            rgb, copies = capture_with_readback(
                provider, mode=mode, pose=pose, repeat_reads=3
            )
            after_tick = clock_receipt()
            snapshots = {}
            for kind in ("road", "wide"):
                same_frame = all(np.array_equal(copies[kind][0], x)
                                 for x in copies[kind][1:])
                if not same_frame:
                    raise RuntimeError("CPU same-frame readback was not bit exact")
                snapshots[kind] = np.array(rgb[kind], copy=True, order="C")
            for kind in snapshots:
                all_raw[kind].append(snapshots[kind])
            readback_exact.append(True)
            clocks.append({
                "render_frame_index_zero_based": i,
                "before": before_tick,
                "after": after_tick,
                "global_clock_frame_count_delta": (
                    after_tick["frame_count"] - before_tick["frame_count"]),
                "global_clock_time_delta_s": (
                    after_tick["frame_time_s"] - before_tick["frame_time_s"]),
                "real_time_delta_s": (
                    after_tick["real_time_s"] - before_tick["real_time_s"]),
            })
        state_after = _scene_snapshot(provider)
        # Pose movement positive control: required for EVERY mode, including
        # graphicsFrame-only (which can otherwise appear stable due stale RAM).
        moved = ((pose[0][0] + 2., pose[0][1], pose[0][2]), pose[1])
        next_pose, _ = capture_with_readback(
            provider, mode=mode, pose=moved, repeat_reads=3,
        )
        positive = {kind:
                    raw_rgb_frame(next_pose[kind]).sha256 !=
                    raw_rgb_frame(all_raw[kind][-1]).sha256
                    for kind in ("road", "wide")}
        # Defer rectification and image analysis until no more render ticks.
        model = {"road": [], "wide": []}
        packed = []
        for i in range(frames):
            sample = {kind: all_raw[kind][i] for kind in ("road", "wide")}
            result, tensor = source_model_frames(provider, sample)
            for kind in ("road", "wide"):
                frame = result[kind]
                model[kind].append(
                    np.frombuffer(frame.rgb, dtype=np.uint8).reshape(
                        frame.height, frame.width, 3
                    ).copy()
                )
            packed.append(np.array(tensor, copy=True, order="C"))
        tick_values = [row["global_clock_frame_count_delta"] for row in clocks]
        clock_data_complete = all(
            all(math.isfinite(float(value)) for value in
                (record["global_clock_time_delta_s"], record["real_time_delta_s"]))
            for record in clocks
        )
        mode_tick_observed = all(x == PANDA_FRAME_COUNT_DELTA[mode] for x in tick_values)
        state_unchanged = (
            state_before["visual_ego_position_xyz"] ==
            state_after["visual_ego_position_xyz"]
            and state_before["visual_ego_heading_pitch_roll"] ==
            state_after["visual_ego_heading_pitch_roll"]
        )
        tasks = state_before["registered_task_names"]
        pssm_task_expected = ablation == "baseline"
        task_identity_valid = (
            ("PSSM.update" in tasks) == pssm_task_expected
            and "igLoop" in tasks
        )
        valid = (all(positive.values()) and all(readback_exact)
                 and mode_tick_observed and clock_data_complete
                 and state_unchanged and task_identity_valid)
        return {
            "status": "OBSERVED_NATIVE_PIXEL_CLOCK" if valid
                      else "INCONCLUSIVE_NATIVE_PIXEL_CLOCK",
            # Identity created only AFTER all captures and post-frame analysis,
            # to verify that repeated camera observations are separate processes.
            "process_id": os.getpid(), "process_uuid": uuid.uuid4().hex,
            "scenario": scenario, "seed": seed, "fraction": fraction,
            "camera_pose": pose, "mode": mode, "ablation": ablation,
            "ablation_receipt": task_report,
            "frames": frames, "warmup": warmup,
            "raw_sensor_rgb_dims": [provider.source_width, provider.source_height],
            "model_rgb_dims": [512, 256],
            "capture_schedule": "existing native MetaDrive paths, no extra ticks",
            "source_rgb": {k: rgb_sequence(v, warmup=warmup)
                           for k,v in all_raw.items()},
            "model_rgb": {k: rgb_sequence(v, warmup=warmup)
                          for k,v in model.items()},
            "onnx_i420": packed_i420_sequence(packed, warmup=warmup),
            "clock_timeline": clocks,
            "expected_panda_global_frame_count_delta_per_pair": PANDA_FRAME_COUNT_DELTA[mode],
            "all_panda_frame_count_deltas_as_expected": mode_tick_observed,
            "task_manager_step_invocations_from_capture_call_path":
                TASK_MANAGER_STEP_CALLS[mode],
            "global_frame_counter_cannot_identify_task_manager_execution": True,
            "clock_observations_finite": clock_data_complete,
            "cpu_readbacks_bit_exact_without_new_render": all(readback_exact),
            "camera_plus_2m_positive": positive,
            "registered_tasks_before": state_before["registered_task_names"],
            "registered_tasks_after": state_after["registered_task_names"],
            "scene_visual_ego_pose_unchanged": state_unchanged,
            "pssm_task_identity_correct": task_identity_valid,
            "gpu_texture_extract_calls": 0,
            "onnx_inference_used": False,
            "same_original_renderer_semantics_after_ablation_unproven": True,
            "model_scoring_allowed": False,
            "real_vehicle_testing": False,
            "cd210_fallback": False,
            "carrot_tuning_used": False,
            "warning": (
                "Both taskMgr.step and graphicsEngine.renderFrame increment "
                "Panda global frame count. Known call-path task count and global "
                "clock count must never be conflated; no specific shader cause proven."
            ),
        }
    finally:
        provider.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Native MetaDrive pixel / clock tick A-B (SIM ONLY)")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    parser.add_argument("--fraction", type=float, choices=ALLOWED_FRACTIONS, default=.12)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--ablation", choices=sorted(ABLATIONS), default="baseline")
    parser.add_argument("--frames", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = native_pixel_clock(
            seed=args.seed, scenario=args.scenario, fraction=args.fraction,
            mode=args.mode, ablation=args.ablation,
            frames=args.frames, warmup=args.warmup,
        )
    except Exception as exc:
        result = {
            "status": "ERROR", "scenario": args.scenario, "seed": args.seed,
            "fraction": args.fraction, "mode": args.mode,
            "ablation": args.ablation,
            "error": f"{type(exc).__name__}: {exc}",
            "model_scoring_allowed": False, "real_vehicle_testing": False,
        }
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print("NATIVE_RAW_PIXEL_CLOCK",args.scenario,args.seed,args.mode,args.ablation,
          result["status"],flush=True)
    return 0 if result["status"] == "OBSERVED_NATIVE_PIXEL_CLOCK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
