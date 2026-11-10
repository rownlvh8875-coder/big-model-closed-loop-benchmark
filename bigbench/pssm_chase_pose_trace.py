"""Sim-only CPU callback camera pose / PSSM MVP timing probe.

Uses sys.setprofile to read the actual main-camera WORLD pose and existing
shadow-camera rig MVP on Python callback call/return. No Panda task is
removed/replaced/reordered. Reading Panda matrix values from inside callbacks
is timing-intrusive. This is not a GPU shadow-depth measurement, nor proof
of photometric/ONNX repeated execution.
"""
from __future__ import annotations

import math
from time import perf_counter_ns
from typing import Any

from .native_callback_profiler import ExactCallbackProfiler, summarize_callback_pair
from .pssm_mvp_trace import capture_native_pssm_mvp


class PoseTraceError(ValueError):
    pass


def world_camera_pose(camera: Any, parent: Any) -> dict:
    """Read Panda3D NodePath WORLD transform, without changing it."""
    p=camera.getPos(parent)
    hpr=camera.getHpr(parent)
    xyz=[float(p[i]) for i in range(3)]
    rotation=[float(hpr[i]) for i in range(3)]
    if not all(math.isfinite(v) for v in xyz+rotation):
        raise PoseTraceError("Panda main camera WORLD pose has nonfinite values")
    return {"xyz_m":xyz,"hpr_deg":rotation}


def position_distance_m(a: dict,b: dict) -> float:
    if not isinstance(a,dict) or not isinstance(b,dict):
        raise PoseTraceError("missing camera pose observation")
    va=a.get("xyz_m")
    vb=b.get("xyz_m")
    if (not isinstance(va,list) or not isinstance(vb,list) or len(va)!=3 or len(vb)!=3
            or any(not isinstance(v,(float,int)) or not math.isfinite(v) for v in va+vb)):
        raise PoseTraceError("invalid camera pose vector")
    return math.dist(va,vb)


class PSSMChasePoseProfiler(ExactCallbackProfiler):
    """Record callback entry/exit and simultaneous RGB-shadow matrix state."""

    def _profile(self,frame,event,_arg):
        if event not in ("call","return"):
            return
        callback=self._codes.get(frame.f_code)
        if callback is None:
            return
        obj=frame.f_locals.get("self")
        if callback=="PSSM.update":
            if obj is not self._pssm:
                return
        elif getattr(obj,"engine",None) is not self._engine:
            return
        # The callback is executing in Panda's Python main thread. These are
        # observations only; no calls to renderFrame, taskMgr.step, update
        # or GPU texture extraction inside the profiler.
        pose=world_camera_pose(self._engine.camera,self._engine.render)
        mvp=capture_native_pssm_mvp(self._engine)
        self.events.append({
            "order_in_trace":len(self.events),
            "event":event,"callback":callback,
            "perf_counter_ns":perf_counter_ns(),
            "main_camera_world_pose":pose,
            "pssm_mvp_cpu_sha256":mvp["all_f64_sha256"],
            "pssm_mvp_numeric":mvp,
            "chase_run_task_flag":(
                bool(getattr(obj,"run_task",False))
                if callback=="MainCamera._chase_task" else None
            ),
        })


def assess_pose_events(events: list[dict], *, expected_ticks: int) -> dict:
    """Analyze actual per-tick callback call/return, no inferred sort-order."""
    verified=summarize_callback_pair(events,expected_ticks)
    ticks=[]
    for tick_id in range(expected_ticks):
        chunk=events[4*tick_id:4*(tick_id+1)]
        if len(chunk)!=4:
            raise PoseTraceError("missing native callback entries")
        by_name={}
        for first,last in ((chunk[0],chunk[1]),(chunk[2],chunk[3])):
            if first["event"]!="call" or last["event"]!="return" or first["callback"]!=last["callback"]:
                raise PoseTraceError("Python callback nesting or record gap")
            if first["callback"] in by_name:
                raise PoseTraceError("duplicate callback")
            for point in (first,last):
                if (point.get("pssm_mvp_numeric",{}).get("status")!="MVP_VALUES_CAPTURED"
                        or point.get("pssm_mvp_cpu_sha256")!=
                            point["pssm_mvp_numeric"]["all_f64_sha256"]):
                    raise PoseTraceError("numeric MVP evidence incomplete/inconsistent")
                world_camera_pose_validation=position_distance_m(
                    point["main_camera_world_pose"],point["main_camera_world_pose"]
                )
                if world_camera_pose_validation!=0:
                    raise PoseTraceError("nonsensical camera pose")
            by_name[first["callback"]]=(first,last)
        pssm_first,pssm_last=by_name["PSSM.update"]
        chase_first,chase_last=by_name["MainCamera._chase_task"]
        before=pssm_first["main_camera_world_pose"]
        pssm_after=pssm_last["main_camera_world_pose"]
        chase_before=chase_first["main_camera_world_pose"]
        chase_after=chase_last["main_camera_world_pose"]
        ticks.append({
            "tick_in_pair_zero_based":tick_id,
            "actual_callback_order":verified["per_taskmgr_step_callback_call_order"][tick_id],
            "pssm_entry_camera":before,
            "pssm_exit_camera":pssm_after,
            "chase_entry_camera":chase_before,
            "chase_exit_camera":chase_after,
            "pssm_entry_mvp_sha256":pssm_first["pssm_mvp_cpu_sha256"],
            "pssm_exit_mvp_sha256":pssm_last["pssm_mvp_cpu_sha256"],
            "chase_entry_mvp_sha256":chase_first["pssm_mvp_cpu_sha256"],
            "chase_exit_mvp_sha256":chase_last["pssm_mvp_cpu_sha256"],
            "pssm_entry_mvp_numeric":pssm_first["pssm_mvp_numeric"]["matrix_values"],
            "pssm_exit_mvp_numeric":pssm_last["pssm_mvp_numeric"]["matrix_values"],
            "chase_exit_mvp_numeric":chase_last["pssm_mvp_numeric"]["matrix_values"],
            "pssm_mvp_changed_during_pssm_callback":(
                pssm_first["pssm_mvp_cpu_sha256"]!=pssm_last["pssm_mvp_cpu_sha256"]
            ),
            "pssm_mvp_changed_during_chase_callback":(
                chase_first["pssm_mvp_cpu_sha256"]!=chase_last["pssm_mvp_cpu_sha256"]
            ),
            "camera_moved_during_pssm_callback_m":
                position_distance_m(before,pssm_after),
            "camera_moved_during_chase_callback_m":
                position_distance_m(chase_before,chase_after),
            "camera_pose_difference_between_pssm_entry_and_chase_exit_m":
                position_distance_m(before,chase_after),
            "chase_callback_run_task_flag":chase_first.get("chase_run_task_flag"),
            "pssm_precedes_chase_on_cpu":(
                verified["per_taskmgr_step_callback_call_order"][tick_id]==[
                    "PSSM.update","MainCamera._chase_task"
                ]
            ),
        })
    return {
        "status":"NUMERIC_PSSM_CAMERA_POSE_AT_ACTUAL_CALLBACK_BOUNDARIES_OBSERVED",
        "expected_taskmgr_ticks":expected_ticks,
        "callback_order_verified_by_actual_call_return":True,
        "per_taskmgr_tick":ticks,
        "pssm_before_chase_every_tick":all(x["pssm_precedes_chase_on_cpu"] for x in ticks),
        "camera_motion_during_pssm_count":sum(
            x["camera_moved_during_pssm_callback_m"]>0 for x in ticks
        ),
        "camera_motion_during_chase_count":sum(
            x["camera_moved_during_chase_callback_m"]>0 for x in ticks
        ),
        "mvp_updates_during_pssm_count":sum(
            x["pssm_mvp_changed_during_pssm_callback"] for x in ticks
        ),
        "mvp_updates_during_chase_count":sum(
            x["pssm_mvp_changed_during_chase_callback"] for x in ticks
        ),
        "observed_pre_chase_pose_differs_from_post_chase_count":sum(
            x["camera_pose_difference_between_pssm_entry_and_chase_exit_m"]>0
            for x in ticks
        ),
        "cpu_profiler_can_change_wall_clock_timing":True,
        "pssm_gpu_shadow_pass_causality_proven":False,
        "original_untouched_pipeline_repeatability_proven":False,
    }


def perturb_camera_before_tick(engine: Any,delta_x_m: float) -> dict:
    """Explicit SIM-ONLY main-camera perturbation before Panda tick.

    Used in a separate experimental arm: alters virtual main camera state and
    thus MUST NEVER be passed off as untouched MetaDrive or a model score.
    """
    if not math.isfinite(delta_x_m) or not 0.1<=abs(delta_x_m)<=3.0:
        raise PoseTraceError("bounded virtual camera perturbation required")
    before=world_camera_pose(engine.camera,engine.render)
    xyz=before["xyz_m"]
    engine.camera.setPos(engine.render,xyz[0]+delta_x_m,xyz[1],xyz[2])
    after=world_camera_pose(engine.camera,engine.render)
    if abs((after["xyz_m"][0]-xyz[0])-delta_x_m)>1e-5:
        raise PoseTraceError("virtual camera perturbation failed positive control")
    return {
        "virtual_intervention":"MAIN_SCENE_CAMERA_X_OFFSET_BEFORE_TASK_TICK",
        "original_camera_world_pose":before,
        "intervened_camera_world_pose":after,
        "measured_delta_x_m":after["xyz_m"][0]-xyz[0],
        "requested_delta_x_m":delta_x_m,
        "real_vehicle_testing":False,
        "untouched_renderer_semantics":False,
    }
