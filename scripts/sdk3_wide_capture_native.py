"""Record the original CPU camera pipeline and timing in one owned SDK3 child."""

import argparse
from contextlib import ExitStack
from dataclasses import asdict
import json
import os
from pathlib import Path
import secrets
import sys
import time
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bigbench import sdk3_wide_capture_contract as c
from bigbench.recorded_official_execution import clone
from bigbench.sdk3_steering_contract import live_limits
from scripts import panda_sdk3_diagnostic as owner, panda_sdk3_runtime as pins
from scripts.sdk3_four_validation_native import bootstrap
from scripts.sdk3_four_validation_trial import atomic_json


class CameraTiming:
    """Observe each real task and RAM read without drawing or reading pixels again."""

    def __init__(self, provider, stack):
        self.origin = provider.env.engine.origin
        self.events = []
        self.active = None
        manager = provider.env.engine.taskMgr
        stack.enter_context(patch.object(manager,'step',self.observe('render_task',manager.step)))
        for role in ('road','wide'):
            cam = provider.env.engine.sensors['bigbench_'+role]
            stack.enter_context(patch.object(cam,'get_rgb_array_cpu',self.observe('read_rgb',cam.get_rgb_array_cpu,cam)))
            stack.enter_context(patch.object(cam,'perceive',self.perceive(role,cam)))

    def perceive(self, role, cam):
        original = cam.perceive

        def call(*args,**kwargs):
            pins.need(self.active is None,'one original perception at a time')
            self.active = role
            try:
                return self.observe('perceive',original,cam)(*args,**kwargs)
            finally:
                self.active = None
        return call

    def observe(self, stage, original, cam=None):
        def call(*args,**kwargs):
            event = dict(stage=stage,role=self.active,begin_ns=time.perf_counter_ns())
            self.events.append(event)
            if cam is not None:
                event['image_seq_before'] = cam.copy_texture.get_image_modified().get_seq()
                event['has_ram_before'] = cam.copy_texture.has_ram_image()
                if stage=='read_rgb':
                    event['world_parent'] = cam.cam.getParent()==self.origin
                    event['position'] = list(cam.cam.getPos())
                    event['hpr'] = list(cam.cam.getHpr())
            try:
                return original(*args,**kwargs)
            finally:
                event['end_ns'] = time.perf_counter_ns()
                if cam is not None:
                    event['image_seq_after'] = cam.copy_texture.get_image_modified().get_seq()
        return call


def save(path, data):
    with path.open('xb') as out:
        out.write(zlib.compress(data,1))
    return dict(name=path.name,extent=len(data))


def child(args):
    out=Path(args.out)
    report=dict(protocol='sdk3-wide-camera-timing-v1',status='FAILED',pid=os.getpid(),
                nonce=args.nonce,trial=args.trial,run_id=args.run_id,activation=args.activation,
                source=args.source,captures=[],provider_closed=False,official_model_processes=0,
                inference_bounds=[0,0],camera_capture_attempts=0)
    report_path=out/'report.json'
    atomic_json(report_path,report)
    provider=None
    try:
        pins.need(args.owner==os.getppid() and Path('/tmp/.X11-unix/X99').exists(),'owned X display')
        pins.need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
                  and not os.environ.get('LD_PRELOAD'),'original isolated child')
        pins.need(json.loads((ROOT/c.REQUEST).read_bytes())==dict(
            source=args.source,limits=c.LIMITS,mode=c.MODE),'exact camera-only request')
        report['effective_resources']=live_limits()
        core,preload,sdk=bootstrap(report)
        from bigbench.full_s_validation import validate_route
        from bigbench.kinematics import AgentState
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.optical_calibration import intrinsics_from_panda_lens
        from bigbench.preprocess_experiment import LiveInput
        from metadrive.component.sensors import base_camera
        from scripts.sdk3_four_validation_trial import _world, driver_info
        from scripts.sdk3_priority_model_native import source_stats_after
        import cv2
        import numpy as np
        archived=json.loads((ROOT/c.POSES).read_bytes())
        pins.need(pins.digest(base_camera.__file__)==c.BASE_CAMERA_SHA,'frozen original BaseCamera.perceive')
        pins.need(len(archived['frames'])==c.LIMITS['captures_per_process'] and archived['case']==list(c.CASE),'registered case and pose count')
        report.update(source_stats_before=source_stats_after(),pose_source_sha256=pins.digest(ROOT/c.POSES),
                      numpy=np.__version__,opencv=cv2.__version__,inserted_wait_s=c.TRIALS[args.trial])
        provider,lanes,receipt=_world(*c.CASE)
        lenses={role:intrinsics_from_panda_lens(provider.env.engine.sensors['bigbench_'+role].get_lens(),964,604)
                for role in ('road','wide')}
        report.update(driver=driver_info(provider),geometry=validate_route(lanes),terrain=receipt,
                      intrinsics={role:asdict(lens) for role,lens in lenses.items()})
        pins.need(all(report[k]==archived[k] for k in ('driver','geometry','intrinsics')),'same historical camera and route')
        camera=NativeWorldCamera(provider)
        inputs=LiveInput(camera,lenses,c.VARIANT,out)
        data=out/'pixels'
        data.mkdir()
        with ExitStack() as stack:
            timing=CameraTiming(provider,stack)
            for frame in archived['frames']:
                step=frame['step']
                gap_begin=time.perf_counter_ns()
                if step>1 and report['inserted_wait_s']:
                    time.sleep(report['inserted_wait_s'])
                started=time.perf_counter_ns()
                timing.events=[]
                report['camera_capture_attempts']=step
                pair=inputs.capture(AgentState(**frame['pose']))
                capture_ended=time.perf_counter_ns()
                images,_=inputs.pending
                tensor=inputs.prepare(pair.road,pair.wide)
                preparation_ended=time.perf_counter_ns()
                pixels={role:{
                    'source':save(data/f'{step:02d}-{role}-source.rgb.zlib',images[role].tobytes()),
                    'canvas':save(data/f'{step:02d}-{role}-canvas.rgb.zlib',getattr(pair,role).rgb),
                } for role in ('road','wide')}
                pixels['tensor']=save(data/f'{step:02d}-input.bin.zlib',tensor.tobytes())
                report['captures'].append(dict(step=step,pose=frame['pose'],hashes=inputs.rows[-1],
                    wait_begin_ns=gap_begin,capture_begin_ns=started,capture_end_ns=capture_ended,
                    preprocessing_end_ns=preparation_ended,evidence_write_end_ns=time.perf_counter_ns(),
                    events=timing.events,pixels=pixels))
                atomic_json(report_path,report)
        report.update(source_stats_after=source_stats_after(),status='CAPTURE_COMPLETE')
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
            report['ort_module_loaded']=any(k=='onnxruntime' or k.startswith('onnxruntime.') for k in sys.modules)
            atomic_json(report_path,report)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('out','source','activation','run-id'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--trial',choices=c.TRIALS,required=True)
    parser.add_argument('--owner',type=int)
    parser.add_argument('--nonce')
    args=parser.parse_args()
    if args.owner is not None:
        pins.need(args.nonce is not None and len(args.nonce)==32,'owned nonce')
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
