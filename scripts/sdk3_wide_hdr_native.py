"""Bind the two diagnostic GPU reads to the existing owned wide camera capture."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import sdk3_wide_hdr_contract as contract
from bigbench.recorded_official_execution import clone
from scripts import sdk3_wide_framebuffer_native as native
from scripts.sdk3_wide_hdr import capture_hdr


if __name__=='__main__':
    child=clone(native.child,c=contract,post_capture=capture_hdr)
    raise SystemExit(clone(native.main,c=contract,__file__=__file__,child=child)())
