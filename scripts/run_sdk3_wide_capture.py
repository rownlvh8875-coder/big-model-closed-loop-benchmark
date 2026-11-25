"""Run one fresh camera-only capture process on a proven Actions runner."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bigbench import sdk3_wide_capture_contract as c
from bigbench.recorded_official_execution import clone
from scripts import sdk3_four_validation_runtime as runtime
from scripts import run_sdk3_four_validation as review, run_sdk3_steering_plan as steering
from scripts import panda_sdk3_runtime as pins
from scripts.verify_sdk3_wide_capture import verify_native


class Deadline:
    @staticmethod
    def run(argv,**kwargs):
        if argv[:3]==['docker','start','--attach']:
            kwargs['timeout']=c.LIMITS['seconds_per_process']+35
        return subprocess.run(argv,**kwargs)


def command(*args,**kwargs):
    argv=runtime.native_command(*args,**kwargs)
    argv[argv.index(runtime.ENTRY)]='/work/repo/scripts/sdk3_wide_capture_native.py'
    return argv


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',choices=c.TRIALS,required=True)
    args=parser.parse_args()
    out=ROOT/'output'/c.OUTPUT/args.trial
    bundle=out/'bundle'
    bundle.mkdir(parents=True)
    work=out/'work'
    work.mkdir()
    summary=dict(trial=args.trial,status='FAILED',official_model_processes=0,
                 inference_bounds=[0,0],camera_process_bounds=[0,0],capture_attempt_bounds=[0,0])
    try:
        identity,run=clone(steering.authenticate,c=c)()
        summary.update(identity)
        pins.write(bundle/'actions-run.json',run)
        cgroup=subprocess.check_output(['docker','info','--format','{{.CgroupDriver}} {{.CgroupVersion}}'],text=True).strip()
        summary['docker_cgroup']=cgroup
        pins.need(cgroup in ('systemd 2','cgroupfs 2'),'native cgroup-v2')
        sdk=review.stage_runtime(work,bundle)
        native=bundle/'native'
        arguments=['--trial',args.trial,'--source',identity['source'],
                   '--activation',identity['activation'],'--run-id',identity['run_id']]
        summary.update(camera_process_bounds=[0,1],capture_attempt_bounds=[0,c.LIMITS['captures_per_process']])
        execution=clone(runtime.run_container,container_command=command,subprocess=Deadline)(
            f'wide-step44-{identity["run_id"]}-{args.trial}',sdk,native,arguments)
        summary['execution']=execution
        if execution['start_attempted'] is False:
            summary.update(camera_process_bounds=[0,0],capture_attempt_bounds=[0,0])
        if (native/'native-child.json').is_file() and (native/'report.json').is_file():
            child=review.read(native/'native-child.json')
            report=review.read(native/'report.json')
            if child.get('pid')==report.get('pid') and report.get('pid',0)>1:
                low=report['camera_capture_attempts']
                high=low if report['status']=='CAPTURE_COMPLETE' else c.LIMITS['captures_per_process']
                summary.update(camera_process_bounds=[1,1],capture_attempt_bounds=[low,high])
        pins.need(execution['returncode']==0 and not execution['failure'],'owned capture process and native logs')
        pins.need(all(report[key]==value for key,value in identity.items()),'bound owned camera identity')
        result=verify_native(native,ROOT/c.POSES,args.trial)
        summary['status']=result['status']
        pins.write(bundle/'verified.json',result)
    except BaseException as exc:
        summary['failure']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        pins.write(bundle/'summary.json',summary)


if __name__=='__main__':
    main()
