"""Ideal planar motion, deliberately independent of all vehicle-specific plants."""
from __future__ import annotations
from dataclasses import dataclass
from math import cos, sin, isfinite


@dataclass(frozen=True)
class AgentState:
    t: float
    x: float
    y: float
    heading: float
    speed: float


@dataclass(frozen=True)
class ModelAction:
    curvature_1pm: float
    acceleration_mps2: float


def step_ideal(state: AgentState, action: ModelAction, dt: float, *,
               speed_override: float | None = None) -> AgentState:
    """Integrate yaw_rate = v * curvature; no wheelbase, mass or actuator model."""
    nums = (state.t, state.x, state.y, state.heading, state.speed,
            action.curvature_1pm, action.acceleration_mps2, dt)
    if not all(isfinite(v) for v in nums) or dt <= 0:
        raise ValueError('nonfinite state, action, or invalid dt')
    if state.speed < 0:
        raise ValueError('speed must be nonnegative')
    if speed_override is not None:
        if not isfinite(speed_override) or speed_override < 0:
            raise ValueError('invalid common speed override')
        next_speed = speed_override
        distance = speed_override * dt
    else:
        acceleration = action.acceleration_mps2
        moving_dt = min(dt, -state.speed / acceleration) if acceleration < 0 else dt
        distance = max(0.0, state.speed * moving_dt + 0.5 * acceleration * moving_dt**2)
        next_speed = max(0.0, state.speed + acceleration * dt)
    # Curvature is geometric d(heading)/ds; integrate by path distance.
    next_heading = state.heading + action.curvature_1pm * distance
    mid_heading = (state.heading + next_heading) * 0.5
    return AgentState(state.t + dt,
                      state.x + cos(mid_heading) * distance,
                      state.y + sin(mid_heading) * distance,
                      next_heading, next_speed)
