"""Run the owned camera control and HDR probe on one Actions runner per history."""

import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bigbench import sdk3_wide_hdr_contract as c
from bigbench.recorded_official_execution import clone
from scripts import panda_sdk3_runtime as pins, run_sdk3_wide_framebuffer as base
from scripts import run_sdk3_four_validation as review, run_sdk3_steering_plan as steering
from scripts import sdk3_four_validation_runtime as runtime
from scripts.verify_sdk3_wide_hdr import verify


def command(*args,**kwargs):
    argv=runtime.native_command(*args,**kwargs)
    argv[argv.index(runtime.ENTRY)]='/work/repo/scripts/sdk3_wide_hdr_native.py'
    return argv


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history',choices=('sequential','sparse'),required=True)
    args=parser.parse_args()
    out=ROOT/'output'/c.OUTPUT/args.history
    bundle=out/'bundle'
    work=out/'work'
    bundle.mkdir(parents=True)
    work.mkdir()
    summary=dict(status='FAILED',trials=[],model_processes=0,inferences=0,history=args.history)
    try:
        identity,run=clone(steering.authenticate,c=c)()
        summary.update(identity)
        pins.write(bundle/'actions-run.json',run)
        driver=subprocess.check_output(['docker','info','--format','{{.CgroupDriver}} {{.CgroupVersion}}'],text=True).strip()
        summary['docker_cgroup']=driver
        pins.need(driver in ('systemd 2','cgroupfs 2'),'actual hosted cgroup v2')
        sdk=review.stage_runtime(work,bundle)
        run_trial=clone(base.run_trial,c=c,command=command,verify=verify)
        for trial in c.TRIALS:
            summary['trials'].append(run_trial(trial,sdk,bundle,identity,args.history))
        pins.need(all(item['status']=='CAPTURE_VERIFIED' for item in summary['trials']),
                  'both owned readout evidence bundles verified')
        summary['status']='CAPTURE_VERIFIED'
    except BaseException as exc:
        summary['failure']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        pins.write(bundle/'summary.json',summary)


if __name__=='__main__':
    main()
