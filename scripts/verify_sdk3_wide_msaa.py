"""Verify same-task MSAA readout and compare it to the native resolved half-float texel."""
from math import isfinite
import struct

import numpy as np

from scripts.panda_sdk3_runtime import need
from scripts.sdk3_wide_framebuffer import POINT, SIZE
from scripts.sdk3_wide_msaa import RENDERBUFFER, RGBA16F
from scripts.verify_sdk3_wide_framebuffer import read
from scripts.verify_sdk3_wide_hdr import verify as verify_base


def verify_sample_math(post,hdr):
    scene,=post['pre_resolve']
    need(post['scene_callback_restored'] and scene['sample_copy_calls']==scene['extra_compute_calls']==1
         and scene['state_restored'] and scene['restore_gl_error']==0 and not scene.get('failure'),
         'one scoped exact MSAA pixel observation and restored engine state')
    need(scene['source_samples']==4 and scene['source_extent']==list(SIZE)
         and scene['source_attachment']>0 and scene['source_scene_draw_fbo']>0
         and scene['source_attachment_type']==RENDERBUFFER and scene['internal_format']==RGBA16F
         and scene['sample_pixel_gl']==[POINT[0],SIZE[1]-1-POINT[1]],
         'original four-sample RGBA16F scene color attachment')
    need(scene['source_scene_draw_fbo']!=post['gl_before']['draw']
         and scene['callback_enter_ns']<=scene['after_original_draw_ns']<=scene['callback_exit_ns']<=post['callback_enter_ns'],
         'original scene samples before original post-process draw')
    gpu_words=scene['private_resolve_words']
    need(scene['private_blit_calls']==1 and len(gpu_words)==4
         and all(type(x) is int and 0<=x<2**32 for x in gpu_words),'one private reference GPU resolve')
    gpu=np.asarray(struct.unpack('<4f',struct.pack('<4I',*gpu_words)),dtype=np.float64)
    need(np.isfinite(gpu).all() and np.array_equal(gpu,gpu.astype('<f2')),'finite exact private HDR16 resolve')
    pos=scene['sample_positions']
    need(len(pos)==4 and len(set(tuple(x) for x in pos))==4
         and all(len(p)==2 and all(isfinite(x) and 0<=x<=1 for x in p) for p in pos),
         'valid native sample geometry')
    words=scene['sample_words']
    need(len(words)==16 and all(type(x) is int and 0<=x<2**32 for x in words),'actual 4-by-4 readback words')
    values=np.asarray(struct.unpack('<16f',struct.pack('<16I',*words)),dtype=np.float64).reshape(4,4)
    need(np.isfinite(values).all(),'finite original sample RGBA')
    center=np.asarray(hdr[1][1],dtype=np.float64)
    average=values.mean(axis=0)
    half=average.astype('<f2')
    actual_half=center.astype('<f2')
    need(np.array_equal(values,values.astype('<f2')) and np.array_equal(center,actual_half),
         'original sample and resolved values are exactly representable RGBA16F')
    return dict(samples_rgba=values.tolist(),mean_rgba=average.tolist(),rounded_half_rgba=half.tolist(),
                resolved_rgba=center.tolist(),mean_matches_resolve=bool(np.array_equal(half,actual_half)),
                rgb_mean_matches_resolve=bool(np.array_equal(half[:3],actual_half[:3])),
                private_resolve_rgba=gpu.tolist(),private_resolve_matches_original=bool(np.array_equal(gpu,center)),
                half_encoding_difference=(actual_half.view('<u2').astype(int)-half.view('<u2').astype(int)).tolist(),
                sample_positions=pos)


def verify(native,poses,trial,context,history='sequential'):
    result=verify_base(native,poses,trial,context,history)
    if trial=='control':
        return result
    post=result['observation']
    result['sample_comparison']=verify_sample_math(post,result['hdr_patch'])
    scene,=post['pre_resolve']
    ledger=read(native/'report.json')['timings']['events']
    task=next(e for e in ledger if e['role']=='wide' and e['stage']=='render_task')
    need(task['begin_ns']<=scene['callback_enter_ns']<=scene['callback_exit_ns']<=task['end_ns'],
         'scene and post observations belong to the same wide camera task')
    result['extra_gl_read_calls']=4
    return result
