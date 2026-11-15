"""Exact source-only name classification for the new SDK; no runtime authority."""
import argparse,collections,json,re,shlex
from pathlib import Path
from scripts import panda_sdk_routes_stage as stage
from scripts import panda_sdk_routes_inputs as inputs
from scripts import panda_sdk_coverage as previous
from scripts import panda_dispatch_coverage as inv
from scripts import build_panda_adapter_sdk as sdk
ROOT=stage.ROOT;need=stage.need
PROFILE_SHA='1cc65667486ddbaa4461e0c55141e1258600aa2bc1fa98da56fc3cc1746f99e7'
SOURCE_SHA={'glGraphicsBuffer_src.cxx':'972b69599873c470879b9c8fbbe03c2e0297178e24f283fd5f812c37387b6ac6','glGraphicsStateGuardian_src.cxx':'1aa249251d6b002917b785c5284bc3048c2584d10fc6515491ff7eaeaa678cec','glxGraphicsStateGuardian.cxx':'8038c1763e9a577e3f313a9a2d2d3ad5ae39438bd027ae0ba931ac81cefe701c','posixGraphicsStateGuardian.cxx':'375ab78cc107c032058b3d42abe2554b822b6fc6371ca0486ca0c0d4ac40bbc1'}
def name_profile():
    data=inv.read_input(ROOT/'docs/evidence/panda-sdk-routes-02/name-profile.json',1024**2);need(inputs.sha(data)==PROFILE_SHA,'explicit name profile pin');return json.loads(data)
def assess_names(names,routes,safe_names):
    required=inv._names(list(names),20000);routed=inv._names(list(routes),64);safe=inv._names(list(safe_names),256)
    need(not safe&routed and not any(n.startswith(inv._UNSAFE) for n in safe),'unsafe or routed name in safe profile')
    missing=required-routed-safe;extra=safe-required
    return dict(lookup_names=sorted(required),lookup_count=len(required),routed_lookup_names=sorted(required&routed),safe_names=sorted(safe),safe_name_count=len(safe),safe_cap=256,unclassified_names=sorted(missing),unused_profile_names=sorted(extra),all_selected_names_classified=not missing and not extra,native_admitted=False)
def qualify_selected(sources,runtime,profile):
    need(inputs.sha(runtime)==stage.NATIVE_PINS['panda_source_dispatch.cxx'],'versioned runtime pin')
    need(profile==name_profile(),'explicit profile mismatch');need(set(sources)==set(SOURCE_SHA) and all(inputs.sha(sources[n])==h for n,h in SOURCE_SHA.items()),'selected source pin mismatch')
    routes=re.findall(rb'PSD_ROUTE\("([^"]+)"',runtime);need(len(routes)==len(set(routes))==28,'typed route table');routes={n.decode() for n in routes}|{'glReadPixels'}
    reports=[inv.scan_source(sources[n],n) for n in sorted(sources)];names={r['name'] for s in reports for r in s['literal_lookups']}
    safe=[r['name'] for r in profile['safe_names']];need(len(safe)==252 and all(r['category'] in profile['categories'] for r in profile['safe_names']),'explicit252classification')
    result=assess_names(names,routes,safe);need(result['all_selected_names_classified'],'selected names unclassified')
    computed=[dict(file=s['file'],**r) for s in reports for r in s['computed_lookups']]
    expected={('glGraphicsStateGuardian_src.cxx','do_get_extension_func'):1,('glxGraphicsStateGuardian.cxx','get_system_func'):1,('glxGraphicsStateGuardian.cxx','do_get_extension_func'):1,('posixGraphicsStateGuardian.cxx','get_system_func'):1}
    need(dict(collections.Counter((r['file'],r['callee']) for r in computed))==expected,'unqualified computed resolver sites')
    text=sources['glxGraphicsStateGuardian.cxx'].decode();finite=set(re.findall(r'funcName\s*=\s*"([^"]+)"',text));need(finite=={'glXGetProcAddress','glXGetProcAddressARB'},'finite private loader names')
    need('get_system_func(funcName)' in text and 'PosixGraphicsStateGuardian::do_get_extension_func(name)' in text,'same-name GLX forwarding')
    need('psd_resolved(&psd_request, do_get_extension_func(name), PSD_SOURCE_RUNTIME)' in sources['glGraphicsStateGuardian_src.cxx'].decode() and 'get_system_func(name)' in sources['posixGraphicsStateGuardian.cxx'].decode(),'same-name unified/POSIX forwarding')
    table=re.search(rb'compiled_function_table\[\]\s*=\s*\{([\s\S]*?)\};',sources['glGraphicsStateGuardian_src.cxx']);need(table is not None and not re.findall(rb'"gl[A-Za-z0-9_]+"',table[1]),'selected empty compiled table required')
    paths=sorted({n.decode() for raw in sources.values() for n in re.findall(rb'psd_path\(\s*(PSD_PATH_[A-Z_]+)',raw)});need(paths==['PSD_PATH_GLX_PRIVATE','PSD_PATH_POSIX'],'selected resolver paths drift')
    result.update(schema='panda-sdk-routes-selected-coverage-v2',source_sha256=SOURCE_SHA,typed_route_count=28,available_route_names=sorted(routes),computed_lookups=computed,computed_names_statically_closed=True,finite_loader_names=sorted(finite),compiled_table_names=[],selected_resolver_paths=paths,coverage_scope='four exact selected source files; no other caller/runtime/driver authority',runtime_resolver_origins_qualified=False,runtime_binding_qualified=False,stage7_complete=False);return result

def preprocess_recorded(command,cwd,env,prefix):
    need(command.count('-MD')==1,'one recorded dependency flag required');bare=list(command);bare.remove('-MD')
    raw,record=previous.preprocess(bare,cwd,env,prefix);record['original_compile_command']=command;return raw,record

def audit_build(build_dir,out):
    build_dir,out=map(stage.canonical,(build_dir,out));need(not out.exists(),'existing inspection preserved');r=json.loads(inv.read_input(build_dir/'receipt.json',4*1024**2))
    need(r.get('schema')=='panda-sdk-routes-build-v2' and r.get('status')=='NEW_SDK_COMPILE_LINK_STATIC_VERIFIED_NOT_LOADED' and r.get('native_admitted') is False and type(r.get('new_native_runs')) is int and r['new_native_runs']==0,'qualified data-only build receipt required')
    source=stage.canonical(r['stage']);sysroot=stage.canonical(r['sysroot']);library=build_dir/'sdk/lib/libpandagl.so';need(r['candidate_library']==str(library) and r['output']==str(build_dir),'owned SDK library required')
    host=json.loads(inv.read_input(build_dir/'host-before.json',16*1024**2));used=json.loads(inv.read_input(build_dir/'used-inputs.json',16*1024**2));rows=json.loads(inv.read_input(build_dir/'sdk-output-manifest.json',16*1024**2));commands=json.loads(inv.read_input(build_dir/'compile-dependencies.json',16*1024**2))
    def verify():
        m=stage.verify_stage(source);need(inputs.sha((source/stage.MANIFEST).read_bytes())==r['source_manifest_sha256'] and r['native_sha256']==stage.NATIVE_PINS,'source manifest binding')
        need(sdk.dependency_profile(sysroot)==json.loads((build_dir/'sysroot-files.json').read_text()),'private input drift');inputs.verify_tool_files(inputs.tool_profile());need(inputs.capture_host_inputs()==host,'host input drift')
        for name,key in [('host-before.json','host_snapshot_sha256'),('used-inputs.json','used_inputs_sha256'),('compile-dependencies.json','compile_dependencies_sha256'),('makepanda.log','build_log_sha256'),('sdk-output-manifest.json','sdk_output_manifest_sha256')]:need(inputs.sha((build_dir/name).read_bytes())==r[key],'build evidence drift: '+name)
        need(stage.old.base.tree_records(build_dir/'sdk')==rows and inputs.sha(library.read_bytes())==r['candidate_sha256'],'SDK output drift');need(inputs.qualify_dependencies([x['path'] for x in used],source,build_dir/'sdk',sysroot,host)==used,'used dependency drift');return m
    manifest=verify();out.mkdir(parents=True);env=sdk.build_env(sysroot);before=inputs.verify_tools(env,out/'tools-before');sources={};records=[]
    expected=previous.commands_for(source,build_dir,sysroot);groups=[{n:stage.old.base.MEMBERS[n] for n in ['glGraphicsStateGuardian_src.cxx','glGraphicsBuffer_src.cxx']},{n:stage.old.base.MEMBERS[n] for n in ['glxGraphicsStateGuardian.cxx','posixGraphicsStateGuardian.cxx']}]
    for index,(wanted,group) in enumerate(zip(expected,groups)):
        target=wanted[wanted.index('-o')+1];hits=[x for x in commands if x['object']==target];need(len(hits)==1,'unique recorded source command');row=hits[0];actual=row['command'];bare=list(actual);need(bare.count('-MD')==1,'recorded dependency flag');bare.remove('-MD');need(bare==wanted,'exact macro compile command')
        need(inputs.sha(Path(row['dependency_file']).read_bytes())==row['dependency_sha256'],'source dependency file drift');raw,record=preprocess_recorded(actual,source,env,out/('tu-'+str(index)));sources.update(previous.select_sources(raw,group));records.append(record)
    need(verify()==manifest,'inputs changed during inspection');after=inputs.verify_tools(env,out/'tools-after')
    for name,raw in sources.items():(out/(name+'.selected')).write_bytes(raw)
    result=qualify_selected(sources,stage.native_files()['panda_source_dispatch.cxx'],name_profile());elf=out/'elf';elf.mkdir();inspection=sdk.inspect_sdk(library,elf);(elf/'inspection.json').write_text(json.dumps(inspection,indent=2)+'\n')
    result.update(candidate_sha256=r['candidate_sha256'],candidate_library=str(library),build_receipt_sha256=inputs.sha((build_dir/'receipt.json').read_bytes()),source_manifest_sha256=r['source_manifest_sha256'],profile_sha256=PROFILE_SHA,compile_commands=records,tools_before=before,tools_after=after,new_native_runs=0,official_model_calls=0)
    (out/'coverage.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',required=True);p.add_argument('--out',required=True);a=p.parse_args(argv)
    try:r=audit_build(a.build,a.out);print(json.dumps({k:r[k] for k in ['lookup_count','safe_name_count','safe_cap','all_selected_names_classified','computed_names_statically_closed','candidate_sha256','native_admitted']}));return 0
    except (ValueError,OSError) as e:print('coverage rejected: '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
