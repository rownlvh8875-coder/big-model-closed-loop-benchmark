"""Launch the same owned camera controls for the bounded MSAA observation."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import sdk3_wide_msaa_contract as c
from bigbench.recorded_official_execution import clone
from scripts import run_sdk3_wide_hdr as base, sdk3_four_validation_runtime as runtime
from scripts.verify_sdk3_wide_msaa import verify


def command(*args,**kwargs):
    argv=runtime.native_command(*args,**kwargs)
    argv[argv.index(runtime.ENTRY)]='/work/repo/scripts/sdk3_wide_msaa_native.py'
    return argv


if __name__=='__main__':
    clone(base.main,c=c,command=command,verify=verify)()
