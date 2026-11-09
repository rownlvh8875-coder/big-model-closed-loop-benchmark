"""Deterministic synthetic longitudinal world/evaluator, not a driving model score.

The ego follows a single *oracle lateral path*, so model steering is excluded.
No actual vehicle dynamics, CAN, CD210 or Carrot controller can be loaded.
This module tests scenario arithmetic only: synthetic actor images and genuine
big-ONNX longitudinal inference still require separate integration.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


class LongitudinalContractError(ValueError):
    pass


@dataclass(frozen=True)
class LeadEvent:
    time_s: float
    acceleration_mps2: float

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.time_s,self.acceleration_mps2)) or self.time_s < 0:
            raise LongitudinalContractError('nonfinite or negative lead event time')


@dataclass(frozen=True)
class LongitudinalScenario:
    name: str
    ego_speed_mps: float
    lead_speed_mps: float
    initial_gap_m: float
    lead_events: tuple[LeadEvent,...]
    merge_at_s: float | None = None

    def __post_init__(self):
        if self.name not in {'lead_brake','stop_go','cut_in'}:
            raise LongitudinalContractError('unknown predefined synthetic scenario')
        vals=(self.ego_speed_mps,self.lead_speed_mps,self.initial_gap_m)
        if not all(math.isfinite(x) for x in vals) or min(vals)<0 or self.initial_gap_m<=0:
            raise LongitudinalContractError('invalid scenario state')
        times=[x.time_s for x in self.lead_events]
        if times!=sorted(set(times)):
            raise LongitudinalContractError('events must be time-ordered and unique')
        if self.merge_at_s is not None and (not math.isfinite(self.merge_at_s) or self.merge_at_s<=0):
            raise LongitudinalContractError('invalid cut-in time')


def scenario(name: str) -> LongitudinalScenario:
    if name=='lead_brake':
        return LongitudinalScenario(name,14,14,34,(LeadEvent(0,0),LeadEvent(1,-3)))
    if name=='stop_go':
        return LongitudinalScenario(name,10,10,27,
                                    (LeadEvent(0,0),LeadEvent(.5,-4),LeadEvent(4,0),LeadEvent(6,2)))
    if name=='cut_in':
        return LongitudinalScenario(name,14,12,24,(LeadEvent(0,0),LeadEvent(3,-2)),2.0)
    raise LongitudinalContractError('unknown scenario')


def _integrate_nonnegative(x: float,v: float,a: float,dt: float) -> tuple[float,float]:
    if not all(math.isfinite(y) for y in (x,v,a,dt)) or v<0 or dt<=0:
        raise LongitudinalContractError('invalid deterministic actor integration')
    moving=min(dt,-v/a) if a<0 else dt
    return x + max(0.,v*moving+.5*a*moving*moving),max(0.,v+a*dt)


def run_longitudinal_actions(scene: LongitudinalScenario, accelerations: list[float], *,
                             dt_s: float=.05, max_abs_accel: float=10) -> dict:
    """Evaluate an explicit acceleration trace, not camera inference.

    Returns a proxy metric receipt. The record is **not** an authorized model
    benchmark unless a future separately tested camera-actor integration
    establishes genuine closed-loop model inputs.
    """
    if not math.isfinite(dt_s) or dt_s<=0 or dt_s>.1 or not accelerations:
        raise LongitudinalContractError('invalid time step or empty acceleration sequence')
    if len(accelerations)>20000 or not math.isfinite(max_abs_accel) or max_abs_accel<=0:
        raise LongitudinalContractError('unsafe synthetic scenario bounds')
    lead_x=scene.initial_gap_m
    lead_v=scene.lead_speed_mps
    ego_x=0.
    ego_v=scene.ego_speed_mps
    rows=[]
    events=scene.lead_events
    previous_a=0.
    for i,a in enumerate(accelerations):
        t=i*dt_s
        if not math.isfinite(a) or abs(a)>max_abs_accel:
            raise LongitudinalContractError('invalid ego acceleration command: no silent clamp')
        lead_a=events[0].acceleration_mps2 if events else 0.
        for event in events:
            if event.time_s<=t+1e-10:
                lead_a=event.acceleration_mps2
        lead_x,lead_v=_integrate_nonnegative(lead_x,lead_v,lead_a,dt_s)
        ego_x,ego_v=_integrate_nonnegative(ego_x,ego_v,a,dt_s)
        present=scene.merge_at_s is None or t>=scene.merge_at_s
        gap=lead_x-ego_x if present else None
        closing=ego_v-lead_v
        ttc=(max(0,gap)/closing if gap is not None and closing>1e-9 else None)
        rows.append({
            't_s':round(t+dt_s,9),'ego_station_m':ego_x,'ego_speed_mps':ego_v,
            'lead_station_m':lead_x,'lead_speed_mps':lead_v,'lead_visible':present,
            'gap_m':gap,'time_to_collision_s':ttc,
            'desired_acceleration_mps2':a,'longitudinal_jerk_mps3':(a-previous_a)/dt_s,
            'collision':gap is not None and gap<=0,
        })
        previous_a=a
    active=[r for r in rows if r['gap_m'] is not None]
    return {
        'scenario':scene.name,'status':'SYNTHETIC_LONGITUDINAL_METRIC_DIAGNOSTIC',
        'model_scoring_allowed':False,'real_vehicle_testing':False,'cd210_fallback':False,
        'sample_count':len(rows),'duration_s':len(rows)*dt_s,
        'minimum_gap_m':min((r['gap_m'] for r in active),default=None),
        'minimum_ttc_s':min((r['time_to_collision_s'] for r in active
                             if r['time_to_collision_s'] is not None),default=None),
        'collision_frames':sum(r['collision'] for r in rows),
        'max_abs_jerk_mps3':max(abs(r['longitudinal_jerk_mps3']) for r in rows),
        'final_ego_speed_mps':rows[-1]['ego_speed_mps'],
        'rows':rows,
    }
