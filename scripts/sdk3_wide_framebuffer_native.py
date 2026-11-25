"""Compare one original wide FBO read to the existing RAM snapshot without a model."""

import argparse
from contextlib import ExitStack, nullcontext
from dataclasses import asdict
import json
import os
from pathlib import Path
import platform
import secrets
import sys
from time import perf_counter_ns

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bigbench import sdk3_wide_framebuffer_contract as c
from bigbench.recorded_official_execution import clone
from bigbench.sdk3_steering_contract import live_limits
from scripts import panda_sdk3_diagnostic as owner, panda_sdk3_runtime as pins
from scripts.sdk3_four_validation_native import bootstrap
from scripts.sdk3_four_validation_trial import atomic_json
from scripts.sdk3_wide_capture_native import CameraTiming, save
from scripts.sdk3_wide_framebuffer import POINT, patch_rgb, post_capture


def cpu_context():
    fields={}
    for line in Path('/proc/cpuinfo').read_text().split('\n\n')[0].splitlines():
        key,sep,value=line.partition(':')
        if sep and key.strip() in ('vendor_id','model name','cpu family','model','stepping','flags'):
            fields[key.strip()]=value.strip()
    return dict(architecture=platform.machine(),kernel=platform.release(),cpu=fields)


def expected_loader(args):
    return not os.environ.get("LD_PRELOAD")


def child(args):
    out=Path(args.out)
    report=dict(status='FAILED',context=args.context,trial=args.trial,history=args.history,pid=os.getpid(),nonce=args.nonce,
                source=args.source,activation=args.activation,run_id=args.run_id,provider_closed=False,
                camera_capture_attempts=0,model_processes=0,inferences=0,frames=[],point=list(POINT),
                fbo_observations=[])
    path=out/'report.json'
    atomic_json(path,report)
    provider=None
    try:
        pins.need(args.owner==os.getppid() and Path('/tmp/.X11-unix/X99').exists(),'owned original X server')
        pins.need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
                  and expected_loader(args),'original isolated native environment')
        request=json.loads((ROOT/c.REQUEST).read_bytes())
        pins.need(request==dict(source=args.source,mode=c.MODE,limits=c.LIMITS),'exact registered camera-only request')
        if args.context=='actions':
            pins.need(args.run_id.isdecimal(),'real Actions run identifier')
            report['effective_resources']=live_limits()
        else:
            pins.need(args.run_id=='cloud-local','local diagnostic label')
        report['cpu_context']=cpu_context()
        core,preload,sdk=bootstrap(report)
        from bigbench.full_s_validation import validate_route
        from bigbench.kinematics import AgentState
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.optical_calibration import intrinsics_from_panda_lens
        from bigbench.preprocess_experiment import LiveInput
        from metadrive.component.sensors import base_camera
        from scripts.sdk3_four_validation_trial import _world,driver_info
        from scripts.sdk3_priority_model_native import source_stats_after

        pins.need(pins.digest(base_camera.__file__)==c.BASE_CAMERA_SHA,'original BaseCamera bytes')
        source=ROOT/c.POSES
        archived=json.loads(source.read_bytes())
        report.update(pose_source_sha256=pins.digest(source),source_stats_before=source_stats_after())
        provider,lanes,terrain=_world(*c.CASE)
        lenses={role:intrinsics_from_panda_lens(provider.env.engine.sensors['bigbench_'+role].get_lens(),964,604)
                for role in ('road','wide')}
        report.update(driver=driver_info(provider),geometry=validate_route(lanes),terrain=terrain,
                      intrinsics={key:asdict(value) for key,value in lenses.items()})
        pins.need(all(report[key]==archived[key] for key in ('driver','geometry','intrinsics')),
                  'same historical driver, geometry and lenses')
        inputs=LiveInput(NativeWorldCamera(provider),lenses,c.VARIANT,out)
        with ExitStack() as stack:
            timing=CameraTiming(provider,stack)
            for frame in archived['frames'][:c.LIMITS['captures_per_process']]:
                step=frame['step']
                if args.history=='sparse' and step not in (1,archived['focus_step']):
                    continue
                report['camera_capture_attempts']+=1
                focus=step==archived['focus_step']
                observed=focus and args.trial=='framebuffer'
                event_scope=post_capture(provider,timing,report['fbo_observations']) if observed else nullcontext()
                timing.events=[]
                with event_scope:
                    begin=perf_counter_ns()
                    pair=inputs.capture(AgentState(**frame['pose']))
                    end=perf_counter_ns()
                images,_=inputs.pending
                tensor=inputs.prepare(pair.road,pair.wide)
                report['frames'].append(dict(step=step,pose=frame['pose'],hashes=inputs.rows[-1]))
                if focus:
                    report.update(callback_restored=True,ram_patch_top_down=patch_rgb(images),
                                  timings=dict(step=step,pose=frame['pose'],wait_begin_ns=begin,
                                               capture_begin_ns=begin,capture_end_ns=end,
                                               preprocessing_end_ns=perf_counter_ns(),events=timing.events))
                    pixels={}
                    for role in ('road','wide'):
                        pixels[role]=dict(source=save(out/f'44-{role}-source.rgb.zlib',images[role].tobytes()),
                                          canvas=save(out/f'44-{role}-canvas.rgb.zlib',getattr(pair,role).rgb))
                    pixels['tensor']=save(out/'44-input.bin.zlib',tensor.tobytes())
                    report['pixels']=pixels
                    report['timings']['evidence_write_end_ns']=perf_counter_ns()
                atomic_json(path,report)
        report.update(status='CAPTURE_COMPLETE',source_stats_after=source_stats_after())
        return 0
    except BaseException as exc:
        report['failure']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        try:
            if provider is not None:
                provider.close()
                report['provider_closed']=True
        finally:
            report['ort_module_loaded']=any(key=='onnxruntime' or key.startswith('onnxruntime.') for key in sys.modules)
            atomic_json(path,report)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('out','source','activation','run-id'):
        parser.add_argument('--'+key,required=True)
    parser.add_argument('--context',choices=('actions','cloud-local'),required=True)
    parser.add_argument('--trial',choices=c.TRIALS,required=True)
    parser.add_argument('--history',choices=('sequential','sparse'),default='sequential')
    parser.add_argument('--owner',type=int)
    parser.add_argument('--nonce')
    args=parser.parse_args()
    if args.owner is not None:
        pins.need(isinstance(args.nonce,str) and len(args.nonce)==32,'registered owner nonce')
        return child(args)
    args.nonce=secrets.token_hex(16)
    args.model_trial=False

    def command(params,parent_pid):
        return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),*sys.argv[1:],
                '--owner',str(parent_pid),'--nonce',params.nonce]

    def wait(worker,server,_):
        return owner.wait_child_then_stop_server(worker,server,c.LIMITS['seconds_per_process'])

    return clone(owner.run_with_server,owned_child_command=command,wait_child_then_stop_server=wait)(args)


if __name__=='__main__':
    raise SystemExit(main())
