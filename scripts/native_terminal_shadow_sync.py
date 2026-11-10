"""Terminal-only GPU PSSM depth/HDR vs native RGB for Chase->PSSM timing.

All MetaDrive 0.4.3 GPU texture extraction occurs AFTER the final sensor
frame. Never extract during a sequence: earlier experiments demonstrated
extractTextureData(scene_tex) can stop that camera's later RGB updates.
Experimental post-Chase PSSM re-sync and virtual main-camera movement CHANGE
simulator semantics. No real car, ONNX inference or model scoring.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import zlib

import numpy as np

from bigbench.curved_lane_scenarios import SCENARIOS
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.native_pixel_clock import rgb_sequence, packed_i420_sequence
from bigbench.pssm_chase_pose_trace import perturb_camera_before_tick, world_camera_pose
from bigbench.pssm_mvp_trace import capture_native_pssm_mvp, registered_task_metadata
from bigbench.render_causality import raw_rgb_frame
from scripts.metadrive_render_causality import (
    capture_with_readback, read_cpu_texture, source_model_frames,
)
from scripts.metadrive_hdr_trace import gpu_readback
from scripts.native_raw_pixel_clock import clock_receipt
from scripts.native_scene_ablation_sweep import ALLOWED_FRACTIONS, scenario_pose


CONDITIONS = {
    # offset last frame?, Panda sort-25 intermediate callback, terminal GPU?
    "natural_no_gpu": (False, None, False),
    "natural_terminal": (False, None, True),
    "offset_no_gpu": (True, None, False),
    "offset_terminal": (True, None, True),
    "offset_probe_terminal": (True, "observe", True),
    "offset_sync_no_gpu": (True, "sync", False),
    "offset_sync_terminal": (True, "sync", True),
}
STAGES = ("pssm_depth", "road_hdr", "wide_hdr")
EXTRA_TASK_NAME = "bigbench_post_chase_shadow_probe"
EXTRA_TASK_SORT = 25


def task_names_and_sort(engine):
    rows=registered_task_metadata(engine.taskMgr)
    names=[row["name"] for row in rows]
    if any(names.count(name)!=1 for name in (
        "PSSM.update","update main chase camera","igLoop")):
        raise RuntimeError("original PSSM/Chase/igLoop tasks not present exactly once")
    sorting={name:next(x["sort"] for x in rows if x["name"]==name)
             for name in ("PSSM.update","update main chase camera","igLoop")}
    if (sorting["PSSM.update"]!=0 or
            sorting["update main chase camera"]!=0 or
            sorting["igLoop"]!=50):
        raise RuntimeError("unexpected original Panda 0/0/50 task sort contract")
    return rows


def run_native_terminal(*, seed:int, scenario:str, fraction:float,
                        condition:str, frames:int=5, warmup:int=2,
                        output_directory:Path) -> dict:
    if scenario not in SCENARIOS or fraction not in ALLOWED_FRACTIONS:
        raise ValueError("unsupported MetaDrive native road-lane pose")
    if condition not in CONDITIONS or type(seed) is not int:
        raise ValueError("invalid native GPU terminal arm")
    if (type(frames) is not int or not 4<=frames<=8
            or type(warmup) is not int or not 0<=warmup<=frames-2):
        raise ValueError("bounded frames/warmup required")
    injected, intermediate, terminal=CONDITIONS[condition]
    output_directory.mkdir(parents=True,exist_ok=True)
    provider=NativeMetaDriveProvider(
        seed=seed,map_config=SCENARIOS[scenario].map_config()
    )
    try:
        engine=provider.env.engine
        from metadrive.constants import CamMask
        provider.env.vehicle.origin.hide(CamMask.RgbCam)
        pose=scenario_pose(provider,scenario,fraction,1.22)
        before_registry=task_names_and_sort(engine)

        # The ONLY extra Panda task (experimental arms) is placed after the
        # native sort-0 PSSM and Chase but before the sort-50 igLoop.
        probe_events=[]
        if intermediate is not None:
            def post_chase_task(task):
                before_camera=world_camera_pose(engine.camera,engine.render)
                pre_mvp=capture_native_pssm_mvp(engine)
                if intermediate=="sync":
                    # Explicitly update CPU shadow camera rig and shader MVP
                    # one extra time, before the SAME frame's igLoop draw.
                    engine.pssm.update(task)
                after_camera=world_camera_pose(engine.camera,engine.render)
                post_mvp=capture_native_pssm_mvp(engine)
                probe_events.append({
                    "post_chase_probe_mode":intermediate,
                    "panda_global_frame_count":clock_receipt()["frame_count"],
                    "main_camera_pose_at_sort25":before_camera,
                    "camera_pose_after_sort25":after_camera,
                    "numeric_mvp_before_extra":pre_mvp,
                    "numeric_mvp_after_extra":post_mvp,
                    "mvp_changed_by_sort25_callback":
                        pre_mvp["all_f64_sha256"]!=post_mvp["all_f64_sha256"],
                    "registered_task_sort":EXTRA_TASK_SORT,
                })
                return task.cont
            engine.taskMgr.add(
                post_chase_task,EXTRA_TASK_NAME,sort=EXTRA_TASK_SORT
            )

        actual_registry=registered_task_metadata(engine.taskMgr)
        new_entries=[x for x in actual_registry if x["name"]==EXTRA_TASK_NAME]
        if (len(new_entries)!=(1 if intermediate is not None else 0) or
                (intermediate is not None and new_entries[0]["sort"]!=EXTRA_TASK_SORT)):
            raise RuntimeError("post-Chase probe task registered at wrong sort")

        # Positive camera pose test BEFORE capture series / ANY GPU extract.
        # Never move the simulated camera or redraw AFTER terminal extract.
        at_pose,_=capture_with_readback(
            provider,mode="task_step_pair",pose=pose,repeat_reads=3
        )
        moved=((pose[0][0]+2.0,pose[0][1],pose[0][2]),pose[1])
        at_moved,_=capture_with_readback(
            provider,mode="task_step_pair",pose=moved,repeat_reads=3
        )
        positive={
            kind:raw_rgb_frame(at_pose[kind]).sha256 !=
                 raw_rgb_frame(at_moved[kind]).sha256
            for kind in ("road","wide")
        }
        if not all(positive.values()):
            raise RuntimeError("camera did not respond to +2m pose positive control")

        raw={"road":[],"wide":[]}
        tick_logs=[]
        for index in range(frames):
            before=clock_receipt()
            numeric_before=capture_native_pssm_mvp(engine)
            intervention=None
            if injected and index==frames-1:
                intervention=perturb_camera_before_tick(engine,2.0)
            before_original=len(probe_events)
            images,groups=capture_with_readback(
                provider,mode="task_step_pair",pose=pose,repeat_reads=3
            )
            after=clock_receipt()
            numeric_after=capture_native_pssm_mvp(engine)
            injected_events=probe_events[before_original:]
            if len(injected_events)!=(1 if intermediate is not None else 0):
                raise RuntimeError("expected exactly one sort-25 execution per native tick")
            copied={}
            for kind in ("road","wide"):
                frame=np.array(images[kind],copy=True,order="C")
                if (frame.shape!=(provider.source_height,provider.source_width,3)
                        or frame.dtype!=np.uint8):
                    raise RuntimeError("unaltered native camera RAM RGB invalid")
                if any(not np.array_equal(frame,other) for other in groups[kind]):
                    raise RuntimeError("native same-tick CPU RGB reads not bit-exact")
                copied[kind]=frame
            for kind in copied:
                raw[kind].append(copied[kind])
            if after["frame_count"]-before["frame_count"]!=1:
                raise RuntimeError("unexpected Panda global clock count within camera pair")
            tick_logs.append({
                "frame_index_zero_based":index,
                "panda_frame_count_delta":1,
                "pssm_mvp_sha_before_tick":numeric_before["all_f64_sha256"],
                "pssm_mvp_sha_after_tick":numeric_after["all_f64_sha256"],
                "main_camera_before_optional_offset":(
                    intervention["original_camera_world_pose"]
                    if intervention else world_camera_pose(engine.camera,engine.render)
                ),
                "virtual_camera_injection":intervention,
                "sort25_event":injected_events[0] if injected_events else None,
            })
        if len(probe_events)!=(frames+2 if intermediate is not None else 0):
            raise RuntimeError("post-Chase task count differs from preflight and frames")

        after_registry=registered_task_metadata(engine.taskMgr)
        if actual_registry!=after_registry:
            raise RuntimeError("Panda task registry changed mid-experiment")

        # These bytes MUST be finalized before ANY GPU readback.
        model={"road":[],"wide":[]}
        tensor=[]
        for i in range(frames):
            transformed,packed=source_model_frames(
                provider,{kind:raw[kind][i] for kind in ("road","wide")}
            )
            for kind in ("road","wide"):
                frame=transformed[kind]
                model[kind].append(
                    np.frombuffer(frame.rgb,dtype=np.uint8).reshape(
                        frame.height,frame.width,3).copy()
                )
            tensor.append(np.array(packed,copy=True,order="C"))
        raw_summary={k:rgb_sequence(v,warmup=warmup) for k,v in raw.items()}
        model_summary={k:rgb_sequence(v,warmup=warmup) for k,v in model.items()}
        tensor_summary=packed_i420_sequence(tensor,warmup=warmup)
        sha_frozen={kind:raw_summary[kind]["all_frame_sha256"][-1]
                    for kind in ("road","wide")}
        final_mvp=capture_native_pssm_mvp(engine)

        # Terminal-only GPU intervention. No renderFrame/taskMgr.step occurs
        # after this block. Persist compressed lossless raw depth/HDR bytes
        # for exact interprocess byte comparison (NOT color-pixel decoding).
        stage_receipts={}
        after_terminal_match={"road":None,"wide":None}
        gpu_files=[]
        if terminal:
            pssm=engine.pssm
            textures={
                "pssm_depth":(
                    pssm.depth_tex,
                    pssm.buffer.getGsg() if pssm.buffer else None
                ),
            }
            for kind in ("road","wide"):
                camera=engine.sensors["bigbench_"+kind]
                textures[kind+"_hdr"]=(camera.scene_tex,camera.buffer.getGsg())
            for stage,(texture,gsg) in textures.items():
                info,data=gpu_readback(engine,stage,texture,gsg)
                if info.get("status")!="EXTRACTED" or data is None:
                    raise RuntimeError(f"terminal GPU stage unavailable: {stage}: {info}")
                name=f"{condition}-{stage}.bin.zlib"
                blob=zlib.compress(data,level=6)
                if len(blob)>64*1024*1024:
                    raise RuntimeError("compressed raw GPU stage exceeds limit")
                (output_directory/name).write_bytes(blob)
                stage_receipts[stage]={
                    **info,"lossless_compressed_filename":name,
                    "compressed_byte_count":len(blob),
                    "uncompressed_bytes_kept":len(data),
                }
                gpu_files.append(name)
            for kind in ("road","wide"):
                camera=engine.sensors["bigbench_"+kind]
                after_raw=read_cpu_texture(
                    camera,provider.source_width,provider.source_height
                )
                after_terminal_match[kind]=(
                    raw_rgb_frame(after_raw).sha256==sha_frozen[kind]
                )
            if not all(after_terminal_match.values()):
                raise RuntimeError("terminal GPU extraction altered final RAM RGB")
        else:
            stage_receipts={
                stage:{"status":"SKIPPED_BY_DESIGN_NO_GPU"}
                for stage in STAGES
            }

        injected_at_final=tick_logs[-1]["virtual_camera_injection"]
        if (bool(injected_at_final)!=injected or
                any(row["virtual_camera_injection"] for row in tick_logs[:-1])):
            raise RuntimeError("controlled main-camera x-offset arm not matched")
        last_event=tick_logs[-1]["sort25_event"]
        if intermediate is not None:
            if not last_event or last_event["post_chase_probe_mode"]!=intermediate:
                raise RuntimeError("post-Chase sync/probe callback not recorded")
            if (last_event["main_camera_pose_at_sort25"]!=
                    last_event["camera_pose_after_sort25"]):
                raise RuntimeError("post-Chase probe unexpectedly moved main camera")
        if intermediate=="sync" and injected:
            if not last_event["mvp_changed_by_sort25_callback"]:
                raise RuntimeError("deliberate post-Chase PSSM sync failed positive control")

        return {
            "status":"OBSERVED_NATIVE_TERMINAL_SHADOW_GPU_SAMPLE" if terminal
                     else "OBSERVED_NATIVE_NO_GPU_CONTROL",
            "seed":seed,"scenario":scenario,"fraction":fraction,
            "camera_pose":pose,"condition":condition,
            "frames":frames,"warmup":warmup,
            "injected_camera_offset_last_frame":injected,
            "post_chase_extra_task_kind":intermediate,
            "terminal_gpu_probe":terminal,
            "virtual_main_camera_x_offset_m":2.0 if injected else 0.0,
            "original_task_names_and_sort":before_registry,
            "tasks_with_optional_extra_sort25":actual_registry,
            "task_registry_unchanged_during_frames":True,
            "gpu_extraction_before_or_during_rgb_capture":False,
            "terminal_gpu_extraction_after_complete_rgb_i420":terminal,
            "gpu_stage_receipts":stage_receipts,
            "gpu_compressed_files":gpu_files,
            "same_tick_final_ram_rgb_unchanged_after_terminal":after_terminal_match,
            "source_rgb":raw_summary,"warped_rgb":model_summary,
            "onnx_i420":tensor_summary,"final_cpu_pssm_mvp":final_mvp,
            "per_frame_cpu_and_extra_task":tick_logs,
            "both_camera_plus_2m_positive":positive,
            "post_chase_sort25_was_separately_registered":intermediate is not None,
            "native_onnx_inference_performed":False,
            "original_renderer_semantics_unchanged":(
                not injected and intermediate is None
            ),
            "real_vehicle_testing":False,"model_scoring_allowed":False,
            "cd210_fallback":False,
            "warning":(
                "Terminal GPU stage capture is ONE LAST-frame snapshot, not "
                "frame-by-frame depth/HDR. Cross-process raw bytes can vary "
                "without the post-Chase sync causing the variation. Offset "
                "and extra PSSM update intentionally change renderer semantics."
            ),
        }
    finally:
        provider.close()


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="MetaDrive 0.4.3 terminal-only GPU shadow A/B")
    p.add_argument("--scenario",choices=sorted(SCENARIOS),required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--fraction",choices=ALLOWED_FRACTIONS,type=float,default=.12)
    p.add_argument("--condition",choices=sorted(CONDITIONS),required=True)
    p.add_argument("--frames",type=int,default=5)
    p.add_argument("--warmup",type=int,default=2)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    try:
        result=run_native_terminal(
            seed=a.seed,scenario=a.scenario,fraction=a.fraction,
            condition=a.condition,frames=a.frames,warmup=a.warmup,
            output_directory=a.out.parent,
        )
    except Exception as exc:
        result={
            "status":"ERROR","seed":a.seed,"scenario":a.scenario,
            "condition":a.condition,"error":f"{type(exc).__name__}: {exc}",
            "model_scoring_allowed":False,"real_vehicle_testing":False,
        }
    a.out.write_text(json.dumps(
        result,indent=2,ensure_ascii=False,allow_nan=False
    )+"\n",encoding="utf-8")
    print("NATIVE_TERMINAL_SHADOW",a.seed,a.scenario,a.condition,
          result["status"],flush=True)
    return 0 if result["status"] in (
        "OBSERVED_NATIVE_NO_GPU_CONTROL",
        "OBSERVED_NATIVE_TERMINAL_SHADOW_GPU_SAMPLE",
    ) else 2


if __name__=="__main__":
    raise SystemExit(main())
