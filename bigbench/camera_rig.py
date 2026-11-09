"""Schematic dual-view model input rig for integration tests only.

Separate views are generated from different virtual headings. This is NOT the
comma camera optics, intrinsic calibration, warp, exposure or visual domain.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from .camera import SchematicCamera, RGBFrame
from .kinematics import AgentState
from .scenario import Scenario


@dataclass(frozen=True)
class SchematicPair:
    road: RGBFrame
    wide: RGBFrame


class SchematicDualCamera:
    def __init__(self, width: int = 512, height: int = 256, wide_yaw_rad: float = 0.06):
        if (width, height) != (512, 256):
            raise ValueError('only tested model canvas size 512x256 is supported')
        self.renderer = SchematicCamera(width, height)
        self.wide_yaw_rad = wide_yaw_rad

    def render_pair(self, scenario: Scenario, state: AgentState, station: float) -> SchematicPair:
        road = self.renderer.render(scenario, state, station)
        wide = self.renderer.render(scenario, replace(state, heading=state.heading + self.wide_yaw_rad), station)
        return SchematicPair(road, wide)
