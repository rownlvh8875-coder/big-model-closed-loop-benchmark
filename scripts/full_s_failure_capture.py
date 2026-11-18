"""Plan bounded failure recording or verify a saved sidecar; never run a model."""
from pathlib import Path
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    plan = sub.add_parser('plan', help='CPU/std-library-only storage plan; no activation')
    plan.add_argument('--out', type=Path, required=True)
    verify = sub.add_parser('verify', help='Read existing saved pixels/states; NumPy/OpenCV only')
    verify.add_argument('--record-dir', type=Path, required=True)
    verify.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        parser.error('--out must be fresh')
    if any(p.is_symlink() for p in args.out.absolute().parents):
        parser.error('--out must not have symlink ancestors')
    if args.mode == 'verify':
        record_root = args.record_dir.resolve()
        output_root = args.out.resolve()
        if output_root.is_relative_to(record_root) or record_root.is_relative_to(output_root):
            parser.error('--out must be outside the recording tree')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from bigbench.full_s_failure_capture import recording_plan, verify_recording
    args.out.mkdir(parents=True)
    try:
        result = recording_plan() if args.mode == 'plan' else verify_recording(args.record_dir)
        with (args.out / ('plan.json' if args.mode == 'plan' else 'verification.json')).open('x') as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
        print(json.dumps(result))
        return 0
    except Exception as exc:
        with (args.out/'error.json').open('x') as stream:
            stream.write(json.dumps(dict(status='ERROR', error=type(exc).__name__+': '+str(exc),
                new_model_processes=0, new_inferences=0, all_four_validation_tracks_passed=False), indent=2)+'\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
