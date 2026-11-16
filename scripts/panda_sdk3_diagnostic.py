"""Owned X server outlives SDK/Panda child finalization; fresh controls stay separate."""
import argparse
import ctypes
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_runtime as policy
from scripts.panda_real_glx_objects import Renderer,PRC


def wait_child_then_stop_server(child,server,timeout):
    try:
        try:return child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=10);raise
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=10)
        if server.poll() is None:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)


def run_with_server(args):
    out=Path(args.out);server=None;child=None;status=dict(spawn_attempted=False,pid=None,returncode=None,server_returncode=None)
    try:
        with (out/'xvfb.log').open('wb') as log:
            server=subprocess.Popen(['/usr/bin/Xvfb',':99','-screen','0','1024x768x24','-nolisten','tcp','-ac','-noreset'],stdout=log,stderr=log)
            deadline=time.monotonic()+15
            while not Path('/tmp/.X11-unix/X99').exists():
                policy.need(server.poll() is None and time.monotonic()<deadline,'owned display readiness');time.sleep(.05)
            argv=[sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(os.getpid()),'--out',args.out,'--nonce',args.nonce,'--load-order',args.load_order,'--factory',args.factory]
            if args.reference_wheel:argv+=['--reference-wheel']
            if args.model_trial:argv+=['--model-trial','--seed',str(args.seed),'--scenario',args.scenario]
            status['spawn_attempted']=True;policy.write(out/'native-child.json',status)
            child=subprocess.Popen(argv);status['pid']=child.pid;policy.write(out/'native-child.json',status)
            status['returncode']=wait_child_then_stop_server(child,server,850 if args.model_trial else 160)
            status['server_returncode']=server.returncode
            return status['returncode']
    except BaseException as e:status['failure']=type(e).__name__+': '+str(e);raise
    finally:
        if child is not None and child.poll() is None:child.kill();child.wait(timeout=10)
        if server is not None and server.poll() is None:server.terminate();server.wait(timeout=5)
        status['server_returncode']=None if server is None else server.returncode
        status['container_cgroup_after_child']={}
        for name in ('memory.max','memory.peak','memory.events'):
            path=Path('/sys/fs/cgroup')/name
            if path.exists():status['container_cgroup_after_child'][name]=path.read_text().strip()
        policy.write(out/'native-child.json',status)
        if (out/'report.json').exists():
            report=json.loads((out/'report.json').read_text());report['server_returncode']=status['server_returncode'];report['child_finalized_before_server_stop']=child is not None and child.poll() is not None;policy.write(out/'report.json',report)


def setup_renderer(c,factory,emit):
    emit('PRC_BEFORE');c.load_prc_file_data('sdk3-runtime',PRC);emit('PRC_AFTER');r=Renderer(c);base=None
    if factory=='showbase':
        emit('SHOWBASE_BEFORE');from direct.showbase.ShowBase import ShowBase
        base=ShowBase(windowType='offscreen');r.engine=base.graphicsEngine;r.output=base.win;pipe=base.pipe;camera=base.cam.node();r.camera_node=base.cam;r.scene=base.render;policy.need(r.output is not None and r.output.is_valid(),'standard offscreen output');r.region=camera.get_display_region(0);emit('SHOWBASE_AFTER')
    else:
        emit('ENGINE_BEFORE');r.engine=c.GraphicsEngine();emit('ENGINE_AFTER')
        emit('PIPE_BEFORE');pipe=c.GraphicsPipeSelection.get_global_ptr().make_module_pipe('pandagl');policy.need(pipe is not None,'pandagl pipe');emit('PIPE_AFTER')
        fb=c.FrameBufferProperties();fb.set_rgb_color(True);fb.set_rgba_bits(8,8,8,8);fb.set_depth_bits(0);fb.set_stencil_bits(0);fb.set_multisamples(0);fb.set_srgb_color(False)
        emit('OUTPUT_BEFORE');r.output=r.engine.make_output(pipe,'sdk3-runtime',0,fb,c.WindowProperties.size(8,8),c.GraphicsPipe.BF_refuse_window);policy.need(r.output is not None,'Panda output');r.engine.open_windows();policy.need(r.output.is_valid(),'valid output');emit('OUTPUT_AFTER')
        r.scene=c.NodePath('sdk3-empty-scene');camera=c.Camera('sdk3-camera');camera.set_scene(r.scene);lens=c.OrthographicLens();lens.set_film_size(2,2);lens.set_near_far(.1,10);camera.set_lens(lens);r.camera_node=r.scene.attach_new_node(camera);r.region=r.output.make_display_region();r.region.set_camera(r.camera_node)
    gsg=r.output.get_gsg();policy.need(gsg is not None and gsg.is_valid(),'valid GSG')
    driver=dict(vendor=gsg.get_driver_vendor(),renderer=gsg.get_driver_renderer(),version=gsg.get_driver_version());emit('DRIVER_AFTER')
    r.texture=c.Texture('sdk3-challenge');r.output.add_render_texture(r.texture,c.GraphicsOutput.RTM_copy_ram,c.GraphicsOutput.RTP_color);r.output.set_clear_color_active(True);r.output.set_clear_depth_active(False);r.region.set_clear_color_active(True);r.ready=True
    objects={k:int(v.this) for k,v in dict(pipe=pipe,output=r.output,gsg=gsg,texture=r.texture,camera=camera).items()}
    details=dict(output_class=type(r.output).__name__,active=r.output.is_active(),framebuffer=str(r.output.get_fb_properties()),width=r.output.get_x_size(),height=r.output.get_y_size())
    return r,base,driver,objects,details


def run(args):
    out=Path(args.out);report=dict(status='FAILED',pid=os.getpid(),nonce=args.nonce,load_order=args.load_order,factory=args.factory,observer_instrumented=not args.reference_wheel)
    renderer=None;base=None;stats_fn=None
    def emit(stage):print('STAGE7_EVENT '+json.dumps(dict(stage=stage,pid=os.getpid(),nonce=args.nonce,monotonic=time.monotonic())),flush=True)
    def core_load():
        emit('CORE_BEFORE');sys.path.insert(0,policy.SITE);import panda3d.core as c
        report.update(core_sha256=policy.digest(c.__file__),panda_version=c.PandaSystem.get_version_string());emit('CORE_AFTER');return c
    def sdk_load():
        emit('PRELOAD_BEFORE');preload=ctypes.CDLL(policy.SITE+'/panda3d/libpanda.so.1.10',mode=os.RTLD_NOW|os.RTLD_GLOBAL);emit('PRELOAD_AFTER')
        emit('SDK_BEFORE');sdk=ctypes.CDLL(policy.SDK_PATH,mode=os.RTLD_NOW|os.RTLD_LOCAL);report['sdk_sha256']=policy.digest(policy.SDK_PATH);emit('SDK_AFTER');return preload,sdk
    def stats():
        raw=(ctypes.c_ubyte*80)(*([165]*80));returned=stats_fn(ctypes.addressof(raw)+16);data=bytes(raw[16:64]);fields=dict(configured=(0,4),closed=(4,4),error=(8,4),forwarded=(16,8),resolutions=(24,8),paths=(32,8),events=(40,8))
        return dict(returned=returned,guards_ok=bytes(raw[:16])==bytes(raw[64:])==bytes([165])*16,values={n:int.from_bytes(data[o:o+w],'little') for n,(o,w) in fields.items()})
    try:
        emit('BOOT');policy.need(args.server_owner==os.getppid(),'owned display parent')
        if args.load_order=='core-first':c=core_load();preload,sdk=sdk_load()
        else:preload,sdk=sdk_load();c=core_load()
        expected=policy.REFERENCE_SHA if args.reference_wheel else policy.SDK_SHA
        policy.need(report['sdk_sha256']==expected and report['core_sha256']==policy.CORE_SHA,'actual payload/core bytes')
        if not args.reference_wheel:
            stats_fn=sdk.psd_get_stats;stats_fn.argtypes=[ctypes.c_void_p];stats_fn.restype=ctypes.c_int
        report['source_stats']=[] if stats_fn is None else [stats()]
        emit('SERVER_BEFORE');policy.need(Path('/tmp/.X11-unix/X99').exists(),'parent-owned live display');emit('SERVER_AFTER')
        if args.model_trial:
            policy.need(not args.reference_wheel,'official model requires SDK3');sys.path.insert(0,'/model-deps')
            from scripts.native_mdv3_repeat_trial import run_trial
            value=run_trial(model=Path('/model.onnx'),spec=Path('/work/repo/model_specs/md-v3.json'),scenario=args.scenario,seed=args.seed,steps=12,speed=8.,initial_fraction=.12)
            value.update(selected_sdk_sha256=policy.SDK_SHA,sdk_load_order='core-first');policy.write(out/'run.json',value)
            policy.need(value['status']=='DIAGNOSTIC_EXECUTED' and value['completed_steps']==12,'complete official model trial');report['status']='OFFICIAL_MODEL_TRIAL_OBSERVED';return report
        renderer,base,report['driver'],report['objects'],report['output_properties']=setup_renderer(c,args.factory,emit);report['frames']=[]
        for i in range(2):
            emit(f'FRAME_{i}_BEFORE');raw=renderer.render(policy.challenge(args.nonce,i));report['frames'].append(dict(index=i,raw_hex=raw.hex(),nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()));emit(f'FRAME_{i}_AFTER')
        emit('CLEANUP_BEFORE');report['cleanup']=renderer.close()
        if base is not None:base.destroy();base=None
        if stats_fn is not None:report['source_stats'].append(stats())
        emit('CLEANUP_AFTER');report['status']='PANDA_REFERENCE_GLX_FRAMES_OBSERVED' if args.reference_wheel else 'SDK3_GLX_FRAMES_OBSERVED';return report
    except BaseException as e:report['failure']=type(e).__name__+': '+str(e);raise
    finally:
        if renderer is not None and not renderer.closed:
            try:report['failure_cleanup']=renderer.close()
            except Exception as e:report['failure_cleanup_error']=str(e)
        if base is not None:
            try:base.destroy()
            except Exception as e:report['base_cleanup_error']=str(e)
        policy.write(out/'report.json',report)


def run_pair(args):
    out=Path(args.out);ledger=[];failure=None
    try:
        for index in range(2):
            dest=out/f'run-{index}';dest.mkdir();nonce=secrets.token_hex(16)
            row=dict(index=index,launcher_spawn_attempted=True,launcher_pid=None,spawn_attempted=False,pid=None,returncode=None);ledger.append(row);policy.write(out/'pair-ledger.json',ledger)
            env=dict(os.environ,HOME='/tmp/home-'+nonce,XDG_CACHE_HOME='/tmp/cache-'+nonce);Path(env['HOME']).mkdir()
            with (dest/'stdout.log').open('wb') as stdout,(dest/'stderr.log').open('wb') as stderr:
                launcher=subprocess.Popen([sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--out',str(dest),'--model-trial','--nonce',nonce,'--seed',str(args.seed),'--scenario',args.scenario],stdout=stdout,stderr=stderr,env=env)
                row['launcher_pid']=launcher.pid;policy.write(out/'pair-ledger.json',ledger)
                try:row['returncode']=launcher.wait(timeout=880)
                except subprocess.TimeoutExpired:launcher.kill();launcher.wait(timeout=10);row['returncode']=launcher.returncode;raise
                finally:
                    if (dest/'native-child.json').exists():
                        native=json.loads((dest/'native-child.json').read_text());row['spawn_attempted']=native['spawn_attempted'];row['pid']=native['pid']
                    policy.write(out/'pair-ledger.json',ledger)
            policy.need(row['returncode']==0,'complete official model child')
    except BaseException as e:failure=type(e).__name__+': '+str(e);raise
    finally:policy.write(out/'pair.json',dict(status='FAILED' if failure else 'PAIR_COMPLETED',failure=failure,counts=policy.observed_model_processes(ledger)))


def main():
    faulthandler.enable();p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--nonce',default='00'*16);p.add_argument('--load-order',choices=['core-first','sdk-first'],default='core-first');p.add_argument('--factory',choices=['manual','showbase'],default='manual');p.add_argument('--reference-wheel',action='store_true');p.add_argument('--owned-child',action='store_true');p.add_argument('--server-owner',type=int);p.add_argument('--model-trial',action='store_true');p.add_argument('--model-pair',action='store_true');p.add_argument('--seed',type=int);p.add_argument('--scenario');args=p.parse_args()
    if args.model_pair:run_pair(args);return 0
    if args.owned_child:run(args);return 0
    return run_with_server(args)

if __name__=='__main__':raise SystemExit(main())
