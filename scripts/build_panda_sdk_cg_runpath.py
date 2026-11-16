"""Separately guarded source-built literal RUNPATH SDK; never run generated code."""
import json,os,subprocess,time,shutil,shlex
from scripts import build_panda_sdk_cg_eigen as previous
from pathlib import Path
from scripts import panda_sdk_cg_inputs as inputs
from scripts import panda_sdk_cg_eigen_inputs as eigen
from scripts import panda_sdk_cg_eigen_layout as literal
from scripts import build_panda_sdk_cg as old
from scripts import panda_sdk_routes_stage as source
from scripts import panda_sdk_routes_inputs as dep
ROOT=inputs.ROOT;need=inputs.need;read=inputs.read;sha=inputs.sha
TOOLS=old.TOOLS;FLAGS=old.FLAGS;write=old.write;run_owned=old.run_owned;verify_records=old.verify_records;capture_headers=old.capture_headers;private_tree=old.private_tree;verify_compile=old.verify_compile
query_commands=previous.query_commands;measure_tools=previous.measure_tools;tool_facts=previous.tool_facts;verify_tools=previous.verify_tools
CONTRACT='docs/evidence/panda-sdk-cg-loader-search-01/contract.json'
CONTRACT_SHA='96221733dcf6cecf4ca26ec0237a52958823e8e91c30a3f31d91ac8e9a307247'
LDFLAGS="-Wl,-z,defs -Wl,--enable-new-dtags,-rpath,'$ORIGIN'"
ORIGIN_ARGUMENT='-Wl,--enable-new-dtags,-rpath,$ORIGIN'
def contract():
 raw=read(ROOT/CONTRACT,1024**2);need(sha(raw)==CONTRACT_SHA,'RUNPATH contract identity');return inputs.parse(raw)
def build_environment(sysroot):
 env=previous.build_environment(sysroot);env['LDFLAGS']=LDFLAGS;return env
def validate_environment(env,private):
 need(env==build_environment(private) and env['LDFLAGS']==contract()['future']['ldflags'],'exact source-built RUNPATH environment')
def validate_link_command(argv,target):
 need(type(argv) is list and argv and argv[0]==TOOLS['cxx'] and argv.count('-shared')==1 and '-c' not in argv and argv.count('-o')==1,'closed shared-link compiler/output form');at=argv.index('-o');need(at+1<len(argv) and argv[at+1]==str(target),'exact link output');need(argv.count(ORIGIN_ARGUMENT)==1 and argv.count('-Wl,-z,defs')==1,'one literal origin and retained defs')
 for token in argv[1:]:
  need(type(token) is str and not token.startswith(('@','-Xlinker','-R','--rpath','--runpath','--enable-new-dtags','--disable-new-dtags','-specs','--specs')),'no indirect linker path options')
  if token.startswith('-Wl,'):need(token in (ORIGIN_ARGUMENT,'-Wl,-z,defs','-Wl,-soname='+Path(target).name),'closed linker options')
 return argv
def capture_link_commands(log,out):
 targets={'candidate':Path(out)/'sdk/lib/libpandagl.so','build_panda':Path(out)/'sdk/lib/libpanda.so.1.10'};result={}
 for line in log.splitlines():
  if not line.startswith(TOOLS['cxx']+' '):continue
  argv=shlex.split(line)
  if '-c' in argv or '-o' not in argv:continue
  at=argv.index('-o');need(at+1<len(argv),'link output argument')
  for key,target in targets.items():
   if argv[at+1]==str(target):need(key not in result,'duplicate selected link command');result[key]=validate_link_command(argv,target)
 need(set(result)==set(targets),'both selected link commands observed');return result
BRANCH='prepare/panda-sdk-cg-runpath-build-20261116-03'
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
 out=Path(out);out.mkdir(parents=True,exist_ok=False);r=dict(schema='panda-sdk-cg-runpath-build-v3',status='BLOCKED',build_start_attempts=0,target_execution=False,native_admitted=False,stage7_complete=False);write(out/'receipt.json',r)
 try:
  action_context();stage=Path(stage).resolve();private=Path(qualified_inputs['root']).resolve();need(qualified_inputs['status']=='CURRENT_IMAGE_CG_INPUTS_QUALIFIED_DATA_ONLY' and qualified_inputs['contract_sha256']==inputs.CONTRACT_SHA,'qualified inputs');verify_tools(tool_profile);need(tool_profile['compiler_major']==13 and tool_profile['tools']==TOOLS,'new gcc13 profile');need(qualified_eigen['status']=='EIGEN_HEADERS_QUALIFIED_DATA_ONLY' and qualified_eigen['contract_sha256']==eigen.CONTRACT_SHA and Path(qualified_eigen['root']).resolve()==private,'qualified Eigen root');manifest=source.verify_stage(stage)
  for name,row in qualified_inputs['files'].items():need(sha(read(private/name,64*1024**2))==row['sha256'],'private Cg drift')
  for name,row in qualified_eigen['files'].items():need(sha(read(private/name,2*1024**2))==row['sha256'],'private Eigen drift')
  header_roots=[Path('/usr/include'),Path('/usr/lib/gcc/x86_64-linux-gnu/13/include'),Path('/usr/share/bison')];host=capture_headers(header_roots);write(out/'host-before.json',host);write(out/'tools-before.json',tool_profile);write(out/'source-manifest.json',manifest)
  before_private=private_tree(private);write(out/'private-before.json',before_private)
  cmd=build_command(stage,private,out,TOOLS['python']);from scripts.panda_sdk_cg_runpath_policy import reserve_build
  environment=build_environment(private);validate_environment(environment,private);r.update(runpath_contract_sha256=CONTRACT_SHA,link_environment=environment);write(out/'receipt.json',r)
  reserve_build(out.parent/'cg-runpath-build-start.json');r.update(status='BUILDING',build_start_attempts=1,argv=cmd,source_manifest_sha256=sha(read(stage/source.MANIFEST,16*1024**2)),contract_sha256=inputs.CONTRACT_SHA);write(out/'receipt.json',r)
  compile_started=time.monotonic();compile_deadline=compile_started+1200
  process=run_owned(cmd,stage,environment,out/'makepanda',1200,disk_root=out);r['command']=process;write(out/'receipt.json',r);need(process['status']=='EXITED' and process['returncode']==0 and process['streams_complete'] and process['owned_group_reaped'],'makepanda build failed')
  commands=[];log=(out/'makepanda/stdout.log').read_text();r['link_commands']=capture_link_commands(log,out);write(out/'receipt.json',r)
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
