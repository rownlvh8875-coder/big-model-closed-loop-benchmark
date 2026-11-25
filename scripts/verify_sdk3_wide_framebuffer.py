"""Bind FBO bytes to the timing and real copy-RAM result."""

from hashlib import sha256
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

import numpy as np

from bigbench import sdk3_wide_framebuffer_contract as c
from bigbench.optical_calibration import PinholeIntrinsics, PinholeRectifier
from bigbench.preprocess_experiment import LiveInput
from scripts.panda_sdk3_runtime import digest, need
from scripts.sdk3_wide_framebuffer import POINT, framebuffer_rgb, patch_rgb
from scripts.verify_sdk3_wide_capture import SOURCE_NBYTES, SOURCE_SHAPE, load_pixels, verify_timing


def read(path):
    return json.loads(path.read_bytes())


def verify(native, poses, trial, context, history="sequential"):
    report=read(native/'report.json')
    child=read(native/'native-child.json')
    need(report['status']=='CAPTURE_COMPLETE' and report['context']==context and report['trial']==trial
         and report['pid']==child['pid'] and child['returncode']==child['server_returncode']==report['server_returncode']==0
         and report['child_finalized_before_server_stop'] and report['provider_closed']
         and report['model_processes']==report['inferences']==0 and report['ort_module_loaded'] is False,
         'complete owned camera-only child')
    if context=='actions':
        attestation=read(native/'execution.json')
        need(attestation['owned_container_removed'] and not attestation['stopped_state']['OOMKilled'],
             'actual stopped and removed Actions container')
    original=read(poses)
    need(report['pose_source_sha256']==digest(poses) and all(report[k]==original[k] for k in ('driver','geometry','intrinsics')),
         'same measured camera context and historical poses')
    steps=original['frames'][:c.LIMITS['captures_per_process']]
    if history=='sparse':
        steps=[steps[0],steps[-1]]
    need(report.get('history','sequential')==history
         and report['camera_capture_attempts']==len(report['frames'])==len(steps),'bounded complete capture history')
    for step,archived in zip(report['frames'],steps,strict=True):
        need(step['pose']==archived['pose'] and step['step']==archived['step'],'exact original world poses')
    timing=verify_timing(report['timings'],0,0)
    need(report['callback_restored'] and report['point']==list(POINT),'target callback removed')
    read_started=next(r['begin_ns'] for r in report['timings']['events'] if (r['role'],r['stage'])==('wide','read_rgb'))
    task=next(r for r in report['timings']['events'] if (r['role'],r['stage'])==('wide','render_task'))
    focus=report['frames'][-1]['hashes']
    lenses={role:PinholeIntrinsics(**lens) for role,lens in report['intrinsics'].items()}
    images={}
    hashes={}
    for role in lenses:
        blob=load_pixels(native,report['pixels'][role]['source'],f'44-{role}-source.rgb.zlib',SOURCE_NBYTES)
        images[role]=np.frombuffer(blob,np.uint8).reshape(SOURCE_SHAPE)
        hashes[role]=sha256(blob).hexdigest()
    need(hashes==focus['source_sha256'],'unchanged actual CPU source')
    pair,_=PinholeRectifier().rectify_pair(images['road'],images['wide'],
                                           road_intrinsics=lenses['road'],wide_intrinsics=lenses['wide'])
    for role in lenses:
        rgb=getattr(pair,role).rgb
        need(load_pixels(native,report['pixels'][role]['canvas'],f'44-{role}-canvas.rgb.zlib',len(rgb))==rgb,
             'exact reconstructed canvas')
    with tempfile.TemporaryDirectory() as tmp:
        prep=LiveInput(SimpleNamespace(),lenses,c.VARIANT,Path(tmp))
        prep.record_native_rgb(images,hashes)
        prep.expected=(pair.road.sha256,pair.wide.sha256)
        new_img=prep.prepare(pair.road,pair.wide).tobytes()
        need(load_pixels(native,report['pixels']['tensor'],'44-input.bin.zlib',len(new_img))==new_img,
             'exact reconstructed input')
        need(focus['step']==len(steps) and dict(prep.rows[-1],step=len(steps))==focus,
             'hashes agree with original pipeline')
    ram_patch=patch_rgb(images)
    need(ram_patch==report['ram_patch_top_down'],'recorded RAM crop bound to raw bytes')
    extra_reads=0
    fbo_patch=None
    observation=None
    if trial=='framebuffer':
        observation,=report['fbo_observations']
        need(observation['original_draw_returns']==observation['extra_gl_read_calls']==1
             and observation['region_proven'] and observation['state_restored']
             and observation['gl_before']==observation['gl_after']
             and not any(observation[k] for k in ('gl_error_before','gl_error_after_read','gl_error_after_restore'))
             and observation['samples']==0,'successful restored one-read final color observation')
        need(task['begin_ns']<=observation['callback_enter_ns']<=observation['after_original_draw_ns']
             <=observation['callback_exit_ns']<=task['end_ns']<=read_started,
             'GL pixel after the original draw and before same-task RAM read')
        need(observation['gl_patch_bottom_left']==[328,296,3,3],'exact top-left to GL coordinate mapping')
        fbo_patch=framebuffer_rgb(observation)
        extra_reads=1
    else:
        need(not report['fbo_observations'],'unobserved control has no additional FBO read')
    return dict(trial=trial,context=context,nonce=report['nonce'],official_model_processes=0,
                official_inferences=0,exact_raw_hashes=focus,ram_patch=ram_patch,framebuffer_patch=fbo_patch,
                same_nine_pixels=fbo_patch==ram_patch if fbo_patch is not None else None,
                extra_gl_read_calls=extra_reads,point=list(POINT),timing=timing,observation=observation,
                pose_source_sha256=digest(poses))
