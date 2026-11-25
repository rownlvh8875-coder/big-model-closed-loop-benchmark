"""Bind the exact MSAA readout to the same owned native scene and post-process task."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import sdk3_wide_msaa_contract as contract
from bigbench.recorded_official_execution import clone
from scripts import sdk3_wide_framebuffer_native as native
from scripts.sdk3_wide_msaa import capture_samples


if __name__=='__main__':
    child=clone(native.child,c=contract,post_capture=capture_samples)
    raise SystemExit(clone(native.main,c=contract,__file__=__file__,child=child)())
