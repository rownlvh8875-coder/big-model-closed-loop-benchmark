"""Fresh-native MetaDrive 0.4.3 task callback order and timing A/B.

Matched conditions use independent Panda worlds and exact native RGB frames:
  control: no Python profile hook;
  observed: sys.setprofile catches PSSM.update / MainCamera._chase_task.
Neither arm removes/reorders registered Panda tasks. Profiling is CPU-timing
intrusive despite leaving the registered task graph untouched. This is not
a model or graphics quality proof and never processes real-car data.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from time import perf_counter_ns

import numpy as np

from bigbench.curved_lane_scenarios import SCENARIOS
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.native_callback_profiler import (
    ExactCallbackProfiler, summarize_callback_pair,
    summarize_callback_sequence,
)
from bigbench.native_pixel_clock import rgb_sequence, packed_i420_sequence
from bigbench.pssm_mvp_trace import registered_task_metadata
from bigbench.render_causality import raw_rgb_frame
from scripts.metadrive_render_causality import capture_with_readback, source_model_frames
from scripts.native_raw_pixel_clock import clock_receipt
from scripts.native_scene_ablation_sweep import ALLOWED_FRACTIONS, scenario_pose


CAPTURE_MODES = {"paired": ("task_step_pair", 1),
                 "sequential": ("perceive_sequential", 2)}
ARMS = ("unprofiled", "profiled")


def run_trial(*, seed: int, scenario: str, fraction: float,
              capture: str, arm: str, frames: int = 8, warmup: int = 2) -> dict:
    if scenario not in SCENARIOS or fraction not in ALLOWED_FRACTIONS:
        raise ValueError("unsupported native scenario or fixed world-pose fraction")
    if capture not in CAPTURE_MODES or arm not in ARMS:
        raise ValueError("unknown capture/profiler arm")
    if (type(seed) is not int or type(frames) is not int or
            not 6 <= frames <= 16 or type(warmup) is not int
            or not 0 <= warmup <= frames-2):
        raise ValueError("invalid bounded native experiment")
    mode, taskmgr_calls = CAPTURE_MODES[capture]
    provider=NativeMetaDriveProvider(
        seed=seed, map_config=SCENARIOS[scenario].map_config()
    )
    try:
        engine=provider.env.engine
        from metadrive.constants import CamMask
        provider.env.vehicle.origin.hide(CamMask.RgbCam)
        pose=scenario_pose(provider,scenario,fraction,1.22)
        tasks_before=registered_task_metadata(engine.taskMgr)
        tasks=[x["name"] for x in tasks_before]
        if (tasks.count("PSSM.update") != 1 or
                tasks.count("update main chase camera") != 1 or
                tasks.count("igLoop") != 1):
            raise RuntimeError("native PSSM, chase, igLoop task identity required")
        # No remove/add/replacement of a task object in either arm.
        profiler=ExactCallbackProfiler(engine) if arm == "profiled" else None
        originals={"road":[],"wide":[]}
        call_receipts=[]
        clock_rows=[]
        for i in range(frames):
            before=clock_receipt()
            started=perf_counter_ns()
            if profiler is not None:
                start_index=len(profiler.events)
                with profiler.observe():
                    observations,readbacks=capture_with_readback(
                        provider,mode=mode,pose=pose,repeat_reads=3,
                    )
                event_slice=profiler.events[start_index:]
                call_receipts.append(
                    summarize_callback_pair(event_slice,taskmgr_calls)
                )
                # Put the complete exact Python callback sequence in source JSON.
                call_receipts[-1]["raw_call_return_events"]=event_slice
            else:
                observations,readbacks=capture_with_readback(
                    provider,mode=mode,pose=pose,repeat_reads=3,
                )
            stopped=perf_counter_ns()
            after=clock_receipt()
            copies={}
            for kind in ("road","wide"):
                snapshot=np.array(observations[kind],copy=True,order="C")
                if snapshot.shape!=(provider.source_height,provider.source_width,3):
                    raise RuntimeError("original MetaDrive RGB shape changed")
                if snapshot.dtype!=np.uint8:
                    raise RuntimeError("native RGB bytes were replaced")
                if any(not np.array_equal(snapshot,v) for v in readbacks[kind]):
                    raise RuntimeError("re-reading same completed CPU RGB was not exact")
                copies[kind]=snapshot
            for kind,snapshot in copies.items():
                originals[kind].append(snapshot)
            delta=after["frame_count"]-before["frame_count"]
            clock_rows.append({
                "frame_index_zero_based":i,
                "before":before,"after":after,
                "global_panda_frame_count_delta":delta,
                "capture_elapsed_cpu_wall_ns":stopped-started,
            })
        tasks_after=registered_task_metadata(engine.taskMgr)
        # Positive control occurs only after capturing original time series.
        shifted=((pose[0][0]+2.0,pose[0][1],pose[0][2]),pose[1])
        moved,_=capture_with_readback(
            provider,mode=mode,pose=shifted,repeat_reads=3
        )
        positive={
            kind:raw_rgb_frame(moved[kind]).sha256 !=
                 raw_rgb_frame(originals[kind][-1]).sha256
            for kind in ("road","wide")
        }
        # Post-process full image time series only after all render task ticks.
        model={"road":[],"wide":[]}
        packed=[]
        for i in range(frames):
            p, tensor=source_model_frames(provider,{
                k:originals[k][i] for k in ("road","wide")
            })
            for kind in ("road","wide"):
                f=p[kind]
                model[kind].append(
                    np.frombuffer(f.rgb,dtype=np.uint8).reshape(
                        f.height,f.width,3
                    ).copy()
                )
            packed.append(np.array(tensor,copy=True,order="C"))
        source={kind:rgb_sequence(originals[kind],warmup=warmup)
                for kind in ("road","wide")}
        transformed={kind:rgb_sequence(model[kind],warmup=warmup)
                     for kind in ("road","wide")}
        result_tensor=packed_i420_sequence(packed,warmup=warmup)
        expected_delta=taskmgr_calls
        ticks_ok=all(
            row["global_panda_frame_count_delta"]==expected_delta
            for row in clock_rows
        )
        finite_clock=all(
            all(math.isfinite(float(item["after"][field]))
                for field in ("frame_time_s","real_time_s","dt_s"))
            for item in clock_rows
        )
        registrations_intact=tasks_before==tasks_after
        if profiler is None:
            trace_summary=None
        else:
            trace_summary=summarize_callback_sequence(
                call_receipts,expected_steps=taskmgr_calls
            )
        success=(all(positive.values()) and ticks_ok and
                 registrations_intact and finite_clock)
        return {
            "status": ("OBSERVED_NATIVE_CALLBACK_CONTROL" if success and arm=="unprofiled"
                       else "OBSERVED_NATIVE_CALLBACK_ORDER" if success
                       else "INCONCLUSIVE_NATIVE_CALLBACK_TRACE"),
            "seed":seed,"scenario":scenario,"fraction":fraction,"world_pose":pose,
            "capture":capture,"capture_mode_in_upstream":mode,"arm":arm,
            "frames":frames,"warmup":warmup,"taskmgr_step_calls_from_source":taskmgr_calls,
            "global_panda_frame_count_delta_expected":expected_delta,
            "global_frame_count_delta_telemetry_correct":ticks_ok,
            "native_task_registration_before":tasks_before,
            "native_task_registration_after":tasks_after,
            "task_registration_unchanged":registrations_intact,
            "actual_python_callback_order":trace_summary,
            "per_frame_callback_receipts":call_receipts,
            "clock_and_capture_wall_time":clock_rows,
            "source_rgb":source,"warped_model_rgb":transformed,
            "model_i420":result_tensor,
            "plus_2m_road_and_wide_response":positive,
            "gpu_hdr_or_depth_extract_calls":0,
            "task_registration_modified":False,
            "cpu_profiler_timing_overhead_possible":arm=="profiled",
            "callbacks_only_observed_on_python_main_thread":True,
            "real_vehicle_testing":False,"model_scoring_allowed":False,
            "onnx_model_inference_executed":False,"cd210_fallback":False,
            "warning": (
                "Profiling does not mutate task registrations but adds CPU overhead. "
                "Timing/photometric equivalence to unprofiled world unproven. "
                "Callback order does not establish GPU draw/shadow pass order."
            ),
        }
    finally:
        provider.close()


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="MetaDrive actual callback trace A/B (SIM ONLY)")
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--scenario",choices=sorted(SCENARIOS),required=True)
    p.add_argument("--fraction",type=float,choices=ALLOWED_FRACTIONS,default=.12)
    p.add_argument("--capture",choices=sorted(CAPTURE_MODES),required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    p.add_argument("--frames",type=int,default=8)
    p.add_argument("--warmup",type=int,default=2)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    try:
        result=run_trial(seed=a.seed,scenario=a.scenario,fraction=a.fraction,
                         capture=a.capture,arm=a.arm,frames=a.frames,
                         warmup=a.warmup)
    except Exception as exc:
        result={
            "status":"ERROR","seed":a.seed,"scenario":a.scenario,
            "capture":a.capture,"arm":a.arm,
            "error":f"{type(exc).__name__}: {exc}",
            "model_scoring_allowed":False,"real_vehicle_testing":False,
        }
    a.out.write_text(
        json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8"
    )
    print("NATIVE_ACTUAL_CALLBACK_OBSERVATION",a.seed,a.scenario,a.capture,
          a.arm,result["status"],flush=True)
    return 0 if result["status"] in (
        "OBSERVED_NATIVE_CALLBACK_CONTROL","OBSERVED_NATIVE_CALLBACK_ORDER"
    ) else 2


if __name__=="__main__":
    raise SystemExit(main())
