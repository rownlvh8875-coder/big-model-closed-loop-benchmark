"""Explicit geometric proxy metrics, not evidence of real-road safety."""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class FrameMetric:
    t_s: float
    station_m: float
    speed_mps: float
    lateral_error_m: float
    inward_error_m: float
    curvature_1pm: float
    desired_curvature_1pm: float
    desired_accel_mps2: float
    lead_distance_m: float | None
    lane_intrusion_m: float
    camera_sha256: str


def summarize(frames: list[FrameMetric], dt_s: float) -> dict[str, float | int | None]:
    if not frames:
        raise ValueError('metrics require at least one frame')
    intrusions = [v.lane_intrusion_m for v in frames]
    errors = [v.lateral_error_m for v in frames]
    inward = [v.inward_error_m for v in frames]
    lead = [v.lead_distance_m for v in frames if v.lead_distance_m is not None]
    return {
        'frames': len(frames),
        'duration_s': round(len(frames) * dt_s, 5),
        'max_abs_lateral_error_m': max(abs(x) for x in errors),
        'rms_lateral_error_m': sqrt(sum(x*x for x in errors) / len(errors)),
        'max_inward_error_m': max(inward),
        'lane_intrusion_frames': sum(x > 0 for x in intrusions),
        'lane_intrusion_duration_s': sum(x > 0 for x in intrusions) * dt_s,
        'max_lane_intrusion_m': max(intrusions),
        'min_lead_gap_m': min(lead) if lead else None,
        'distinct_camera_frames': len(set(x.camera_sha256 for x in frames)),
        'end_station_m': frames[-1].station_m,
    }
