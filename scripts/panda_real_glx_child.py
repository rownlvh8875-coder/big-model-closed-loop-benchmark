"""One owned default-off SDK/Panda software-GLX frame process."""
import argparse,os,stat,sys,time
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_real_glx_runtime as wire
from scripts import panda_real_glx_profile as profile
from scripts import panda_real_glx_policy as policy
from scripts import readback_process_mapping as mapping
from scripts.panda_real_glx_frames import need,sha,challenge,frame_packet
from scripts.panda_real_glx_objects import Renderer
from scripts.panda_dispatch_coverage import read_input

def execute(in_fd,out_fd,state):
 need(in_fd!=out_fd and in_fd>=3 and out_fd>=3 and all(stat.S_ISFIFO(os.fstat(fd).st_mode) for fd in (in_fd,out_fd)),'private FIFO descriptors');stop=time.monotonic()+180;config=wire.read_frame(in_fd,stop);p=config['profile'];library=Path(config['library']);fixture=config['fixture'];nonce=config['nonce'];pid=os.getpid();started=mapping._starttime(pid);state.update(nonce=nonce,pid=pid,starttime=started,phase='BOOT');need(config['parent_pid']==os.getppid() and config['parent_starttime']==mapping._starttime(os.getppid()),'owned live parent');need(sha(read_input(library,64*1024**2))==p['sdk_sha256'],'child SDK bytes')
 if fixture:need(p['sdk_sha256']!=profile.SDK_SHA and library.name=='librealgl_fixture.so','fixture isolation')
 else:need(policy.ROOT==Path('/work/repo') and str(library)==policy.SDK_PATH and os.geteuid()==65534 and sys.executable=='/opt/venv/bin/python' and p==policy.glx_profile(policy.ROOT),'qualified image child')
 def report(stage,**extra):wire.write_frame(out_fd,dict(stage=stage,nonce=nonce,pid=pid,starttime=started,**extra),stop)
 def permit(stage):
  value=wire.read_frame(in_fd,stop);need(value['stage']==stage and value['nonce']==nonce,'exact parent challenge');state['phase']=stage;return value
 report('BOOT');permit('LOAD')
 import ctypes
 if not fixture:preload=ctypes.CDLL(policy.PRELOAD,mode=os.RTLD_NOW|os.RTLD_GLOBAL,use_errno=True)
 sdk=ctypes.CDLL(str(library),mode=os.RTLD_NOW|os.RTLD_LOCAL,use_errno=True);anchor=ctypes.cast(getattr(sdk,p['anchor_name']),ctypes.c_void_p).value;base=anchor-p['anchor_vaddr'];addresses={n:base+v['vaddr'] for n,v in p['functions'].items()};stats_fn=sdk.psd_get_stats;stats_fn.argtypes=[ctypes.c_void_p];stats_fn.restype=ctypes.c_int
 def source_stats():
  raw=(ctypes.c_ubyte*80)(*([165]*80));returned=stats_fn(ctypes.addressof(raw)+16);data=bytes(raw[16:64]);fields=dict(configured=(0,4),closed=(4,4),error=(8,4),forwarded=(16,8),resolutions=(24,8),paths=(32,8),events=(40,8));return dict(returned=returned,values={n:int.from_bytes(data[o:o+w],'little') for n,(o,w) in fields.items()},guards_ok=bytes(raw[:16])==bytes(raw[64:])==bytes([165])*16)
 before=source_stats();state['source_stats_before']=before;need(before['returned']==0 and before['guards_ok'] and all(v==0 for v in before['values'].values()),'default-off SDK before objects');report('READY',addresses=addresses,source_stats=before,panda_preloads=0 if fixture else 1,sdk_loads=1);permit('OBJECTS');renderer=None
 try:
  if fixture:
   from tests.fixtures import panda_real_glx_cpu as core
   core_path=str(Path(core.__file__).resolve());core_sha=sha(read_input(Path(core_path),1024**2));version='CPU fixture'
  else:
   need(policy.SITE not in sys.path,'one explicit image site path');sys.path.insert(0,policy.SITE);import panda3d.core as core
   core_path=os.path.realpath(core.__file__);need(core_path==policy.CORE_PATH and sha(read_input(Path(core_path),32*1024**2))==policy.CORE_SHA,'pinned actual Panda core');core_sha=policy.CORE_SHA;version=core.PandaSystem.get_version_string();need(version=='1.10.13','fixed Panda version')
  renderer=Renderer(core);objects=renderer.setup();objects.update(core_path=core_path,core_sha256=core_sha,panda_version=version);state['objects']=objects;report('OBJECTS',report=objects)
  for index in range(2):
   value=permit('FRAME');need(set(value)=={'stage','nonce','index','rgb'} and value['index']==index and value['rgb']==challenge(nonce,index),'fresh ordered RGB challenge');raw=renderer.render(value['rgb']);frame=frame_packet(raw,nonce,index);state.setdefault('frames',[]).append(frame);report('FRAME',frame=frame)
  permit('CLEANUP');closed=renderer.close();state['cleanup']=closed;after=source_stats();state['source_stats_after']=after;report('CLEANED',cleanup=closed,source_stats=after);permit('EXIT')
 finally:
  if renderer is not None and not renderer.closed:
   try:state['failure_cleanup']=renderer.close()
   except BaseException as e:state['failure_cleanup_error']=type(e).__name__+': '+str(e)

def main():
 p=argparse.ArgumentParser();p.add_argument('--owned-child',action='store_true',required=True);p.add_argument('--wire-in',type=int,required=True);p.add_argument('--wire-out',type=int,required=True);args=p.parse_args();state={}
 try:execute(args.wire_in,args.wire_out,state);return 0
 except BaseException as e:
  try:wire.write_frame(args.wire_out,dict(stage='ERROR',failure=type(e).__name__+': '+str(e),**state),time.monotonic()+1)
  except BaseException:pass
  return 2
if __name__=='__main__':raise SystemExit(main())
