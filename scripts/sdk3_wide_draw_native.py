"""Run an owned canonical short capture with the scoped GL observation when requested."""

from hashlib import sha256
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import sdk3_wide_draw_contract as contract
from bigbench.recorded_official_execution import clone
from scripts import sdk3_wide_framebuffer_native as native
from scripts.sdk3_wide_draw import trace_draws


def exact_loader(args):
    if args.context!='cloud-local':
        return False
    actual=os.environ.get('LD_PRELOAD')
    if args.trial=='control':
        return not actual
    return actual=='/observer.so' and sha256(Path(actual).read_bytes()).hexdigest()==os.environ.get('SDK3_OBSERVER_SHA')


if __name__=='__main__':
    child=clone(native.child,c=contract,post_capture=trace_draws,expected_loader=exact_loader)
    raise SystemExit(clone(native.main,c=contract,__file__=__file__,child=child)())
