"""Two official large ONNX native-MetaDrive lateral feedback diagnostics.

Outputs are deliberately NOT approved driving rankings, because the virtual
camera domain is an ideal pinhole render rather than calibrated comma imagery.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

from bigbench.native_model_campaign import (
    CampaignSpec, compare_episode_receipts, run_native_episode,
)
from bigbench.onnx_policy import OnnxBigModelPolicy


def main(argv=None):
    p=argparse.ArgumentParser(description='Pinned large ONNX camera feedback comparison, offline only')
    p.add_argument('--first-model',type=Path,required=True)
    p.add_argument('--first-spec',type=Path,required=True)
    p.add_argument('--second-model',type=Path,required=True)
    p.add_argument('--second-spec',type=Path,required=True)
    p.add_argument('--scenario',default='s_curve_left_right',
                   choices=['s_curve_left_right','s_curve_right_left','in_ramp','out_ramp'])
    p.add_argument('--steps',type=int,default=12)
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--speed',type=float,default=8.0)
    p.add_argument('--out',type=Path,default=Path('output/two-model-native'))
    p.add_argument('--repeat-first',action='store_true',help='run model A again as an independent repeatability diagnostic')
    args=p.parse_args(argv)
    spec=CampaignSpec(scenario=args.scenario,steps=args.steps,
                      speed_mps=args.speed,seed=args.seed)
    args.out.mkdir(parents=True,exist_ok=True)
    receipts=[]
    for label,path,manifest in (
        ('model_a',args.first_model,args.first_spec),
        ('model_b',args.second_model,args.second_spec),
    ):
        policy=OnnxBigModelPolicy(path,manifest)
        report=run_native_episode(policy,spec)
        report['model_inference_steps']=len(policy.trace)
        report['inference_elapsed_ms']=[round(t.elapsed_ms,3) for t in policy.trace]
        report['mode']='FIXED_SPEED_LATERAL_ONLY'
        report['model_score_allowed']=False
        (args.out/(label+'.json')).write_text(
            json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
            encoding='utf-8')
        print('NATIVE_BIG_ONNX',label,report['status'],len(policy.trace),
              report['model_sha256'],flush=True)
        receipts.append(report)
        del policy
        gc.collect()
    summary=compare_episode_receipts(receipts[0],receipts[1])
    if not summary['first_camera_sha_equal']:
        raise RuntimeError('initial camera condition differs between models')
    summary['model_hashes']=[r['model_sha256'] for r in receipts]
    summary['optics']='IDEAL_METADRIVE_PINHOLE_NOT_REAL_COMMA_CAMERA'
    summary['real_vehicle_testing']=False
    (args.out/'paired_diagnostic.json').write_text(
        json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
        encoding='utf-8')
    from bigbench.dashboard import save_diagnostic_dashboard
    save_diagnostic_dashboard(args.out/'comparison_dashboard.html',receipts,summary)
    print('OFFLINE_COMPARISON_DASHBOARD_READY',flush=True)
    if args.repeat_first:
        from bigbench.reproducibility import compare_repeat_receipts
        policy=OnnxBigModelPolicy(args.first_model,args.first_spec)
        repeated=run_native_episode(policy,spec)
        repeated['model_inference_steps']=len(policy.trace)
        (args.out/'repeat_model_a.json').write_text(
            json.dumps(repeated,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
            encoding='utf-8')
        repeat=compare_repeat_receipts(receipts[0],repeated)
        (args.out/'repeatability.json').write_text(
            json.dumps(repeat,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
            encoding='utf-8')
        print('OFFLINE_REPEATABILITY',repeat['status'],flush=True)
        del policy
        gc.collect()
    print('PAIR_NATIVE_ONNX_DIAGNOSTIC_PASS',spec.scenario,spec.steps,flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
