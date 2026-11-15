"""Measured new gcc13 Cg build, and a compile-only layout object; no target load."""
import json,os,selectors,signal,stat,subprocess,time,shutil
from pathlib import Path
from scripts import panda_sdk_cg_inputs as inputs
from scripts import panda_sdk_routes_stage as source
from scripts import panda_sdk_routes_inputs as dep
need=inputs.need;read=inputs.read;sha=inputs.sha;ROOT=inputs.ROOT
FLAGS='-D_GLIBCXX_USE_CXX11_ABI=0 -MD'
TOOLS={'cc':'/usr/bin/gcc-13','cxx':'/usr/bin/g++-13','readelf':'/usr/bin/readelf','objdump':'/usr/bin/objdump','ld':'/usr/bin/ld','as':'/usr/bin/as','ar':'/usr/bin/ar','ranlib':'/usr/bin/ranlib','bison':'/usr/bin/bison','flex':'/usr/bin/flex','m4':'/usr/bin/m4','pkg-config':'/usr/bin/pkg-config','python':'/usr/bin/python3','git':'/usr/bin/git'}
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def record(p):
 p=Path(p)
 try:real=p.resolve(strict=True);raw=read(real,64*1024**2)
 except OSError as e:raise ValueError('missing tool/input') from e
 return dict(resolved_path=str(real),nbytes=len(raw),sha256=sha(raw))
def verify_records(rows):
 for p,r in rows.items():need(record(p)==r,'tool/input drift: '+p)
def run_owned(command,cwd,env,out,seconds,stream_limit=16*1024**2,disk_root=None,disk_limit=8*1024**3):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);started=time.monotonic();r=dict(argv=list(command),cwd=str(cwd),status='SPAWN_FAILED',returncode=None,owned_group_reaped=True,streams_complete=False,elapsed_seconds=0);write(out/'command.json',r);p=None;sel=selectors.DefaultSelector();counts={'stdout':0,'stderr':0};saved=dict(counts);hashes={k:__import__('hashlib').sha256() for k in counts};files={k:(out/(k+'.log')).open('xb') for k in counts};last_disk=started
 try:
  p=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,start_new_session=True)
  r['pid']=p.pid;r['status']='RUNNING'
  for k,stream in [('stdout',p.stdout),('stderr',p.stderr)]:os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,k)
  while sel.get_map():
   now=time.monotonic()
   if now-started>seconds:r['status']='TIMEOUT';break
   if disk_root and now-last_disk>.25:
    used=sum(q.stat().st_size for q in Path(disk_root).rglob('*') if q.is_file() and not q.is_symlink());last_disk=now
    if used>disk_limit:r['status']='DISK_LIMIT';break
   for key,_ in sel.select(min(.05,max(.001,seconds-(now-started)))):
    block=os.read(key.fileobj.fileno(),65536)
    if not block:sel.unregister(key.fileobj);key.fileobj.close();continue
    k=key.data;hashes[k].update(block);counts[k]+=len(block);keep=block[:max(0,stream_limit-saved[k])];files[k].write(keep);saved[k]+=len(keep)
    if counts[k]>stream_limit:r['status']='OUTPUT_LIMIT';break
   if r['status']!='RUNNING':break
  if r['status']=='RUNNING':
   try:p.wait(timeout=max(.001,seconds-(time.monotonic()-started)));r['status']='EXITED';r['streams_complete']=True
   except subprocess.TimeoutExpired:r['status']='TIMEOUT'
 except (OSError,ValueError) as e:r['failure']=type(e).__name__+': '+str(e)
 finally:
  if p:
   try:os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:p.wait(timeout=1)
   except subprocess.TimeoutExpired:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    try:p.wait(timeout=1)
    except subprocess.TimeoutExpired:r['owned_group_reaped']=False
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   r['returncode']=p.returncode
  for key in list(sel.get_map().values()):key.fileobj.close()
  sel.close()
  for f in files.values():f.close()
  r.update(elapsed_seconds=time.monotonic()-started,streams={k:dict(observed_nbytes=counts[k],saved_nbytes=saved[k],sha256=hashes[k].hexdigest()) for k in counts});write(out/'command.json',r)
 return r

def build_environment(sysroot):
 sysroot=Path(sysroot);return dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',PYTHONNOUSERSITE='1',CC=TOOLS['cc'],CXX=TOOLS['cxx'],RPM_OPT_FLAGS=FLAGS,LDFLAGS='-Wl,-z,defs',PKG_CONFIG_LIBDIR=str(sysroot/'usr/lib/pkgconfig'),PKG_CONFIG_SYSROOT_DIR=str(sysroot),BISON_PKGDATADIR='/usr/share/bison',M4=TOOLS['m4'])
def build_command(stage,private,out,python):
 stage,private,out=map(Path,(stage,private,out));cmd=[python,'-B',str(stage/'makepanda/makepanda.py'),'--nothing','--use-gl','--use-x11','--use-nvidiacg','--no-python','--no-copy-python','--optimize','3','--threads','2','--git-commit',source.old.REVISION,'--outputdir',str(out/'sdk'),'--nocolor','--verbose']
 for pkg in ['gl','x11','nvidiacg','cggl']:cmd+=['--'+pkg+'-incdir',str(private/'usr/include'),'--'+pkg+'-libdir',str(private/'usr/lib/x86_64-linux-gnu')]
 return cmd

def verify_compile(cmd):
 need(cmd.count('-MD')==1 and cmd.count('-D_GLIBCXX_USE_CXX11_ABI=0')==1 and sum('_GLIBCXX_USE_CXX11_ABI' in x for x in cmd)==1,'one exact ABI0/MD flag')
def layout_command(include,private,out,cxx):
 return [cxx,'-std=gnu++11','-D_GLIBCXX_USE_CXX11_ABI=0','-MD','-fno-access-control','-Wno-invalid-'+'offsetof','-I'+str(include),'-I'+str(Path(private)/'usr/include'),'-c',str(ROOT/'native/panda_sdk_cg_v1/layout_contract.cxx'),'-o',str(out)]
def action_context():
 need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')=='rownlvh8875-coder/big-model-closed-loop-benchmark' and os.environ.get('GITHUB_REF_NAME')=='prepare/panda-sdk-cg-build-20261115-01' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and str(ROOT).startswith('/home/runner/work/'),'qualified build-only Actions context')

def measure_tools(paths=None,out=None):
 selected=dict(TOOLS if paths is None else paths);rows={};queries=[]
 profile=dict(schema='panda-sdk-cg-tools-v1',status='PREFLIGHT',tools=selected,files=rows,queries=queries,compiler_major=13)
 def save():
  if out is not None:write(out,profile)
 save()
 try:
  for name,path in selected.items():rows[path]=record(path);save()
  need(set(selected)==set(TOOLS),'complete tool set')
  env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}
  for name in ('cc','cxx'):
   raw=subprocess.check_output([selected[name],'-dumpfullversion'],env=env,timeout=5);need(len(raw)<=4096 and raw.decode().strip().split('.')[0]=='13','compiler major13 required');queries.append(dict(argv=[selected[name],'-dumpfullversion'],stdout=raw.decode()))
   args=['-print-prog-name=cc1plus' if name=='cxx' else '-print-prog-name=cc1','-print-prog-name=collect2','-print-prog-name=as','-print-prog-name=ld','-print-file-name=crti.o','-print-file-name=crtbeginS.o','-print-file-name=crtendS.o','-print-file-name=crtn.o','-print-file-name=libgcc.a','-print-file-name=libgcc_s.so','-print-file-name=libstdc++.so','-print-search-dirs']
   for arg in args:
    argv=[selected[name],'-shared','-fPIC',arg];raw=subprocess.check_output(argv,env=env,timeout=5);need(len(raw)<=16384,'bounded tool query');value=raw.decode().strip();query=dict(argv=argv,stdout=raw.decode())
    if arg!='-print-search-dirs':
     chosen=value if Path(value).is_absolute() else shutil.which(value,path=env['PATH']) if arg.startswith('-print-prog-name=') else None
     need(chosen is not None and Path(chosen).is_absolute(),'resolved selected compiler input');query['selected_path']=chosen;rows[chosen]=record(chosen)
    queries.append(query)
  verify_records(rows);profile['status']='VERIFIED';save();return profile
 except (OSError,subprocess.SubprocessError,ValueError) as e:
  profile.update(status='FAILED',failure=type(e).__name__+': '+str(e));save();raise ValueError('missing/unqualified build tool: '+str(e)) from e

def verify_tools(profile):
 verify_records(profile['files']);current=measure_tools(profile['tools']);need(current==profile,'compiler search selection drift')

def capture_headers(roots):
 result={};total=0
 for root in roots:
  root=Path(root);need(root.is_dir(),'host header root')
  for p in [root,*sorted(root.rglob('*'))]:
   need(len(result)<65536,'host header nodes')
   if p.is_symlink():r=dict(kind='symlink',target=os.readlink(p))
   elif p.is_dir():r=dict(kind='directory',mode=stat.S_IMODE(p.stat().st_mode))
   else:r=dep.file_record(p);total+=r['nbytes'];need(total<=1024**3,'host header bytes')
   result[str(p)]=r
 return result

def private_tree(root):
 root=Path(root).resolve();rows={}
 for p in sorted(root.rglob('*')):
  if p.is_symlink():
   need(p.resolve(strict=True).is_relative_to(root),'private alias escapes qualified tree');rows[str(p.relative_to(root))]=dict(kind='symlink',target=os.readlink(p))
  elif p.is_file():rows[str(p.relative_to(root))]=dep.file_record(p)
 return rows

def validate_declared_headers(rows):
 for row in rows:
  if row['origin']=='host':need(not (row['path'].startswith('/usr/include/') and any('/'+n+'/' in row['path'] for n in ('GL','Cg','X11'))),'unregistered host graphics header')

def compile_layout(sdk_include,qualified_inputs,out,tool_profile):
 action_context();out=Path(out);out.mkdir(exist_ok=False);verify_tools(tool_profile);obj=out/'layout-contract.o';cmd=layout_command(sdk_include,qualified_inputs['root'],obj,tool_profile['tools']['cxx']);r=run_owned(cmd,ROOT,build_environment(qualified_inputs['root']),out/'compile',60);write(out/'receipt.json',dict(command=r,target_execution=False));need(r['status']=='EXITED' and r['returncode']==0 and r['streams_complete'] and r['owned_group_reaped'],'layout compilation failed');verify_tools(tool_profile);return dict(object=str(obj),object_sha256=sha(read(obj,1024**2)),command=r,target_execution=False)

def build(stage,qualified_inputs,out,tool_profile):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);r=dict(schema='panda-sdk-cg-build-v1',status='BLOCKED',build_start_attempts=0,target_execution=False,native_admitted=False,stage7_complete=False);write(out/'receipt.json',r)
 try:
  action_context();stage=Path(stage).resolve();private=Path(qualified_inputs['root']).resolve();need(qualified_inputs['status']=='CURRENT_IMAGE_CG_INPUTS_QUALIFIED_DATA_ONLY' and qualified_inputs['contract_sha256']==inputs.CONTRACT_SHA,'qualified inputs');verify_tools(tool_profile);need(tool_profile['compiler_major']==13 and tool_profile['tools']==TOOLS,'new gcc13 profile');manifest=source.verify_stage(stage)
  for name,row in qualified_inputs['files'].items():need(sha(read(private/name,64*1024**2))==row['sha256'],'private Cg drift')
  header_roots=[Path('/usr/include'),Path('/usr/lib/gcc/x86_64-linux-gnu/13/include'),Path('/usr/share/bison')];host=capture_headers(header_roots);write(out/'host-before.json',host);write(out/'tools-before.json',tool_profile);write(out/'source-manifest.json',manifest)
  before_private=private_tree(private);write(out/'private-before.json',before_private)
  cmd=build_command(stage,private,out,TOOLS['python']);from scripts.panda_sdk_cg_build_policy import reserve_build
  reserve_build(out.parent/'cg-build-start.json');r.update(status='BUILDING',build_start_attempts=1,argv=cmd,source_manifest_sha256=sha(read(stage/source.MANIFEST,16*1024**2)),contract_sha256=inputs.CONTRACT_SHA);write(out/'receipt.json',r)
  process=run_owned(cmd,stage,build_environment(private),out/'makepanda',1200,disk_root=out);r['command']=process;write(out/'receipt.json',r);need(process['status']=='EXITED' and process['returncode']==0 and process['streams_complete'] and process['owned_group_reaped'],'makepanda build failed')
  commands=[];log=(out/'makepanda/stdout.log').read_text()
  for line in log.splitlines():
   import shlex
   if not line.startswith(('/usr/bin/gcc-13 ','/usr/bin/g++-13 ')):continue
   cmd=shlex.split(line)
   if '-c' not in cmd:continue
   verify_compile(cmd);need('-o' in cmd,'compiler object output');obj=Path(cmd[cmd.index('-o')+1]);need(obj.is_relative_to(out/'sdk') and obj.suffix=='.o','owned compiler object');d=obj.with_suffix('.d');raw=read(d,4*1024**2);commands.append(dict(command=cmd,object=str(obj),dependency_sha256=sha(raw),paths=dep.parse_dependencies(raw)))
  need(commands,'actual dependency-bearing compiler commands');used=dep.qualify_dependencies([n for row in commands for n in row['paths']],stage,out/'sdk',private,host);write(out/'compile-dependencies.json',commands);write(out/'used-inputs.json',used)
  config=(out/'sdk/include/dtool_config.h').read_text();macros={}
  for line in config.splitlines():
   f=line.split()
   if len(f)>=2 and f[0] in ('#define','#undef'):macros[f[1]]=False if f[0]=='#undef' else (' '.join(f[2:]) or True)
  need(macros.get('HAVE_CG') in ('1',True) and macros.get('HAVE_X11') in ('1',True) and macros.get('HAVE_PYTHON') is False and macros.get('STDFLOAT_DOUBLE') is False,'required generated configuration');write(out/'configuration.json',macros)
  layout=compile_layout(out/'sdk/include',qualified_inputs,out/'layout-build',tool_profile);r['layout']=layout
  layout_dep=Path(layout['object']).with_suffix('.d');raw=read(layout_dep,4*1024**2);commands.append(dict(command=layout['command']['argv'],object=layout['object'],dependency_sha256=sha(raw),paths=dep.parse_dependencies(raw)))
  project_layout=(ROOT/'native/panda_sdk_cg_v1/layout_contract.cxx').resolve()
  names=[n for row in commands for n in row['paths'] if (Path(n) if Path(n).is_absolute() else stage/n).resolve()!=project_layout]
  used=dep.qualify_dependencies(names,stage,out/'sdk',private,host);used.append(dict(path=str(project_layout),origin='source',source_group='candidate-layout-project',**dep.file_record(project_layout)));validate_declared_headers(used);write(out/'compile-dependencies.json',commands);write(out/'used-inputs.json',used)
  need(source.verify_stage(stage)==manifest,'source changed during build');verify_tools(tool_profile)
  for p,row in host.items():
   if row['kind']=='file' and p in {x['path'] for x in used}:need(dep.file_record(Path(p))==row,'used host-header drift')
  need(private_tree(private)==before_private,'private input drift')
  candidate=out/'sdk/lib/libpandagl.so';buildpanda=out/'sdk/lib/libpanda.so.1.10';need(candidate.is_file() and buildpanda.is_file(),'actual candidate outputs');write(out/'sdk-output-manifest.json',source.old.base.tree_records(out/'sdk'));write(out/'tools-after.json',tool_profile)
  r.update(status='CG_SDK_COMPILED_NOT_LOADED',candidate=str(candidate),candidate_sha256=sha(read(candidate,4*1024**2)),build_panda=str(buildpanda),build_panda_sha256=sha(read(buildpanda,64*1024**2)),configuration=macros,compiler_commands=len(commands),layout_object=layout['object'],source_state_instances=None);write(out/'receipt.json',r);return r
 except BaseException as e:
  if (out/'layout-build/receipt.json').is_file():r['layout_failed_command']=inputs.parse(read(out/'layout-build/receipt.json',1024**2))
  r.update(status='BLOCKED' if r['build_start_attempts']==0 else 'FAILED',failure=type(e).__name__+': '+str(e));write(out/'receipt.json',r);raise
