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

import numpy as np

from bigbench.image_adapter import camera_pair_to_model
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
    ap.add_argument('--model-action-frame',choices=('auto','model-frd','world-flu'),default='auto')
    args=ap.parse_args(argv)
    if (args.model is None) != (args.spec is None):
        ap.error('--model and --spec must be supplied together')
    if not 1 <= args.steps <= 20:
        ap.error('--steps must be in 1..20 (bounded optical probe)')
    if args.model is None and args.model_action_frame!='auto':
        ap.error('--model-action-frame requires --model and --spec')
    binding=None
    if args.model is not None:
        from bigbench.public_action_frame import create_public_onnx_policy, _write_binding_receipt
        binding=create_public_onnx_policy(args.model,args.spec,model_action_frame=args.model_action_frame)
    rig=None
    try:
        provider=NativeMetaDriveProvider(seed=args.seed,source_width=args.source_width,
                                         source_height=args.source_height)
        rig=MetaDriveOpticalRig(provider,source_width=args.source_width,
                                 source_height=args.source_height)
        args.out.mkdir(parents=True,exist_ok=True)
        if args.model is not None:
            policy=binding.policy
            result,last=probe_model_with_metadrive(policy,rig,steps=args.steps)
            result['public_action_frame']=binding.receipt()
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
            # Real MetaDrive RGB -> pinhole warp -> model I420/YUV6 tensor.
            # This validates software plumbing, not real comma lens fidelity.
            packed_first = camera_pair_to_model(baseline.pair.road, baseline.pair.wide)
            packed_shifted = camera_pair_to_model(shifted.pair.road, shifted.pair.wide)
            if packed_first.shape != (2, 6, 128, 256) or packed_first.dtype != np.uint8:
                raise RuntimeError('MetaDrive ONNX camera input shape/dtype mismatch')
            if packed_shifted.shape != packed_first.shape or packed_shifted.dtype != packed_first.dtype:
                raise RuntimeError('MetaDrive ONNX camera input changed contract')
            if np.array_equal(packed_first[0], packed_first[1]):
                raise RuntimeError('Road and wide ONNX camera inputs are identical')
            if np.array_equal(packed_first, packed_shifted):
                raise RuntimeError('MetaDrive pose shift did not change ONNX camera tensor')
            if (baseline.pair.road.sha256==shifted.pair.road.sha256 or
                    baseline.pair.wide.sha256==shifted.pair.wide.sha256):
                raise RuntimeError('MetaDrive pose change did not change both camera images')
            result={
                'classification':'METADRIVE_REAL_RENDER_PINHOLE_INTRINSICS_ONLY',
                'scoring_allowed':False, 'cd210_used':False, 'real_vehicle_testing':False,
                'camera_audit':{k:v.to_dict() for k,v in shifted.audit.items()},
                'distinct_frames_road':2, 'distinct_frames_wide':2,
                'model_input_shape':list(packed_first.shape),
                'model_input_dtype':str(packed_first.dtype),
                'model_input_changed_with_pose':True,
                'model_input_road_wide_distinct':True,
                'warning':'Real MetaDrive render, but lens distortion/extrinsics/photometrics and model driving fidelity are NOT validated',
            }
        (args.out/'optical_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k not in ('camera_audit','records')},ensure_ascii=False,indent=2))
        return 0
    finally:
        try:
            if rig is not None:rig.close()
        finally:
            if binding is not None:
                _write_binding_receipt(binding,args.out/'action_frame_binding.json')


if __name__=='__main__':
    raise SystemExit(main())
