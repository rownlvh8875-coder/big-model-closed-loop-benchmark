"""Inspect the exact aa7e SDK and compiler-selected sources; never load Panda."""
import argparse,hashlib,json,re,shlex,subprocess,time
from pathlib import Path
from scripts import panda_adapter_sdk_stage as stage
from scripts import build_panda_adapter_sdk as sdk
from scripts import panda_dispatch_coverage as inventory
from scripts.build_panda_source_dispatch import stop_build_group
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE='aa7e14e71f98b083faa60536ecf6b0a05e3996b4771d38e4a2ccfd43c0903088'
PREPROCESSOR_PROFILE_SHA='de9913e26f5e465bbc8153596f5639827761ab68094e112c8290f09e90e87c6c'
BUILD_LOG_SHA='eddef4b58530fd9cc18e9c78f073d2cabc7256610c40fe93dee01440442e3e9f'
BUILD_LOG_NBYTES=521374
PINS={'selected-sdk.json':'a459629ab59d297da402cf1c37dd2c5242ba4edeaf10303daa66be42629ad9e1','after-fix/build/receipt.json':'909d9c7efc7fcfddd314231e7e44cb17330d01722c7d126fc479090d6d7122ef','after-fix/build/sdk-output-manifest.json':'b775210f6fb68eab8db463eb9b858c355dfa124afa756d346e73fb3991a73839'}
MEMBERS=dict(stage.base.MEMBERS)
need=stage.need

def digest(data):return hashlib.sha256(data).hexdigest()
def fixed(name):
    data=inventory.read_input(ROOT/'docs/evidence/panda-adapter-sdk-01'/name,16*1024**2)
    need(digest(data)==PINS[name],'fixed SDK evidence pin');return json.loads(data)

def select_sources(data,members):
    need(type(data) is bytes and len(data)<=32*1024**2 and type(members) is dict and members,'preprocessed input budget')
    need(all(type(k) is str and type(v) is str and k==Path(v).name for k,v in members.items()),'source marker profile')
    try:text=data.decode('utf-8')
    except UnicodeError as exc:raise ValueError('preprocessed UTF8') from exc
    result={name:[] for name in members};current=None
    reverse={v:k for k,v in members.items()};need(len(reverse)==len(members),'duplicate marker path')
    for line in text.splitlines(True):
        if line.lstrip().startswith('#') and not line.startswith('#pragma '):
            marker=re.fullmatch(r'# ([0-9]{1,10}) "([^"\n]+)"(?: [1-4])*\s*',line)
            need(marker is not None and int(marker[1])<2**31,'malformed compiler line marker')
            path=marker[2];name=Path(path).name
            need(name not in members or path==members[name],'unexpected selected source origin')
            current=reverse.get(path)
        elif current is not None:result[current].append(line)
    need(all(lines for lines in result.values()),'selected source missing')
    selected={name:''.join(lines).encode() for name,lines in result.items()}
    need(all(len(raw)<=1024**2 for raw in selected.values()),'selected source budget');return selected

def assess_selected(sources,runtime):
    need(type(runtime) is bytes and digest(runtime)==stage.NATIVE_PINS['panda_source_dispatch.cxx'],'runtime pin mismatch')
    need(type(sources) is dict and 1<=len(sources)<=4,'selected source set')
    routes=set(re.findall(rb'PSD_ROUTE\("([^"]+)"',runtime));routes={n.decode() for n in routes}|{'glReadPixels'}
    reports=[inventory.scan_source(raw,name) for name,raw in sorted(sources.items())]
    names={r['name'] for s in reports for r in s['literal_lookups']};safe=names-routes
    prohibited=sorted(n for n in safe if n.startswith(inventory._UNSAFE))
    computed=[dict(file=s['file'],**row) for s in reports for row in s['computed_lookups']]
    tables=[]
    for name,raw in sources.items():
        text=raw.decode();at=text.find('compiled_function_table[]')
        if at>=0:
            end=text.find('};',at);need(end>=at,'compiled extension table boundary')
            body=text[at:end];tables.extend(re.findall(r'\{\s*"(gl[A-Za-z0-9_]+)"\s*,',body))
    need(len(tables)==len(set(tables)),'duplicate compiled table name')
    paths=sorted({m.decode() for raw in sources.values() for m in re.findall(rb'psd_path\(\s*(PSD_PATH_[A-Z_]+)',raw)})
    blockers=[]
    if len(safe)>256:blockers.append('SAFE_NAME_CAP_EXCEEDED')
    if prohibited:blockers.append('UNSUPPORTED_PREFIX_PROHIBITED_LOOKUPS')
    if computed:blockers.append('COMPUTED_LOOKUP_REQUIRES_BINDING')
    return dict(schema='panda-selected-sdk-coverage-v1',lookup_names=sorted(names),lookup_count=len(names),routed_lookup_names=sorted(names&routes),routes=sorted(routes),required_safe_names=sorted(safe),required_safe_count=len(safe),safe_cap=256,unsupported_prefix_names=prohibited,computed_lookups=computed,compiled_table_names=sorted(tables),selected_resolver_paths=paths,sources=reports,blockers=blockers,name_capacity_satisfied=len(safe)<=256,all_selected_lookups_routable=not blockers,preprocessor_branches_selected=True,runtime_paths_observed=False,runtime_binding_qualified=False,native_admitted=False)

def commands_for(source,build,sysroot):
    common=['/usr/bin/g++','-std=gnu++11','-ftemplate-depth-70','-fPIC','-c','-o']
    includes=['-I'+str(sysroot/'usr/include'),'-I'+str(build/'sdk/tmp'),'-I'+str(build/'sdk/include')]
    flags=['-fvisibility=hidden','-pthread','-fno-exceptions','-fno-strict-aliasing','-ffast-math','-fno-stack-protector','-fno-finite-math-only','-fno-unsafe-math-optimizations','-O2','-Wall','-Wno-unused-function','-Wno-reorder','-DBUILDING_PANDAGL']
    return [common+[str(build/'sdk/tmp/p3glgsg_glgsg.o'),*includes,'-Ipanda/src/glgsg','-Ipanda/src/glstuff',*flags,'panda/src/glgsg/glgsg.cxx'],common+[str(build/'sdk/tmp/p3glxdisplay_composite1.o'),*includes,'-DHAVE_GLX=','-Ipanda/src/glxdisplay',*flags,'panda/src/glxdisplay/p3glxdisplay_composite1.cxx']]

def verify_commands(log,commands):
    logged=[shlex.split(line) for line in log.splitlines() if line.startswith('/usr/bin/g++ ')]
    for cmd in commands:
        target=cmd[cmd.index('-o')+1]
        matching=[line for line in logged if '-o' in line and line.index('-o')+1<len(line) and line[line.index('-o')+1]==target]
        need(matching==[cmd],'exact original compile command required')

def verify_build_log(path,sha=BUILD_LOG_SHA,nbytes=BUILD_LOG_NBYTES):
    data=inventory.read_input(path,32*1024**2)
    need(len(data)==nbytes and digest(data)==sha,'original build log pin mismatch');return data

def preprocessor_profile():
    data=inventory.read_input(ROOT/'docs/evidence/panda-sdk-integration-01/preprocessor-profile.json',1024**2)
    need(digest(data)==PREPROCESSOR_PROFILE_SHA,'preprocessor profile pin mismatch');return json.loads(data)

def verify_preprocessor_inputs(profile):
    driver=Path(profile['driver_path']);need(str(driver.resolve())==profile['driver_realpath'],'preprocessor tool pin: driver path')
    for path,sha in ((driver.resolve(),profile['driver_sha256']),(Path(profile['cc1plus_path']),profile['cc1plus_sha256'])):
        need(digest(inventory.read_input(path,64*1024**2))==sha,'preprocessor tool pin mismatch')
    for name in profile['selection_absent_paths']:
        p=Path(name);need(not p.exists() and not p.is_symlink(),'compiler selection configuration changed')

def verify_preprocessor_selection(profile,env,out,prefix):
    verify_preprocessor_inputs(profile);results=[]
    for index,(flag,sha) in enumerate(profile['query_stdout_sha256'].items()):
        r=sdk.cpu.run_command([profile['driver_path'],flag],ROOT,env,out/(prefix+'-'+str(index)),5)
        need(r['returncode']==0 and r['stderr']=='' and digest(r['stdout'].encode())==sha,'compiler selection query changed');results.append(r)
    verify_preprocessor_inputs(profile);return results

def preprocess(command,cwd,env,prefix):
    cmd=list(command);i=cmd.index('-o');del cmd[i:i+2];cmd.remove('-c');cmd.append('-E')
    stdout=Path(str(prefix)+'.ii');stderr=Path(str(prefix)+'.stderr');start=time.perf_counter();reason=None;p=None
    try:
        with stdout.open('xb') as output,stderr.open('xb') as error:
            p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=output,stderr=error,start_new_session=True)
            while p.poll() is None:
                if time.perf_counter()-start>45:reason='deadline';break
                if stdout.stat().st_size>32*1024**2 or stderr.stat().st_size>2*1024**2:reason='output_budget';break
                time.sleep(.05)
    finally:
        if p is not None:stop_build_group(p)
    record=dict(command=cmd,returncode=p.returncode,wall_seconds=time.perf_counter()-start,limit_failure=reason,stdout_nbytes=stdout.stat().st_size,stderr_nbytes=stderr.stat().st_size)
    Path(str(prefix)+'.json').write_text(json.dumps(record,indent=2)+'\n')
    need(p.returncode==0 and reason is None and stdout.stat().st_size<=32*1024**2 and stderr.stat().st_size<=2*1024**2,'preprocessing failed; outputs retained')
    return inventory.read_input(stdout,32*1024**2),record

def audit_sdk(out):
    out=stage.canonical(out);need(not out.exists(),'existing audit preserved');out.mkdir(parents=True)
    selected=fixed('selected-sdk.json');receipt=fixed('after-fix/build/receipt.json');rows=fixed('after-fix/build/sdk-output-manifest.json')
    source=stage.canonical(selected['source_stage']);build=ROOT/'output/stage7-panda-adapter-sdk-01/build-final';sysroot=ROOT/'output/stage7-panda-source-dispatch-01/sysroot';profile=preprocessor_profile()
    def verify():
        need(preprocessor_profile()==profile,'preprocessor profile changed');verify_preprocessor_inputs(profile);verify_build_log(build/'makepanda.log')
        manifest=stage.verify_stage(source);need(len(manifest['source_tree'])==7289,'complete source required');need(len(sdk.dependency_profile(sysroot))==665,'complete private sysroot required')
        for name,sha in receipt['tool_sha256'].items():need(digest(inventory.read_input(Path(name).resolve(),64*1024**2))==sha,'build tool changed')
        for row in rows:
            p=ROOT/'output/stage7-panda-adapter-sdk-01'/row['path']
            if row['kind']=='symlink':need(p.is_symlink() and str(p.readlink())==row['target'],'SDK output link changed')
            else:need(not p.is_symlink() and p.stat().st_size==row['nbytes'] and digest(p.read_bytes())==row['sha256'],'SDK output changed')
        image=inventory.read_input(Path(selected['candidate_library']),64*1024**2);need(digest(image)==CANDIDATE,'candidate image changed');return manifest
    manifest=verify();commands=commands_for(source,build,sysroot);log=verify_build_log(build/'makepanda.log').decode();verify_commands(log,commands)
    identity_before=verify_preprocessor_selection(profile,sdk.build_env(sysroot),out,'compiler-before')
    sources={};records=[]
    groups=[{n:MEMBERS[n] for n in ('glGraphicsStateGuardian_src.cxx','glGraphicsBuffer_src.cxx')},{n:MEMBERS[n] for n in ('glxGraphicsStateGuardian.cxx','posixGraphicsStateGuardian.cxx')}]
    for index,(command,group) in enumerate(zip(commands,groups)):
        data,record=preprocess(command,source,sdk.build_env(sysroot),out/('tu-'+str(index)));sources.update(select_sources(data,group));records.append(record)
    need(verify()==manifest,'inputs changed while preprocessing')
    identity_after=verify_preprocessor_selection(profile,sdk.build_env(sysroot),out,'compiler-after')
    for name,data in sources.items():(out/(name+'.selected')).write_bytes(data)
    r=assess_selected(sources,stage.native_files()['panda_source_dispatch.cxx']);r.update(kind='ACTUAL_PINNED_COMPILER_PREPROCESSING_DATA_ONLY',candidate_sha256=CANDIDATE,source_manifest_sha256=selected['source_manifest_sha256'],compiler_commands=records,preprocessor_tool_profile=profile,preprocessor_selection_before=identity_before,preprocessor_selection_after=identity_after,original_build_log_sha256=BUILD_LOG_SHA,original_build_log_nbytes=BUILD_LOG_NBYTES,source_files=7289,sysroot_records=665,sdk_output_records=len(rows),new_native_runs=0,new_gl_calls=0,stage7_complete=False)
    (out/'coverage.json').write_text(json.dumps(r,indent=2)+'\n');return r

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args(argv)
    try:r=audit_sdk(args.out);print(json.dumps({k:r[k] for k in ('lookup_count','required_safe_count','safe_cap','unsupported_prefix_names','blockers','native_admitted')}));return 0
    except (OSError,ValueError,subprocess.SubprocessError) as exc:print('SDK audit rejected: '+str(exc));return 2
if __name__=='__main__':raise SystemExit(main())
