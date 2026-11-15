"""Build a bounded first-party CPU probe; never load the installed SDK."""
import base64,hashlib,json,os,stat,time
from pathlib import Path
from scripts import panda_cache_adapter_cpu as cpu
from scripts.panda_dispatch_coverage import read_input
from scripts.panda_sdk_link_elf import inspect_elf
from scripts.readback_process_mapping import elf_ranges
ROOT=Path(__file__).resolve().parents[1]
SOURCE='native/panda_sdk_dispatch_probe.cxx'
def need(v,m='dispatch probe rejected'):
 if not v:raise ValueError(m)
def sha(b):return hashlib.sha256(b).hexdigest()
def executable_profile(raw):
 e=inspect_elf(raw);need(e['machine']==62 if 'machine' in e else True,'amd64 probe');functions={}
 for i,p in enumerate(elf_ranges(raw)):
  if p['flags']&1:
   need(not p['flags']&2 and 0<p['filesz']<=1024**2,'bounded nonwritable executable');functions['text_'+str(i)]=dict(vaddr=p['vaddr'],size=p['filesz'],file_offset=p['offset'],sha256=sha(raw[p['offset']:p['offset']+p['filesz']]))
 hits=[s for s in e['exports'] if s['name']=='probe_run'];need(len(hits)==1 and hits[0]['symbol_type']==2,'one probe entry');need(functions,'probe text');return dict(functions=functions,anchor_vaddr=hits[0]['value'])
def build_probe(out):
 out=Path(out).absolute();need(not out.exists() and out.parent.resolve()==out.parent,'new canonical probe output');out.mkdir();tool=Path('/usr/bin/g++').resolve();before=read_input(tool,64*1024**2);source=read_input(ROOT/SOURCE,1024**2);native=ROOT/'native/panda_sdk_routes_v2';target=out/'probe.so';deps=out/'probe.d'
 cmd=[str(tool),'-std=c++11','-O2','-fPIC','-fno-exceptions','-fno-rtti','-shared','-nodefaultlibs','-I',str(native),'-MMD','-MF',str(deps),str(ROOT/SOURCE),'-Wl,-z,defs,-z,now,-z,relro,-z,noexecstack','-lc','-ldl','-o',str(target)]
 record=cpu.run_command(cmd,ROOT,cpu.cpu_environment(),out/'compile',30);need(record['returncode']==0,'probe compile failed: '+record.get('stderr','')[:1000]);need(read_input(tool,64*1024**2)==before and read_input(ROOT/SOURCE,1024**2)==source,'compile inputs changed');raw=read_input(target,1024**2);target.chmod(0o755)
 dependency_text=read_input(deps,16384).decode().replace('\\\n',' ');paths=dependency_text.split(':',1)[1].split();need(paths and all(Path(p).resolve().is_relative_to(ROOT) for p in paths),'project dependency scope');dependency={str(Path(p).resolve().relative_to(ROOT)):sha(read_input(Path(p),1024**2)) for p in paths}
 return dict(path=str(target),nbytes=len(raw),sha256=sha(raw),mode=0o755,profile=executable_profile(raw),source_path=SOURCE,source_sha256=sha(source),dependencies=dependency,compiler_path=str(tool),compiler_sha256=sha(before),command=record,elf_base64=base64.b64encode(raw).decode(),host_system_header_closure_qualified=False,image_inventory_member=False)
def validate_probe(r):
 need(type(r) is dict and r.get('schema')=='panda-sdk-dispatch-probe-v1','probe schema')
 expected=dict(mode=0,sizes=[2640344,2320],original_calls=22,args_ok=1,errno_ok=1,returns_ok=1,guards_ok=1,pack_snapshots=[42,0,77,0,0],tags=[1,1,2,1,3],lifecycle=[2,1,1,0,3,0],failed_switch_preserved=0,finish=0,adapter_error=0,source_error=0,source_closed=1,forwarded=22,resolutions=7,paths=28,events=57,bootstrap=39,replayed=39,applied=57,pbo_resets=1,live=0,pending=0,native_admitted=False,driver_state_qualified=False)
 for k,v in expected.items():need(type(r.get(k)) is type(v) and r[k]==v,'probe result: '+k)
 need(len(r['wrappers'])==len(r['originals'])==7 and all(type(v) is int and 0<v<2**64 for v in r['wrappers']+r['originals']) and all(a!=b for a,b in zip(r['wrappers'],r['originals'])),'typed wrapper identities')
 kinds=[7,11,3,4,2,6,7,11,3,4,2,11,13,11,13,11,7,11,3,4,13,11];need(len(r['trace'])==22 and [v[0] for v in r['trace']]==kinds and all(len(v)==7 and v[5]==34 for v in r['trace']),'forwarding trace')
 return True
