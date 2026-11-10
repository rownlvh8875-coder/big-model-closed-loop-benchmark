"""MetaDrive 0.4.3: main camera pose at PSSM and chase CPU callback boundaries.

Three fresh-process arms:
 - boundary_control: no Python profiler, original MetaDrive scene;
 - boundary_observed: profiler, original scene;
 - virtual_x_intervention: profiler + explicitly shift VIRTUAL main camera x
   by +2 m immediately before selected taskMgr steps (SIM-ONLY falsification).

The intervention is NOT a renderer repair nor a substitute for native ONNX
model inputs. No real vehicle, GPU shadow texture extraction or ranking.
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
from bigbench.native_pixel_clock import rgb_sequence, packed_i420_sequence
from bigbench.pssm_chase_pose_trace import (
    PSSMChasePoseProfiler, assess_pose_events,
    world_camera_pose, perturb_camera_before_tick,
)
from bigbench.pssm_mvp_trace import capture_native_pssm_mvp, registered_task_metadata
from bigbench.render_causality import raw_rgb_frame
from scripts.metadrive_render_causality import capture_with_readback, source_model_frames
from scripts.native_raw_pixel_clock import clock_receipt
from scripts.native_scene_ablation_sweep import ALLOWED_FRACTIONS, scenario_pose


ARMS = ("boundary_control","boundary_observed","virtual_x_intervention")
CAPTURES = {"paired":("task_step_pair",1),
            "sequential":("perceive_sequential",2)}
INTERVENTION_FRAMES=(3,5)
INTERVENTION_DELTA_M=2.0


def run_pose_trial(*,seed:int,scenario:str,fraction:float,capture:str,arm:str,
                   frames:int=8,warmup:int=2) -> dict:
    if (scenario not in SCENARIOS or fraction not in ALLOWED_FRACTIONS
            or capture not in CAPTURES or arm not in ARMS):
        raise ValueError("unsupported native camera-lane experimental condition")
    if (type(seed) is not int or type(frames) is not int
            or not 8<=frames<=16 or type(warmup) is not int
            or not 0<=warmup<=frames-2):
        raise ValueError("bounded native frame count invalid")
    mode,steps_per_pair=CAPTURES[capture]
    provider=NativeMetaDriveProvider(seed=seed,map_config=SCENARIOS[scenario].map_config())
    try:
        engine=provider.env.engine
        from metadrive.constants import CamMask
        provider.env.vehicle.origin.hide(CamMask.RgbCam)
        pose=scenario_pose(provider,scenario,fraction,1.22)
        before_tasks=registered_task_metadata(engine.taskMgr)
        names=[x["name"] for x in before_tasks]
        if any(names.count(t)!=1 for t in (
                "PSSM.update","update main chase camera","igLoop")):
            raise RuntimeError("native shadow/chase/graphics task identity missing")
        profiler=(None if arm=="boundary_control"
                  else PSSMChasePoseProfiler(engine))
        raw={"road":[],"wide":[]}
        timeline=[]
        for i in range(frames):
            before_world=world_camera_pose(engine.camera,engine.render)
            pre_mvp=capture_native_pssm_mvp(engine)["all_f64_sha256"]
            injection=None
            if arm=="virtual_x_intervention" and i in INTERVENTION_FRAMES:
                injection=perturb_camera_before_tick(engine,INTERVENTION_DELTA_M)
            injected_world=world_camera_pose(engine.camera,engine.render)
            start_clock=clock_receipt()
            start=perf_counter_ns()
            if profiler is None:
                images,readbacks=capture_with_readback(
                    provider,mode=mode,pose=pose,repeat_reads=3)
                evidence=None
                raw_events=[]
            else:
                cursor=len(profiler.events)
                with profiler.observe():
                    images,readbacks=capture_with_readback(
                        provider,mode=mode,pose=pose,repeat_reads=3)
                raw_events=profiler.events[cursor:]
                evidence=assess_pose_events(raw_events,expected_ticks=steps_per_pair)
            elapsed_ns=perf_counter_ns()-start
            end_clock=clock_receipt()
            after_world=world_camera_pose(engine.camera,engine.render)
            post_mvp=capture_native_pssm_mvp(engine)["all_f64_sha256"]
            for kind in ("road","wide"):
                original=np.array(images[kind],copy=True,order="C")
                if (original.shape!=(provider.source_height,provider.source_width,3)
                        or original.dtype!=np.uint8):
                    raise RuntimeError("native original RAM RGB contract broken")
                if any(not np.array_equal(original,other) for other in readbacks[kind]):
                    raise RuntimeError("no-render CPU copies of same RGB differed")
                raw[kind].append(original)
            timeline.append({
                "frame_index_zero_based":i,
                "camera_pose_before_optional_intervention":before_world,
                "camera_pose_before_task_tick":injected_world,
                "camera_pose_after_task_tick":after_world,
                "mvp_sha_before_tick":pre_mvp,
                "mvp_sha_after_tick":post_mvp,
                "controlled_virtual_main_camera_offset":injection,
                "start_clock":start_clock,
                "end_clock":end_clock,
                "panda_global_frame_count_delta":
                    end_clock["frame_count"]-start_clock["frame_count"],
                "capture_elapsed_wall_ns":elapsed_ns,
                "exact_python_callback_event_receipt":evidence,
                "raw_python_call_return_events":raw_events,
            })
        after_tasks=registered_task_metadata(engine.taskMgr)
        # Capture the pose response AFTER the experimental time series only.
        shifted=((pose[0][0]+2.0,pose[0][1],pose[0][2]),pose[1])
        moved,_=capture_with_readback(provider,mode=mode,pose=shifted,repeat_reads=3)
        positive={
            kind:raw_rgb_frame(moved[kind]).sha256 != raw_rgb_frame(raw[kind][-1]).sha256
            for kind in ("road","wide")
        }
        # Model warping and all difference analyses run AFTER the last native tick.
        canvas={"road":[],"wide":[]}
        tensors=[]
        for i in range(frames):
            img,packed=source_model_frames(provider,{
                kind:raw[kind][i] for kind in ("road","wide")
            })
            for kind in ("road","wide"):
                pic=img[kind]
                canvas[kind].append(np.frombuffer(
                    pic.rgb,dtype=np.uint8
                ).reshape(pic.height,pic.width,3).copy())
            tensors.append(np.array(packed,copy=True,order="C"))
        frame_deltas_ok=all(row["panda_global_frame_count_delta"]==steps_per_pair
                            for row in timeline)
        clock_finite=all(
            all(math.isfinite(float(v[field]))
                for v in (row["start_clock"],row["end_clock"])
                for field in ("frame_time_s","real_time_s","dt_s"))
            for row in timeline
        )
        intrusion_correct=(
            all((row["controlled_virtual_main_camera_offset"] is not None)==
                (arm=="virtual_x_intervention" and row["frame_index_zero_based"] in
                 INTERVENTION_FRAMES)
                for row in timeline)
        )
        callback_coverage=(
            all(row["exact_python_callback_event_receipt"] is not None
                for row in timeline)
            if profiler is not None else
            all(row["exact_python_callback_event_receipt"] is None
                and not row["raw_python_call_return_events"] for row in timeline)
        )
        recorded_registered_tasks=before_tasks==after_tasks
        valid=(all(positive.values()) and frame_deltas_ok and clock_finite
               and intrusion_correct and callback_coverage
               and recorded_registered_tasks)
        raw_stats={kind:rgb_sequence(v,warmup=warmup) for kind,v in raw.items()}
        model_stats={kind:rgb_sequence(v,warmup=warmup) for kind,v in canvas.items()}
        i420_stats=packed_i420_sequence(tensors,warmup=warmup)
        return {
            "status":"OBSERVED_NATIVE_PSSM_CHASE_CAMERA_BOUNDARIES" if valid
                     else "INCONCLUSIVE_NATIVE_PSSM_CHASE_CAMERA_BOUNDARIES",
            "seed":seed,"scenario":scenario,"fraction":fraction,"world_pose":pose,
            "capture":capture,"arm":arm,"frames":frames,"warmup":warmup,
            "mode":mode,"taskmgr_calls_per_pair_from_original_code":steps_per_pair,
            "registered_tasks_before":before_tasks,
            "registered_tasks_after":after_tasks,
            "registered_tasks_unchanged":recorded_registered_tasks,
            "callback_trace_instrumented":profiler is not None,
            "original_main_camera_state_deliberately_modified":
                arm=="virtual_x_intervention",
            "virtual_offset_intervention_frames_zero_based":list(
                INTERVENTION_FRAMES) if arm=="virtual_x_intervention" else [],
            "virtual_offset_m_requested":(INTERVENTION_DELTA_M
                                          if arm=="virtual_x_intervention" else 0),
            "timeline":timeline,
            "raw_source_rgb":raw_stats,
            "warped_model_rgb":model_stats,
            "onnx_image_tensor_i420":i420_stats,
            "plus_2m_pose_response":positive,
            "panda_global_frame_deltas_match":frame_deltas_ok,
            "panda_clock_finite":clock_finite,
            "controlled_intervention_identity_valid":intrusion_correct,
            "callback_evidence_complete":callback_coverage,
            "native_gpu_hdr_extract_calls":0,
            "real_vehicle_testing":False,"model_scoring_allowed":False,
            "onnx_inference_executed":False,"cd210_fallback":False,
            "warning":(
                "CPU profile/pose/MVP telemetry perturbs wall-clock timing; "
                "virtual camera x intervention deliberately changes the scene. "
                "GPU shadow-map draw ordering and official model determinism "
                "are NOT proven by these numeric matrix observations."
            ),
        }
    finally:
        provider.close()


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="SIM-ONLY native PSSM vs Chase pose lag")
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--scenario",choices=sorted(SCENARIOS),required=True)
    p.add_argument("--fraction",type=float,choices=ALLOWED_FRACTIONS,default=.12)
    p.add_argument("--capture",choices=sorted(CAPTURES),required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    p.add_argument("--frames",type=int,default=8)
    p.add_argument("--warmup",type=int,default=2)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    try:
        report=run_pose_trial(seed=a.seed,scenario=a.scenario,fraction=a.fraction,
                              capture=a.capture,arm=a.arm,frames=a.frames,
                              warmup=a.warmup)
    except Exception as exc:
        report={
            "status":"ERROR","seed":a.seed,"scenario":a.scenario,
            "capture":a.capture,"arm":a.arm,
            "error":f"{type(exc).__name__}: {exc}",
            "real_vehicle_testing":False,"model_scoring_allowed":False,
        }
    a.out.write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8"
    )
    print("NATIVE_PSSM_CHASE_POSE_BOUNDARY",a.seed,a.scenario,a.capture,a.arm,
          report["status"],flush=True)
    return 0 if report["status"]=="OBSERVED_NATIVE_PSSM_CHASE_CAMERA_BOUNDARIES" else 2


if __name__=="__main__":
    raise SystemExit(main())
