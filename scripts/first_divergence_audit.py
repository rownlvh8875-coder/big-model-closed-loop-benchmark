"""Explicit diagnostic entry points; importing starts no native/model work."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description='Accepted-buffer diagnostic; no original strict PASS claim')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('capture-canary').add_argument('--out',type=Path,required=True)
    commands.add_parser('validate-canary').add_argument('--root',type=Path,required=True)
    trial=commands.add_parser('native-trial')
    study=commands.add_parser('model-study')
    for command in (trial,study):
        command.add_argument('--model',type=Path,required=True)
        command.add_argument('--spec',type=Path,required=True)
        command.add_argument('--out',type=Path,required=True)
    trial.add_argument('--arm',choices=('original','proxy','retention'),required=True)
    trial.add_argument('--repeat',type=int,choices=(0,1),required=True)
    trial.add_argument('--nonce',required=True)
    commands.add_parser('validate-study').add_argument('--root',type=Path,required=True)
    gate=commands.add_parser('verify-accepted-canary')
    gate.add_argument('--request',type=Path,required=True)
    gate.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='validate-canary':
            from bigbench.first_divergence import validate_capture_dataset
            result=validate_capture_dataset(args.root)
        else:
            from bigbench import first_divergence_model as model
            if args.command=='capture-canary':result=model.run_canary(args.out)
            elif args.command=='native-trial':result=model.run_trial(args.model,args.spec,args.arm,args.repeat,args.nonce,args.out)
            elif args.command=='model-study':result=model.run_study(args.model,args.spec,args.out)
            elif args.command=='validate-study':result=model.validate_study(args.root)
            else:result=model.verify_accepted_canary(args.request,args.out)
    except (ValueError,RuntimeError,OSError) as exc:
        print(json.dumps(dict(status='FAILED_OR_INCOMPLETE',error=f'{type(exc).__name__}: {exc}',original_strict_pass=False)),flush=True)
        return 1
    print(json.dumps({k:v for k,v in result.items() if k in ('status','accepted_pairs','capture_count','model_calls')},allow_nan=False),flush=True)
    return 1 if result.get('status')=='FAILED_OR_INCOMPLETE' else 0


if __name__=='__main__':raise SystemExit(main())
