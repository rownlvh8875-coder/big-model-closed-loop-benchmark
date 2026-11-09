"""Vehicle-independent world-coordinate lane tracking truth (evaluation ONLY).

The model NEVER receives lane-truth objects through this module. A lane's
right-positive signed coordinate is derived from the MetaDrive lane interface,
not from a particular vehicle's steering, tyres, wheelbase or model setting.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from typing import Any


class LaneTruthError(ValueError):
    pass


def _finite(*args: float) -> None:
    if not all(math.isfinite(float(x)) for x in args):
        raise LaneTruthError('lane truth requires finite values')


def _wrap_angle(x: float) -> float:
    return math.atan2(math.sin(x), math.cos(x))


def lane_curvature(lane: Any, s: float, *, delta_m: float = .5) -> float:
    """Finite-difference native lane heading, signed 1/m, no vehicle model."""
    length = float(lane.length)
    _finite(length, s, delta_m)
    if length <= 0 or delta_m <= 0 or s < 0 or s > length:
        raise LaneTruthError('invalid curvature sampling position')
    a, b = max(0.0, s - delta_m), min(length, s + delta_m)
    if b <= a:
        raise LaneTruthError('no valid curvature interval')
    before, after = float(lane.heading_theta_at(a)), float(lane.heading_theta_at(b))
    _finite(before, after)
    return _wrap_angle(after - before) / (b - a)


@dataclass(frozen=True)
class LaneTruthSample:
    lane_id: str
    longitudinal_m: float
    signed_lateral_right_m: float
    lane_width_m: float
    curvature_1pm: float
    heading_error_rad: float
    virtual_agent_half_width_m: float
    left_edge_clearance_m: float
    right_edge_clearance_m: float
    intrusion_depth_m: float
    inside_turn_offset_m: float | None
    classification: str = 'SYNTHETIC_WORLD_TRUTH_ONLY'

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_native_lane_state(lane: Any, x_m: float, y_m: float, heading_rad: float, *,
                               half_width_m: float = .9) -> LaneTruthSample:
    """Geometric center/side error and footprint intrusion for a *virtual* agent.

    Assumes native MetaDrive `lane.local_coordinates` (positive right). The
    virtual footprint is a chosen geometric reference, NOT a Santa Fe dimension.
    The heading and curvature are not passed to the driving model from here.
    """
    _finite(x_m, y_m, heading_rad, half_width_m)
    if half_width_m <= 0 or half_width_m >= 4:
        raise LaneTruthError('virtual half-width out of benchmark bounds')
    length = float(lane.length)
    s, r = map(float, lane.local_coordinates((x_m, y_m)))
    _finite(length, s, r)
    # Don't silently treat a point far beyond the end of one link as belonging
    # to that link. The caller must explicitly switch to the actual next lane.
    if length <= 0 or s < 0 or s > length:
        raise LaneTruthError('ego longitudinal coordinate outside lane segment')
    width = float(lane.width_at(s))
    native_heading = float(lane.heading_theta_at(s))
    _finite(width, native_heading)
    if width <= 0:
        raise LaneTruthError('invalid native lane width')
    k = lane_curvature(lane, s)
    left_clear = width / 2 + r - half_width_m
    right_clear = width / 2 - r - half_width_m
    intrusion = max(0.0, -left_clear, -right_clear)
    inside = (-math.copysign(1.0, k) * r) if abs(k) > 1e-6 else None
    return LaneTruthSample(str(getattr(lane,'index','unknown')),s,r,width,k,
                           _wrap_angle(heading_rad - native_heading),half_width_m,
                           left_clear,right_clear,intrusion,inside)


def evaluate_closest_native_lane(lanes: list[Any], x_m: float, y_m: float,
                                 heading_rad: float, *, half_width_m: float = .9) -> LaneTruthSample:
    """Pick nearest *geometrically valid* native lane, not a recorded ego route."""
    accepted=[]
    for lane in lanes:
        try:
            obs = evaluate_native_lane_state(lane, x_m, y_m, heading_rad,
                                              half_width_m=half_width_m)
        except LaneTruthError:
            continue
        accepted.append(obs)
    if not accepted:
        raise LaneTruthError('no geometrically valid native lane for evaluation')
    return min(accepted,key=lambda v:(abs(v.signed_lateral_right_m),abs(v.heading_error_rad),v.lane_id))


def evaluate_target_lane_by_id(lanes: list[Any], target_lane_id: str,
                               x_m: float, y_m: float, heading_rad: float, *,
                               half_width_m: float = .9) -> LaneTruthSample:
    """Score a preselected native lane; NEVER switch to a closer ramp lane.

    Intended for fixed target-path benchmarks where nearest-lane selection
    could erase a genuine incursion at a ramp split or merge. Route changes
    must be explicitly supplied by a scenario-level target-lane timeline.
    """
    if not isinstance(target_lane_id, str) or not target_lane_id:
        raise LaneTruthError('explicit target lane identity is required')
    matches = [lane for lane in lanes
               if str(getattr(lane, 'index', 'unknown')) == target_lane_id]
    if len(matches) != 1:
        raise LaneTruthError('target lane is missing or ambiguous; nearest fallback forbidden')
    return evaluate_native_lane_state(matches[0], x_m, y_m, heading_rad,
                                      half_width_m=half_width_m)


def summarize_lane_truth(samples: list[LaneTruthSample], *, dt_s: float) -> dict:
    """Geometry-only lateral metric aggregation at a fixed virtual time grid.

    Segment/lane switches are allowed only if the caller explicitly supplied
    each sample's target lane. This routine never chooses a route or computes
    model scores from an unqualified camera.
    """
    _finite(dt_s)
    if dt_s <= 0 or not samples:
        raise LaneTruthError('samples and a positive time step are required')
    errors = [abs(p.signed_lateral_right_m) for p in samples]
    intrusions = [p.intrusion_depth_m for p in samples]
    for p in samples:
        _finite(p.signed_lateral_right_m, p.intrusion_depth_m)
        if p.intrusion_depth_m < 0:
            raise LaneTruthError('negative intrusion is invalid')
    import statistics
    intrusion_events = 0
    previously_intruding = False
    for v in intrusions:
        intruding = v > 1e-9
        if intruding and not previously_intruding:
            intrusion_events += 1
        previously_intruding = intruding
    sorted_errors = sorted(errors)
    percentile_index = (len(sorted_errors) - 1) * 0.90
    lo, hi = int(math.floor(percentile_index)), int(math.ceil(percentile_index))
    p90 = sorted_errors[lo] + (sorted_errors[hi] - sorted_errors[lo]) * (percentile_index - lo)
    return {
        'classification': 'SYNTHETIC_WORLD_TRUTH_ONLY_NOT_DRIVING_MODEL_SCORE',
        'frame_count': len(samples),
        'dt_s': dt_s,
        'absolute_lateral_error_mean_m': statistics.fmean(errors),
        'absolute_lateral_error_max_m': max(errors),
        'absolute_lateral_error_p90_m': p90,
        'intrusion_count': intrusion_events,
        'intrusion_duration_s': sum(v > 1e-9 for v in intrusions) * dt_s,
        'intrusion_depth_max_m': max(intrusions),
        'target_lane_ids': sorted({p.lane_id for p in samples}),
        'real_vehicle_testing': False,
    }
