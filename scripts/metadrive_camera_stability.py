"""Detect renderer time dependence without ONNX or any vehicle physics.

Repeated camera captures at exactly one virtual world pose MUST ideally
produce identical RGB frames. Any drift is diagnostic failure, not a reason
to loosen model-performance acceptance thresholds.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bigbench.kinematics import AgentState
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.native_model_campaign import NativeWorldCamera
from bigbench.frame_stability import pixel_consistency_summary


def capture_sequence(*, seed: int, frames: int, fixed_clock: bool=False,
                     return_frames: bool=False, hide_ego_rgb: bool=False) -> list[dict] | tuple[list[dict],dict]:
    provider=NativeMetaDriveProvider(seed=seed,fixed_virtual_clock=fixed_clock)
    try:
        if hide_ego_rgb:
            # The fixed WORLD pose may otherwise stare into MetaDrive's default
            # visual ego prop. Suppress ONLY its RGB render mask for this audit.
            # This is not a controller/vehicle-state or dynamics modification.
            from metadrive.constants import CamMask
            provider.env.vehicle.origin.hide(CamMask.RgbCam)
        camera=NativeWorldCamera(provider)
        fixed_pose=AgentState(0.0,0.0,0.0,0.0,0.0)
        hashes=[]
        actual={'road':[],'wide':[]}
        for k in range(frames):
            pair=camera.capture(fixed_pose)
            if return_frames:
                actual['road'].append(pair.road)
                actual['wide'].append(pair.wide)
            hashes.append({'frame':k,'road_sha256':pair.road.sha256,
                           'wide_sha256':pair.wide.sha256})
        return (hashes,actual) if return_frames else hashes
    finally:
        provider.close()


def main(argv=None):
    p=argparse.ArgumentParser(description='Native virtual camera fixed-pose repeatability, no model')
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--frames',type=int,default=12)
    p.add_argument('--fixed-clock',action='store_true',help='use a fresh non-real-time Panda frame clock')
    p.add_argument('--out',type=Path,default=Path('output/camera-stability.json'))
    p.add_argument('--pixel-audit',action='store_true',help='compare actual RGB pixels rather than hashes alone')
    p.add_argument('--warmup',type=int,default=0,help='exclude startup frames only from extra diagnostic; never hide original drift')
    p.add_argument('--save-frames',action='store_true',help='save reference and drifted virtual model RGB images')
    p.add_argument('--hide-ego-rgb',action='store_true',help='exclude the MetaDrive default ego visual prop from road-only optics audit')
    args=p.parse_args(argv)
    if not 2<=args.frames<=30:
        p.error('frames must be 2..30')
    if not 0<=args.warmup<args.frames:
        p.error('warmup must be less than total frames')
    data=capture_sequence(seed=args.seed,frames=args.frames,fixed_clock=args.fixed_clock,
                          return_frames=args.pixel_audit or args.save_frames,
                          hide_ego_rgb=args.hide_ego_rgb)
    a,images=(data if isinstance(data,tuple) else (data,None))
    road_unique=len({x['road_sha256'] for x in a})
    wide_unique=len({x['wide_sha256'] for x in a})
    result={'default_ego_render_masked':args.hide_ego_rgb,
            'clock_mode':'PANDA_FIXED_NON_REAL_TIME' if args.fixed_clock else 'PANDA_DEFAULT',
            'status':'FIXED_POSE_CAMERA_STABLE' if road_unique==wide_unique==1
                 else 'FIXED_POSE_CAMERA_DRIFT',
            'seed':args.seed,'frames':args.frames,
            'unique_road_frames':road_unique,'unique_wide_frames':wide_unique,
            'no_model_or_vehicle_control':True,'model_scoring_allowed':False,
            'real_vehicle_testing':False,'raw_frame_hashes':a}
    if args.pixel_audit:
        assert images is not None
        result['pixel_diagnostics']={k:pixel_consistency_summary(v,warmup=args.warmup)
                                     for k,v in images.items()}
        result['warmup_excluded_from_pixel_diagnostics_only']=args.warmup
    if args.save_frames:
        assert images is not None
        dest=args.out.parent/(args.out.stem+'_frames')
        dest.mkdir(parents=True,exist_ok=True)
        # Save first and every changed model canvas for visual root-cause analysis.
        for kind,frames in images.items():
            baseline=frames[0].sha256
            frames[0].save_png(dest/(kind+'_00.png'))
            for i,frame in enumerate(frames[1:],start=1):
                if frame.sha256!=baseline:
                    frame.save_png(dest/(kind+f'_{i:02d}.png'))
        result['saved_frame_directory']=str(dest)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('NATIVE_FIXED_POSE_CAMERA_STABILITY',result['status'],road_unique,wide_unique,flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
