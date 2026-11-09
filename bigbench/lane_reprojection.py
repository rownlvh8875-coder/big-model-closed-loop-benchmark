"""Independent lane-world geometry to rendered camera pixel comparison.

This module is an offline, vehicle-independent optical test. It obtains *real*
MetaDrive lane boundary geometry, projects it using Panda3D camera transforms,
then searches the rendered RGB image for the physical lane paint. Image evidence
is separate from world geometry; simply drawing an overlay is NOT a pass.

It does not certify any real comma device/lens or a driving model's performance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

import cv2
import numpy as np

from .camera import RGBFrame
from .optical_calibration import (
    OpticalContractError, destination_to_source_homography,
    reference_model, transform_points,
)


@dataclass(frozen=True)
class BoundaryLandmark:
    road_id: str
    lane_id: int
    side: str
    paint_color: str
    type_name: str
    longitudinal_m: float
    world_x_m: float
    world_y_m: float
    world_z_m: float = 0.018

    def to_dict(self) -> dict:
        return asdict(self)


def lane_boundary_landmarks(
        lanes: Iterable[Any], ego_xy: tuple[float, float], *,
        distances_m: tuple[float, ...] = (6, 8, 10, 12, 14, 16, 18, 21, 24, 28, 32, 38, 44, 50),
        include_broken: bool = True) -> list[BoundaryLandmark]:
    """Use MetaDrive's *actual painted* sides; do not synthesize a lane centerline.

    PGBlock.create_in_world draws left line for every lane, right line only
    for the outermost lane. For broken paint, the simulator draws the even
    2-metre polyline segments; sample near their midpoints, not in the gaps.
    """
    lanes = tuple(lanes)
    if not lanes:
        raise OpticalContractError('no MetaDrive lane geometry is available')
    from metadrive.constants import PGLineColor, PGLineType  # optional dependency
    marks: list[BoundaryLandmark] = []
    for idx, lane in enumerate(lanes):
        if not hasattr(lane, 'position') or not hasattr(lane, 'width_at') or not hasattr(lane, 'local_coordinates'):
            raise OpticalContractError('MetaDrive lane API does not expose geometric boundaries')
        anchor_s, _ = lane.local_coordinates(ego_xy)
        length = float(lane.length)
        for side_idx, (side, direction) in enumerate((('left', -1), ('right', 1))):
            if side_idx == 1 and idx != len(lanes) - 1:
                continue  # MetaDrive PGBlock doesn't paint this redundant boundary
            kind = lane.line_types[side_idx]
            if kind == PGLineType.NONE or kind == PGLineType.GUARDRAIL:
                continue
            if kind == PGLineType.BROKEN and not include_broken:
                continue
            if kind not in (PGLineType.SIDE, PGLineType.CONTINUOUS, PGLineType.BROKEN):
                raise OpticalContractError('unknown MetaDrive lane-line paint type')
            color = 'yellow' if tuple(lane.line_colors[side_idx]) == tuple(PGLineColor.YELLOW) else 'white'
            for distance in distances_m:
                s = float(anchor_s) + float(distance)
                if not (0.5 < s < length - 0.5):
                    continue
                if kind == PGLineType.BROKEN and (s % 4.0) > 1.65:
                    continue
                width = float(lane.width_at(s))
                xy = np.asarray(lane.position(s, direction * width * .5), dtype=float)
                if xy.shape != (2,) or not np.isfinite(xy).all() or width <= 0:
                    raise OpticalContractError('invalid MetaDrive lane position/width')
                marks.append(BoundaryLandmark(
                    road_id=str(getattr(lane, 'index', 'unknown')), lane_id=idx,
                    side=side, paint_color=color, type_name=str(kind),
                    longitudinal_m=s, world_x_m=float(xy[0]), world_y_m=float(xy[1]),
                ))
    if not marks:
        raise OpticalContractError('no paintable lane boundaries within sampled road interval')
    return marks



def map_boundary_landmarks(road_network: Any, ego_xy: tuple[float, float], *,
                           max_radius_m: float = 85.0, sample_step_m: float = 2.0,
                           max_markings: int = 2000) -> list[BoundaryLandmark]:
    """Collect painted 3D boundaries from ALL connected MetaDrive road blocks.

    Spawn/current_ref_lanes can refer to a very short entry/exit segment whose
    markers aren't actually visible. A camera may look ahead into subsequent
    blocks; we must sample the underlying native road-network graph, not rely on
    only one navigation reference segment.
    """
    if not (math.isfinite(max_radius_m) and 10 <= max_radius_m <= 150 and
            math.isfinite(sample_step_m) and .5 <= sample_step_m <= 5):
        raise ValueError('invalid map ground-truth sampling bounds')
    if not hasattr(road_network, 'graph') or not isinstance(road_network.graph, dict):
        raise OpticalContractError('expected native MetaDrive NodeRoadNetwork graph')
    points: list[BoundaryLandmark] = []
    for to_dict in road_network.graph.values():
        if not isinstance(to_dict, dict):
            continue
        for lanes in to_dict.values():
            lanes=tuple(l for l in lanes if hasattr(l, 'line_types') and hasattr(l, 'line_colors'))
            if not lanes:
                continue
            ref=lanes[0]
            length=float(ref.length)
            if not math.isfinite(length) or not 0 < length <= 10000:
                continue
            base=float(ref.local_coordinates(ego_xy)[0])
            # Include all longitudinal positions; then filter out remote points.
            absolute=np.arange(1.0,length-0.5,sample_step_m,dtype=float)
            distances=tuple(float(s-base) for s in absolute)
            if not distances:
                continue
            try:
                sample=lane_boundary_landmarks(lanes,ego_xy,distances_m=distances)
            except OpticalContractError as exc:
                if 'no paintable lane boundaries' in str(exc):
                    continue
                raise
            for mark in sample:
                if math.hypot(mark.world_x_m-ego_xy[0],mark.world_y_m-ego_xy[1])<=max_radius_m:
                    points.append(mark)
                    if len(points)>max_markings:
                        raise OpticalContractError('native lane data unexpectedly exceeds bounded audit')
    if not points:
        raise OpticalContractError('no painted road-network lane coordinates near virtual camera')
    return points

def project_panda_camera_points(
        camera: Any, origin: Any, points: list[BoundaryLandmark],
        width: int, height: int, source_intrinsics: Any, model_intrinsics: Any,
        *, near_m: float = 0.15) -> list[dict]:
    """Project MetaDrive WORLD (x,y,z) via the *actual* Panda scene transform.

    Panda3D camera local +Y is forward; X right and Z up. The lane position
    is in MetaDrive world coordinates, identical to Panda world coordinates
    in current MetaDrive; NO hard-coded 90-degree axis exchange is performed.
    """
    from panda3d.core import Point3  # optional dependency
    h = np.linalg.inv(destination_to_source_homography(source_intrinsics, model_intrinsics))
    out = []
    for point in points:
        cam = camera.getRelativePoint(origin, Point3(point.world_x_m, point.world_y_m, point.world_z_m))
        xyz = [float(cam.x), float(cam.y), float(cam.z)]
        if not np.isfinite(xyz).all() or xyz[1] <= near_m:
            continue
        u_src = source_intrinsics.cx + source_intrinsics.fx * xyz[0] / xyz[1]
        v_src = source_intrinsics.cy - source_intrinsics.fy * xyz[2] / xyz[1]
        u, v = transform_points(h, np.array([[u_src, v_src]]))[0]
        if (not (0 <= u_src < width and 0 <= v_src < height) or
                not (5 <= u < model_intrinsics.width - 5 and
                     max(20, model_intrinsics.cy + 2) <= v < model_intrinsics.height - 5)):
            continue
        out.append({**point.to_dict(), 'source_uv': [u_src, v_src],
                    'model_uv': [float(u), float(v)], 'camera_depth_m': xyz[1]})
    return out


def _paint_mask(frame: RGBFrame, *, min_luma: float = 120) -> tuple[np.ndarray, np.ndarray]:
    """Image-only segmentation, independent from projected 3D lane coordinates."""
    raw = np.frombuffer(frame.rgb, dtype=np.uint8)
    if raw.size != frame.width * frame.height * 3:
        raise OpticalContractError('invalid RGB camera frame length')
    img = raw.reshape((frame.height, frame.width, 3)).astype(np.float32)
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    lum = .299 * r + .587 * g + .114 * b
    sat = np.max(img, axis=2) - np.min(img, axis=2)
    # White/grey paint is relatively light and achromatic. Yellow is warm.
    white = (lum >= min_luma) & (sat <= 48) & (np.min(img, axis=2) >= 98)
    yellow = (r >= 110) & (g >= 80) & (b <= np.minimum(r, g) * .70) & ((r - b) >= 55)
    return white, yellow


def evaluate_visible_lane_paint(frame: RGBFrame, projected: list[dict], *,
                                search_radius_px: int = 12, row_radius_px: int = 2) -> dict:
    """Measure 2D residual to *observed* paint; missing/ambiguous is not PASS.

    For each predicted marking find the closest relevant-colored RGB pixel in a
    narrow horizontal image strip. Do not use a rendered line overlay as
    evidence. Background/curb false positives remain possible; diagnostic only.
    """
    if not 1 <= search_radius_px <= 40 or not 0 <= row_radius_px <= 6:
        raise ValueError('invalid paint search windows')
    white, yellow = _paint_mask(frame)
    measured=[]
    for p in projected:
        u, v = p['model_uv']
        x, y = int(round(u)), int(round(v))
        if not (row_radius_px <= y < frame.height-row_radius_px and 0 <= x < frame.width):
            continue
        lo, hi = max(0, x-search_radius_px), min(frame.width, x+search_radius_px+1)
        mask = yellow if p['paint_color']=='yellow' else white
        yy, xx = np.nonzero(mask[y-row_radius_px:y+row_radius_px+1, lo:hi])
        item = dict(p)
        if xx.size:
            dx = (xx.astype(float)+lo-u)
            dy = (yy.astype(float)+y-row_radius_px-v)
            idx = int(np.argmin(dx*dx+dy*dy))
            item['observed_uv'] = [float(xx[idx]+lo), float(yy[idx]+y-row_radius_px)]
            item['pixel_error_px'] = float(np.hypot(dx[idx],dy[idx]))
            item['horizontal_error_px'] = float(dx[idx])
        else:
            item['observed_uv']=None
            item['pixel_error_px']=None
            item['horizontal_error_px']=None
        measured.append(item)
    errors = [p['pixel_error_px'] for p in measured if p['pixel_error_px'] is not None]
    # Factual readout plus a conservative diagnostic classification; no performance score.
    return {'total_visible_candidates': len(measured), 'matched_count': len(errors),
            'matched_fraction': len(errors)/len(measured) if measured else 0.0,
            'median_pixel_error_px': float(np.median(errors)) if errors else None,
            'p90_pixel_error_px': float(np.percentile(errors,90)) if errors else None,
            'classification': ('LANE_PIXEL_MEASUREMENT_AVAILABLE' if len(errors)>=5
                               else 'INSUFFICIENT_OBSERVED_LANE_PAINT'),
            'points': measured}


def draw_lane_alignment(frame: RGBFrame, result: dict) -> RGBFrame:
    """Overlay geometry predictions (red) and independent pixel detections (green)."""
    img=np.frombuffer(frame.rgb,dtype=np.uint8).reshape(frame.height,frame.width,3).copy()
    for row in result['points']:
        x,y=map(lambda z:int(round(z)),row['model_uv'])
        cv2.circle(img,(x,y),3,(255,60,60),1,cv2.LINE_AA)
        if row['observed_uv'] is not None:
            ox,oy=map(lambda z:int(round(z)),row['observed_uv'])
            cv2.line(img,(x,y),(ox,oy),(255,220,0),1,cv2.LINE_AA)
            cv2.circle(img,(ox,oy),2,(30,255,50),-1,cv2.LINE_AA)
    return RGBFrame(frame.width,frame.height,img.tobytes())
