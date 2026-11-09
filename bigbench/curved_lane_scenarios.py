"""Pure metadata for MetaDrive curves/ramps and testable geometry admission gates.

No on-road sources, actual vehicle dynamics, or Carrot controls participate.
All scenarios use real native MetaDrive block types. An invalid curve direction,
missing ramp block or absent circular path must fail, not score as a successful test.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math


@dataclass(frozen=True)
class CurveCase:
    name: str
    block_ids: tuple[str, ...]
    expected_curve_directions: tuple[int, ...] = ()

    def map_config(self) -> dict:
        if self.expected_curve_directions:
            # PGMap._config_generate uses its own saved-map form: initial I
            # followed by explicit ID, previous socket and ParameterSpace fields.
            blocks: list[dict[str, object]] = [{'id': 'I'}]
            for d in self.expected_curve_directions:
                blocks.append({'id': 'C', 'pre_block_socket_index': 0,
                               'length': 60.0, 'radius': 55.0,
                               'angle': 47.0, 'dir': d})
            return {'type': 'pg_map_file', 'config': blocks, 'lane_num': 2,
                    'lane_width': 3.5, 'exit_length': 60.0}
        if self.name == 'in_ramp':
            seq = 'r'
        elif self.name == 'out_ramp':
            seq = 'R'
        else:
            raise ValueError('unsupported scenario')
        return {'type': 'block_sequence', 'config': seq, 'lane_num': 2,
                'lane_width': 3.5, 'exit_length': 60.0}


SCENARIOS: dict[str, CurveCase] = {
    's_curve_left_right': CurveCase('s_curve_left_right', ('C', 'C'), (0, 1)),
    's_curve_right_left': CurveCase('s_curve_right_left', ('C', 'C'), (1, 0)),
    'in_ramp': CurveCase('in_ramp', ('r',)),
    'out_ramp': CurveCase('out_ramp', ('R',)),
}


class ScenarioGeometryError(ValueError):
    pass


def _positive_circular_lane(block: Any) -> Any:
    """Select the forward curve directly from the block's positive road.

    The inverse/opposing road is deliberately *not* used for determining the
    S-curve direction; otherwise one bend falsely appears bidirectional.
    """
    socket = block.pre_block_socket
    start = socket.positive_road.end_node
    candidates = block.block_network.graph.get(start, {})
    for lanes in candidates.values():
        circular = [lane for lane in lanes if float(getattr(lane, 'radius', 0)) > 0]
        if circular:
            return circular[-1]
    raise ScenarioGeometryError('Curve block has no forward circular lane')


def select_native_curve_lanes(current_map: Any, case: CurveCase) -> list[Any]:
    """Return testable native curve/ramp lane objects (never inferred from rendered RGB)."""
    blocks = list(current_map.blocks)
    chosen = [b for b in blocks if str(getattr(b, 'ID', '')) in case.block_ids]
    if len(chosen) != len(case.block_ids):
        raise ScenarioGeometryError(f'{case.name}: expected {case.block_ids}, found '
                                    f'{[getattr(b,"ID",None) for b in blocks]}')
    selected: list[Any] = []
    if case.expected_curve_directions:
        directions = tuple(int(b.get_config()['dir']) for b in chosen)
        if directions != case.expected_curve_directions:
            raise ScenarioGeometryError(f'{case.name}: generated turn directions {directions} do not match '
                                        f'{case.expected_curve_directions}')
        for block in chosen:
            selected.append(_positive_circular_lane(block))
        signed = [int(math.copysign(1, float(getattr(l, 'direction')))) for l in selected]
        if len(set(signed)) != 2:
            raise ScenarioGeometryError(f'{case.name}: no forward-curve curvature sign reversal: {signed}')
    else:
        # Ramp has separate merging/diverging circular branches not necessarily
        # connected to the *mainline* positive socket. Look only inside the ramp
        # block and prefer explicit low-speed ramp branches.
        block = chosen[0]
        all_lanes = []
        for to_dict in block.block_network.graph.values():
            for lanes in to_dict.values():
                for lane in lanes:
                    if float(getattr(lane, 'radius', 0)) > 0 and float(getattr(lane, 'length', 0)) > 2.5:
                        all_lanes.append(lane)
        all_lanes.sort(key=lambda l: (float(getattr(l,'speed_limit', 1000)) >= 20,
                                      -float(getattr(l,'length', 0))))
        unique = {}
        for l in all_lanes:
            unique.setdefault(str(getattr(l, 'index', id(l))), l)
        selected = list(unique.values())[:2]
        if not selected:
            raise ScenarioGeometryError(f'{case.name}: actual ramp block has no circular ramp-road geometry')
    return selected


def world_camera_pose(lane: Any, fraction: float, *, height_m: float = 1.22) -> tuple[float, float, float, float]:
    """(world x,y,z, camera Panda H deg) for route-forward camera on lane."""
    if not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError('invalid lane sample fraction')
    if not math.isfinite(height_m) or not 0.25 <= height_m <= 4:
        raise ValueError('invalid synthetic camera height')
    s = float(lane.length) * fraction
    xy = lane.position(s, 0)
    theta = float(lane.heading_theta_at(s))
    coords = (float(xy[0]), float(xy[1]), float(height_m),
              math.degrees(theta) - 90.0)  # MetaDrive +x driving; Panda camera +y forward
    if not all(math.isfinite(v) for v in coords):
        raise ScenarioGeometryError('nonfinite native lane pose')
    return coords
