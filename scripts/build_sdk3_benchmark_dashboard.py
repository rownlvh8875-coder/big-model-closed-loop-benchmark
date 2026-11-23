"""Independently verify local SDK3 benchmark receipts and write an offline report."""

import argparse
import json
from pathlib import Path

from bigbench.benchmark_results import build_comparison
from bigbench.benchmark_dashboard import render_benchmark_dashboard


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--md-v3',type=Path,required=True)
    parser.add_argument('--light-speed-2',type=Path,required=True)
    parser.add_argument('--longitudinal',type=Path,required=True)
    parser.add_argument('--ramps', type=Path, help='ramp evidence directory with camera-gate.json, probes and models')
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args(argv)
    report = build_comparison(args.md_v3,args.light_speed_2,args.longitudinal)
    if args.ramps is not None:
        from scripts.verify_sdk3_ramps import verify_campaign

        try:
            report['ramp'] = verify_campaign(
                args.ramps/'models', args.ramps/'camera-gate.json', probe_root=args.ramps/'probes')
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(f'cannot verify ramp evidence: {error}')
    args.out.mkdir(parents=True,exist_ok=False)
    with (args.out/'comparison.json').open('x', encoding='utf-8') as output:
        json.dump(report,output,ensure_ascii=False,indent=2,allow_nan=False)
        output.write('\n')
    with (args.out/'index.html').open('x', encoding='utf-8') as output:
        output.write(render_benchmark_dashboard(report))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
