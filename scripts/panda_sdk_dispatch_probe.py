"""Build a bounded first-party CPU probe; never load the installed SDK."""
import base64,hashlib,json,os,shutil,stat,time
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
def project_inputs(root=ROOT):
 paths={SOURCE}|{'native/panda_sdk_routes_v2/'+n for n in ('panda_cache_adapter.h','panda_source_activity.h','panda_source_dispatch.h','readback_command_state.h','readback_return_core.h')}
 return {p:sha(read_input(root/p,1024**2)) for p in sorted(paths)}
def build_probe(out):
 out=Path(out).absolute();need(not out.exists() and out.parent.resolve()==out.parent,'new canonical probe output');out.mkdir();tool=Path('/usr/bin/g++').resolve();source=read_input(ROOT/SOURCE,1024**2);inputs_before=project_inputs();native=ROOT/'native/panda_sdk_routes_v2';target=out/'probe.so';deps=out/'probe.d';env=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',TMPDIR='/tmp')
 tool_paths={'driver':str(tool)};queries=[]
 driver_hash=sha(read_input(tool,64*1024**2))
 for name in ['cc1plus','collect2','as','ld']:
  q=cpu.run_command([str(tool),'-print-prog-name='+name],ROOT,env,out/('query-'+name),10);need(q['returncode']==0,'compiler tool query');queries.append(q);value=q['stdout'].strip();path=Path(value) if value.startswith('/') else Path(shutil.which(value,path=env['PATH']) or '/missing');need(path.is_file(),'compiler tool unavailable');tool_paths[name]=str(path.resolve())
 def tools():return {n:dict(path=v,sha256=sha(read_input(Path(v),64*1024**2))) for n,v in tool_paths.items()}
 before=tools();need(before['driver']['sha256']==driver_hash,'compiler changed during queries')
 cmd=[str(tool),'-std=c++11','-O2','-fPIC','-fno-exceptions','-fno-rtti','-shared','-nodefaultlibs','-I',str(native),'-MMD','-MF',str(deps),str(ROOT/SOURCE),'-Wl,-z,defs,-z,now,-z,relro,-z,noexecstack','-lc','-ldl','-o',str(target)]
 record=cpu.run_command(cmd,ROOT,env,out/'compile',30);need(record['returncode']==0,'probe compile failed: '+record.get('stderr','')[:1000]);after=tools();inputs_after=project_inputs();need(before==after and inputs_before==inputs_after,'probe compiler/project inputs changed');raw=read_input(target,1024**2);target.chmod(0o755)
 dependency_text=read_input(deps,16384).decode().replace('\\\n',' ');paths=dependency_text.split(':',1)[1].split();need(paths and all(Path(p).resolve().is_relative_to(ROOT) for p in paths),'project dependency scope');dependency={str(Path(p).resolve().relative_to(ROOT)):sha(read_input(Path(p),1024**2)) for p in paths};need(dependency==inputs_before,'exact compiled project header closure')
 return dict(path=str(target),nbytes=len(raw),sha256=sha(raw),mode=0o755,profile=executable_profile(raw),source_path=SOURCE,source_sha256=sha(source),dependencies=dependency,compiler_path=str(tool),compiler_sha256=driver_hash,command=record,tool_queries=queries,tools_before=before,tools_after=after,tool_profiles_unchanged=True,project_inputs_unchanged=True,elf_base64=base64.b64encode(raw).decode(),host_system_header_closure_qualified=False,image_inventory_member=False)
def validate_probe(r):
 need(type(r) is dict and r.get('schema')=='panda-sdk-dispatch-probe-v1','probe schema')
 expected=dict(mode=0,sizes=[2640344,2320],original_calls=22,args_ok=1,errno_ok=1,returns_ok=1,guards_ok=1,pack_snapshots=[42,0,77,0,0],tags=[1,1,2,1,3],lifecycle=[2,1,1,0,3,0],failed_switch_preserved=0,finish=0,adapter_error=0,source_error=0,source_closed=1,forwarded=22,resolutions=7,paths=28,events=57,bootstrap=39,replayed=39,applied=57,pbo_resets=1,live=0,pending=0,native_admitted=False,driver_state_qualified=False)
 for k,v in expected.items():need(type(r.get(k)) is type(v) and r[k]==v,'probe result: '+k)
 need(len(r['wrappers'])==len(r['originals'])==7 and all(type(v) is int and 0<v<2**64 for v in r['wrappers']+r['originals']) and all(a!=b for a,b in zip(r['wrappers'],r['originals'])),'typed wrapper identities')
 kinds=[7,11,3,4,2,6,7,11,3,4,2,11,13,11,13,11,7,11,3,4,13,11];need(len(r['trace'])==22 and [v[0] for v in r['trace']]==kinds and all(len(v)==7 and v[5]==34 for v in r['trace']),'forwarding trace')
 expected_trace=[
 [7,1,2,0,1,34,4369],[11,1,7,4369,0,34,1],[3,36160,9,0,0,34,0],[4,36064,0,0,0,34,0],
 [2,35051,42,0,0,34,0],None,[7,1,2,0,1,34,8738],[11,1,8,8738,0,34,1],
 [3,36160,10,0,0,34,0],[4,36064,0,0,0,34,0],[2,35051,77,0,0,34,0],
 [11,1,7,4369,0,34,1],[13,1,4369,0,0,34,0],[11,1,8,8738,0,34,1],
 [13,1,8738,0,0,34,0],[11,1,0,0,0,34,1],[7,1,2,0,1,34,4369],[11,1,9,4369,0,34,1],
 [3,36160,11,0,0,34,0],[4,36064,0,0,0,34,0],[13,1,4369,0,0,34,0],[11,1,0,0,0,34,1]]
 for row,want in zip(r['trace'],expected_trace):
  need(all(type(v) is int and 0<=v<2**64 for v in row),'trace scalar ABI')
  if want is not None:need(row==want,'normalized original arguments/return')
  else:need(row[:2]==[6,1] and 0<row[2]<2**64 and row[3:]==[0,0,34,0],'copied delete signature')
 return True

def validate_identity(q,root=ROOT):
 need(type(q) is dict and q.get('source_path')==SOURCE and q.get('image_inventory_member') is False and q.get('host_system_header_closure_qualified') is False,'source-bound probe scope')
 need(q.get('tool_profiles_unchanged') is True and q.get('project_inputs_unchanged') is True and q.get('tools_before')==q.get('tools_after') and set(q.get('tools_before',{}))=={'driver','cc1plus','collect2','as','ld'},'stable probe build tools/inputs')
 raw=base64.b64decode(q['elf_base64'],validate=True);need(0<len(raw)<=1024**2 and q['nbytes']==len(raw) and q['sha256']==sha(raw) and q['profile']==executable_profile(raw) and q['mode']==0o755,'probe byte/profile identity')
 paths={SOURCE}|{'native/panda_sdk_routes_v2/'+n for n in ('panda_cache_adapter.h','panda_source_activity.h','panda_source_dispatch.h','readback_command_state.h','readback_return_core.h')}
 need(set(q['dependencies'])==paths and q['source_sha256']==sha(read_input(root/SOURCE,1024**2)),'probe source/dependency closure')
 for p,h in q['dependencies'].items():need(sha(read_input(root/p,1024**2))==h,'probe compiler input bytes')
 return q

def verify_probe_file(path,q):
 path=Path(path);need(path.is_absolute() and path.resolve()==path and not path.is_symlink(),'canonical probe file');raw=read_input(path,1024**2);need(len(raw)==q['nbytes'] and sha(raw)==q['sha256'] and stat.S_IMODE(path.stat().st_mode)==q['mode'] and executable_profile(raw)==q['profile'],'actual probe file identity');return True
