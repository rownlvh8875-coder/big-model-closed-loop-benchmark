"""Requalify original selected source names under the actual replacement ABI0 flags."""
from scripts.panda_sdk_routes_coverage import *
from scripts import build_panda_sdk_link as replacement
def preprocess_recorded(command,cwd,env,prefix):
    replacement.verify_compile_command(command);bare=list(command);bare.remove('-MD')
    raw,record=previous.preprocess(bare,cwd,env,prefix);record['original_compile_command']=command;return raw,record

def audit_build(build_dir,out):
    build_dir,out=map(stage.canonical,(build_dir,out));need(not out.exists(),'existing inspection preserved');r=json.loads(inv.read_input(build_dir/'receipt.json',4*1024**2))
    need(r.get('schema')=='panda-sdk-link-build-v1' and r.get('status')=='ABI0_SDK_COMPILE_LINK_STATIC_VERIFIED_NOT_LOADED' and r.get('native_admitted') is False and type(r.get('new_native_runs')) is int and r['new_native_runs']==0,'qualified data-only build receipt required')
    source=stage.canonical(r['stage']);sysroot=stage.canonical(r['sysroot']);library=build_dir/'sdk/lib/libpandagl.so';need(r['candidate_library']==str(library) and r['output']==str(build_dir),'owned SDK library required')
    host=json.loads(inv.read_input(build_dir/'host-before.json',16*1024**2));used=json.loads(inv.read_input(build_dir/'used-inputs.json',16*1024**2));rows=json.loads(inv.read_input(build_dir/'sdk-output-manifest.json',16*1024**2));commands=json.loads(inv.read_input(build_dir/'compile-dependencies.json',16*1024**2))
    def verify():
        m=stage.verify_stage(source);need(inputs.sha((source/stage.MANIFEST).read_bytes())==r['source_manifest_sha256'] and r['native_sha256']==stage.NATIVE_PINS,'source manifest binding')
        need(sdk.dependency_profile(sysroot)==json.loads((build_dir/'sysroot-files.json').read_text()),'private input drift');inputs.verify_tool_files(inputs.tool_profile());need(inputs.capture_host_inputs()==host,'host input drift')
        for name,key in [('host-before.json','host_snapshot_sha256'),('used-inputs.json','used_inputs_sha256'),('compile-dependencies.json','compile_dependencies_sha256'),('makepanda.log','build_log_sha256'),('sdk-output-manifest.json','sdk_output_manifest_sha256')]:need(inputs.sha((build_dir/name).read_bytes())==r[key],'build evidence drift: '+name)
        need(stage.old.base.tree_records(build_dir/'sdk')==rows and inputs.sha(library.read_bytes())==r['candidate_sha256'],'SDK output drift');need(inputs.qualify_dependencies([x['path'] for x in used],source,build_dir/'sdk',sysroot,host)==used,'used dependency drift');return m
    manifest=verify();out.mkdir(parents=True);env=replacement.build_env(sysroot);before=inputs.verify_tools(env,out/'tools-before');sources={};records=[]
    expected=previous.commands_for(source,build_dir,sysroot);
    for cmd in expected:cmd.insert(cmd.index('-DBUILDING_PANDAGL'),'-D_GLIBCXX_USE_CXX11_ABI=0')
    groups=[{n:stage.old.base.MEMBERS[n] for n in ['glGraphicsStateGuardian_src.cxx','glGraphicsBuffer_src.cxx']},{n:stage.old.base.MEMBERS[n] for n in ['glxGraphicsStateGuardian.cxx','posixGraphicsStateGuardian.cxx']}]
    for index,(wanted,group) in enumerate(zip(expected,groups)):
        target=wanted[wanted.index('-o')+1];hits=[x for x in commands if x['object']==target];need(len(hits)==1,'unique recorded source command');row=hits[0];actual=row['command'];replacement.verify_compile_command(actual);bare=list(actual);need(bare.count('-MD')==1,'recorded dependency flag');bare.remove('-MD');need(bare==wanted,'exact macro compile command')
        need(inputs.sha(Path(row['dependency_file']).read_bytes())==row['dependency_sha256'],'source dependency file drift');raw,record=preprocess_recorded(actual,source,env,out/('tu-'+str(index)));sources.update(previous.select_sources(raw,group));records.append(record)
    need(verify()==manifest,'inputs changed during inspection');after=inputs.verify_tools(env,out/'tools-after')
    for name,raw in sources.items():(out/(name+'.selected')).write_bytes(raw)
    result=qualify_selected(sources,stage.native_files()['panda_source_dispatch.cxx'],name_profile());elf=out/'elf';elf.mkdir();inspection=sdk.inspect_sdk(library,elf);(elf/'inspection.json').write_text(json.dumps(inspection,indent=2)+'\n')
    result.update(schema='panda-sdk-link-selected-coverage-v1',fixed_rpm_opt_flags=replacement.FIXED_FLAGS,candidate_sha256=r['candidate_sha256'],candidate_library=str(library),build_receipt_sha256=inputs.sha((build_dir/'receipt.json').read_bytes()),source_manifest_sha256=r['source_manifest_sha256'],profile_sha256=PROFILE_SHA,compile_commands=records,tools_before=before,tools_after=after,new_native_runs=0,official_model_calls=0)
    (out/'coverage.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',required=True);p.add_argument('--out',required=True);a=p.parse_args(argv)
    try:r=audit_build(a.build,a.out);print(json.dumps({k:r[k] for k in ['lookup_count','safe_name_count','safe_cap','all_selected_names_classified','computed_names_statically_closed','candidate_sha256','native_admitted']}));return 0
    except (ValueError,OSError) as e:print('coverage rejected: '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
