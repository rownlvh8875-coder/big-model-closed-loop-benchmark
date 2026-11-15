"""Owned Xvfb/Panda child, independent code/maps and fresh frame checkpoints."""
import base64,hashlib,json,os,re,resource,secrets,select,signal,stat,subprocess,sys,tempfile,time
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_real_glx_policy as policy
from scripts import panda_real_glx_profile as profile
from scripts import readback_process_mapping as mapping
from scripts.panda_real_glx_frames import need,sha,challenge,validate_frame
from scripts.panda_dispatch_coverage import read_input
CLEAN_ENV=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',TMPDIR='/tmp',PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',DISPLAY=':99',LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='softpipe',LP_NUM_THREADS='1',OMP_NUM_THREADS='1',MESA_SHADER_CACHE_DISABLE='true')
def read_frame(fd,stop):
 raw=bytearray()
 while not raw.endswith(b'\n'):
  left=min(stop-time.monotonic(),45);need(left>0,'wire deadline');ready,_,_=select.select([fd],[],[],left);need(ready,'wire timeout');block=os.read(fd,min(4096,65537-len(raw)));need(block,'wire closed');raw.extend(block);need(len(raw)<=65536,'wire budget')
 need(raw.count(b'\n')==1,'one wire frame');return policy.parse(bytes(raw))
def write_frame(fd,value,stop):
 raw=(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n').encode();need(len(raw)<=65536,'wire budget');os.set_blocking(fd,False)
 while raw:
  left=stop-time.monotonic();need(left>0,'wire deadline');_,ready,_=select.select([],[fd],[],min(45,left));need(ready,'wire timeout');raw=raw[os.write(fd,raw):]
def limits():
 for kind,value in [(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CPU,180),(resource.RLIMIT_FSIZE,1024**2)]:resource.setrlimit(kind,(value,value))
def log_payload(path):
 p=Path(path)
 if not p.exists():raw=b'';observed=0
 else:
  observed=p.stat().st_size
  with p.open('rb') as f:raw=f.read(1024**2)
 return dict(nbytes=len(raw),observed_nbytes=observed,sha256=sha(raw),base64=base64.b64encode(raw).decode(),text=raw[:4096].decode(errors='replace'),truncated=observed>len(raw))
def stop_owned(child,started):
 if child is None:return
 if child.poll() is None:
  need(mapping._starttime(child.pid)==started and os.getpgid(child.pid)==child.pid,'owned live group identity')
  try:os.killpg(child.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:child.wait(timeout=1)
  except subprocess.TimeoutExpired:
   try:os.killpg(child.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   child.wait(timeout=5)
 else:child.wait(timeout=1)
class ServerFailure(ValueError):
 def __init__(self,message,receipt):super().__init__(message);self.receipt=receipt
class OwnedServer:
 def __init__(self,argv,env,owned,ready_path,timeout=15):
  self.child=None;self.started=None;self.ready=False;self.root=Path(owned);self.stdout=self.root/'server.stdout';self.stderr=self.root/'server.stderr';self.record=dict(argv=list(argv),ready=False,reaped=False)
  try:
   need(not Path(ready_path).exists(),'fresh server socket')
   with self.stdout.open('xb') as out,self.stderr.open('xb') as err:self.child=subprocess.Popen(argv,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits,close_fds=True)
   self.pid=self.child.pid;self.started=mapping._starttime(self.pid);self.record.update(pid=self.pid,starttime=self.started);stop=time.monotonic()+timeout
   while True:
    need(self.child.poll() is None,'server exited before readiness');need(time.monotonic()<stop,'server readiness timeout');need(self.stdout.stat().st_size<=1024**2 and self.stderr.stat().st_size<=1024**2,'server log budget')
    try:ready=stat.S_ISSOCK(Path(ready_path).lstat().st_mode)
    except FileNotFoundError:ready=False
    if ready:break
    time.sleep(.02)
   need(mapping._starttime(self.pid)==self.started,'stable server process');self.ready=True;self.record['ready']=True
  except BaseException as e:
   self.stop();self.record['failure']=type(e).__name__+': '+str(e);raise ServerFailure(str(e),self.record) from e
 def stop(self):
  try:stop_owned(self.child,self.started);self.record['reaped']=self.child is None or self.child.returncode is not None
  finally:self.record.update(returncode=None if self.child is None else self.child.returncode,stdout=log_payload(self.stdout),stderr=log_payload(self.stderr))
  return self.record

def finish_server(server,audit):
 result=dict(snapshot={},server={},errors=[])
 try:
  if server.child.poll() is None:result['snapshot']=audit.snapshot(server.pid,True)
  else:result['errors'].append('owned server exited before controlled stop')
 except BaseException as e:result['errors'].append(type(e).__name__+': '+str(e))
 finally:
  try:result['server']=server.stop()
  except BaseException as e:result['server']=server.record;result['errors'].append(type(e).__name__+': '+str(e))
 return result

def special_regions(rows,allowed):
 generated=[];shared=[]
 for m in rows:
  path=m['path'];execute='x' in m['perms'];special=path.startswith(('/memfd:','/SYSV','/dev/shm/'))
  if path in ('[vdso]','[vsyscall]'):continue
  if execute and (not path.startswith('/') or special):
   need(allowed and (path=='' or special),'unqualified generated executable region');generated.append(m)
  elif special:need(allowed,'driver shared memory before driver phase');shared.append(m)
  elif not path.startswith('/'):need(m['inode']==0 and not execute,'anonymous mapping identity')
 need(len(generated)<=16 and sum(m['end']-m['start'] for m in generated)<=4*1024**2,'generated executable bounds');need(len(shared)<=32 and sum(m['end']-m['start'] for m in shared)<=64*1024**2,'driver shared-memory bounds')
 return dict(generated_code=generated,shared_driver_memory=shared)
def _key(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
class MapAudit:
 def __init__(self,manifest,fixture=False,deadline=None):self.expected={} if fixture else {v['path']:v for v in manifest['entries']};self.cache={};self.fixture=fixture;self.deadline=deadline or time.monotonic()+180
 def verify_file(self,path):
  need(path in self.expected and self.expected[path]['kind']=='file' and os.path.realpath(path)==path,'mapped file outside authenticated image');e=self.expected[path];st=os.lstat(path);need(stat.S_ISREG(st.st_mode) and st.st_size==e['nbytes']<=192*1024**2 and stat.S_IMODE(st.st_mode)==e['mode'],'mapped file metadata');key=_key(st)
  if path in self.cache and self.cache[path][0]==key:return dict(self.cache[path][1])
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  with os.fdopen(fd,'rb') as f:
   need(_key(os.fstat(f.fileno()))==key,'opened mapped file identity');h=hashlib.sha256();size=0
   while True:
    need(time.monotonic()<self.deadline,'mapped file deadline');block=f.read(65536)
    if not block:break
    h.update(block);size+=len(block);need(size<=e['nbytes'],'mapped file extent')
   need(size==e['nbytes'] and h.hexdigest()==e['sha256'] and key==_key(os.fstat(f.fileno()))==_key(os.lstat(path)),'mapped file bytes/race')
  value=dict(origin='authenticated-image',nbytes=size,sha256=e['sha256'],major=os.major(st.st_dev),minor=os.minor(st.st_dev),inode=st.st_ino);self.cache[path]=(key,value);return dict(value)
 def snapshot(self,pid,allow_generated=False):
  started=mapping._starttime(pid);raw=mapping._read_bounded('/proc/'+str(pid)+'/maps',1024**2);rows=mapping.parse_maps(raw);special=special_regions(rows,allow_generated);skip={m['start'] for key in special for m in special[key]};files={};total=0
  for m in rows:
   if not m['path'].startswith('/') or m['start'] in skip:continue
   need(not m['path'].endswith(' (deleted)') and not ('w' in m['perms'] and 'x' in m['perms']),'unregistered/deleted executable file')
   if self.fixture:continue
   if m['path'] not in files:
    v=self.verify_file(m['path']);files[m['path']]=v;total+=v['nbytes'];need(len(files)<=192 and total<=768*1024**2,'mapped image total bounds')
   v=files[m['path']];need((v['major'],v['minor'],v['inode'])==(m['major'],m['minor'],m['inode']),'mapped image inode')
  if special['generated_code']:
   fd=os.open('/proc/'+str(pid)+'/mem',os.O_RDONLY)
   try:
    for m in special['generated_code']:
     h=hashlib.sha256();position=m['start']
     while position<m['end']:
      block=os.pread(fd,min(65536,m['end']-position),position);need(block,'generated code extent');position+=len(block);h.update(block)
     m['sha256']=h.hexdigest();m['image_membership_verified']=False;m['generated_code_origin_qualified']=False
   finally:os.close(fd)
  need(mapping._starttime(pid)==started,'snapshot stable process');return dict(pid=pid,starttime=started,raw_maps=raw.decode(),file_mappings=[m for m in rows if m['path'].startswith('/') and m['start'] not in skip],files=files,generated_code=special['generated_code'],shared_driver_memory=special['shared_driver_memory'],image_file_membership_verified=not self.fixture,generated_code_origin_qualified=False)

def checkpoint(pid,library,p,addresses,audit,allow_generated):
 code=mapping.verify_process_code(pid,library,p['sdk_sha256'],{n:dict(vaddr=v['vaddr'],size=v['size']) for n,v in p['functions'].items()},addresses);result=dict(code=code,addresses=dict(addresses),maps=audit.snapshot(pid,allow_generated),exe_realpath=os.readlink('/proc/'+str(pid)+'/exe'))
 if p['read_binding'] is not None:
  name=next(iter(p['functions']));bias=addresses[name]-p['functions'][name]['vaddr'];fd=os.open('/proc/'+str(pid)+'/mem',os.O_RDONLY)
  try:raw=os.pread(fd,8,bias+p['read_binding']['slot_vaddr'])
  finally:os.close(fd)
  need(len(raw)==8,'read target slot');pointer=int.from_bytes(raw,'little');g=p['gl_profile'];observed=mapping.verify_process_code(pid,g['path'],g['sha256'],{n:dict(vaddr=v['vaddr'],size=v['size']) for n,v in g['functions'].items()},{'glReadPixels':pointer});result['read_binding']=dict(slot_vaddr=p['read_binding']['slot_vaddr'],pointer=pointer,code=observed,invocation_trace_qualified=False)
 return result

def memory_snapshot():
 root=Path('/sys/fs/cgroup');maximum=(root/'memory.max').read_text().strip();need(maximum==str(2*1024**3),'memory cgroup');events={k:int(v) for k,v in (line.split() for line in (root/'memory.events').read_text().splitlines())};need(events['oom']==events['oom_kill']==0,'cgroup OOM');return dict(max_bytes=int(maximum),events=events,peak_bytes=int((root/'memory.peak').read_text()),peak_is_rss=False)
def check_context(f,host):
 need(f['pid']==1 and f['uid']==f['gid']==65534 and f['cap_eff']==f['cap_bnd']==0 and f['no_new_privs']==1 and f['seccomp']==2,'runtime privilege context');need(set(host)==set(f['namespaces'])=={'pid','net','mnt','ipc'} and all(re.fullmatch(k+r':\[[0-9]{1,20}\]',f['namespaces'][k]) and f['namespaces'][k]!=host[k] for k in host),'isolated runtime namespaces');need(all('ro' in f['mounts'].get(p,[]) for p in ['/','/work/repo','/work/binding']) and {'rw','nosuid','nodev','noexec'}<=set(f['mounts'].get('/tmp',[])),'readonly runtime mounts');need(f['pids_max']==64 and 0<f['cpu_quota']==f['cpu_period'],'runtime PID/CPU');return True
def collect_context(host):
 status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line);mounts={}
 for line in Path('/proc/self/mountinfo').read_text().splitlines():v=line.split();mounts[v[4]]=v[5].split(',')
 quota,period=Path('/sys/fs/cgroup/cpu.max').read_text().split();f=dict(pid=os.getpid(),uid=os.geteuid(),gid=os.getegid(),cap_eff=int(status['CapEff'].strip(),16),cap_bnd=int(status['CapBnd'].strip(),16),no_new_privs=int(status['NoNewPrivs'].strip()),seccomp=int(status['Seccomp'].strip()),namespaces={k:os.readlink('/proc/self/ns/'+k) for k in ['pid','net','mnt','ipc']},mounts={k:mounts.get(k,[]) for k in ['/','/work/repo','/work/binding','/tmp']},pids_max=int(Path('/sys/fs/cgroup/pids.max').read_text()),cpu_quota=int(quota),cpu_period=int(period));check_context(f,host);return f
class WindowFailure(ValueError):
 def __init__(self,message,receipt):super().__init__(message);self.receipt=receipt

def validate_window(p,r):
 need(r['status']=='REAL_GLX_FRAMES_OBSERVED' and r['child_returncode']==0 and len(r['frames'])==2 and r['cleanup']==dict(windows_after=0,texture_ram_after=False,render_calls=4,ram_reads=2,cpp_deallocation_verified=False),'selected frame/cleanup scope');need(r['objects']['driver']['renderer'].strip().lower()=='softpipe' and 1<=r['objects']['windows']<=2,'software driver/owned outputs')
 for i,f in enumerate(r['frames']):validate_frame(f,r['nonce'],i)
 need(r['frames'][0]['sha256']!=r['frames'][1]['sha256'],'distinct fresh frames');start=r['boot']['starttime'];pid=r['boot']['pid'];need(r['boot']['nonce']==r['ready']['nonce']==r['nonce'] and r['ready']['pid']==pid and r['ready']['starttime']==start and r['ready']['sdk_loads']==1 and r['ready']['panda_preloads']==(0 if r['fixture'] else 1),'owned loader identity')
 need(r['ready']['addresses']==r['loaded']['addresses']==r['before']['addresses']==r['after']['addresses'],'stable SDK addresses')
 for name in ['loaded','before','after']:
  c=r[name]['code'];need(c['process_code_verified'] is True and c['pid']==pid and c['starttime']==start and c['file_sha256']==p['sdk_sha256'] and c['ranges']==p['functions'],'SDK executable profile')
  if not r['fixture']:
   b=r[name]['read_binding'];g=p['gl_profile'];need(b['slot_vaddr']==830720 and b['invocation_trace_qualified'] is False and b['code']['process_code_verified'] is True and b['code']['file_sha256']==g['sha256'] and b['code']['ranges']==g['functions'],'original libGL entry binding')
 if not r['fixture']:
  need(r['objects']['core_path']==policy.CORE_PATH and r['objects']['core_sha256']==policy.CORE_SHA and r['objects']['panda_version']=='1.10.13','actual image Panda core');need(r['server']['ready'] and r['server']['reaped'] and r['server']['argv']==[policy.XVFB,':99','-screen','0','64x64x24','-nolisten','tcp','-ac','-noreset'],'owned Xvfb lifecycle');
  for stage in ['server_before','server_after']:
   s=r[stage];need(s['pid']==r['server']['pid'] and s['starttime']==r['server']['starttime'] and s['image_file_membership_verified'] is True and policy.XVFB in s['files'],'actual owned Xvfb process/image')
  need(r['loaded']['read_binding']['pointer']==r['before']['read_binding']['pointer']==r['after']['read_binding']['pointer'],'stable original read pointer')
  for stage in ['before','after']:
   files=r[stage]['maps']['files'];need(r[stage]['maps']['image_file_membership_verified'] is True and all(k in files for k in [policy.CORE_PATH,policy.GL_PATH,policy.GALLIUM,policy.GLX_MESA]),'actual image core/driver mappings')
 need(r['loaded']['exe_realpath']==r['before']['exe_realpath']==r['after']['exe_realpath'],'stable actual executable');objects=r['objects']['objects'];need(set(objects)=={'pipe','output','gsg','texture','camera'} and all(type(v['pointer']) is int and 0<v['pointer']<2**64 and type(v['type']) is str and 0<len(v['type'])<=128 for v in objects.values()) and len({v['pointer'] for v in objects.values()})==5,'exact distinct object identities')
 for stats in r['source_stats']:need(type(stats['returned']) is int and stats['returned']==0 and set(stats['values'])=={'configured','closed','error','forwarded','resolutions','paths','events'} and all(type(v) is int and v==0 for v in stats['values'].values()) and stats['guards_ok'] is True,'SDK default-off observer')
 need(len(r['source_stats'])==2 and r['native_admitted'] is False and r['external_origin_authenticated'] is False and r['full_object_abi_qualified'] is False and r['physical_gpu_qualified'] is False,'no general/native/scientific admission');return True

def run_window(library,p,*,fixture=False,timeout=180,manifest=None,nonce=None):
 library=Path(library).absolute();need(type(fixture) is bool and type(timeout) in (int,float) and 0<timeout<=180,'window scope');need(sha(read_input(library,64*1024**2))==p['sdk_sha256'],'window SDK file')
 if fixture:need(p['sdk_sha256']!=profile.SDK_SHA and library.name=='librealgl_fixture.so','CPU fixture scope')
 else:need(policy.ROOT==Path('/work/repo') and str(library)==policy.SDK_PATH and os.geteuid()==65534 and sys.executable=='/opt/venv/bin/python' and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and p==policy.glx_profile(policy.ROOT) and manifest==policy.expected_inventory(policy.ROOT),'registered image driver window only')
 nonce=nonce or secrets.token_hex(16);challenge(nonce,0);stop=time.monotonic()+timeout;child=None;child_started=None;server=None;fds=[];r=dict(schema='panda-real-glx-runtime-v1',status='FAILED',fixture=fixture,nonce=nonce,frames=[],source_stats=[],actual_driver_execution_verified=False,native_admitted=False,external_origin_authenticated=False,full_object_abi_qualified=False,physical_gpu_qualified=False,stage7_complete=False);audit=MapAudit(manifest,fixture,stop)
 try:
  if not fixture:r['memory_before']=memory_snapshot()
  with tempfile.TemporaryDirectory(prefix='owned-real-glx-') as temp:
   logdir=Path(temp);env=dict(CLEAN_ENV,XDG_CACHE_HOME=str(logdir/'cache'))
   try:
    if not fixture:
     need(not Path('/tmp/.X99-lock').exists(),'fresh display lock');audit.verify_file(policy.XVFB);server=OwnedServer([policy.XVFB,':99','-screen','0','64x64x24','-nolisten','tcp','-ac','-noreset'],env,logdir,Path('/tmp/.X11-unix/X99'),timeout=15);r['server_before']=audit.snapshot(server.pid,True)
    cmd_r,cmd_w=os.pipe();reply_r,reply_w=os.pipe();fds=[cmd_r,cmd_w,reply_r,reply_w]
    with (logdir/'child.stdout').open('wb') as stdout,(logdir/'child.stderr').open('wb') as stderr:child=subprocess.Popen([sys.executable,'-I','-S','-B',str(Path(__file__).with_name('panda_real_glx_child.py')),'--owned-child','--wire-in',str(cmd_r),'--wire-out',str(reply_w)],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,env=env,pass_fds=(cmd_r,reply_w),close_fds=True,start_new_session=True,preexec_fn=limits)
    child_started=mapping._starttime(child.pid);os.close(cmd_r);fds.remove(cmd_r);os.close(reply_w);fds.remove(reply_w)
    write_frame(cmd_w,dict(fixture=fixture,profile=p,library=str(library),nonce=nonce,parent_pid=os.getpid(),parent_starttime=mapping._starttime(os.getpid())),stop)
    def receive(stage):
     v=read_frame(reply_r,stop);r['last_message']=v;need(v.get('stage')==stage and v['nonce']==nonce and v['pid']==child.pid and v['starttime']==child_started,'owned child stage '+stage);return v
    def permit(stage,**extra):write_frame(cmd_w,dict(stage=stage,nonce=nonce,**extra),stop)
    r['boot']=receive('BOOT');r['before_load']=audit.snapshot(child.pid,False);need(not any(v['path'] in (policy.SDK_PATH,policy.PRELOAD) for v in r['before_load']['file_mappings']),'fresh unmapped SDK');permit('LOAD');r['ready']=receive('READY');addresses=r['ready']['addresses'];r['source_stats'].append(r['ready']['source_stats']);r['loaded']=checkpoint(child.pid,library,p,addresses,audit,False);permit('OBJECTS');objects=receive('OBJECTS');r['objects']=objects['report'];need(r['objects']['driver']['renderer'].strip().lower()=='softpipe','fixed softpipe renderer');r['before']=checkpoint(child.pid,library,p,addresses,audit,True)
    for i in range(2):permit('FRAME',index=i,rgb=challenge(nonce,i));v=receive('FRAME');validate_frame(v['frame'],nonce,i);r['frames'].append(v['frame'])
    r['after']=checkpoint(child.pid,library,p,addresses,audit,True);permit('CLEANUP');v=receive('CLEANED');r['cleanup']=v['cleanup'];r['source_stats'].append(v['source_stats']);permit('EXIT');child.wait(timeout=max(.001,stop-time.monotonic()));need(child.returncode==0,'clean child exit')
   finally:
    errors=[]
    try:stop_owned(child,child_started)
    except BaseException as e:errors.append(type(e).__name__+': '+str(e))
    r['child_returncode']=None if child is None else child.returncode
    if server:
     final=finish_server(server,audit);r['server_after']=final['snapshot'];r['server']=final['server'];errors.extend(final['errors'])
    for name in ['child.stdout','child.stderr']:r[name.replace('.','_')]=log_payload(logdir/name)
    if errors:r['cleanup_failures']=errors;raise ValueError('owned cleanup/snapshot failure')
   if fixture:r['server']=dict(fixture=True,ready=False,reaped=True)
   need(all(not r[k]['truncated'] for k in ['child_stdout','child_stderr']),'complete child logs');r['status']='REAL_GLX_FRAMES_OBSERVED';validate_window(p,r)
  if not fixture:r['memory_after']=memory_snapshot()
  need(time.monotonic()<stop,'whole window deadline');r['actual_driver_execution_verified']=not fixture;return r
 except BaseException as e:
  if isinstance(e,ServerFailure):r['server']=e.receipt
  r.update(status='FAILED',actual_driver_execution_verified=False,failure=type(e).__name__+': '+str(e));raise WindowFailure(str(e),r) from e
 finally:
  try:stop_owned(child,child_started)
  except BaseException as e:r.setdefault('cleanup_failures',[]).append(type(e).__name__+': '+str(e))
  if server and not server.record.get('reaped'):
   try:r['server']=server.stop()
   except BaseException as e:r.setdefault('cleanup_failures',[]).append(type(e).__name__+': '+str(e))
  for fd in fds:
   try:os.close(fd)
   except OSError:pass

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--binding-sha',required=True);args=p.parse_args();r=dict(status='FAILED',native_admitted=False,external_origin_authenticated=False)
 try:
  raw=read_input(Path('/work/binding/binding.json'),1024**2);need(sha(raw)==args.binding_sha,'binding bytes');b=policy.parse(raw);policy.validate_request(b['request'],policy.ROOT);need(b['window_max']==1 and b['image_sha256']==policy.IMAGE_SHA,'new realGLX binding');context=collect_context(b['host_namespaces']);r=run_window(policy.SDK_PATH,policy.glx_profile(policy.ROOT),manifest=policy.expected_inventory(policy.ROOT),nonce=b['nonce']);r.update(binding_sha256=args.binding_sha,context=context);print(json.dumps(r,separators=(',',':')));return 0
 except BaseException as e:
  r=getattr(e,'receipt',r);r.update(status='FAILED',failure=type(e).__name__+': '+str(e));print(json.dumps(r,separators=(',',':')));return 2
if __name__=='__main__':raise SystemExit(main())
