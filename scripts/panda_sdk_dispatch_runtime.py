"""Owned parent: bounded private pipes and independent child /proc snapshots."""
import base64,hashlib,json,os,re,resource,secrets,select,signal,stat,subprocess,sys,tempfile,time
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk_dispatch_profile as profile
from scripts import panda_sdk_dispatch_policy as policy
from scripts import readback_process_mapping as mapping
from scripts.panda_dispatch_coverage import read_input
from scripts import panda_sdk_dispatch_probe as probe
need=profile.need
CLEAN_ENV=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',TMPDIR='/tmp',PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1')
def read_frame(fd,stop):
 raw=bytearray()
 while not raw.endswith(b'\n'):
  left=min(stop-time.monotonic(),15);need(left>0,'wire deadline');ready,_,_=select.select([fd],[],[],left);need(ready,'wire timeout');b=os.read(fd,min(4096,65537-len(raw)));need(b,'wire closed');raw.extend(b);need(len(raw)<=65536,'wire budget')
 need(raw.count(b'\n')==1,'one wire frame');return policy.parse(bytes(raw))
def write_frame(fd,value,stop):
 raw=(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n').encode();need(len(raw)<=65536,'wire budget');os.set_blocking(fd,False)
 while raw:
  left=stop-time.monotonic();need(left>0,'wire deadline');_,ready,_=select.select([],[fd],[],min(left,15));need(ready,'wire timeout');n=os.write(fd,raw);raw=raw[n:]
def limits():
 for which,value in [(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,64),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,1024**2)]:resource.setrlimit(which,(value,value))
def image_snapshot(pid,manifest,fixture=False,extra=None):
 raw=mapping._read_bounded('/proc/'+str(pid)+'/maps',1024**2);rows=mapping.parse_maps(raw);files={};total=0;expected={} if fixture else {r['path']:r for r in manifest['entries']}
 if extra and not fixture:
  path=extra['path'];need(path=='/work/binding/probe.so' and path not in expected,'one explicit source-bound probe');expected[path]=dict(kind='file',nbytes=extra['nbytes'],sha256=extra['sha256'],mode=extra['mode'])
 for m in rows:
  path=m['path']
  if not path.startswith('/'):
   need(m['inode']==0 and ('x' not in m['perms'] or path in ('[vdso]','[vsyscall]')),'nonimage executable mapping');continue
  need(not path.endswith(' (deleted)'),'deleted mapping')
  if fixture:continue
  need(path in expected and expected[path]['kind']=='file' and os.path.realpath(path)==path,'mapped file outside authenticated image');entry=expected[path]
  if path not in files:
   data=read_input(Path(path),64*1024**2);st=os.stat(path);total+=len(data);need(total<=256*1024**2 and len(files)<64,'mapped file budget');need(len(data)==entry['nbytes'] and profile.sha(data)==entry['sha256'] and stat.S_IMODE(st.st_mode)==entry['mode'],'mapped file bytes/mode');need((os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)==(m['major'],m['minor'],m['inode']),'mapped inode mismatch');files[path]=dict(origin='source-bound-probe' if extra and path==extra['path'] else 'authenticated-image',sha256=entry['sha256'],nbytes=len(data),major=m['major'],minor=m['minor'],inode=m['inode'])
 return dict(raw_maps=raw.decode(),file_mappings=[m for m in rows if m['path'].startswith('/')],files=files,image_and_probe_membership_verified=not fixture)
def checkpoint(pid,library,p,addresses,manifest,fixture,extra=None):
 code=mapping.verify_process_code(pid,library,p['sdk_sha256'],{n:dict(vaddr=r['vaddr'],size=r['size']) for n,r in p['functions'].items()},addresses)
 return dict(code=code,addresses=dict(addresses),maps=image_snapshot(pid,manifest,fixture,extra),exe_realpath=os.readlink('/proc/'+str(pid)+'/exe'))
def validate_window(p,r):
 need(r['status']=='SELECTED_DISPATCH_ABI_OBSERVED' and r['child']['nonce']==r['nonce'],'dispatch status/challenge');a,b=r['before']['code'],r['after']['code'];need(a['pid']==b['pid']==r['child']['pid'] and a['starttime']==b['starttime']==r['child']['starttime'] and a['process_code_verified'] is True and b['process_code_verified'] is True,'owned process identity')
 need(r['before']['exe_realpath']==r['after']['exe_realpath'] and r['before']['maps']['file_mappings']==r['after']['maps']['file_mappings'],'stable executable/mappings')
 need(r['before']['addresses']==r['after']['addresses']==r['ready']['addresses'] and set(r['ready']['addresses'])==set(p['functions']),'SDK text addresses')
 for stage in ['boot','ready']:need(r[stage]['nonce']==r['nonce'] and r[stage]['pid']==a['pid'] and r[stage]['starttime']==a['starttime'],'boot/loader identity')
 need(r['ready']['sdk_loads']==r['ready']['probe_loads']==1 and r['ready']['panda_preloads']==(0 if r['fixture'] else 1) and r['child']['probe_invocations']==1 and r['child']['probe_returned']==0,'exact loads/invocation')
 for evidence in [a,b]:
  need(evidence['file_sha256']==p['sdk_sha256'] and set(evidence['ranges'])==set(p['functions']),'SDK profile')
  for n,v in p['functions'].items():need(all(evidence['ranges'][n][k]==v[k] for k in ['vaddr','size','file_offset','sha256']),'SDK executable bytes')
 q=r['probe_identity'];probe.validate_identity(q)
 for point in ['probe_before','probe_after']:
  item=r[point];v=item['code'];need(v['pid']==a['pid'] and v['starttime']==a['starttime'] and v['process_code_verified'] is True and v['file_sha256']==q['sha256'] and v['ranges']==q['profile']['functions'] and item['addresses']==r['ready']['probe_addresses'],'probe executable bytes/process')
 probe.validate_probe(r['child']['probe'])
 def contains(pointer,addresses,functions):return any(addresses[n]<=pointer<addresses[n]+v['size'] for n,v in functions.items())
 need(all(contains(v,r['ready']['addresses'],p['functions']) for v in r['child']['probe']['wrappers']),'SDK wrapper code origin');need(all(contains(v,r['ready']['probe_addresses'],q['profile']['functions']) for v in r['child']['probe']['originals']),'CPU original code origin')
 need(r['native_admitted'] is False and r['external_origin_authenticated'] is False and r['full_object_abi_qualified'] is False,'no scientific admission from packets');return True
class WindowFailure(ValueError):
 def __init__(self,message,receipt):super().__init__(message);self.receipt=receipt
def memory_snapshot():
 root=Path('/sys/fs/cgroup');maximum=(root/'memory.max').read_text().strip();need(maximum==str(policy.BUDGET['memory_bytes']),'memory cgroup limit');events=dict(line.split() for line in (root/'memory.events').read_text().splitlines());need(int(events['oom'])==int(events['oom_kill'])==0,'cgroup OOM');return dict(max_bytes=int(maximum),events={k:int(v) for k,v in events.items()},peak_bytes=int((root/'memory.peak').read_text()),peak_is_rss=False)
def check_context(f,host):
 need(f['pid']==1 and f['uid']==f['gid']==65534 and f['cap_eff']==f['cap_bnd']==0 and f['no_new_privs']==1 and f['seccomp']==2,'runtime privilege context')
 need(set(host)==set(f['namespaces'])=={'pid','net','mnt'} and all(re.fullmatch(k+r':\[[0-9]{1,20}\]',f['namespaces'][k]) and f['namespaces'][k]!=host[k] for k in host),'isolated runtime namespaces')
 need(all('ro' in f['mounts'].get(p,[]) for p in ['/','/work/repo','/work/binding']) and {'rw','nosuid','nodev','noexec'}<=set(f['mounts'].get('/tmp',[])),'readonly runtime mounts')
 need(f['pids_max']==32 and type(f['cpu_quota']) is int and 0<f['cpu_quota']==f['cpu_period'],'runtime PID/CPU cgroup');return True
def collect_context(host):
 status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line);mounts={}
 for line in Path('/proc/self/mountinfo').read_text().splitlines():
  fields=line.split();mounts[fields[4]]=fields[5].split(',')
 quota,period=Path('/sys/fs/cgroup/cpu.max').read_text().split();f=dict(pid=os.getpid(),uid=os.geteuid(),gid=os.getegid(),cap_eff=int(status['CapEff'].strip(),16),cap_bnd=int(status['CapBnd'].strip(),16),no_new_privs=int(status['NoNewPrivs'].strip()),seccomp=int(status['Seccomp'].strip()),namespaces={k:os.readlink('/proc/self/ns/'+k) for k in ['pid','net','mnt']},mounts={k:mounts.get(k,[]) for k in ['/','/work/repo','/work/binding','/tmp']},pids_max=int(Path('/sys/fs/cgroup/pids.max').read_text()),cpu_quota=int(quota),cpu_period=int(period));check_context(f,host);return f
def run_window(library,p,*,probe_identity,fixture=False,timeout=60,manifest=None,nonce=None):
 probe.validate_identity(probe_identity);probe.verify_probe_file(probe_identity['path'],probe_identity);extra=probe_identity
 library=Path(library).absolute();need(type(fixture) is bool and type(timeout) in (int,float) and 0<timeout<=60,'runtime scope/budget');need(profile.sha(read_input(library,64*1024**2))==p['sdk_sha256'],'runtime target identity')
 if fixture:need(p['sdk_sha256']!=profile.SDK_SHA and library.name=='libdispatch_fixture.so','CPU fixture cannot load actual SDK')
 else:
  need(probe_identity['path']=='/work/binding/probe.so' and policy.ROOT==Path('/work/repo') and str(library)==policy.SDK_PATH and os.geteuid()==65534 and sys.executable=='/opt/venv/bin/python' and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,'registered image runtime only');need(p==policy.dispatch_profile(policy.ROOT) and manifest==policy.expected_inventory(policy.ROOT),'registered runtime inputs')
 nonce=nonce or secrets.token_hex(16);need(type(nonce) is str and len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce),'runtime nonce');stop=time.monotonic()+timeout;child=None;fds=[];r=dict(probe_identity=probe_identity,schema='panda-sdk-dispatch-runtime-v1',status='FAILED',nonce=nonce,fixture=fixture,image_and_probe_membership_verified=not fixture,native_admitted=False,external_origin_authenticated=False,full_object_abi_qualified=False,stage7_complete=False)
 try:
  if not fixture:r['memory_before']=memory_snapshot()
  with tempfile.TemporaryDirectory(prefix='owned-sdk-dispatch-') as owned:
   logdir=Path(owned);cmd_r,cmd_w=os.pipe();reply_r,reply_w=os.pipe();fds=[cmd_r,cmd_w,reply_r,reply_w]
   try:
    with (logdir/'stdout').open('wb') as stdout,(logdir/'stderr').open('wb') as stderr:
     child=subprocess.Popen([sys.executable,'-I','-S','-B',str(Path(__file__).with_name('panda_sdk_dispatch_child.py')),'--owned-child','--wire-in',str(cmd_r),'--wire-out',str(reply_w)],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,env=CLEAN_ENV,pass_fds=(cmd_r,reply_w),close_fds=True,start_new_session=True,preexec_fn=limits)
     os.close(cmd_r);fds.remove(cmd_r);os.close(reply_w);fds.remove(reply_w)
     write_frame(cmd_w,dict(fixture=fixture,profile=p,probe_identity={k:probe_identity[k] for k in ['path','nbytes','sha256','mode','profile']},library=str(library),nonce=nonce,parent_pid=os.getpid(),parent_starttime=mapping._starttime(os.getpid())),stop);boot=read_frame(reply_r,stop);need(boot.get('stage')=='BOOT' and boot['nonce']==nonce and boot['pid']==child.pid and boot['starttime']==mapping._starttime(child.pid),'owned child boot');r['boot']=boot;r['before_load']=image_snapshot(child.pid,manifest,fixture,extra)
     need(not any(x['path'] in (policy.SDK_PATH,policy.PRELOAD,extra['path']) for x in r['before_load']['file_mappings']),'SDK/Panda already mapped');write_frame(cmd_w,dict(stage='LOAD',nonce=nonce),stop);ready=read_frame(reply_r,stop);r['ready']=ready;need(ready.get('stage')=='READY' and ready['nonce']==nonce and ready['pid']==child.pid,'SDK loader readiness')
     r['probe_before']=dict(code=mapping.verify_process_code(child.pid,extra['path'],extra['sha256'],{n:dict(vaddr=v['vaddr'],size=v['size']) for n,v in extra['profile']['functions'].items()},ready['probe_addresses']),addresses=ready['probe_addresses']);r['before']=checkpoint(child.pid,library,p,ready['addresses'],manifest,fixture,extra);write_frame(cmd_w,dict(stage='CALLS',nonce=nonce),stop);report=read_frame(reply_r,stop);r['child']=report;need(report.get('stage')=='REPORT','ABI report');r['probe_after']=dict(code=mapping.verify_process_code(child.pid,extra['path'],extra['sha256'],{n:dict(vaddr=v['vaddr'],size=v['size']) for n,v in extra['profile']['functions'].items()},ready['probe_addresses']),addresses=ready['probe_addresses']);r['after']=checkpoint(child.pid,library,p,ready['addresses'],manifest,fixture,extra);r['status']='SELECTED_DISPATCH_ABI_OBSERVED';validate_window(p,r);write_frame(cmd_w,dict(stage='EXIT',nonce=nonce),stop);child.wait(timeout=max(.001,stop-time.monotonic()));need(child.returncode==0,'child exit')
   finally:
    if child:
     try:os.killpg(child.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     child.wait(timeout=5);r['child_returncode']=child.returncode
    for name in ['stdout','stderr']:
     if not (logdir/name).exists():continue
     raw=(logdir/name).read_bytes();need(len(raw)<=1024**2,'child log budget');r[name]=dict(nbytes=len(raw),sha256=profile.sha(raw),base64=base64.b64encode(raw).decode(),text=raw[:4096].decode(errors='replace'),preview_truncated=len(raw)>4096)
  if not fixture:r['memory_after']=memory_snapshot()
  need(time.monotonic()<stop,'whole runtime deadline');return r
 except BaseException as e:
  r['status']='FAILED';r['failure']=type(e).__name__+': '+str(e);raise WindowFailure(str(e),r) from e
 finally:
  if child:
   try:os.killpg(child.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   child.wait(timeout=5)
  for fd in fds:
   try:os.close(fd)
   except OSError:pass
def main():
 import argparse
 q=argparse.ArgumentParser();q.add_argument('--binding-sha',required=True);args=q.parse_args();r=dict(status='FAILED',native_admitted=False,external_origin_authenticated=False)
 try:
  raw=read_input(Path('/work/binding/binding.json'),1024**2);need(profile.sha(raw)==args.binding_sha,'binding identity');b=policy.parse(raw);request=policy.validate_request(b['request'],policy.ROOT);need(b['window_max']==1 and b['nonce'] and b['image_sha256']==policy.IMAGE_SHA,'qualified binding');context=collect_context(b['host_namespaces']);r=run_window(policy.SDK_PATH,policy.dispatch_profile(policy.ROOT),probe_identity=b['probe_identity'],manifest=policy.expected_inventory(policy.ROOT),nonce=b['nonce']);r['binding_sha256']=args.binding_sha;r['context']=context;print(json.dumps(r,separators=(',',':')));return 0
 except BaseException as e:
  r=getattr(e,'receipt',r);r.update(status='FAILED',failure=type(e).__name__+': '+str(e));print(json.dumps(r,separators=(',',':')));return 2
if __name__=='__main__':raise SystemExit(main())
