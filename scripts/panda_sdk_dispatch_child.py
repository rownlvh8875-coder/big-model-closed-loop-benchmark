"""One source-bound CPU-original dispatch invocation in the owned SDK child."""
import argparse,os,stat,sys,time
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk_dispatch_runtime as wire
from scripts import panda_sdk_dispatch_profile as profile
from scripts import panda_sdk_dispatch_policy as policy
from scripts import panda_sdk_dispatch_probe as probe
from scripts import readback_process_mapping as mapping
from scripts.panda_dispatch_coverage import read_input
need=profile.need

def execute(in_fd,out_fd):
 need(in_fd!=out_fd and in_fd>=3 and out_fd>=3 and all(stat.S_ISFIFO(os.fstat(fd).st_mode) for fd in (in_fd,out_fd)),'private FIFO descriptors');stop=time.monotonic()+60;c=wire.read_frame(in_fd,stop);p=c['profile'];q=c['probe_identity'];fixture=c['fixture'];library=Path(c['library']);nonce=c['nonce'];need(c['parent_pid']==os.getppid() and c['parent_starttime']==mapping._starttime(os.getppid()),'owned live parent');need(profile.sha(read_input(library,64*1024**2))==p['sdk_sha256'],'child SDK identity');probe.verify_probe_file(q['path'],q)
 if fixture:need(p['sdk_sha256']!=profile.SDK_SHA and library.name=='libdispatch_fixture.so','CPU scope')
 else:need(policy.ROOT==Path('/work/repo') and str(library)==policy.SDK_PATH and q['path']=='/work/binding/probe.so' and os.geteuid()==65534 and sys.executable=='/opt/venv/bin/python' and p==policy.dispatch_profile(policy.ROOT),'qualified dispatch image')
 pid=os.getpid();start=mapping._starttime(pid);wire.write_frame(out_fd,dict(stage='BOOT',nonce=nonce,pid=pid,starttime=start),stop)
 def permit(stage):need(wire.read_frame(in_fd,stop)==dict(stage=stage,nonce=nonce),'one exact parent permit')
 permit('LOAD')
 import ctypes
 if not fixture:preload=ctypes.CDLL(policy.PRELOAD,mode=os.RTLD_NOW|os.RTLD_GLOBAL,use_errno=True)
 sdk=ctypes.CDLL(str(library),mode=os.RTLD_NOW|os.RTLD_LOCAL,use_errno=True);helper=ctypes.CDLL(q['path'],mode=os.RTLD_NOW|os.RTLD_LOCAL,use_errno=True)
 anchor=ctypes.cast(sdk.pca_context_size,ctypes.c_void_p).value;base=anchor-p['anchor_vaddr'];entry=helper.probe_run;entry.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t];entry.restype=ctypes.c_int;helper_base=ctypes.cast(entry,ctypes.c_void_p).value-q['profile']['anchor_vaddr'];addresses={n:base+v['vaddr'] for n,v in p['functions'].items()};probe_addresses={n:helper_base+v['vaddr'] for n,v in q['profile']['functions'].items()}
 wire.write_frame(out_fd,dict(stage='READY',nonce=nonce,pid=pid,starttime=start,addresses=addresses,probe_addresses=probe_addresses,panda_preloads=0 if fixture else 1,sdk_loads=1,probe_loads=1),stop);permit('CALLS');buf=ctypes.create_string_buffer(65536);returned=entry(sdk._handle,0,buf,len(buf));raw=buf.value;report=policy.parse(raw) if raw else {'empty_probe_output':True};wire.write_frame(out_fd,dict(stage='REPORT',nonce=nonce,pid=pid,starttime=start,probe_invocations=1,probe_returned=returned,probe=report),stop);permit('EXIT')
def main():
 p=argparse.ArgumentParser();p.add_argument('--owned-child',action='store_true',required=True);p.add_argument('--wire-in',type=int,required=True);p.add_argument('--wire-out',type=int,required=True);a=p.parse_args()
 try:execute(a.wire_in,a.wire_out);return 0
 except BaseException as e:
  try:wire.write_frame(a.wire_out,dict(stage='ERROR',failure=type(e).__name__+': '+str(e)),time.monotonic()+1)
  except BaseException:pass
  return 2
if __name__=='__main__':raise SystemExit(main())
