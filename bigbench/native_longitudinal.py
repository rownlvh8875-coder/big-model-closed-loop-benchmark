"""Native virtual lead-actor camera loop for LONGITUDINAL model diagnostics.

MetaDrive supplies a moving VISUAL traffic prop only; its vehicle physics,
Carrot controls, CAN, personal logs and real-road testing are never used.
The ego's lateral path is the common x-axis oracle; only ONNX-requested
longitudinal acceleration affects its speed. No model score is authorized.
"""
from __future__ import annotations

from math import isfinite
from typing import Any
from dataclasses import dataclass

from .kinematics import AgentState,ModelAction,step_ideal
from .longitudinal_world import LongitudinalScenario,LongitudinalContractError
from .policies import ModelObservation


@dataclass
class LeadState:
    station_m: float
    speed_mps: float


class DeterministicLeadTimeline:
    """Explicit exogenous actor movement, independent of model output."""
    def __init__(self,scenario:LongitudinalScenario):
        self.scenario=scenario
        self.reset()

    def reset(self):
        self.state=LeadState(self.scenario.initial_gap_m,self.scenario.lead_speed_mps)

    def step(self,time_s:float,dt_s:float)->LeadState:
        if not all(isfinite(x) for x in (time_s,dt_s)) or dt_s<=0:
            raise LongitudinalContractError('invalid lead time grid')
        accel=0.
        for event in self.scenario.lead_events:
            if time_s+1e-10>=event.time_s:
                accel=event.acceleration_mps2
        move=min(dt_s,-self.state.speed_mps/accel) if accel<0 else dt_s
        self.state=LeadState(
            self.state.station_m+max(0.,self.state.speed_mps*move+.5*accel*move*move),
            max(0.,self.state.speed_mps+accel*dt_s))
        return self.state


class NativeLeadVisualRenderer:
    """MetaDrive DefaultVehicle is a graphic obstacle, not a simulated plant."""
    def __init__(self,provider:Any,*,target_lane=None,adjacent_lane=None,origin_station_m=0.):
        from metadrive.component.vehicle.vehicle_type import DefaultVehicle
        from .native_model_campaign import NativeWorldCamera
        self.provider=provider
        self.target_lane=target_lane
        self.adjacent_lane=adjacent_lane
        self.origin_station_m=origin_station_m
        from copy import deepcopy
        config=deepcopy(provider.env.engine.global_config['vehicle_config'])
        # BaseVehicle.reset requires an explicit valid lane identifier;
        # the default traffic config has spawn_lane_index=None.
        ego_lane=getattr(provider.env.vehicle,'lane',None)
        lane_index=getattr(ego_lane,'index',None)
        if lane_index is None:
            raise LongitudinalContractError('native MetaDrive map has no valid spawn lane')
        config['spawn_lane_index']=tuple(lane_index)
        self.actor=provider.env.engine.spawn_object(
            DefaultVehicle,
            vehicle_config=config,
            random_seed=provider.seed+1,
        )
        self.world_camera=NativeWorldCamera(provider)
        self.capture_world=self.world_camera.capture
        self.actor.set_heading_theta(0.0)

    def capture(self,ego:AgentState,lead:LeadState,*,in_lane:bool=True):
        if self.target_lane is None:
            self.actor.set_position([lead.station_m,0.0 if in_lane else -5.0])
            self.actor.set_heading_theta(0.0)
            return self.capture_world(ego)
        lead_lane=self.target_lane if in_lane else self.adjacent_lane
        lead_station=self.origin_station_m+lead.station_m
        ego_station=self.origin_station_m+ego.x
        if not (lead_lane is not None and 0.<=lead_station<=lead_lane.length
                and 0.<=ego_station<=self.target_lane.length):
            raise LongitudinalContractError('ego or lead exceeds the measured native straight lane')
        self.actor.set_position(lead_lane.position(lead_station,0.))
        self.actor.set_heading_theta(lead_lane.heading_theta_at(lead_station))
        x,y=map(float,self.target_lane.position(ego_station,0.))
        pose=AgentState(ego.t,x,y,float(self.target_lane.heading_theta_at(ego_station)),ego.speed)
        return self.capture_world(pose)

    def close(self):
        if getattr(self,'actor',None) is not None:
            self.provider.env.engine.clear_objects([self.actor.id])
            self.actor=None


def run_longitudinal_native(policy:Any,scene:LongitudinalScenario,
                            camera:Any,*,steps:int=60,dt_s:float=.05,
                            stop_at_collision:bool=False,progress=None)->dict:
    if type(steps) is not int or not 1<=steps<=2000 or abs(dt_s-.05)>1e-12:
        raise LongitudinalContractError('need bounded native model clock at 20 Hz')
    ego=AgentState(0.,0.,0.,0.,scene.ego_speed_mps)
    lead=DeterministicLeadTimeline(scene)
    policy.reset()
    trace=[]
    previous_accel=0.
    failure=None
    termination='STEP_LIMIT'
    for k in range(steps):
        visible=scene.merge_at_s is None or ego.t>=scene.merge_at_s
        try:
            pair=camera.capture(ego,lead.state,in_lane=visible)
            if progress is not None:
                progress(dict(status='INFERENCE_PENDING',completed_rows=len(trace)))
            model_action=policy.step(ModelObservation(pair.road,ego.speed,ego.t,
                                                      wide_frame=pair.wide))
            accel=model_action.acceleration_mps2
            if not isfinite(accel):
                raise LongitudinalContractError('nonfinite native model longitudinal action')
            # Common fixed oracle lateral path: all models have curvature 0.
            next_ego=step_ideal(ego,ModelAction(0.,accel),dt_s)
            next_lead=lead.step(ego.t,dt_s)
            gap=(next_lead.station_m-next_ego.x) if visible else None
            closing=next_ego.speed-next_lead.speed_mps
            trace.append({
                'step':k+1,'time_s':next_ego.t,
                'ego_station_m':next_ego.x,'ego_speed_mps':next_ego.speed,
                'lead_station_m':next_lead.station_m,'lead_speed_mps':next_lead.speed_mps,
                'lead_in_target_lane':visible,'gap_m':gap,
                'ttc_s':max(0.,gap)/closing if gap is not None and closing>1e-9 else None,
                'raw_model_accel_mps2':accel,'jerk_mps3':(accel-previous_accel)/dt_s,
                'road_camera_sha256':pair.road.sha256,
                'wide_camera_sha256':pair.wide.sha256,
            })
            previous_accel=accel
            ego=next_ego
            if progress is not None:
                progress(dict(status='STEP_COMMITTED',completed_rows=len(trace)))
            if stop_at_collision and gap is not None and gap<=0.:
                termination='LEAD_GAP_NONPOSITIVE'
                break
        except (LongitudinalContractError,ValueError,RuntimeError) as exc:
            failure=f'{type(exc).__name__}: {exc}'
            termination='RUNTIME_ERROR'
            break
    gaps=[r['gap_m'] for r in trace if r['gap_m'] is not None]
    min_ttc=min((row['ttc_s'] for row in trace if row['ttc_s'] is not None),default=None)
    stopped=next((index for index,row in enumerate(trace) if row['ego_speed_mps']==0.),None)
    restarted=next((row for row in trace[stopped+1:] if row['ego_speed_mps']>0.),None) if stopped is not None else None
    return {
        'classification':'NATIVE_METADRIVE_LEAD_ONNX_INPUT_NOT_PHOTOMETRICALLY_VALIDATED',
        'status':'DIAGNOSTIC_EXECUTED' if failure is None else 'FAILED_OR_INCOMPLETE',
        'error':failure,'scenario':scene.name,'termination':termination,
        'steps_requested':steps,'steps_completed':len(trace),
        'model_name':policy.name,'model_sha256':getattr(getattr(policy,'contract',None),'sha256',None),
        'model_scoring_allowed':False,'real_vehicle_testing':False,'cd210_used':False,
        'plant_used':False,'oracle_lateral_path':True,
        'minimum_synthetic_gap_m':min(gaps) if gaps else None,
        'minimum_ttc_s':min_ttc,
        'maximum_abs_jerk_mps3':max((abs(r['jerk_mps3']) for r in trace),default=None),
        'ego_first_stop_s':trace[stopped]['time_s'] if stopped is not None else None,
        'ego_first_restart_s':restarted['time_s'] if restarted is not None else None,
        'collision_observed':any(g<=0 for g in gaps),
        'trace':trace,
    }
