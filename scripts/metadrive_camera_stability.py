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


def capture_sequence(*, seed: int, frames: int) -> list[dict]:
    provider=NativeMetaDriveProvider(seed=seed)
    try:
        camera=NativeWorldCamera(provider)
        fixed_pose=AgentState(0.0,0.0,0.0,0.0,0.0)
        hashes=[]
        for k in range(frames):
            pair=camera.capture(fixed_pose)
            hashes.append({'frame':k,'road_sha256':pair.road.sha256,
                           'wide_sha256':pair.wide.sha256})
        return hashes
    finally:
        provider.close()


def main(argv=None):
    p=argparse.ArgumentParser(description='Native virtual camera fixed-pose repeatability, no model')
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--frames',type=int,default=12)
    p.add_argument('--out',type=Path,default=Path('output/camera-stability.json'))
    args=p.parse_args(argv)
    if not 2<=args.frames<=30:
        p.error('frames must be 2..30')
    a=capture_sequence(seed=args.seed,frames=args.frames)
    road_unique=len({x['road_sha256'] for x in a})
    wide_unique=len({x['wide_sha256'] for x in a})
    result={'status':'FIXED_POSE_CAMERA_STABLE' if road_unique==wide_unique==1
                 else 'FIXED_POSE_CAMERA_DRIFT',
            'seed':args.seed,'frames':args.frames,
            'unique_road_frames':road_unique,'unique_wide_frames':wide_unique,
            'no_model_or_vehicle_control':True,'model_scoring_allowed':False,
            'real_vehicle_testing':False,'raw_frame_hashes':a}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('NATIVE_FIXED_POSE_CAMERA_STABILITY',result['status'],road_unique,wide_unique,flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
