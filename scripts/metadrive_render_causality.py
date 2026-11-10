"""Controlled MetaDrive 0.4.3 RGB render/readback/scene isolation experiment.

There are three independent capture schedules:
  perceive_sequential: upstream BaseCamera.perceive -> taskMgr.step per camera
  task_step_pair: mount both cameras, taskMgr.step ONCE, then read both RAM textures
  graphics_frame_pair: mount both cameras, graphicsEngine.renderFrame ONCE
No live vehicle/ONNX/Carrot dynamics: fixed WORLD pose throughout each sample.
Every native observation is measured before/after image rectification and I420
conversion. A moved-pose positive control prevents stale buffers appearing PASS.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np

from bigbench.camera import RGBFrame
from bigbench.frame_stability import compare_rgb_frames
from bigbench.image_adapter import camera_pair_to_model
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.optical_calibration import PinholeRectifier, intrinsics_from_panda_lens
from bigbench.task_ablation import ALLOWED_VISUAL_TASKS, remove_visual_scene_task
from bigbench.render_causality import (
    raw_rgb_frame, summarize_frame_sequence, summarize_readback_groups,
    interpret_pipeline,
)


CAPTURE_MODES=('perceive_sequential','task_step_pair','graphics_frame_pair')
WORLD_POSE=((0.,0.,1.22),(-90.,0.,0.))


@contextmanager
def mount_world_pair(provider: Any, pose=WORLD_POSE):
    """Restore exact Panda parent/local pose on errors; only camera transforms change."""
    if provider.env is None:
        raise RuntimeError('native MetaDrive environment was closed')
    engine=provider.env.engine
    sensors={k:engine.sensors['bigbench_'+k] for k in ('road','wide')}
    originals=[]
    try:
        for sensor in sensors.values():
            node=sensor.get_cam()
            originals.append((node,node.getParent(),node.getPos(),node.getHpr()))
            node.reparentTo(engine.origin)
            node.setPos(*pose[0])
            node.setHpr(*pose[1])
        yield sensors
    finally:
        for node,parent,pos,hpr in reversed(originals):
            node.reparentTo(parent)
            node.setPos(pos)
            node.setHpr(hpr)


def read_cpu_texture(sensor: Any, source_width: int, source_height: int) -> np.ndarray:
    """Read MetaDrive's RTMCopyRam WITHOUT calling taskMgr or a graphics render."""
    texture=getattr(sensor,'copy_texture',None)
    if texture is None:
        raise RuntimeError('MetaDrive RAM-backed RGB sensor texture missing')
    data=texture.getRamImageAs('RGB').getData()
    raw=np.frombuffer(data,dtype=np.uint8)
    if raw.size!=source_width*source_height*3:
        raise RuntimeError('CPU texture has no completed RGB frame')
    return np.ascontiguousarray(raw.reshape(source_height,source_width,3)[::-1])


def capture_with_readback(provider: Any, *, mode: str, pose=WORLD_POSE,
                          repeat_reads: int=3) -> tuple[dict,dict]:
    """Capture two raw camera frames plus repeated reads of identical GPU copies.

    Simultaneous modes allow strict task scheduling comparison. They never
    use a borrowed camera that is auto-restored between road/wide captures.
    """
    if mode not in CAPTURE_MODES or not 2<=repeat_reads<=6:
        raise ValueError('unsupported capture mode or read count')
    engine=provider.env.engine
    source_w=provider.source_width
    source_h=provider.source_height
    samples={}
    groups={}
    if mode=='perceive_sequential':
        for kind in ('road','wide'):
            sensor=engine.sensors['bigbench_'+kind]
            raw=sensor.perceive(to_float=False,new_parent_node=engine.origin,
                                position=pose[0],hpr=pose[1])
            if not isinstance(raw,np.ndarray):
                raw=raw.get()
            # The first image is a private copy of the perceive() return.
            # Subsequent reads of the same RAM texture do NOT advance rendering.
            values=[np.array(raw,copy=True)]
            values.extend(read_cpu_texture(sensor,source_w,source_h)
                          for _ in range(repeat_reads-1))
            samples[kind]=values[0]
            groups[kind]=values
    else:
        with mount_world_pair(provider,pose) as sensors:
            if mode=='task_step_pair':
                engine.taskMgr.step()
            else:
                engine.graphicsEngine.renderFrame()
            for kind,sensor in sensors.items():
                values=[read_cpu_texture(sensor,source_w,source_h)
                        for _ in range(repeat_reads)]
                samples[kind]=values[0]
                groups[kind]=values
    return samples,groups


def source_model_frames(provider:Any, raws:dict) -> tuple[dict, np.ndarray]:
    rectifier=PinholeRectifier(source_width=provider.source_width,
                               source_height=provider.source_height)
    measured={}
    for kind in ('road','wide'):
        camera=provider.env.engine.sensors['bigbench_'+kind]
        measured[kind]=intrinsics_from_panda_lens(camera.get_lens(),
                             provider.source_width,provider.source_height)
    pair,_=rectifier.rectify_pair(raws['road'],raws['wide'],
                                  road_intrinsics=measured['road'],
                                  wide_intrinsics=measured['wide'])
    model={'road':pair.road,'wide':pair.wide}
    packed=camera_pair_to_model(pair.road,pair.wide)
    if packed.shape!=(2,6,128,256) or packed.dtype!=np.uint8:
        raise RuntimeError('unexpected ONNX image tensor contract')
    return model,packed


def _packed_summary(tensors:list[np.ndarray],warmup:int) -> dict:
    hashes=[sha256(x.tobytes()).hexdigest() for x in tensors]
    selected=tensors[warmup:]
    base=selected[0].astype(np.int16)
    differences=[np.abs(x.astype(np.int16)-base) for x in selected]
    changed=[int(np.count_nonzero(x)) for x in differences]
    return {
        'shape':list(tensors[0].shape),'dtype':str(tensors[0].dtype),
        'all_unique_sha256':len(set(hashes)),
        'all_frame_sha256':hashes,
        'bit_exact_all':len(set(hashes))==1,
        'after_warmup_unique_sha256':len(set(hashes[warmup:])),
        'after_warmup_bit_exact':len(set(hashes[warmup:]))==1,
        'max_changed_tensor_elements_after_warmup':max(changed),
        'max_value_delta_after_warmup':max(int(x.max()) for x in differences),
    }


def _scene_snapshot(provider:Any) -> dict:
    engine=provider.env.engine
    node=provider.env.vehicle.origin
    p=node.getPos(engine.origin)
    r=node.getHpr(engine.origin)
    try:
        tasks=sorted(str(x.getName()) for x in engine.taskMgr.getAllTasks())
    except Exception:
        tasks=[]
    from panda3d.core import ClockObject
    clock=ClockObject.getGlobalClock()
    return {
        'visual_ego_position_xyz':[float(p[0]),float(p[1]),float(p[2])],
        'visual_ego_heading_pitch_roll':[float(r[0]),float(r[1]),float(r[2])],
        'registered_task_names':tasks,
        'clock_frame_time_s':float(clock.getFrameTime()),
        'clock_frame_count':int(clock.getFrameCount()),
    }


def _pre_tonemap_probe(provider:Any) -> dict:
    """Last-frame-only GPU extraction, NOT mixed into the main capture time series."""
    result={}
    engine=provider.env.engine
    for kind in ('road','wide'):
        sensor=engine.sensors['bigbench_'+kind]
        tex=getattr(sensor,'scene_tex',None)
        if tex is None:
            result[kind]={'status':'UNAVAILABLE_NO_PRE_TONEMAP_TEXTURE'}
            continue
        try:
            if not engine.graphicsEngine.extractTextureData(tex,sensor.buffer.getGsg()):
                result[kind]={'status':'GPU_EXTRACT_UNAVAILABLE'}
                continue
            data=bytes(tex.getRamImage().getData())
            if not data:
                result[kind]={'status':'EMPTY_PRE_TONEMAP_TEXTURE'}
            else:
                result[kind]={'status':'EXTRACTED_FOR_INSPECTION_ONLY',
                              'byte_count':len(data),'sha256':sha256(data).hexdigest()}
        except Exception as exc:
            result[kind]={'status':'UNAVAILABLE','error':f'{type(exc).__name__}: {exc}'}
    return result


def run_condition(*,mode:str,scene:str,frames:int,seed:int,warmup:int,
                  fixed_clock:bool=False,probe_pre_tonemap:bool=False,
                  ablate_task:str | None=None) -> dict:
    """One fresh MetaDrive world per render schedule and scene visibility."""
    if mode not in CAPTURE_MODES or scene not in ('ego_visible','ego_hidden'):
        raise ValueError('unknown independent experimental condition')
    if type(frames) is not int or not 4<=frames<=20 or not 0<=warmup<=frames-2:
        raise ValueError('bounded frames/warmup required')
    provider=NativeMetaDriveProvider(seed=seed,fixed_virtual_clock=fixed_clock)
    try:
        ablation=(remove_visual_scene_task(provider.env.engine.taskMgr,ablate_task)
                  if ablate_task is not None else None)
        if scene=='ego_hidden':
            from metadrive.constants import CamMask
            provider.env.vehicle.origin.hide(CamMask.RgbCam)
        start=_scene_snapshot(provider)
        raws={k:[] for k in ('road','wide')}
        models={k:[] for k in ('road','wide')}
        cpu_reads={k:[] for k in ('road','wide')}
        tensors=[]
        for i in range(frames):
            observed,repeats=capture_with_readback(provider,mode=mode)
            model,packed=source_model_frames(provider,observed)
            for kind in ('road','wide'):
                raws[kind].append(raw_rgb_frame(observed[kind]))
                models[kind].append(model[kind])
                cpu_reads[kind].append([raw_rgb_frame(x) for x in repeats[kind]])
            tensors.append(packed)
        end=_scene_snapshot(provider)
        raw_pose_shift,_=capture_with_readback(
            provider,mode=mode,
            pose=((WORLD_POSE[0][0]+2.,WORLD_POSE[0][1],WORLD_POSE[0][2]),WORLD_POSE[1]))
        pose_shift_positive={kind:
            raw_rgb_frame(raw_pose_shift[kind]).sha256!=raws[kind][-1].sha256
            for kind in ('road','wide')}
        out={
            'status':'OBSERVED' if all(pose_shift_positive.values())
                     else 'INCONCLUSIVE_NO_POSE_RESPONSE',
            'condition':f'{scene}_{mode}', 'seed':seed,
            'scene_task_ablation':ablation,
            'mode':mode,'scene':scene,'fixed_virtual_clock':fixed_clock,
            'frames':frames,'warmup':warmup,
            'native_source_dims':[provider.source_width,provider.source_height],
            'readback_without_render_asserted':True,
            'capture_schedule':{
                'perceive_sequential':'one taskMgr.step separately for road and wide',
                'task_step_pair':'one shared taskMgr.step before both reads',
                'graphics_frame_pair':'one graphicsEngine.renderFrame without taskMgr.step',
            }[mode],
            'source_frame_stability':{k:summarize_frame_sequence(v,warmup=warmup)
                                      for k,v in raws.items()},
            'model_frame_stability':{k:summarize_frame_sequence(v,warmup=warmup)
                                     for k,v in models.items()},
            'cpu_readback':{k:summarize_readback_groups(v) for k,v in cpu_reads.items()},
            'onnx_packed_tensor_stability':_packed_summary(tensors,warmup),
            'pose_shift_positive_control':pose_shift_positive,
            'scene_before':start,'scene_after':end,
            'scene_visual_ego_transform_unchanged':(
                start['visual_ego_position_xyz']==end['visual_ego_position_xyz']
                and start['visual_ego_heading_pitch_roll']==end['visual_ego_heading_pitch_roll']),
            'model_scoring_allowed':False,'real_vehicle_testing':False,
        }
        if probe_pre_tonemap:
            out['last_frame_pre_tonemap_gpu_readback']=_pre_tonemap_probe(provider)
        return out
    finally:
        provider.close()


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='MetaDrive rendering/readback/scene isolation, synthetic only')
    p.add_argument('--out',type=Path,default=Path('output/render-causality'))
    p.add_argument('--frames',type=int,default=6)
    p.add_argument('--warmup',type=int,default=2)
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--modes',nargs='+',choices=CAPTURE_MODES,default=list(CAPTURE_MODES))
    p.add_argument('--scenes',nargs='+',choices=['ego_visible','ego_hidden'],
                   default=['ego_visible','ego_hidden'])
    p.add_argument('--fixed-clock',action='store_true')
    p.add_argument('--probe-pre-tonemap',action='store_true')
    p.add_argument('--ablate-visual-task',choices=sorted(ALLOWED_VISUAL_TASKS),default=None,
                   help='EXPERIMENT only: remove exactly one known visual scene task; never igLoop')
    args=p.parse_args(argv)
    args.out.mkdir(parents=True,exist_ok=True)
    conditions={}
    for scene in args.scenes:
        for mode in args.modes:
            key=f'{scene}_{mode}'
            print('NATIVE_RENDER_CAUSALITY_START',key,flush=True)
            try:
                conditions[key]=run_condition(mode=mode,scene=scene,seed=args.seed,
                    frames=args.frames,warmup=args.warmup,
                    fixed_clock=args.fixed_clock,probe_pre_tonemap=args.probe_pre_tonemap,
                    ablate_task=args.ablate_visual_task)
            except Exception as exc:
                conditions[key]={'status':'ERROR',
                    'error':f'{type(exc).__name__}: {exc}',
                    'model_scoring_allowed':False,'real_vehicle_testing':False}
            (args.out/(key+'.json')).write_text(
                json.dumps(conditions[key],ensure_ascii=False,indent=2,allow_nan=False)+'\n',
                encoding='utf-8')
            print('NATIVE_RENDER_CAUSALITY_RESULT',key,
                  conditions[key]['status'],conditions[key].get('error',''),flush=True)
    interpretation=interpret_pipeline(conditions)
    result={
        'status':'DIAGNOSTIC_COMPLETE_WITH_UNRESOLVED_CAUSALITY',
        'scope':'RENDER_TIMING_CPU_COPY_SCENE_VISIBILITY_ONLY',
        'real_vehicle_testing':False,'model_scoring_allowed':False,
        'clock':'fixed' if args.fixed_clock else 'default',
        'visual_task_ablation_requested':args.ablate_visual_task,
        'condition_statuses':{k:v['status'] for k,v in conditions.items()},
        'interpretation':interpretation,
        'experiment_count':len(conditions),
        'all_requested_modes_observed':all(x.get('status')=='OBSERVED'
                                           for x in conditions.values()),
        'warning':'Even stable RGB here does not prove full ONNX feedback determinism',
    }
    (args.out/'causality_summary.json').write_text(
        json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',
        encoding='utf-8')
    print('NATIVE_RENDER_CAUSALITY_SUMMARY',json.dumps(
        {'modes':result['condition_statuses'],
         'readback':interpretation['readback_status'],
         'task_vs_graphics':interpretation['task_vs_graphics'],
         'scene':interpretation['scene_visibility']},ensure_ascii=False),flush=True)
    # A diagnostic with missing/failed conditions is not a software pass,
    # but its preserved JSON remains useful evidence.
    return 0 if result['all_requested_modes_observed'] else 2


if __name__=='__main__':
    raise SystemExit(main())
