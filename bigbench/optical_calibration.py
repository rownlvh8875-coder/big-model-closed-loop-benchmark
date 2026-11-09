"""Reference pinhole projection for *virtual* narrow/wide road cameras.

Reference numeric constants are transcribed from commaai/openpilot:
  openpilot/common/transformations/camera.py  (1928x1208, focal 2648/567)
  openpilot/common/transformations/model.py   (medmodel 910/cy 47.6;
                                              sbigmodel 455/cy 151.8)

Matches the IDEAL, aligned, zero-distortion projection only.  It does *not*
validate actual comma optical distortion, exposure, camera mount, or real-road
model behavior.  No real vehicle interface is used or imported.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np

from .camera import RGBFrame
from .camera_rig import SchematicPair

NATIVE_SOURCE_WIDTH = 1928
NATIVE_SOURCE_HEIGHT = 1208
MODEL_WIDTH = 512
MODEL_HEIGHT = 256
ROAD_RAW_FOCAL_PX = 2648.0
WIDE_RAW_FOCAL_PX = 567.0
ROAD_MODEL_FOCAL_PX = 910.0
WIDE_MODEL_FOCAL_PX = 455.0
ROAD_MODEL_CY = 47.6
WIDE_MODEL_CY = (256.0 + ROAD_MODEL_CY) / 2.0


class OpticalContractError(ValueError):
    """A geometric or source-image precondition was not met."""


@dataclass(frozen=True)
class PinholeIntrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float

    def __post_init__(self) -> None:
        if (type(self.width) is not int or type(self.height) is not int or
                self.width <= 0 or self.height <= 0):
            raise OpticalContractError('camera width and height must be positive integers')
        if not all(math.isfinite(x) for x in (self.fx, self.fy, self.cx, self.cy)):
            raise OpticalContractError('camera intrinsics must be finite')
        if self.fx <= 0 or self.fy <= 0:
            raise OpticalContractError('camera focal lengths must be positive')

    @property
    def matrix(self) -> np.ndarray:
        return np.array([[self.fx, 0.0, self.cx],
                         [0.0, self.fy, self.cy],
                         [0.0, 0.0, 1.0]], dtype=np.float64)

    @property
    def fov_h_deg(self) -> float:
        return math.degrees(2.0 * math.atan(self.width / (2.0 * self.fx)))

    @property
    def fov_v_deg(self) -> float:
        return math.degrees(2.0 * math.atan(self.height / (2.0 * self.fy)))


def reference_source(kind: str, width: int = 964, height: int = 604) -> PinholeIntrinsics:
    """Reference comma pinhole sensor, optionally downsampled with equal x/y scale."""
    if kind not in ('road', 'wide'):
        raise OpticalContractError('kind must be road or wide')
    if width <= 0 or height <= 0 or width * NATIVE_SOURCE_HEIGHT != height * NATIVE_SOURCE_WIDTH:
        raise OpticalContractError('source resolution must preserve the native 1928x1208 aspect ratio')
    scale = width / NATIVE_SOURCE_WIDTH
    f_native = ROAD_RAW_FOCAL_PX if kind == 'road' else WIDE_RAW_FOCAL_PX
    return PinholeIntrinsics(width, height, f_native * scale, f_native * scale,
                             width / 2.0, height / 2.0)


def reference_model(kind: str) -> PinholeIntrinsics:
    if kind == 'road':
        return PinholeIntrinsics(MODEL_WIDTH, MODEL_HEIGHT,
                                 ROAD_MODEL_FOCAL_PX, ROAD_MODEL_FOCAL_PX,
                                 MODEL_WIDTH / 2.0, ROAD_MODEL_CY)
    if kind == 'wide':
        return PinholeIntrinsics(MODEL_WIDTH, MODEL_HEIGHT,
                                 WIDE_MODEL_FOCAL_PX, WIDE_MODEL_FOCAL_PX,
                                 MODEL_WIDTH / 2.0, WIDE_MODEL_CY)
    raise OpticalContractError('kind must be road or wide')


def destination_to_source_homography(source: PinholeIntrinsics,
                                     destination: PinholeIntrinsics) -> np.ndarray:
    """Aligned pinhole dest-pixel -> source-pixel warp, **not** a lens-distortion model.

    This is K_source * inverse(K_dest), the zero-calibration-rotation case
    of openpilot modeld.get_warp_matrix(). WARP_INVERSE_MAP is required in cv2.
    """
    return source.matrix @ np.linalg.inv(destination.matrix)


def transform_points(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    matrix = np.asarray(matrix, dtype=np.float64)
    if matrix.shape != (3, 3) or points.ndim != 2 or points.shape[1] != 2:
        raise OpticalContractError('expected 3x3 matrix and Nx2 points')
    if not np.isfinite(matrix).all() or not np.isfinite(points).all():
        raise OpticalContractError('nonfinite projection values')
    ph = np.column_stack((points, np.ones(len(points)))) @ matrix.T
    if np.any(np.abs(ph[:, 2]) < 1e-12):
        raise OpticalContractError('invalid projective depth')
    return ph[:, :2] / ph[:, 2, None]


def assert_intrinsics_match(actual: PinholeIntrinsics, expected: PinholeIntrinsics,
                            *, tolerance_fraction: float = 0.01) -> None:
    """Reject unexpected render-camera zoom/crop/film-offset instead of silently resizing."""
    if (actual.width, actual.height) != (expected.width, expected.height):
        raise OpticalContractError('rendered sensor resolution differs from reference')
    if not math.isfinite(tolerance_fraction) or not 0 < tolerance_fraction < 1:
        raise OpticalContractError('invalid focal tolerance')
    for attribute in ('fx', 'fy'):
        a, e = getattr(actual, attribute), getattr(expected, attribute)
        if abs(a - e) > abs(e) * tolerance_fraction:
            raise OpticalContractError(f'{attribute} differs from reference by more than tolerance')
    for attribute in ('cx', 'cy'):
        if abs(getattr(actual, attribute) - getattr(expected, attribute)) > 0.5:
            raise OpticalContractError(f'{attribute} principal point does not match reference')


def intrinsics_from_panda_lens(lens: Any, width: int, height: int) -> PinholeIntrinsics:
    """Read the *actual* Panda3D lens film geometry, not a presumed setFov value.

    Assumes a centered pinhole lens and top-left image array after vertical flip.
    Film offsets are disallowed until the sign/axis calibration is verified.
    """
    film = lens.getFilmSize()
    offset = lens.getFilmOffset()
    f = float(lens.getFocalLength())
    sx, sy = float(film[0]), float(film[1])
    if sx <= 0 or sy <= 0 or f <= 0:
        raise OpticalContractError('invalid Panda3D lens film geometry')
    if abs(float(offset[0])) > 1e-9 or abs(float(offset[1])) > 1e-9:
        raise OpticalContractError('nonzero film offset requires separately validated projection')
    return PinholeIntrinsics(width, height, f * width / sx, f * height / sy,
                             width / 2.0, height / 2.0)


@dataclass(frozen=True)
class CameraWarpAudit:
    camera: str
    reference_source: PinholeIntrinsics
    measured_source: PinholeIntrinsics
    model_target: PinholeIntrinsics
    fraction_valid_source_pixels: float
    warp_dst_to_src: tuple[tuple[float, ...], ...]
    evidence_class: str = 'VIRTUAL_PINHOLE_GEOMETRY_ONLY_NOT_CAMERA_FIDELITY'

    def to_dict(self) -> dict:
        return asdict(self)


class PinholeRectifier:
    """MetaDrive RGB source -> model-specific rectified 512x256 RGB canvas.

    Inputs MUST represent road and wide lenses, both at the same orientation.
    This adapter does not remove real fisheye distortion or model lens noise.
    """
    def __init__(self, *, source_width: int = 964, source_height: int = 604,
                 min_coverage: float = 0.99):
        self.expected = {name: reference_source(name, source_width, source_height)
                         for name in ('road', 'wide')}
        if not 0 < min_coverage <= 1:
            raise OpticalContractError('invalid coverage requirement')
        self.min_coverage = min_coverage

    def _rectify(self, name: str, raw: np.ndarray, intrinsics: PinholeIntrinsics) -> tuple[RGBFrame, CameraWarpAudit]:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError('camera rectification requires opencv-python-headless') from exc
        expected = self.expected[name]
        assert_intrinsics_match(intrinsics, expected)
        if (not isinstance(raw, np.ndarray) or raw.dtype != np.uint8 or
                raw.shape != (expected.height, expected.width, 3)):
            raise OpticalContractError(f'{name} requires uint8 RGB top-left [{expected.height},{expected.width},3]')
        target = reference_model(name)
        matrix = destination_to_source_homography(intrinsics, target)
        options = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP
        model_rgb = cv2.warpPerspective(raw, matrix, (target.width, target.height),
                                        flags=options, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
        coverage_mask = cv2.warpPerspective(
            np.full((expected.height, expected.width), 255, dtype=np.uint8),
            matrix, (target.width, target.height),
            flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP,
            borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        coverage = float(np.count_nonzero(coverage_mask == 255)) / coverage_mask.size
        if coverage < self.min_coverage:
            raise OpticalContractError(f'{name} warp source coverage {coverage:.5f} < {self.min_coverage:.5f}')
        data = np.ascontiguousarray(model_rgb, dtype=np.uint8)
        audit = CameraWarpAudit(name, expected, intrinsics, target, coverage,
                                 tuple(tuple(float(x) for x in row) for row in matrix))
        return RGBFrame(target.width, target.height, data.tobytes()), audit

    def rectify_pair(self, road_rgb: np.ndarray, wide_rgb: np.ndarray,
                     *, road_intrinsics: PinholeIntrinsics | None = None,
                     wide_intrinsics: PinholeIntrinsics | None = None) -> tuple[SchematicPair, dict[str, CameraWarpAudit]]:
        road, report_road = self._rectify('road', road_rgb, road_intrinsics or self.expected['road'])
        wide, report_wide = self._rectify('wide', wide_rgb, wide_intrinsics or self.expected['wide'])
        return SchematicPair(road, wide), {'road': report_road, 'wide': report_wide}
