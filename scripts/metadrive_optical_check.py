"""Offline MetaDrive camera / model input probe. No driving performance ranking.

Examples (Linux with software OpenGL/Xvfb):
  xvfb-run -a python -m scripts.metadrive_optical_check --out output/optical-check
  xvfb-run -a python -m scripts.metadrive_optical_check --out output/md-v3 --steps 3 \
    --model /private/cache/mdv3.onnx --spec model_specs/md-v3.json
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path

from bigbench.kinematics import AgentState
from bigbench.metadrive_camera import (
    MetaDriveOpticalRig, NativeMetaDriveProvider, probe_model_with_metadrive,
)


def main(argv=None) -> int:
    ap=argparse.ArgumentParser(description='Real MetaDrive virtual pinhole camera check. NOT a model ranking.')
    ap.add_argument('--out',type=Path,default=Path('output/metadrive-optics'))
    ap.add_argument('--seed',type=int,default=20261109)
    ap.add_argument('--steps',type=int,default=2)
    ap.add_argument('--source-width',type=int,default=964)
    ap.add_argument('--source-height',type=int,default=604)
    ap.add_argument('--model',type=Path,default=None)
    ap.add_argument('--spec',type=Path,default=None)
    args=ap.parse_args(argv)
    if (args.model is None) != (args.spec is None):
        ap.error('--model and --spec must be supplied together')
    if not 1 <= args.steps <= 20:
        ap.error('--steps must be in 1..20 (bounded optical probe)')
    provider=NativeMetaDriveProvider(seed=args.seed,source_width=args.source_width,
                                     source_height=args.source_height)
    rig=MetaDriveOpticalRig(provider,source_width=args.source_width,
                             source_height=args.source_height)
    try:
        args.out.mkdir(parents=True,exist_ok=True)
        if args.model is not None:
            from bigbench.onnx_policy import OnnxBigModelPolicy
            policy=OnnxBigModelPolicy(args.model,args.spec)
            result,last=probe_model_with_metadrive(policy,rig,steps=args.steps)
            result['model_sha256']=policy.contract.sha256
            result['model_inference_steps']=len(policy.trace)
            with (args.out/'model_inference.csv').open('w',newline='',encoding='utf-8') as f:
                writer=csv.DictWriter(f,fieldnames=list(asdict(policy.trace[0])))
                writer.writeheader()
                writer.writerows(asdict(v) for v in policy.trace)
            last.pair.road.save_png(args.out/'road_model_last.png')
            last.pair.wide.save_png(args.out/'wide_model_last.png')
        else:
            baseline=rig.capture(AgentState(0,0,0,0,0))
            shifted=rig.capture(AgentState(0.05,3,0.5,0.01,0))
            baseline.pair.road.save_png(args.out/'road_model_first.png')
            baseline.pair.wide.save_png(args.out/'wide_model_first.png')
            shifted.pair.road.save_png(args.out/'road_model_shifted.png')
            shifted.pair.wide.save_png(args.out/'wide_model_shifted.png')
            if (baseline.pair.road.sha256==shifted.pair.road.sha256 or
                    baseline.pair.wide.sha256==shifted.pair.wide.sha256):
                raise RuntimeError('MetaDrive pose change did not change both camera images')
            result={
                'classification':'METADRIVE_REAL_RENDER_PINHOLE_INTRINSICS_ONLY',
                'scoring_allowed':False, 'cd210_used':False, 'real_vehicle_testing':False,
                'camera_audit':{k:v.to_dict() for k,v in shifted.audit.items()},
                'distinct_frames_road':2, 'distinct_frames_wide':2,
                'warning':'Real MetaDrive render, but lens distortion/extrinsics/photometrics and model driving fidelity are NOT validated',
            }
        (args.out/'optical_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k not in ('camera_audit','records')},ensure_ascii=False,indent=2))
        return 0
    finally:
        rig.close()


if __name__=='__main__':
    raise SystemExit(main())
