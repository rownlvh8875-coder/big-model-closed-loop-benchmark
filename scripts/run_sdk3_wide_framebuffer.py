"""Run two fresh camera processes consecutively on the same Actions runner."""

import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bigbench import sdk3_wide_framebuffer_contract as c
from bigbench.recorded_official_execution import clone
from scripts import panda_sdk3_runtime as pins
from scripts import run_sdk3_four_validation as review, run_sdk3_steering_plan as steering
from scripts import sdk3_four_validation_runtime as runtime
from scripts.verify_sdk3_wide_framebuffer import verify


class Deadline:
    @staticmethod
    def run(argv,**kwargs):
        if argv[:3]==['docker','start','--attach']:
            kwargs['timeout']=c.LIMITS['seconds_per_process']+35
        return subprocess.run(argv,**kwargs)


def command(*args,**kwargs):
    argv=runtime.native_command(*args,**kwargs)
    argv[argv.index(runtime.ENTRY)]='/work/repo/scripts/sdk3_wide_framebuffer_native.py'
    return argv


def run_trial(trial, sdk, bundle, identity):
    target=bundle/trial
    target.mkdir()
    item=dict(trial=trial,status='FAILED',model_processes=0,inferences=0,
              camera_process_bounds=[0,1],camera_capture_bounds=[0,c.LIMITS['captures_per_process']])
    pins.write(target/'summary.json',item)
    try:
        native=target/'native'
        args=['--context','actions','--trial',trial,'--source',identity['source'],
              '--activation',identity['activation'],'--run-id',identity['run_id']]
        execution=clone(runtime.run_container,container_command=command,subprocess=Deadline)(
            f'wide-fbo-{identity["run_id"]}-{trial}',sdk,native,args)
        item['execution']=execution
        if execution['start_attempted'] is False:
            item.update(camera_process_bounds=[0,0],camera_capture_bounds=[0,0])
        if (native/'report.json').is_file() and (native/'native-child.json').is_file():
            report=review.read(native/'report.json')
            child=review.read(native/'native-child.json')
            if report.get('pid')==child.get('pid') and report.get('pid',0)>1:
                progress=report['camera_capture_attempts']
                upper=progress if report['status']=='CAPTURE_COMPLETE' else c.LIMITS['captures_per_process']
                item.update(camera_process_bounds=[1,1],camera_capture_bounds=[progress,upper])
        pins.need(execution['returncode']==0 and not execution['failure'],'actual camera child completion')
        pins.need(all(report[key]==value for key,value in identity.items()),'exact hosted native provenance')
        proof=verify(native,ROOT/c.POSES,trial,'actions')
        pins.write(target/'verified.json',proof)
        item['status']='CAPTURE_VERIFIED'
    except Exception as exc:
        item['failure']=f'{type(exc).__name__}: {exc}'
    finally:
        pins.write(target/'summary.json',item)
    return item


def main():
    out=ROOT/'output'/c.OUTPUT
    bundle=out/'bundle'
    work=out/'work'
    bundle.mkdir(parents=True)
    work.mkdir()
    summary=dict(status='FAILED',trials=[],model_processes=0,inferences=0)
    try:
        identity,run=clone(steering.authenticate,c=c)()
        summary.update(identity)
        pins.write(bundle/'actions-run.json',run)
        driver=subprocess.check_output(['docker','info','--format','{{.CgroupDriver}} {{.CgroupVersion}}'],text=True).strip()
        summary['docker_cgroup']=driver
        pins.need(driver in ('systemd 2','cgroupfs 2'),'actual hosted cgroup v2')
        sdk=review.stage_runtime(work,bundle)
        for trial in c.TRIALS:
            summary['trials'].append(run_trial(trial,sdk,bundle,identity))
        pins.need(all(item['status']=='CAPTURE_VERIFIED' for item in summary['trials']),
                  'both owned diagnostic evidence bundles verified')
        summary['status']='CAPTURE_VERIFIED'
    except BaseException as exc:
        summary['failure']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        pins.write(bundle/'summary.json',summary)


if __name__=='__main__':
    main()
