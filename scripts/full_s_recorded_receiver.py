"""Plan/verify recorded full-S diagnostics; no model/native execution mode."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('plan')
    verify=sub.add_parser('verify');verify.add_argument('--trial-dir',required=True,type=Path);verify.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(argv)
    from bigbench.full_s_recorded_receiver import plan,inspect_trial
    from bigbench.full_s_recorded_worker import need,_fresh,_write_receipt
    if args.command=='plan':print(json.dumps(plan(),indent=2));return 0
    output=args.out.absolute();source=args.trial_dir.absolute()
    need(not source.is_symlink() and all(not p.is_symlink() for p in source.parents) and
         not output.is_symlink() and all(not p.is_symlink() for p in output.parents),'nonsymlink input/output paths required')
    output=output.resolve();source=source.resolve()
    need(not output.is_relative_to(source) and not source.is_relative_to(output) and
         not output.exists() and not output.is_symlink() and all(not p.is_symlink() for p in output.parents),
         'fresh output outside evidence with nonsymlink ancestors required before writes')
    if sys.flags.no_site:
        from bigbench.worker_ownership import prepare_interpreter
        prepare_interpreter(paths_only=True)
    result=inspect_trial(source)
    output=_fresh(output);_write_receipt(output/'receiver.json',result)
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
