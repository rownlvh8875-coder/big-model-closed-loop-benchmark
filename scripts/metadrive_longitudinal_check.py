"""Real-model longitudinal synthetic lead perception diagnostic; NEVER rank."""
from __future__ import annotations

import argparse,json
from pathlib import Path

from bigbench.longitudinal_world import scenario
from bigbench.native_longitudinal import NativeLeadVisualRenderer,run_longitudinal_native
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.onnx_policy import OnnxBigModelPolicy


def main(argv=None):
    p=argparse.ArgumentParser(description='Native MetaDrive visual lead-only ONNX input smoke')
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--scenario',choices=['lead_brake','stop_go','cut_in'],default='lead_brake')
    p.add_argument('--steps',type=int,default=26)
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--out',type=Path,default=Path('output/longitudinal-native'))
    args=p.parse_args(argv)
    policy=OnnxBigModelPolicy(args.model,args.spec)
    provider=NativeMetaDriveProvider(seed=args.seed)
    view=None
    try:
        view=NativeLeadVisualRenderer(provider)
        result=run_longitudinal_native(policy,scenario(args.scenario),view,steps=args.steps)
        result['model_inference_steps']=len(policy.trace)
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out/'longitudinal_diagnostic.json').write_text(
            json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        print('NATIVE_LONGITUDINAL_MODEL',result['status'],result['steps_completed'],
              'scoring_allowed',result['model_scoring_allowed'],flush=True)
        if result['status']!='DIAGNOSTIC_EXECUTED' or len(policy.trace)!=args.steps:
            return 1
        return 0
    finally:
        if view is not None:
            view.close()
        provider.close()


if __name__=='__main__':
    raise SystemExit(main())
