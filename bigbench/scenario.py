"""Publicly reproducible synthetic scenarios only; no real route identifiers."""
from __future__ import annotations
from dataclasses import dataclass
from .geometry import CurveSection, Centerline


@dataclass(frozen=True)
class LeadActor:
    start_station_m: float
    speed_mps: float
    braking_at_s: float = float('inf')
    braking_accel_mps2: float = 0.0

    def station(self, t: float) -> float:
        if t < self.braking_at_s:
            return self.start_station_m + self.speed_mps * t
        elapsed = t - self.braking_at_s
        v0 = self.speed_mps
        if self.braking_accel_mps2 >= 0:
            return self.start_station_m + v0 * t + 0.5 * self.braking_accel_mps2 * elapsed**2
        stop_time = -v0 / self.braking_accel_mps2
        use_dt = min(elapsed, stop_time)
        return self.start_station_m + v0 * self.braking_at_s + v0 * use_dt + 0.5 * self.braking_accel_mps2 * use_dt**2


@dataclass(frozen=True)
class Scenario:
    name: str
    road: Centerline
    lane_width_m: float
    duration_s: float
    initial_speed_mps: float
    lead: LeadActor | None = None


def get_scenario(name: str) -> Scenario:
    straight = CurveSection(80, 0, 0)
    after = CurveSection(200, 0, 0)
    if name == 's_curve':
        sections = (straight, CurveSection(35, 0, 0.012), CurveSection(70, 0.012, -0.012),
                    CurveSection(35, -0.012, 0), after)
        return Scenario(name, Centerline(sections), 3.4, 16.0, 15.0)
    if name == 'ramp_right':
        sections = (CurveSection(50, 0, 0), CurveSection(35, 0, -0.02),
                    CurveSection(65, -0.02, -0.02), CurveSection(35, -0.02, 0),
                    CurveSection(190, 0, 0))
        return Scenario(name, Centerline(sections), 3.3, 14.0, 13.0)
    if name == 'ramp_left':
        sections = (CurveSection(50, 0, 0), CurveSection(35, 0, 0.02),
                    CurveSection(65, 0.02, 0.02), CurveSection(35, 0.02, 0),
                    CurveSection(190, 0, 0))
        return Scenario(name, Centerline(sections), 3.3, 14.0, 13.0)
    if name == 'straight':
        return Scenario(name, Centerline((CurveSection(450, 0, 0),)), 3.6, 15.0, 15.0)
    if name == 'lead_brake':
        return Scenario(name, Centerline((CurveSection(500, 0, 0),)), 3.6, 14.0, 14.0,
                        LeadActor(start_station_m=75.0, speed_mps=11.0,
                                  braking_at_s=3.0, braking_accel_mps2=-2.0))
    raise ValueError(f'unknown synthetic scenario: {name}')


SCENARIOS = ('straight', 's_curve', 'ramp_left', 'ramp_right', 'lead_brake')
