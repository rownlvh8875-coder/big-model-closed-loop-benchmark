"""One fixed MetaDrive road/wide RGB pair, two fresh official ONNX sessions.

This is strictly an inference determinism *isolation* experiment, not a
closed-loop camera run, a lane benchmark, or a model ranking.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

from bigbench.curved_lane_scenarios import SCENARIOS, select_native_curve_lanes
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.native_model_campaign import CampaignSpec,NativeWorldCamera
from bigbench.onnx_policy import OnnxBigModelPolicy
from bigbench.frozen_camera_diagnostic import isolate_model_repeatability


def main(argv=None):
    p=argparse.ArgumentParser(description='Pinned ONNX frozen native RGB inference isolation, never model scoring')
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--scenario',choices=('s_curve_left_right','s_curve_right_left'),
                   default='s_curve_left_right')
    p.add_argument('--steps',type=int,default=12)
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--out',type=Path,default=Path('output/frozen-native-onnx'))
    args=p.parse_args(argv)
    spec=CampaignSpec(scenario=args.scenario,steps=args.steps,
                      seed=args.seed,speed_mps=8.)
    provider=NativeMetaDriveProvider(seed=args.seed,map_config=SCENARIOS[spec.scenario].map_config())
    try:
        native_lanes=select_native_curve_lanes(provider.env.current_map,SCENARIOS[spec.scenario])
        if not native_lanes:
            raise RuntimeError('native curve ground truth absent')
        result=isolate_model_repeatability(
            make_policy=lambda:OnnxBigModelPolicy(args.model,args.spec),
            native_camera=NativeWorldCamera(provider),
            lane=native_lanes[0],spec=spec)
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out/'fixed_camera_inference_report.json').write_text(
            json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
            encoding='utf-8')
        print('FROZEN_NATIVE_RGB_MODEL_REPEAT',result['status'],flush=True)
        if result.get('comparison'):
            print('FROZEN_NATIVE_RGB_MAX_POSE_DIFFERENCE_M',
                  result['comparison']['max_pose_disagreement_m'],flush=True)
        return 0 if result['status']=='SYNTHETIC_REPEATED_DIAGNOSTIC_MATCH' else 1
    finally:
        provider.close()


if __name__=='__main__':
    raise SystemExit(main())
