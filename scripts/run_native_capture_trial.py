"""Run one fresh native process; accept Xvfb cleanup status only with evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from scripts.compare_native_capture_schedule import SCHEDULES, validate_schedule_trial
from scripts.compare_native_pssm_cross_process import SEEDS, SCENES


def run_capture(*,seed:int,scene:str,arm:str,out:Path)->int:
    if seed not in SEEDS or scene not in SCENES or arm not in SCHEDULES:
        raise ValueError('unknown native capture condition')
    if out.exists():
        raise ValueError('preexisting output cannot prove a fresh native process')
    out.parent.mkdir(parents=True,exist_ok=True)
    mode,_=SCHEDULES[arm]
    command=['xvfb-run','-a',sys.executable,'-m','scripts.native_raw_pixel_clock',
             '--seed',str(seed),'--scenario',scene,'--fraction','0.12',
             '--mode',mode,'--ablation','baseline','--frames','10','--warmup','2',
             '--out',str(out)]
    status=subprocess.run(command).returncode
    if status not in (0,5):
        return status
    validate_schedule_trial(json.loads(out.read_text()),seed,scene,arm)
    if status==5:
        print('XVFB_CLEANUP_STATUS_5_WITH_VALIDATED_FRESH_NATIVE_RECEIPT',out,flush=True)
    return 0


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed',type=int,choices=SEEDS,required=True)
    p.add_argument('--scene',choices=SCENES,required=True)
    p.add_argument('--arm',choices=SCHEDULES,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    return run_capture(seed=a.seed,scene=a.scene,arm=a.arm,out=a.out)


if __name__=='__main__':
    raise SystemExit(main())
