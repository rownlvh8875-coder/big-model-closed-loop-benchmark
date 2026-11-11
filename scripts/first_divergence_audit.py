"""Explicit diagnostic entry points; importing starts no native/model work."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Accepted-buffer diagnostic; no original strict PASS claim')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('capture-canary').add_argument('--out', type=Path, required=True)
    commands.add_parser('validate-canary').add_argument('--root', type=Path, required=True)
    args = parser.parse_args(argv)
    from bigbench.first_divergence import capture_canary, validate_capture_dataset
    try:
        result = capture_canary(args.out) if args.command == 'capture-canary' else validate_capture_dataset(args.root)
    except (ValueError, RuntimeError, OSError) as exc:
        print(json.dumps(dict(status='FAILED_OR_INCOMPLETE',error=f'{type(exc).__name__}: {exc}',
                              original_strict_pass=False)),flush=True)
        return 1
    print(json.dumps({k: result[k] for k in ('status','accepted_pairs','capture_count','model_calls')},allow_nan=False),flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
