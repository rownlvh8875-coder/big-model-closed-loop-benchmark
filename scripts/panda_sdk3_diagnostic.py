"""Granular actual SDK3/Panda/GLX checkpoints inside a disposable image."""
import argparse
import ctypes
import faulthandler
import hashlib
import json
import os
import secrets
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_runtime as policy
from scripts.panda_real_glx_objects import Renderer


def run(args):
    out=Path(args.out);report=dict(status='FAILED',pid=os.getpid(),nonce=args.nonce,load_order=args.load_order)
    server=None;renderer=None;server_log=None;stats_fn=None
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
        emit('BOOT')
        if args.load_order=='core-first':c=core_load();preload,sdk=sdk_load()
        else:preload,sdk=sdk_load();c=core_load()
        policy.need(report['sdk_sha256']==policy.SDK_SHA and report['core_sha256']==policy.CORE_SHA,'actual SDK/core bytes')
        stats_fn=sdk.psd_get_stats;stats_fn.argtypes=[ctypes.c_void_p];stats_fn.restype=ctypes.c_int;report['source_stats']=[stats()]
        emit('SERVER_BEFORE');server_log=(out/'xvfb.log').open('wb');server=subprocess.Popen(['/usr/bin/Xvfb',':99','-screen','0','1024x768x24','-nolisten','tcp','-ac','-noreset'],stdout=server_log,stderr=server_log)
        deadline=time.monotonic()+15
        while not Path('/tmp/.X11-unix/X99').exists():
            policy.need(server.poll() is None and time.monotonic()<deadline,'owned display readiness');time.sleep(.05)
        emit('SERVER_AFTER')
        if args.model_trial:
            sys.path.insert(0,'/model-deps')
            from scripts.native_mdv3_repeat_trial import run_trial
            value=run_trial(model=Path('/model.onnx'),spec=Path('/work/repo/model_specs/md-v3.json'),scenario=args.scenario,seed=args.seed,steps=12,speed=8.,initial_fraction=.12)
            value.update(selected_sdk_sha256=policy.SDK_SHA,sdk_load_order='core-first');policy.write(out/'run.json',value)
            policy.need(value['status']=='DIAGNOSTIC_EXECUTED' and value['completed_steps']==12,'complete official model trial')
            report['status']='OFFICIAL_MODEL_TRIAL_OBSERVED';return report
        from scripts.panda_real_glx_objects import PRC
        emit('PRC_BEFORE');c.load_prc_file_data('sdk3-runtime',PRC);emit('PRC_AFTER');renderer=Renderer(c)
        emit('ENGINE_BEFORE');renderer.engine=c.GraphicsEngine();emit('ENGINE_AFTER')
        emit('PIPE_BEFORE');pipe=c.GraphicsPipeSelection.get_global_ptr().make_module_pipe('pandagl');policy.need(pipe is not None,'pandagl pipe');emit('PIPE_AFTER')
        fb=c.FrameBufferProperties();fb.set_rgb_color(True);fb.set_rgba_bits(8,8,8,8);fb.set_depth_bits(0);fb.set_stencil_bits(0);fb.set_multisamples(0);fb.set_srgb_color(False)
        emit('OUTPUT_BEFORE');renderer.output=renderer.engine.make_output(pipe,'sdk3-runtime',0,fb,c.WindowProperties.size(8,8),c.GraphicsPipe.BF_refuse_window);policy.need(renderer.output is not None,'Panda output');renderer.engine.open_windows();policy.need(renderer.output.is_valid(),'valid output');gsg=renderer.output.get_gsg();policy.need(gsg is not None and gsg.is_valid(),'valid GSG');emit('OUTPUT_AFTER')
        report['driver']=dict(vendor=gsg.get_driver_vendor(),renderer=gsg.get_driver_renderer(),version=gsg.get_driver_version());emit('DRIVER_AFTER')
        renderer.texture=c.Texture('sdk3-challenge');renderer.output.add_render_texture(renderer.texture,c.GraphicsOutput.RTM_copy_ram,c.GraphicsOutput.RTP_color);renderer.output.set_clear_color_active(True);renderer.output.set_clear_depth_active(False)
        renderer.scene=c.NodePath('sdk3-empty-scene');camera=c.Camera('sdk3-camera');camera.set_scene(renderer.scene);lens=c.OrthographicLens();lens.set_film_size(2,2);lens.set_near_far(.1,10);camera.set_lens(lens);renderer.camera_node=renderer.scene.attach_new_node(camera);renderer.region=renderer.output.make_display_region();renderer.region.set_camera(renderer.camera_node);renderer.region.set_clear_color_active(True);renderer.ready=True
        report['objects']={k:int(v.this) for k,v in dict(pipe=pipe,output=renderer.output,gsg=gsg,texture=renderer.texture,camera=camera).items()};report['frames']=[]
        for i in range(2):
            emit(f'FRAME_{i}_BEFORE');raw=renderer.render(policy.challenge(args.nonce,i));report['frames'].append(dict(index=i,raw_hex=raw.hex(),nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()));emit(f'FRAME_{i}_AFTER')
        emit('CLEANUP_BEFORE');report['cleanup']=renderer.close();report['source_stats'].append(stats());emit('CLEANUP_AFTER');report['status']='SDK3_GLX_FRAMES_OBSERVED';return report
    except BaseException as e:report['failure']=type(e).__name__+': '+str(e);raise
    finally:
        if renderer is not None and not renderer.closed:
            try:report['failure_cleanup']=renderer.close()
            except Exception as e:report['failure_cleanup_error']=str(e)
        if server is not None:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
            report['server_returncode']=server.returncode
        if server_log is not None:server_log.close()
        policy.write(out/'report.json',report)


def run_pair(args):
    out=Path(args.out);ledger=[];failure=None
    try:
        for index in range(2):
            dest=out/f'run-{index}';dest.mkdir();nonce=secrets.token_hex(16)
            row=dict(index=index,spawn_attempted=True,pid=None,returncode=None);ledger.append(row);policy.write(out/'pair-ledger.json',ledger)
            env=dict(os.environ,HOME='/tmp/home-'+nonce,XDG_CACHE_HOME='/tmp/cache-'+nonce)
            Path(env['HOME']).mkdir()
            with (dest/'stdout.log').open('wb') as stdout,(dest/'stderr.log').open('wb') as stderr:
                child=subprocess.Popen([sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--out',str(dest),'--model-trial','--nonce',nonce,'--seed',str(args.seed),'--scenario',args.scenario],stdout=stdout,stderr=stderr,env=env)
                row['pid']=child.pid;policy.write(out/'pair-ledger.json',ledger)
                try:row['returncode']=child.wait(timeout=850)
                except subprocess.TimeoutExpired:
                    child.kill();child.wait(timeout=10);row['returncode']=child.returncode;raise
                finally:policy.write(out/'pair-ledger.json',ledger)
            policy.need(row['returncode']==0,'complete official model child')
    except BaseException as e:failure=type(e).__name__+': '+str(e);raise
    finally:policy.write(out/'pair.json',dict(status='FAILED' if failure else 'PAIR_COMPLETED',failure=failure,counts=policy.observed_model_processes(ledger)))


def main():
    faulthandler.enable();p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--nonce',default='00'*16);p.add_argument('--load-order',choices=['core-first','sdk-first'],default='core-first');p.add_argument('--model-trial',action='store_true');p.add_argument('--model-pair',action='store_true');p.add_argument('--seed',type=int);p.add_argument('--scenario');args=p.parse_args();run_pair(args) if args.model_pair else run(args)

if __name__=='__main__':main()
