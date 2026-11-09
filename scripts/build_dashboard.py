"""Build a local no-JavaScript HTML diagnosis from existing model receipts."""
from __future__ import annotations
import argparse,json
from pathlib import Path

from bigbench.dashboard import save_diagnostic_dashboard


def main(argv=None):
    p=argparse.ArgumentParser(description='Offline ONNX diagnostic HTML viewer (never a performance rank)')
    p.add_argument('--first',type=Path,required=True)
    p.add_argument('--second',type=Path,required=True)
    p.add_argument('--comparison',type=Path,default=None)
    p.add_argument('--out',type=Path,default=Path('output/model-diagnostic.html'))
    args=p.parse_args(argv)
    a=json.loads(args.first.read_text(encoding='utf-8'))
    b=json.loads(args.second.read_text(encoding='utf-8'))
    compare=json.loads(args.comparison.read_text(encoding='utf-8')) if args.comparison else None
    output=save_diagnostic_dashboard(args.out,[a,b],compare)
    print('OFFLINE_DIAGNOSTIC_DASHBOARD',output)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
