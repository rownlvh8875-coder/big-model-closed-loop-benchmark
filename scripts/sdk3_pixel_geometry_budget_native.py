"""Measured-budget geometry observer over unchanged progress-native bootstrap."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from types import FunctionType
import argparse,hashlib,os,sys,zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_diagnostic as owner,panda_sdk3_runtime as p,sdk3_capture_progress_native as progress
from scripts.sdk3_capture_progress import observe,stack_watchdog,wait_observed


def wait_renderer(child,server,legacy_timeout,out):
    p.need(legacy_timeout==160,'known zero-model legacy wait,not model resource selection')
    return wait_observed(child,server,600,out)


def owned_child_command(args,parent_pid):
    return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--repeat','0','--nonce',args.nonce]


def run_with_server(args):
    original=owner.run_with_server
    def wait(child,server,timeout):return wait_renderer(child,server,timeout,Path(args.out))
    function=FunctionType(original.__code__,dict(original.__globals__,owned_child_command=owned_child_command,wait_child_then_stop_server=wait),original.__name__,original.__defaults__,original.__closure__)
    function.__kwdefaults__=dict(original.__kwdefaults__ or {});return function(args)


@contextmanager
def geometry_observe(camera,journal,out,nonce,snapshot=None):
    # Called only after unchanged bootstrap has enabled the pinned site/SDK.
    from scripts import sdk3_pixel_geometry as g
    out=Path(out);engine=camera.provider.env.engine;sensor=engine.sensors['bigbench_road'];stats=None
    saved=[(obj,name,getattr(obj,name),name in vars(obj)) for obj,name in [(camera,'capture'),(engine.taskMgr,'step')]+[(engine.sensors['bigbench_'+kind],name) for kind in ('road','wide') for name in ('perceive','get_rgb_array_cpu')]]
    manifest=dict(protocol='sdk3-pixel-geometry-budget-v1',pid=journal.identity['pid'],nonce=nonce,status='INSTALLED',child_timeout_seconds=600,container_timeout_seconds=630,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False)
    p.write(out/'geometry-observer.json',manifest)
    def inspect(rgb):
        p.need(journal.step==7 and journal.camera=='road','actual seventh borrowed Road read')
        raw=rgb.tobytes(order='C');packed=zlib.compress(raw,6);name='target-road.rgb.zlib';(out/name).write_bytes(packed)
        manifest.update(status='CPU_SCAN_STARTED',target_step=7,target_pixel_xy=[596,494],target_pixel_rgb=rgb[494,596].tolist(),target_read_sha256=hashlib.sha256(raw).hexdigest(),target_image=dict(camera='road',file=name,shape=list(rgb.shape),sha256=hashlib.sha256(raw).hexdigest(),raw_bytes=len(raw),compressed_bytes=len(packed)),observer=dict(stats))
        p.write(out/'geometry-observer.json',manifest);journal.emit('checkpoint',stage='GEOMETRY_ENTER',target_sha256=manifest['target_read_sha256'])
        if snapshot is None:
            import panda3d.core as core
            from scripts.sdk3_pixel_geometry_native import snapshot_geometry
            geometry=snapshot_geometry(core,engine,sensor,out)
        else:geometry=snapshot(engine,sensor,out)
        manifest.update(status='GEOMETRY_RECORDED',geometry=geometry);p.write(out/'geometry-observer.json',manifest);journal.emit('checkpoint',stage='GEOMETRY_RETURN')
    try:
        with observe(camera,journal):
            with g.post_read_observer(sensor,inspect,target_call=7) as stats:yield
    except BaseException as error:manifest['failure']=type(error).__name__+': '+str(error);raise
    finally:
        manifest['observer']=dict(stats) if stats is not None else None
        manifest['observers_restored']=all(getattr(obj,name)==value and (name in vars(obj))==owned for obj,name,value,owned in saved)
        p.write(out/'geometry-observer.json',manifest)


def run_native(args):
    p.need(args.server_owner==os.getppid(),'owned measured-budget child')
    p.write(Path(args.out)/'geometry-observer.json',dict(protocol='sdk3-pixel-geometry-budget-v1',pid=os.getpid(),nonce=args.nonce,status='OWNED_BOOT',child_timeout_seconds=600,container_timeout_seconds=630,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False))
    def observer(camera,journal):return geometry_observe(camera,journal,Path(args.out),args.nonce)
    original=progress.run_native;function=FunctionType(original.__code__,dict(original.__globals__,observe=observer),original.__name__,original.__defaults__,original.__closure__);function.__kwdefaults__=dict(original.__kwdefaults__ or {});return function(args)


def main():
    import faulthandler;faulthandler.enable()
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--nonce',required=True);parser.add_argument('--repeat',type=int,choices=(0,),required=True);parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);args=parser.parse_args();args.model_trial=False
    if args.owned_child:
        with stack_watchdog(Path(args.out)/'stacks.log'):run_native(args)
        return 0
    return 0 if run_with_server(args)==0 else 1
if __name__=='__main__':raise SystemExit(main())
