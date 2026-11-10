"""Native PSSM shadow-camera MVP versus RGB and task/clock observations.

Two camera screenshots remain original MetaDrive/Panda3D RGB. Each arm uses
a FRESH independent MetaDrive process; no real vehicle, model, control, GPU
extractTextureData, frame replay, pixel substitution or ranking. Additional
CPU matrix/task observations may change wall-clock timing, so every result
is an instrumented causal diagnostic, NOT native driving benchmark evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from bigbench.curved_lane_scenarios import SCENARIOS
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.native_pixel_clock import rgb_sequence, packed_i420_sequence
from bigbench.pssm_mvp_trace import (
    capture_native_pssm_mvp, summarize_mvp_sequence,
    compare_mvp_and_rgb, registered_task_metadata,
)
from bigbench.render_causality import raw_rgb_frame
from bigbench.task_ablation import remove_visual_scene_task
from scripts.metadrive_render_causality import (
    capture_with_readback, mount_world_pair, read_cpu_texture, source_model_frames,
)
from scripts.native_raw_pixel_clock import clock_receipt
from scripts.native_scene_ablation_sweep import ALLOWED_FRACTIONS, scenario_pose


CONDITIONS = {
    "sequential_baseline": ("perceive_sequential", None, 2, 2),
    "paired_baseline": ("task_step_pair", None, 1, 1),
    "graphics_only": ("graphics_frame_pair", None, 1, 0),
    "paired_pssm_off": ("task_step_pair", "PSSM.update", 1, 1),
}


def _node_transform(node, parent) -> dict:
    p = node.getPos(parent)
    h = node.getHpr(parent)
    values = [float(v) for v in p] + [float(v) for v in h]
    if not all(math.isfinite(v) for v in values):
        raise RuntimeError("native camera/light transform nonfinite")
    return {"position_xyz": values[:3], "hpr_deg": values[3:]}


def _moment(engine) -> dict:
    """Read PSSM camera-rig CPU matrices and scene camera, never GPU texture."""
    rig = capture_native_pssm_mvp(engine)
    pssm = engine.pssm
    return {
        "mvp": rig,
        "global_clock": clock_receipt(),
        "main_scene_camera": _node_transform(engine.camera, engine.render),
        "directional_light": _node_transform(
            pssm.directional_light, engine.render
        ),
        "pssm_shadow_enabled": bool(pssm.use_pssm),
        "pssm_freeze_flag": bool(pssm.freeze_pssm),
    }


def _read_after_perceive(sensor, width: int, height: int, result) -> np.ndarray:
    if not isinstance(result, np.ndarray):
        result = result.get()
    original = np.array(result, copy=True, order="C")
    if original.dtype != np.uint8 or original.shape != (height, width, 3):
        raise RuntimeError("perceive did not return the native raw RGB contract")
    for _ in range(2):
        if not np.array_equal(original, read_cpu_texture(sensor, width, height)):
            raise RuntimeError("CPU reads of the same GPU-completed frame differ")
    return original


def take_pssm_mvp_trial(*, seed: int, scenario: str, fraction: float,
                        fixed_clock: bool, condition: str,
                        frames: int = 8, warmup: int = 2) -> dict:
    if scenario not in SCENARIOS or fraction not in ALLOWED_FRACTIONS:
        raise ValueError("unknown native scenario or camera lane fraction")
    if condition not in CONDITIONS:
        raise ValueError("unknown PSSM/renderer arm")
    if type(seed) is not int or type(fixed_clock) is not bool:
        raise ValueError("seed/clock type invalid")
    if (type(frames) is not int or not 6 <= frames <= 12 or
            type(warmup) is not int or not 0 <= warmup <= frames-2):
        raise ValueError("invalid experiment frames and warmup")
    mode, deleted_task, expected_global_frames, taskmgr_calls = CONDITIONS[condition]
    provider = NativeMetaDriveProvider(
        seed=seed, map_config=SCENARIOS[scenario].map_config(),
        fixed_virtual_clock=fixed_clock,
    )
    try:
        engine = provider.env.engine
        from metadrive.constants import CamMask
        provider.env.vehicle.origin.hide(CamMask.RgbCam)
        ablation = remove_visual_scene_task(engine.taskMgr, deleted_task) if deleted_task else None
        pose = scenario_pose(provider, scenario, fraction, 1.22)
        before_tasks = registered_task_metadata(engine.taskMgr)
        names = [v["name"] for v in before_tasks]
        if "igLoop" not in names or ("PSSM.update" in names) != (deleted_task is None):
            raise RuntimeError("native task registration does not match experiment")
        raw_frames = {"road": [], "wide": []}
        per_frame = []
        for index in range(frames):
            before = _moment(engine)
            if mode == "perceive_sequential":
                images = {}
                intermediate = []
                for kind in ("road", "wide"):
                    sensor = engine.sensors["bigbench_"+kind]
                    current = sensor.perceive(
                        to_float=False, new_parent_node=engine.origin,
                        position=pose[0], hpr=pose[1],
                    )
                    images[kind] = _read_after_perceive(
                        sensor, provider.source_width, provider.source_height, current,
                    )
                    intermediate.append(_moment(engine))
                after = intermediate[-1]
            else:
                images, readbacks = capture_with_readback(
                    provider, mode=mode, pose=pose, repeat_reads=3,
                )
                for kind in ("road", "wide"):
                    if not all(np.array_equal(readbacks[kind][0], item)
                               for item in readbacks[kind][1:]):
                        raise RuntimeError("paired completed-RGB CPU copy discrepancy")
                images = {k: np.array(v, copy=True, order="C") for k,v in images.items()}
                intermediate = []
                after = _moment(engine)
            for kind in ("road", "wide"):
                raw_frames[kind].append(images[kind])
            delta = (
                after["global_clock"]["frame_count"] -
                before["global_clock"]["frame_count"]
            )
            per_frame.append({
                "index_zero_based": index,
                "before": before,
                "intermediate_after_each_perceive": intermediate[:-1],
                "after": after,
                "observed_global_frame_delta": delta,
                "expected_global_frame_delta": expected_global_frames,
                "taskmgr_step_calls_from_inspected_python_call_path": taskmgr_calls,
                "main_camera_moved_after_tick": (
                    before["main_scene_camera"] != after["main_scene_camera"]
                ),
                "light_pose_moved_after_tick": (
                    before["directional_light"] != after["directional_light"]
                ),
                "mvp_changed_during_pair": (
                    before["mvp"]["all_f64_sha256"] != after["mvp"]["all_f64_sha256"]
                ),
            })
            print("PSSM_MVP_CPU_OBSERVED",seed,scenario,fixed_clock,condition,
                  index,delta,flush=True)
        # Positional positive control *before* any model warping or pixel difference.
        shifted = ((pose[0][0]+2.0, pose[0][1], pose[0][2]),pose[1])
        pos, _ = capture_with_readback(provider, mode=mode, pose=shifted)
        positive = {
            kind: raw_rgb_frame(pos[kind]).sha256 !=
                  raw_rgb_frame(raw_frames[kind][-1]).sha256
            for kind in ("road", "wide")
        }
        last_tasks = registered_task_metadata(engine.taskMgr)
        # Delay expensive RGB and I420 differences until after all native ticks.
        canvas = {"road": [], "wide": []}
        tensors = []
        for index in range(frames):
            source = {k: raw_frames[k][index] for k in ("road", "wide")}
            rendered, packed = source_model_frames(provider, source)
            for kind in ("road", "wide"):
                f = rendered[kind]
                canvas[kind].append(np.frombuffer(
                    f.rgb, dtype=np.uint8
                ).reshape(f.height, f.width, 3).copy())
            tensors.append(np.array(packed, copy=True, order="C"))
        mvp_summary = summarize_mvp_sequence(
            [x["after"]["mvp"] for x in per_frame],warmup=warmup,
        )
        raw = {k: rgb_sequence(v,warmup=warmup) for k,v in raw_frames.items()}
        model = {k: rgb_sequence(v,warmup=warmup) for k,v in canvas.items()}
        packed_summary = packed_i420_sequence(tensors,warmup=warmup)
        associations = {
            k: compare_mvp_and_rgb(mvp_summary, raw[k],warmup=warmup)
            for k in ("road","wide")
        }
        clock_observed = all(
            x["observed_global_frame_delta"] == expected_global_frames
            for x in per_frame
        )
        finite_clock = all(
            all(math.isfinite(float(z["global_clock"][attr]))
                for z in (x["before"],x["after"])
                for attr in ("frame_time_s","real_time_s","dt_s"))
            for x in per_frame
        )
        independent_frames = all(
            len(raw[k]["all_frame_sha256"]) == frames for k in ("road","wide")
        )
        all_success = (
            all(positive.values()) and clock_observed and finite_clock
            and independent_frames and before_tasks == last_tasks
        )
        return {
            "status": ("OBSERVED_NATIVE_PSSM_MVP_TASK_TIMING" if all_success
                       else "INCONCLUSIVE_NATIVE_PSSM_MVP_TASK_TIMING"),
            "seed":seed,"scenario":scenario,"fraction":fraction,"world_pose":pose,
            "fixed_virtual_clock":fixed_clock,
            "condition":condition,"mode":mode,"removed_task":deleted_task,
            "ablation_receipt":ablation,"frames":frames,"warmup":warmup,
            "raw_source_dimensions":[provider.source_width,provider.source_height],
            "task_registry_sort_metadata_only_not_execution_proof":before_tasks,
            "registered_tasks_unchanged":before_tasks==last_tasks,
            "pssm_shadow_atlas_gpu_readback_performed":False,
            "render_semantics_altered_when_task_removed":deleted_task is not None,
            "mvp_post_warmup":mvp_summary,
            "raw_source_rgb":raw,"warped_model_rgb":model,
            "onnx_i420":packed_summary,
            "pssm_vs_raw_rgb_associations":associations,
            "per_frame_before_after_and_intra_pair":per_frame,
            "expected_global_frame_delta_per_camera_pair":expected_global_frames,
            "global_frame_deltas_match":clock_observed,
            "taskmgr_calls_from_code_not_global_clock":taskmgr_calls,
            "clock_values_finite":finite_clock,
            "plus_2m_camera_pose_response":positive,
            "real_vehicle_testing":False,"model_scoring_allowed":False,
            "onnx_inference_executed":False,"cd210_fallback":False,
            "warning": (
                "CPU inspection can change Panda scheduling. Task sort values "
                "indicate registration not observed execution sequence. "
                "MVP and RGB co-variation is not a unique shader cause."
            ),
        }
    finally:
        provider.close()


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="PSSM MVP, task registry and camera RGB probe")
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--scenario",choices=sorted(SCENARIOS),required=True)
    p.add_argument("--fraction",type=float,choices=ALLOWED_FRACTIONS,default=.12)
    p.add_argument("--clock",choices=("normal","fixed"),required=True)
    p.add_argument("--condition",choices=sorted(CONDITIONS),required=True)
    p.add_argument("--frames",type=int,default=8)
    p.add_argument("--warmup",type=int,default=2)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    try:
        report=take_pssm_mvp_trial(
            seed=a.seed,scenario=a.scenario,fraction=a.fraction,
            fixed_clock=a.clock=="fixed",condition=a.condition,
            frames=a.frames,warmup=a.warmup,
        )
    except Exception as exc:
        report={
            "status":"ERROR","seed":a.seed,"scenario":a.scenario,
            "fraction":a.fraction,"clock":a.clock,"condition":a.condition,
            "error":f"{type(exc).__name__}: {exc}",
            "real_vehicle_testing":False,"model_scoring_allowed":False,
        }
    a.out.write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8",
    )
    print("NATIVE_PSSM_MVP_RESULT",a.seed,a.scenario,a.clock,a.condition,
          report["status"],flush=True)
    return 0 if report["status"]=="OBSERVED_NATIVE_PSSM_MVP_TASK_TIMING" else 2


if __name__=="__main__":
    raise SystemExit(main())
