"""Camera-pipeline causal diagnostics from independent raw MetaDrive observations.

The three mechanisms must not be collapsed:
  1) multiple CPU reads without any new draw;
  2) taskMgr.step (simulation tasks + rendering) vs graphicsEngine.renderFrame;
  3) same render method with/without default visual ego geometry.

This module *analyzes* observations. It never alters model pixels, optimizes
camera output or declares real driving-model performance. An exact source RGB
hash is distinct from its warped/compressed I420 model tensor hash.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
from typing import Any

import numpy as np

from .frame_stability import compare_rgb_frames
from .camera import RGBFrame


@dataclass(frozen=True)
class PixelReceipt:
    first_sha256: str
    second_sha256: str
    changed_pixels: int
    changed_fraction: float
    max_rgb_channel_delta: int
    mean_rgb_channel_delta: float
    identical: bool

    def to_dict(self) -> dict:
        return vars(self).copy()


def raw_rgb_frame(array: np.ndarray) -> RGBFrame:
    """Keep a private immutable copy so later Panda buffers cannot mutate evidence."""
    if (not isinstance(array,np.ndarray) or array.ndim!=3 or
        array.shape[2]!=3 or array.dtype!=np.uint8 or
        array.shape[0]<=0 or array.shape[1]<=0):
        raise ValueError('raw MetaDrive RGB must be [height,width,3] uint8')
    height,width,_=array.shape
    return RGBFrame(width,height,np.ascontiguousarray(array).tobytes())


def difference(a: RGBFrame, b: RGBFrame) -> PixelReceipt:
    d=compare_rgb_frames(a,b)
    return PixelReceipt(a.sha256,b.sha256,d.changed_pixels,d.changed_fraction,
                        d.max_absolute_channel_delta,d.mean_absolute_rgb_delta,
                        d.identical)


def summarize_frame_sequence(frames: list[RGBFrame], *, warmup: int = 2) -> dict:
    """Report ALL frames and post-warmup separately; never discard startup drift."""
    if len(frames)<2 or type(warmup) is not int or warmup<0 or warmup>=len(frames)-1:
        raise ValueError('need at least 2 frames after bounded warmup')
    hashes=[f.sha256 for f in frames]
    against_first=[difference(frames[0],f).to_dict() for f in frames]
    after=frames[warmup:]
    after_diffs=[difference(after[0],f).to_dict() for f in after]
    return {
        'all_frame_count':len(frames),
        'all_unique_sha256':len(set(hashes)),
        'bit_exact_all':len(set(hashes))==1,
        'warmup_frames_excluded_only_in_secondary_view':warmup,
        'post_warmup_frame_count':len(after),
        'post_warmup_unique_sha256':len(set(f.sha256 for f in after)),
        'bit_exact_after_warmup':len(set(f.sha256 for f in after))==1,
        'max_changed_pixels_all':max(x['changed_pixels'] for x in against_first),
        'max_channel_delta_all':max(x['max_rgb_channel_delta'] for x in against_first),
        'max_changed_pixels_after_warmup':max(x['changed_pixels'] for x in after_diffs),
        'max_channel_delta_after_warmup':max(x['max_rgb_channel_delta'] for x in after_diffs),
        'per_frame_vs_first':against_first,
        'per_frame_after_warmup':after_diffs,
    }


def summarize_readback_groups(groups: list[list[RGBFrame]]) -> dict:
    """Many CPU reads of a SINGLE completed GPU frame, with NO tick in between."""
    if not groups or any(len(g)<2 for g in groups):
        raise ValueError('each CPU-readback group requires >=2 reads')
    samples=[]
    for i,group in enumerate(groups):
        unique=len({f.sha256 for f in group})
        rows=[difference(group[0],f).to_dict() for f in group]
        samples.append({
            'render_sample_index':i,'read_count_without_render':len(group),
            'unique_read_hashes':unique,'bit_exact':unique==1,
            'max_changed_pixels':max(x['changed_pixels'] for x in rows),
            'max_rgb_channel_delta':max(x['max_rgb_channel_delta'] for x in rows),
            'read_differences':rows,
        })
    return {
        'status': 'BIT_EXACT_CPU_READBACK_WITHOUT_RENDER'
                  if all(s['bit_exact'] for s in samples)
                  else 'CPU_READBACK_DIFFERENCE_WITHOUT_RENDER',
        'samples':samples,
        'readback_bit_exact':all(s['bit_exact'] for s in samples),
        'no_task_or_graphics_tick_between_reads':True,
    }


def compare_image_shapes(raw: RGBFrame, model: RGBFrame) -> dict:
    return {
        'source_dimensions':[raw.width,raw.height],
        'model_dimensions':[model.width,model.height],
        'raw_sha256':raw.sha256,
        'model_sha256':model.sha256,
    }


def interpret_pipeline(conditions: dict[str,dict]) -> dict:
    """Observational logic ONLY: never promote a correlation into sole cause."""
    if not conditions:
        raise ValueError('no independent capture conditions')
    out={'status':'OBSERVATIONS_RECORDED_CAUSE_NOT_PROVEN',
         'claims_prohibited':['MODEL_DRIVING_RANKING','REAL_CAMERA_FIDELITY',
                              'EXACT_NATIVE_FEEDBACK_REPEATABILITY_FROM_THIS_TEST'],
         'readback_status':'UNTESTED',
         'task_vs_graphics':'UNTESTED',
         'scene_visibility':'UNTESTED',
         'observations':[]}
    candidates=[]
    for key,report in conditions.items():
        if report.get('status')=='ERROR':
            out['observations'].append(f'{key}: test unavailable - {report.get("error","unknown")}')
            continue
        cpu=report.get('cpu_readback',{})
        if cpu:
            if not cpu.get('road',{}).get('readback_bit_exact',False) or not cpu.get('wide',{}).get('readback_bit_exact',False):
                candidates.append('Repeated CPU reads without render differed: investigate CPU copy/aliasing.')
            else:
                out['readback_status']='CPU_READS_BIT_EXACT_WITHOUT_NEW_RENDER'
    paired={}
    for name in ('perceive_sequential','task_step_pair','graphics_frame_pair'):
        key='ego_hidden_'+name
        data=conditions.get(key,{})
        if data.get('status')=='OBSERVED':
            paired[name]=data
    if 'task_step_pair' in paired and 'graphics_frame_pair' in paired:
        a=paired['task_step_pair']['model_frame_stability']
        b=paired['graphics_frame_pair']['model_frame_stability']
        if all(b[cam]['bit_exact_after_warmup'] for cam in ('road','wide')) and not all(
                a[cam]['bit_exact_after_warmup'] for cam in ('road','wide')):
            out['task_vs_graphics']='GRAPHICS_ONLY_STABLER_THAN_TASK_STEP_IN_THIS_SCENE'
            candidates.append('Scene tasks/render timing correlated with jitter; not proof of specific task.')
        else:
            out['task_vs_graphics']='NO_UNAMBIGUOUS_TASK_VS_GRAPHICS_SEPARATION'
    a=conditions.get('ego_visible_perceive_sequential',{})
    b=conditions.get('ego_hidden_perceive_sequential',{})
    if a.get('status')=='OBSERVED' and b.get('status')=='OBSERVED':
        if all(b['model_frame_stability'][cam]['bit_exact_after_warmup'] for cam in ('road','wide')) and not all(
                a['model_frame_stability'][cam]['bit_exact_after_warmup'] for cam in ('road','wide')):
            out['scene_visibility']='HIDING_DEFAULT_EGO_CORRELATED_WITH_STABILITY'
        else:
            out['scene_visibility']='EGO_VISIBILITY_NOT_SUFFICIENT_TO_REMOVE_DRIFT'
    out['hypotheses_to_test_next']=list(dict.fromkeys(candidates))
    out['real_vehicle_testing']=False
    out['model_scoring_allowed']=False
    return out
