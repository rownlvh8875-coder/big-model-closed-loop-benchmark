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
from bigbench.public_action_frame import create_public_onnx_policy, preflight_public_onnx_policy, MODEL_ACTION_FRAMES, _write_binding_receipt


def main(argv=None):
    p=argparse.ArgumentParser(description='Pinned large ONNX camera feedback comparison, offline only')
    p.add_argument('--first-model',type=Path,required=True)
    p.add_argument('--first-spec',type=Path,required=True)
    p.add_argument('--second-model',type=Path,required=True)
    p.add_argument('--second-spec',type=Path,required=True)
    p.add_argument('--first-model-action-frame',choices=MODEL_ACTION_FRAMES,default='auto')
    p.add_argument('--second-model-action-frame',choices=MODEL_ACTION_FRAMES,default='auto')
    p.add_argument('--scenario',default='s_curve_left_right',
                   choices=['s_curve_left_right','s_curve_right_left','in_ramp','out_ramp'])
    p.add_argument('--steps',type=int,default=12)
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--speed',type=float,default=8.0)
    p.add_argument('--out',type=Path,default=Path('output/two-model-native'))
    p.add_argument('--repeat-first',action='store_true',help='run model A again as an independent repeatability diagnostic')
    p.add_argument('--full-s-route',action='store_true',help='validate explicit two-bend route via native road graph')
    args=p.parse_args(argv)
    spec=CampaignSpec(scenario=args.scenario,steps=args.steps,
                      speed_mps=args.speed,seed=args.seed)
    # Both identities/bases must pass before either constructor, provider or episode.
    preflight_public_onnx_policy(args.first_model,args.first_spec,model_action_frame=args.first_model_action_frame)
    preflight_public_onnx_policy(args.second_model,args.second_spec,model_action_frame=args.second_model_action_frame)
    args.out.mkdir(parents=True,exist_ok=True)
    receipts=[]
    for label,path,manifest,declaration in (
        ('model_a',args.first_model,args.first_spec,args.first_model_action_frame),
        ('model_b',args.second_model,args.second_spec,args.second_model_action_frame),
    ):
        binding=create_public_onnx_policy(path,manifest,model_action_frame=declaration)
        policy=binding.policy
        try:
            report=run_native_episode(policy,spec,full_s_route=args.full_s_route)
        finally:
            _write_binding_receipt(binding,args.out/(label+'_action_frame_binding.json'))
        report['public_action_frame']=binding.receipt()
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
        del policy,binding
        gc.collect()
    summary=compare_episode_receipts(receipts[0],receipts[1])
    if args.full_s_route and receipts[0].get('explicit_route_lane_ids')!=receipts[1].get('explicit_route_lane_ids'):
        raise RuntimeError('native explicit route differs between model runs')
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
        binding=create_public_onnx_policy(args.first_model,args.first_spec,model_action_frame=args.first_model_action_frame)
        policy=binding.policy
        try:
            repeated=run_native_episode(policy,spec,full_s_route=args.full_s_route)
        finally:
            _write_binding_receipt(binding,args.out/'repeat_model_a_action_frame_binding.json')
        repeated['public_action_frame']=binding.receipt()
        repeated['model_inference_steps']=len(policy.trace)
        (args.out/'repeat_model_a.json').write_text(
            json.dumps(repeated,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
            encoding='utf-8')
        repeat=compare_repeat_receipts(receipts[0],repeated)
        (args.out/'repeatability.json').write_text(
            json.dumps(repeat,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
            encoding='utf-8')
        print('OFFLINE_REPEATABILITY',repeat['status'],flush=True)
        del policy,binding
        gc.collect()
    print('PAIR_NATIVE_ONNX_DIAGNOSTIC_PASS',spec.scenario,spec.steps,flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
