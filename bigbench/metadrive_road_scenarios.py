"""MetaDrive map recipes for lane-pixel optical qualification, not driving scores.

The source IDs and parameters are verified against MetaDrive 0.4.3:
- Curve.ID == "C"; Curve consumes length, radius, angle, dir.
- InRampOnStraight.ID == "r".
- OutRampOnStraight.ID == "R".
- PGMap pg_map_file uses explicit block list with FirstPGBlock placeholder.
A scene name is only a CANDIDATE until the actual generated map is checked.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import atan2, cos, isfinite, sin
from typing import Any

SCENES = ("s_left_right", "s_right_left", "on_ramp", "off_ramp")


def scene_map_config(name: str) -> dict[str, Any]:
    """Build deterministic maps, with explicit S-curve turn directions.

    Ramp blocks use native MetaDrive topology rather than a synthetic overlay.
    Initial geometry is still unqualified until native rendering succeeds.
    """
    if name not in SCENES:
        raise ValueError(f"unknown MetaDrive optical scenario: {name}")
    if name in ("s_left_right", "s_right_left"):
        first, second = ((0, 1) if name == "s_left_right" else (1, 0))
        blocks = [
            {"id": "I", "pre_block_socket_index": 0},
            {"id": "C", "pre_block_socket_index": 0,
             "length": 35, "radius": 65, "angle": 32, "dir": first},
            {"id": "C", "pre_block_socket_index": 0,
             "length": 35, "radius": 65, "angle": 32, "dir": second},
        ]
        return {"type": "pg_map_file", "config": blocks,
                "lane_num": 2, "lane_width": 3.5, "exit_length": 45}
    symbol = "r" if name == "on_ramp" else "R"
    return {"type": "block_sequence", "config": symbol,
            "lane_num": 2, "lane_width": 3.5, "exit_length": 65}


def map_signatures(road_network: Any) -> dict[str, object]:
    """Get actual signed geometric bends, not map-name assumptions.

    Each circular segment has a tangent derivative and therefore a stable
    nonzero direction of signed curvature. Signed turns must be observed
    in the native map before the scenario is called an S-curve.
    """
    graph = getattr(road_network, "graph", None)
    if not isinstance(graph, dict):
        raise ValueError("native MetaDrive road_network.graph is required")
    curves = []
    total_lanes = 0
    for to_dict in graph.values():
        if not isinstance(to_dict, dict):
            continue
        for lanes in to_dict.values():
            if not lanes:
                continue
            total_lanes += len(lanes)
            lane = lanes[0]
            length = float(getattr(lane, "length", 0.0))
            if not isfinite(length) or length <= 2.0:
                continue
            if not hasattr(lane, "heading_theta_at"):
                continue
            heading_before = float(lane.heading_theta_at(0.1 * length))
            heading_after = float(lane.heading_theta_at(0.9 * length))
            change = atan2(sin(heading_after - heading_before),
                           cos(heading_after - heading_before))
            if abs(change) >= 0.02:
                curves.append({
                    "lane_index": str(getattr(lane, "index", "")),
                    "heading_delta_rad": change,
                    "sign": 1 if change > 0 else -1,
                })
    return {"lanes": total_lanes, "curves": curves,
            "positive_bends": sum(c["sign"] > 0 for c in curves),
            "negative_bends": sum(c["sign"] < 0 for c in curves),
            "has_opposing_bends": any(c["sign"] > 0 for c in curves) and
                                  any(c["sign"] < 0 for c in curves)}


def check_scene_topology(name: str, road_network: Any) -> dict[str, object]:
    if name not in SCENES:
        raise ValueError("unsupported optical scenario")
    observed = map_signatures(road_network)
    if name.startswith("s_"):
        valid = observed["has_opposing_bends"]
        why = ("both curvature signs found" if valid else
               "curve directions not independently established")
    else:
        # Ramp topology can contain branching lanes and lane merges. A
        # curvature count alone is not a proof of merge/diverge geometry.
        valid = False
        why = ("ramp map recipe generated; native branching topology and "
               "road-paint projection still require explicit inspection")
    return {"scenario": name,
            "topology_candidate_verified": valid,
            "status": "TOPOLOGY_GATE_PASS_ONLY" if valid else "UNQUALIFIED",
            "reason": why,
            "observed": observed}


def camera_pose_from_world(ego_xy: tuple[float, float],
                           heading_rad: float) -> tuple[float, float, float]:
    """Convert a chosen global (x,y,heading) to the existing provider local rig.

    NativeMetaDriveProvider currently reuses its vehicle.origin as a camera
    coordinate parent. Its virtual forward/lateral state is vehicle-origin
    relative, not absolute world coordinates; callers must account for that
    transform rather than simply plugging a global lane position into state.
    """
    if not all(isfinite(float(v)) for v in (*ego_xy, heading_rad)):
        raise ValueError("camera target pose is nonfinite")
    return float(ego_xy[0]), float(ego_xy[1]), float(heading_rad)
