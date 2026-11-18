"""Prepare/check the recorded worker; this CLI never starts a native/model run."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    for name in ('preflight', 'process-check'):
        p = sub.add_parser(name)
        p.add_argument('--out', required=True, type=Path)
    child = sub.add_parser('internal-check', help=argparse.SUPPRESS)
    child.add_argument('--out', required=True, type=Path)
    child.add_argument('--parent', required=True, type=int)
    child.add_argument('--nonce', required=True)
    child.add_argument('--seed', required=True, type=int)
    child.add_argument('--scene', required=True)
    args = parser.parse_args()
    from bigbench import full_s_recorded_worker as worker
    if args.mode == 'internal-check':
        return worker.worker_check(args)
    if args.mode == 'process-check':
        result = worker.process_check(args.out)
    else:
        out = worker._fresh(args.out)
        result = worker.preflight()
        worker._write_receipt(out/'preflight.json', result)
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
