"""Same pinned ONNX model twice: strict native renderer repeatability gate.

No ranking or image rewriting. The native renderer is initialized separately
for each model run. Camera-convergence is experimental and opt-in.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

from bigbench.native_model_campaign import CampaignSpec,run_native_episode
from bigbench.onnx_policy import OnnxBigModelPolicy
from bigbench.reproducibility import compare_repeat_receipts


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='Native large ONNX same-model repeat experiment (SIM ONLY)')
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--scenario',default='s_curve_left_right',
                   choices=['s_curve_left_right','s_curve_right_left'])
    p.add_argument('--steps',type=int,default=12)
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--speed',type=float,default=8.)
    p.add_argument('--camera-convergence',type=int,default=6)
    p.add_argument('--camera-pixel-tolerance',type=int,default=0)
    p.add_argument('--camera-channel-delta',type=int,default=0)
    p.add_argument('--out',type=Path,default=Path('output/native-strict-repeat'))
    args=p.parse_args(argv)
    spec=CampaignSpec(scenario=args.scenario,seed=args.seed,
                      steps=args.steps,speed_mps=args.speed)
    args.out.mkdir(parents=True,exist_ok=True)
    receipts=[]
    for i in range(2):
        policy=OnnxBigModelPolicy(args.model,args.spec)
        report=run_native_episode(policy,spec,camera_convergence=args.camera_convergence,
                                  camera_pixel_tolerance=args.camera_pixel_tolerance,
                                  camera_rgb_delta=args.camera_channel_delta)
        report['run_index']=i
        report['model_inference_steps']=len(policy.trace)
        (args.out/f'run_{i}.json').write_text(
            json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',
            encoding='utf-8')
        receipts.append(report)
        del policy
        gc.collect()
        print('STRICT_REPEAT_NATIVE_MODEL',i,report['status'],
              report['completed_steps'],'cam',report.get('strict_same_pose_convergence'),flush=True)
    if any(r['status']!='DIAGNOSTIC_EXECUTED' for r in receipts):
        return 2
    decision=compare_repeat_receipts(*receipts)
    decision['strict_convergence_experiment']=True
    decision['camera_convergence_bound']=args.camera_convergence
    decision['pixel_tolerance_count']=args.camera_pixel_tolerance
    decision['channel_tolerance']=args.camera_channel_delta
    decision['bit_exact_camera_required']=args.camera_pixel_tolerance==0
    decision['driving_model_quality_rank_allowed']=False
    decision['real_vehicle_testing']=False
    (args.out/'repeat_decision.json').write_text(
        json.dumps(decision,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
        encoding='utf-8')
    print('STRICT_REPEAT_DECISION',decision['status'],
          decision['max_pose_disagreement_m'],decision['frame_hashes_identical'],flush=True)
    # Repeated_model mismatch is a real failed reproducibility gate.
    return 0 if decision['status']=='SYNTHETIC_REPEATED_DIAGNOSTIC_MATCH' else 1


if __name__=='__main__':
    raise SystemExit(main())
