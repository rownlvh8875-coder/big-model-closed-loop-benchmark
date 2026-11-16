"""New measured Eigen/Cg build and section-only descriptor; never execute target code."""
import json,os,subprocess,time,shutil
from pathlib import Path
from scripts import panda_sdk_cg_inputs as inputs
from scripts import panda_sdk_cg_eigen_inputs as eigen
from scripts import panda_sdk_cg_eigen_layout as literal
from scripts import build_panda_sdk_cg as old
from scripts import panda_sdk_routes_stage as source
from scripts import panda_sdk_routes_inputs as dep
ROOT=inputs.ROOT;need=inputs.need;read=inputs.read;sha=inputs.sha
TOOLS=old.TOOLS;FLAGS=old.FLAGS;write=old.write;run_owned=old.run_owned;verify_records=old.verify_records;capture_headers=old.capture_headers;private_tree=old.private_tree;verify_compile=old.verify_compile;build_environment=old.build_environment
def query_commands(tools):
 commands=[]
 for name in ('cc','cxx'):
  commands.append([tools[name],'-dumpfullversion'])
  for arg in ['-print-prog-name=cc1plus' if name=='cxx' else '-print-prog-name=cc1','-print-prog-name=collect2','-print-prog-name=as','-print-prog-name=ld','-print-file-name=crti.o','-print-file-name=crtbeginS.o','-print-file-name=crtendS.o','-print-file-name=crtn.o','-print-file-name=libgcc.a','-print-file-name=libgcc_s.so','-print-file-name=libstdc++.so','-print-search-dirs']:commands.append([tools[name],'-shared','-fPIC',arg])
 return commands

def measure_tools(paths=None,out=None,query_seconds=5):
 need(out is not None and 0<query_seconds<=5,'owned tool measurement output/deadline');out=Path(out);need(not out.exists() and not out.is_symlink(),'fresh tool profile');out.parent.mkdir(parents=True,exist_ok=True);selected=dict(TOOLS if paths is None else paths);rows={};queries=[];profile=dict(schema='panda-cg-eigen-tools-v2',status='PREFLIGHT',tools=selected,files=rows,queries=queries,compiler_major=13,evidence_path=str(out.absolute()));write(out,profile)
 try:
  need(set(selected)==set(TOOLS),'complete selected host tool set')
  for path in selected.values():rows[path]=old.record(path);write(out,profile)
  env=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C')
  for index,argv in enumerate(query_commands(selected)):
   folder=out.parent/(out.stem+'-queries')/str(index);r=run_owned(argv,ROOT,env,folder,query_seconds,stream_limit=65536);q=dict(argv=argv,result=r,stdout_path=str(folder/'stdout.log'),stderr_path=str(folder/'stderr.log'),stdout=read(folder/'stdout.log',65536).decode('utf-8',errors='replace'),stderr=read(folder/'stderr.log',65536).decode('utf-8',errors='replace'));queries.append(q);write(out,profile);need(r['status']=='EXITED' and r['returncode']==0 and r['owned_group_reaped'] and r['streams_complete'],'owned compiler-selection query failed');value=q['stdout'].strip();arg=argv[-1]
   if arg=='-dumpfullversion':need(len(q['stdout'])<=4096 and value.split('.')[0]=='13','compiler major13 required')
   elif arg!='-print-search-dirs':
    chosen=value if Path(value).is_absolute() else shutil.which(value,path=env['PATH']) if arg.startswith('-print-prog-name=') else None;need(chosen is not None,'selected compiler input');chosen=os.path.abspath(chosen);q['selected_path']=chosen;rows[chosen]=old.record(chosen)
   need(len(q['stdout'])<=16384,'bounded compiler selection output');write(out,profile)
  verify_records(rows);profile['status']='VERIFIED';write(out,profile);return profile
 except (ValueError,OSError,UnicodeError) as error:
  profile.update(status='FAILED',failure=type(error).__name__+': '+str(error));write(out,profile);raise ValueError('Eigen tool measurement failed: '+str(error)) from error

def tool_facts(profile):
 need(profile['schema']=='panda-cg-eigen-tools-v2' and profile['status']=='VERIFIED' and type(profile['compiler_major']) is int and profile['compiler_major']==13 and set(profile['tools'])==set(TOOLS),'verified measured profile');need([q['argv'] for q in profile['queries']]==query_commands(profile['tools']),'closed tool-selection queries');need(set(profile['tools'].values())<=set(profile['files']),'all selected tool bytes recorded');facts=[]
 for q in profile['queries']:
  r=q['result'];need(r['argv']==q['argv'] and r['status']=='EXITED' and r['returncode']==0 and r['owned_group_reaped'] is True and r['streams_complete'] is True and 0<=r['elapsed_seconds']<=10,'owned successful tool query')
  for stream in ('stdout','stderr'):
   data=q[stream].encode();x=r['streams'][stream];need(len(data)==x['observed_nbytes']==x['saved_nbytes']<=65536 and sha(data)==x['sha256'],'tool query diagnostic binding')
  if q['argv'][-1]=='-dumpfullversion':need(q['stdout'].strip().split('.')[0]=='13','measured compiler version')
  elif q['argv'][-1]!='-print-search-dirs':need(q['selected_path'] in profile['files'],'selected subtool/link input bytes')
  facts.append({k:q[k] for k in ['argv','stdout','stderr']+(['selected_path'] if 'selected_path' in q else [])})
 return dict(tools=profile['tools'],files=profile['files'],queries=facts,compiler_major=13)

def verify_tools(profile):
 root=Path(profile['evidence_path']).parent/'tool-rechecks';root.mkdir(exist_ok=True);folder=None
 for index in range(16):
  try:folder=root/str(index);folder.mkdir();break
  except FileExistsError:continue
 else:raise ValueError('tool recheck count bound')
 out=folder/'profile.json'
 try:verify_records(profile['files'])
 except (ValueError,OSError) as error:write(out,dict(schema='panda-cg-eigen-tools-v2',status='FAILED',failure='pre-query drift: '+str(error),queries=[],target_execution=False));raise
 measured=measure_tools(profile['tools'],out=out);need(tool_facts(measured)==tool_facts(profile),'compiler byte/search selection drift');return measured
BRANCH='prepare/panda-sdk-cg-eigen-build-20261116-02'
def action_context():
 need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')=='rownlvh8875-coder/big-model-closed-loop-benchmark' and os.environ.get('GITHUB_REF_NAME')==BRANCH and os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and str(ROOT).startswith('/home/runner/work/'),'qualified Eigen build-only Actions context')
def build_command(stage,private,out,python):return old.build_command(stage,private,out,python)+['--use-eigen','--eigen-incdir',str(Path(private)/'usr/include/eigen3')]
def layout_command(include,private,out,cxx):
 return [cxx,'-std=gnu++11','-D_GLIBCXX_USE_CXX11_ABI=0','-MD','-fno-access-control','-Wno-invalid-'+'offsetof','-I'+str(include),'-I'+str(Path(private)/'usr/include'),'-I'+str(Path(private)/'usr/include/eigen3'),'-c',str(ROOT/'native/panda_sdk_cg_v2/layout_contract.cxx'),'-o',str(out)]
def validate_generated(macros):
 need(all(macros.get(k) in ('1',True) for k in ('HAVE_CG','HAVE_EIGEN','HAVE_X11')) and all(macros.get(k) is False for k in ('HAVE_PYTHON','STDFLOAT_DOUBLE')),'required generated Eigen configuration')
def validate_effective(macros):
 need(all(macros.get(k)=='1' for k in ('HAVE_CG','HAVE_EIGEN','HAVE_X11','LINMATH_ALIGN')) and not macros.get('HAVE_PYTHON') and not macros.get('STDFLOAT_DOUBLE') and macros.get('MEMORY_HOOK_ALIGNMENT')=='16' and macros.get('_GLIBCXX_USE_CXX11_ABI')=='0','effective Eigen/vector configuration')
def validate_declared_headers(rows):
 old.validate_declared_headers(rows)
 for row in rows:
  if row['origin']=='host':need('/Eigen/' not in row['path'] and '/eigen3/' not in row['path'],'host Eigen fallback')
def configuration_delta(macros):
 path=ROOT/'docs/evidence/panda-sdk-cg-candidate-01/actual/acceptance/candidate/reports/configuration.json';raw=read(path,1024**2);need(sha(raw)==BASE_CONFIGURATION_SHA,'baseline generated configuration');before=inputs.parse(raw);return {k:dict(old=before.get(k),candidate=macros.get(k)) for k in sorted(set(before)|set(macros)) if before.get(k)!=macros.get(k)}
def compile_layout(sdk_include,qualified_inputs,out,tool_profile,deadline=None):
 action_context();out=Path(out);out.mkdir(exist_ok=False);verify_tools(tool_profile);obj=out/'layout-contract.o';cmd=layout_command(sdk_include,qualified_inputs['root'],obj,tool_profile['tools']['cxx']);record=dict(target_execution=False)
 def remaining(argv,key):
  seconds=min(60,deadline-time.monotonic()) if deadline is not None else 60
  if seconds<=0:
   record[key]=dict(argv=argv,status='NOT_STARTED_DEADLINE',returncode=None,owned_group_reaped=True,elapsed_seconds=0);write(out/'receipt.json',record);raise ValueError('whole SDK compile deadline exhausted')
  return seconds
 r=run_owned(cmd,ROOT,build_environment(qualified_inputs['root']),out/'compile',remaining(cmd,'command'));record['command']=r;write(out/'receipt.json',record);need(r['status']=='EXITED' and r['returncode']==0 and r['streams_complete'] and r['owned_group_reaped'],'layout compilation failed')
 extraction=literal.extract_literal(read(obj,1024**2));raw=extraction.pop('raw');descriptor=out/'layout-descriptor.data';descriptor.write_bytes(raw);measured=literal.validate_descriptor(raw)
 macro_cmd=[x for x in cmd[:-2] if x not in ('-c','-MD')]+['-E','-dM'];r=run_owned(macro_cmd,ROOT,build_environment(qualified_inputs['root']),out/'effective-macros',remaining(macro_cmd,'macro_command'),stream_limit=1024**2);record['macro_command']=r;write(out/'receipt.json',record);need(r['status']=='EXITED' and r['returncode']==0 and r['streams_complete'] and r['owned_group_reaped'],'effective macro preprocessing failed');macros={}
 for line in (out/'effective-macros/stdout.log').read_text().splitlines():
  fields=line.split(maxsplit=2)
  if len(fields)>=2 and fields[0]=='#define':macros[fields[1]]=fields[2] if len(fields)==3 else ''
 validate_effective(macros);effective=dict(schema='panda-cg-eigen-effective-config-v2',macros={k:macros.get(k) for k in ('HAVE_CG','HAVE_EIGEN','HAVE_X11','HAVE_PYTHON','STDFLOAT_DOUBLE','LINMATH_ALIGN','MEMORY_HOOK_ALIGNMENT','_GLIBCXX_USE_CXX11_ABI')},vector_alignment=measured['vector_alignment'],memory_alignment=measured['memory_alignment'],macro_stdout_sha256=sha(read(out/'effective-macros/stdout.log',1024**2)),target_execution=False);verify_tools(tool_profile);return dict(object=str(obj),object_sha256=sha(read(obj,1024**2)),descriptor=str(descriptor),descriptor_sha256=sha(raw),command=record['command'],macro_command=r,effective_configuration=effective,extraction=extraction,target_execution=False)
BASE_CONFIGURATION_SHA='28d178d6752ff8fc18a78c5ba1ba6be76c59a0712e1c1655f11b69de9478c836'
def build(stage,qualified_inputs,qualified_eigen,out,tool_profile):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);r=dict(schema='panda-sdk-cg-eigen-build-v2',status='BLOCKED',build_start_attempts=0,target_execution=False,native_admitted=False,stage7_complete=False);write(out/'receipt.json',r)
 try:
  action_context();stage=Path(stage).resolve();private=Path(qualified_inputs['root']).resolve();need(qualified_inputs['status']=='CURRENT_IMAGE_CG_INPUTS_QUALIFIED_DATA_ONLY' and qualified_inputs['contract_sha256']==inputs.CONTRACT_SHA,'qualified inputs');verify_tools(tool_profile);need(tool_profile['compiler_major']==13 and tool_profile['tools']==TOOLS,'new gcc13 profile');need(qualified_eigen['status']=='EIGEN_HEADERS_QUALIFIED_DATA_ONLY' and qualified_eigen['contract_sha256']==eigen.CONTRACT_SHA and Path(qualified_eigen['root']).resolve()==private,'qualified Eigen root');manifest=source.verify_stage(stage)
  for name,row in qualified_inputs['files'].items():need(sha(read(private/name,64*1024**2))==row['sha256'],'private Cg drift')
  for name,row in qualified_eigen['files'].items():need(sha(read(private/name,2*1024**2))==row['sha256'],'private Eigen drift')
  header_roots=[Path('/usr/include'),Path('/usr/lib/gcc/x86_64-linux-gnu/13/include'),Path('/usr/share/bison')];host=capture_headers(header_roots);write(out/'host-before.json',host);write(out/'tools-before.json',tool_profile);write(out/'source-manifest.json',manifest)
  before_private=private_tree(private);write(out/'private-before.json',before_private)
  cmd=build_command(stage,private,out,TOOLS['python']);from scripts.panda_sdk_cg_eigen_policy import reserve_build
  reserve_build(out.parent/'cg-eigen-build-start.json');r.update(status='BUILDING',build_start_attempts=1,argv=cmd,source_manifest_sha256=sha(read(stage/source.MANIFEST,16*1024**2)),contract_sha256=inputs.CONTRACT_SHA);write(out/'receipt.json',r)
  compile_started=time.monotonic();compile_deadline=compile_started+1200
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
  validate_generated(macros);write(out/'configuration.json',macros);write(out/'configuration-delta.json',configuration_delta(macros))
  layout=compile_layout(out/'sdk/include',qualified_inputs,out/'layout-build',tool_profile,deadline=compile_deadline);r['compile_elapsed_seconds']=time.monotonic()-compile_started;need(r['compile_elapsed_seconds']<=1200,'SDK plus descriptor compile budget');r['layout']=layout;r['effective_configuration']=layout['effective_configuration'];write(out/'effective-configuration.json',layout['effective_configuration']);write(out/'layout-extraction.json',layout['extraction'])
  layout_dep=Path(layout['object']).with_suffix('.d');raw=read(layout_dep,4*1024**2);commands.append(dict(command=layout['command']['argv'],object=layout['object'],dependency_sha256=sha(raw),paths=dep.parse_dependencies(raw)))
  project_layout=(ROOT/'native/panda_sdk_cg_v2/layout_contract.cxx').resolve()
  names=[n for row in commands for n in row['paths'] if (Path(n) if Path(n).is_absolute() else stage/n).resolve()!=project_layout]
  used=dep.qualify_dependencies(names,stage,out/'sdk',private,host);used.append(dict(path=str(project_layout),origin='source',source_group='candidate-layout-project',**dep.file_record(project_layout)));validate_declared_headers(used);write(out/'compile-dependencies.json',commands);write(out/'used-inputs.json',used)
  need(source.verify_stage(stage)==manifest,'source changed during build');after_tools=verify_tools(tool_profile)
  for p,row in host.items():
   if row['kind']=='file' and p in {x['path'] for x in used}:need(dep.file_record(Path(p))==row,'used host-header drift')
  need(private_tree(private)==before_private,'private input drift')
  candidate=out/'sdk/lib/libpandagl.so';buildpanda=out/'sdk/lib/libpanda.so.1.10';need(candidate.is_file() and buildpanda.is_file(),'actual candidate outputs');write(out/'sdk-output-manifest.json',source.old.base.tree_records(out/'sdk'));write(out/'tools-after.json',after_tools)
  r.update(status='CG_EIGEN_SDK_COMPILED_NOT_LOADED',candidate=str(candidate),candidate_sha256=sha(read(candidate,4*1024**2)),build_panda=str(buildpanda),build_panda_sha256=sha(read(buildpanda,64*1024**2)),configuration=macros,compiler_commands=len(commands),layout_object=layout['object'],layout_descriptor=layout['descriptor'],source_state_instances=None);write(out/'receipt.json',r);return r
 except BaseException as e:
  if (out/'layout-build/receipt.json').is_file():r['layout_failed_command']=inputs.parse(read(out/'layout-build/receipt.json',1024**2))
  r.update(status='BLOCKED' if r['build_start_attempts']==0 else 'FAILED',failure=type(e).__name__+': '+str(e));write(out/'receipt.json',r);raise
