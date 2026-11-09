"""Exact six-channel I420 channel packing, but NOT real camera calibration.

Packing follows carrot-wip compile_modeld.frames_to_tensor.  Image capture,
optical warp, distortion, and exposure must be independently validated before
these tensors can be used to make claims about driving performance.
"""
from __future__ import annotations

import numpy as np
from .camera import RGBFrame

MODEL_WIDTH = 512
MODEL_HEIGHT = 256


def i420_planes_to_six(y: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Y [H,W], U/V [H/2,W/2] -> six uint8 planes [6,H/2,W/2]."""
    if (y.ndim != 2 or y.shape[0] % 2 or y.shape[1] % 2 or
            u.shape != (y.shape[0] // 2, y.shape[1] // 2) or v.shape != u.shape):
        raise ValueError('I420 plane dimensions are inconsistent')
    if any(p.dtype != np.uint8 for p in (y, u, v)):
        raise ValueError('expected uint8 I420 planes')
    return np.ascontiguousarray(np.stack((y[0::2, 0::2], y[1::2, 0::2],
                                           y[0::2, 1::2], y[1::2, 1::2], u, v)))


def rgb_frame_to_six(frame: RGBFrame) -> np.ndarray:
    """Convert an already rectified 512x256 RGB model canvas into 6 YUV planes.

    NO silent resize or geometric warp. The provided RGB canvas must already be
    rendered in the intended model camera frame; this is not guaranteed by the
    schematic renderer.
    """
    if (frame.width, frame.height) != (MODEL_WIDTH, MODEL_HEIGHT):
        raise ValueError(f'model RGB canvas must be {MODEL_WIDTH}x{MODEL_HEIGHT}, got '
                         f'{frame.width}x{frame.height}; arbitrary resizing prohibited')
    if len(frame.rgb) != MODEL_WIDTH * MODEL_HEIGHT * 3:
        raise ValueError('RGB frame byte count mismatch')
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError('image conversion requires opencv-python-headless') from exc
    rgb = np.frombuffer(frame.rgb, dtype=np.uint8).reshape(MODEL_HEIGHT, MODEL_WIDTH, 3)
    i420 = cv2.cvtColor(rgb, cv2.COLOR_RGB2YUV_I420)
    y = i420[:MODEL_HEIGHT].reshape(MODEL_HEIGHT, MODEL_WIDTH)
    u = i420[MODEL_HEIGHT:MODEL_HEIGHT+MODEL_HEIGHT//4].reshape(MODEL_HEIGHT//2, MODEL_WIDTH//2)
    v = i420[MODEL_HEIGHT+MODEL_HEIGHT//4:].reshape(MODEL_HEIGHT//2, MODEL_WIDTH//2)
    return i420_planes_to_six(y, u, v)


def camera_pair_to_model(road: RGBFrame, wide: RGBFrame) -> np.ndarray:
    """Return 2x6x128x256 [road, wide] uint8 tensor; no implicit camera duplication."""
    return np.ascontiguousarray(np.stack((rgb_frame_to_six(road), rgb_frame_to_six(wide))))
