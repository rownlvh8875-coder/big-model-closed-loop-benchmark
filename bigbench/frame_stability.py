"""Read-only pixel-level temporal consistency diagnostics for native virtual RGB frames.

This is NOT a model input repair. A small mean pixel error must never be
silently interpreted as bit-exact deterministic camera frames.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import numpy as np

from .camera import RGBFrame


@dataclass(frozen=True)
class FrameDifference:
    identical: bool
    changed_pixels: int
    changed_fraction: float
    mean_absolute_rgb_delta: float
    max_absolute_channel_delta: int
    changed_bbox_xyxy: tuple[int, int, int, int] | None

    def to_dict(self) -> dict:
        return asdict(self)


def compare_rgb_frames(reference: RGBFrame, observed: RGBFrame) -> FrameDifference:
    if reference.width != observed.width or reference.height != observed.height:
        raise ValueError('frame dimensions differ')
    n=reference.width * reference.height * 3
    if len(reference.rgb)!=n or len(observed.rgb)!=n:
        raise ValueError('incorrect RGB byte count')
    a=np.frombuffer(reference.rgb,dtype=np.uint8).reshape(reference.height,reference.width,3)
    b=np.frombuffer(observed.rgb,dtype=np.uint8).reshape(observed.height,observed.width,3)
    delta=np.abs(a.astype(np.int16)-b.astype(np.int16))
    changed=(delta!=0).any(axis=2)
    count=int(changed.sum())
    bounds=None
    if count:
        ys,xs=np.nonzero(changed)
        bounds=(int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max()))
    return FrameDifference(
        identical=count==0,
        changed_pixels=count,
        changed_fraction=count/(reference.height*reference.width),
        mean_absolute_rgb_delta=float(delta.mean()),
        max_absolute_channel_delta=int(delta.max()),
        changed_bbox_xyxy=bounds,
    )


def pixel_consistency_summary(frames: list[RGBFrame], *, warmup: int = 0) -> dict:
    if not frames or warmup<0 or warmup>=len(frames):
        raise ValueError('frames and bounded warmup required')
    selected=frames[warmup:]
    compared=[compare_rgb_frames(selected[0],frame).to_dict() for frame in selected]
    hashes=[frame.sha256 for frame in selected]
    stable=len(set(hashes))==1
    return {
        'status':'BIT_EXACT_STABLE' if stable else 'PIXEL_DRIFT_DETECTED',
        'frames_after_warmup':len(selected),
        'unique_sha256':len(set(hashes)),
        'max_changed_fraction':max(row['changed_fraction'] for row in compared),
        'max_abs_rgb_delta':max(row['max_absolute_channel_delta'] for row in compared),
        'max_mean_rgb_delta':max(row['mean_absolute_rgb_delta'] for row in compared),
        'first_divergence_index_after_warmup': next((i for i,row in enumerate(compared)
                                               if not row['identical']),None),
        'comparisons':compared,
        'model_scoring_allowed':False,
        'real_vehicle_testing':False,
    }
