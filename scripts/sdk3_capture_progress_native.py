"""One owned zero-model capture replay with durable boundaries and timed stacks."""
from __future__ import annotations
import argparse,os,sys
from pathlib import Path
from types import FunctionType
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_diagnostic as owner
from scripts.sdk3_capture_progress import Journal,observe,stack_watchdog,wait_observed


def owned_child_command(args,parent_pid):
    return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--repeat','0','--nonce',args.nonce]


def run_with_server(args):
    original=owner.run_with_server
    def wait(child,server,timeout):return wait_observed(child,server,timeout,Path(args.out))
    function=FunctionType(original.__code__,dict(original.__globals__,owned_child_command=owned_child_command,wait_child_then_stop_server=wait),original.__name__,original.__defaults__,original.__closure__)
    function.__kwdefaults__=dict(original.__kwdefaults__ or {});return function(args)


def run_native(args):
    import ctypes,hashlib,json,uuid,zlib
    from scripts import panda_sdk3_runtime as p
    out=Path(args.out);provider=None;journal=None
    report=dict(protocol='sdk3-capture-progress-v1',status='INCOMPLETE',pid=os.getpid(),process_uuid=uuid.uuid4().hex,nonce=args.nonce,repeat=0,seed=20261110,scenario='s_curve_left_right',official_model_processes=0,onnx_inferences=0,model_weights_used=False,repair_proven=False,stage7_complete=False,provider_closed=False,captures=[])
    try:
        p.need(args.server_owner==os.getppid(),'owned capture-only child');journal=Journal(out,dict(pid=os.getpid(),nonce=args.nonce,protocol=report['protocol']))
        def checkpoint(stage):report['checkpoint']=stage;p.write(out/'report.json',report);journal.emit('checkpoint',stage=stage)
        checkpoint('OWNED_BOOT');sys.path.insert(0,p.SITE)
        import numpy as np
        checkpoint('DEPENDENCIES_READY')
        import panda3d.core as core
        report['core_sha256']=p.digest(Path(core.__file__));report['panda_version']=core.PandaSystem.getVersionString()
        preload=ctypes.CDLL(p.SITE+'/panda3d/libpanda.so.1.10',mode=os.RTLD_NOW|os.RTLD_GLOBAL);sdk=ctypes.CDLL(p.SDK_PATH,mode=os.RTLD_NOW|os.RTLD_LOCAL)
        report['sdk_sha256']=p.digest(Path(p.SDK_PATH));p.need(report['core_sha256']==p.CORE_SHA and report['sdk_sha256']==p.SDK_SHA,'frozen core/SDK bytes');checkpoint('SDK_VERIFIED')
        raw=Path('/reference.json').read_bytes();reference=json.loads(raw);report['reference_sha256']=hashlib.sha256(raw).hexdigest()
        from bigbench.metadrive_camera import NativeMetaDriveProvider
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.curved_lane_scenarios import SCENARIOS,select_native_curve_lanes
        from bigbench.kinematics import AgentState
        import metadrive.component.sensors.base_camera as camera_module
        report['base_camera_sha256']=p.digest(Path(camera_module.__file__));checkpoint('PROVIDER_ENTER')
        provider=NativeMetaDriveProvider(seed=20261110,map_config=SCENARIOS['s_curve_left_right'].map_config());engine=provider.env.engine;lane=select_native_curve_lanes(provider.env.current_map,SCENARIOS['s_curve_left_right'])[0]
        s=float(lane.length)*.12;xy=lane.position(s,0.);initial=dict(t=0.,x=float(xy[0]),y=float(xy[1]),heading=float(lane.heading_theta_at(s)),speed=8.)
        poses=[initial,*reference['previous_states']]
        class RGB:
            def __init__(self):self.count=0;self.images=[]
            def record_native_rgb(self,rgb,hashes):
                self.count+=1;self.images=[]
                for camera in ('road','wide'):
                    array=rgb[camera];raw=array.tobytes(order='C');p.need(hashlib.sha256(raw).hexdigest()==hashes[camera],'original copied source bytes');name=f'step{self.count}-{camera}.rgb.zlib';packed=zlib.compress(raw,6);(out/name).write_bytes(packed)
                    self.images.append(dict(camera=camera,file=name,shape=list(array.shape),sha256=hashes[camera],raw_bytes=len(raw),compressed_bytes=len(packed)))
        rgb=RGB();capture=NativeWorldCamera(provider,raw_rgb_observer=rgb);clock=core.ClockObject.getGlobalClock();before_frame=clock.getFrameCount();tasks=lambda:sorted(t.getName() for t in engine.taskMgr.getTasks());report['tasks_before']=tasks()
        sensor=engine.sensors['bigbench_road'];gsg=sensor.buffer.getGsg();report['driver']=dict(vendor=gsg.getDriverVendor(),renderer=gsg.getDriverRenderer(),version=gsg.getDriverVersion())
        attrs=[(capture,'capture'),(engine.taskMgr,'step')]+[(engine.sensors['bigbench_'+kind],name) for kind in ('road','wide') for name in ('perceive','get_rgb_array_cpu')];saved=[(obj,name,getattr(obj,name),name in vars(obj)) for obj,name in attrs]
        checkpoint('WORLD_READY')
        with observe(capture,journal):
            for step,pose in enumerate(poses,1):
                report['active_step']=step;checkpoint('CAPTURE_ENTER');capture.capture(AgentState(**pose));hashes=capture.last_source_rgb_sha256
                report['captures'].append(dict(step=step,pose=pose,road_sha256=hashes['road'],wide_sha256=hashes['wide'],images=rgb.images,task_frame_count_delta=clock.getFrameCount()-before_frame));checkpoint('CAPTURE_RETURN')
        report['observers_restored']=all(getattr(obj,name)==value and (name in vars(obj))==owned for obj,name,value,owned in saved);report['tasks_after']=tasks();report['task_frame_count_delta']=clock.getFrameCount()-before_frame;report['ort_module_loaded']=any(k=='onnxruntime' or k.startswith('onnxruntime.') for k in sys.modules);report['extra_gpu_queries']=report['extra_render_tasks']=0
        report['status']='CAPTURE_REPLAY_RECORDED';checkpoint('REPLAY_COMPLETE');return report
    except BaseException as error:report['failure']=type(error).__name__+': '+str(error);raise
    finally:
        if provider is not None:
            try:provider.close();report['provider_closed']=True
            except BaseException as error:report['close_failure']=type(error).__name__+': '+str(error)
        p.write(out/'report.json',report)
        if journal is not None:
            try:journal.emit('checkpoint',stage='CHILD_FINAL_REPORT')
            finally:journal.close()


def main():
    import faulthandler;faulthandler.enable()
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--nonce',required=True);parser.add_argument('--repeat',type=int,choices=(0,),required=True);parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);args=parser.parse_args();args.model_trial=False
    if args.owned_child:
        with stack_watchdog(Path(args.out)/'stacks.log'):run_native(args)
        return 0
    return 0 if run_with_server(args)==0 else 1

if __name__=='__main__':raise SystemExit(main())
