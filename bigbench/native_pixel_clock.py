"""Exact pixel-space receipts for native simulator diagnostics (SIM ONLY).

Pure post-capture analysis: no Panda3D imports, rendering calls, thresholds,
image alteration, optical calibration assumptions, or model performance scores.
Image coordinates are zero-based (x=column, y=row), top-left origin.
"""
from __future__ import annotations

from hashlib import sha256

import numpy as np


def rgb_delta(first: np.ndarray, second: np.ndarray, *, examples: int = 12) -> dict:
    """Describe every changed uint8 RGB pixel, preserving actual values.

    This does not mask/filter image changes. Example coordinates are only
    a readable sample; changed_pixels and bounding box include ALL changes.
    """
    if (not isinstance(first, np.ndarray) or not isinstance(second, np.ndarray)
            or first.shape != second.shape or first.ndim != 3
            or first.shape[2] != 3 or first.dtype != np.uint8
            or second.dtype != np.uint8 or first.size == 0):
        raise ValueError("same-shape nonempty [H,W,3] uint8 RGB required")
    if type(examples) is not int or not 0 <= examples <= 24:
        raise ValueError("bounded example count required")
    a = np.ascontiguousarray(first)
    b = np.ascontiguousarray(second)
    difference = np.abs(a.astype(np.int16) - b.astype(np.int16))
    mask = np.any(difference != 0, axis=2)
    yy, xx = np.nonzero(mask)
    n = int(yy.size)
    samples = [
        {
            "x": int(xx[k]), "y": int(yy[k]),
            "first_rgb": [int(v) for v in a[yy[k], xx[k]]],
            "second_rgb": [int(v) for v in b[yy[k], xx[k]]],
        }
        for k in range(min(n, examples))
    ]
    return {
        "first_sha256": sha256(a.tobytes()).hexdigest(),
        "second_sha256": sha256(b.tobytes()).hexdigest(),
        "identical": bool(n == 0),
        "changed_pixels": n,
        "changed_pixel_fraction": float(n / mask.size),
        "changed_channel_values": int(np.count_nonzero(difference)),
        "max_channel_delta": int(difference.max()),
        "bounding_box_xyxy_inclusive": (
            [int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())]
            if n else None
        ),
        "first_changed_pixel_xy": [int(xx[0]), int(yy[0])] if n else None,
        "changed_rows_count": int(np.unique(yy).size),
        "changed_columns_count": int(np.unique(xx).size),
        "changed_pixel_examples": samples,
        "source_coordinate_convention": "top-left 0-based x-column y-row",
    }


def rgb_sequence(frames: list[np.ndarray], *, warmup: int = 2) -> dict:
    if (not isinstance(frames, list) or len(frames) < 3 or
            type(warmup) is not int or not 0 <= warmup <= len(frames) - 2):
        raise ValueError("bounded sequence/warmup needs at least two later frames")
    base = np.array(frames[warmup], copy=True, order="C")
    all_sha = [sha256(np.ascontiguousarray(x).tobytes()).hexdigest() for x in frames]
    per_frame = [rgb_delta(base, x) for x in frames[warmup:]]
    first_diverge = next(
        (warmup + i for i, v in enumerate(per_frame) if not v["identical"]), None
    )
    return {
        "all_frame_sha256": all_sha,
        "all_unique_sha256": len(set(all_sha)),
        "warmup_frames_separated_not_discarded": warmup,
        "post_warmup_unique_sha256": len(set(all_sha[warmup:])),
        "bit_exact_after_warmup": len(set(all_sha[warmup:])) == 1,
        "max_changed_pixels_post_warmup": max(x["changed_pixels"] for x in per_frame),
        "first_divergence_frame_index_zero_based": first_diverge,
        "per_frame_vs_first_post_warmup": per_frame,
    }


def packed_i420_delta(a: np.ndarray, b: np.ndarray) -> dict:
    """Compare exact model-ready uint8 [2,6,128,256] tensor elements."""
    shape = (2, 6, 128, 256)
    if (not isinstance(a, np.ndarray) or not isinstance(b, np.ndarray)
            or a.shape != shape or b.shape != shape
            or a.dtype != np.uint8 or b.dtype != np.uint8):
        raise ValueError("packed ONNX I420 must be [2,6,128,256] uint8")
    arr_a = np.ascontiguousarray(a)
    arr_b = np.ascontiguousarray(b)
    d = np.abs(arr_a.astype(np.int16) - arr_b.astype(np.int16))
    changed = np.argwhere(d != 0)
    return {
        "sha256_a": sha256(arr_a.tobytes()).hexdigest(),
        "sha256_b": sha256(arr_b.tobytes()).hexdigest(),
        "changed_elements": int(changed.shape[0]),
        "max_element_delta": int(d.max()),
        "first_changed_indices_camera_plane_row_col": (
            [int(v) for v in changed[0]] if changed.size else None
        ),
        "first_12_changed_element_indices": [
            [int(v) for v in point] for point in changed[:12]
        ],
        "bit_exact": bool(changed.size == 0),
    }


def packed_i420_sequence(frames: list[np.ndarray], warmup: int = 2) -> dict:
    if (not isinstance(frames, list) or len(frames) < 3 or
            type(warmup) is not int or not 0 <= warmup <= len(frames) - 2):
        raise ValueError("bad model tensor sequence")
    baseline = frames[warmup]
    per_frame = [packed_i420_delta(baseline, image) for image in frames[warmup:]]
    hashes = [sha256(np.ascontiguousarray(x).tobytes()).hexdigest() for x in frames]
    first_change = next(
        (warmup + i for i, v in enumerate(per_frame) if not v["bit_exact"]), None
    )
    return {
        "all_frame_sha256": hashes,
        "post_warmup_unique_sha256": len(set(hashes[warmup:])),
        "bit_exact_after_warmup": len(set(hashes[warmup:])) == 1,
        "first_divergence_frame_index_zero_based": first_change,
        "max_changed_elements_post_warmup": max(v["changed_elements"] for v in per_frame),
        "per_frame_vs_first_post_warmup": per_frame,
    }
