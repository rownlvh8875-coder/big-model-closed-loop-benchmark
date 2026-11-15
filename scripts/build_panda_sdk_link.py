"""Build fixed old-string-ABI SDK with actual dependency inputs; DATA ONLY."""
import argparse,json,shlex,sys,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scripts import panda_sdk_routes_stage as source
from scripts import panda_sdk_routes_inputs as inputs
from scripts import build_panda_adapter_sdk as old
ROOT=source.ROOT;need=source.need
FIXED_FLAGS='-D_GLIBCXX_USE_CXX11_ABI=0 -MD'

def verify_compile_command(cmd):
    need(cmd.count('-MD')==1 and cmd.count('-D_GLIBCXX_USE_CXX11_ABI=0')==1 and sum('_GLIBCXX_USE_CXX11_ABI' in x for x in cmd)==1,'every compile requires one literal ABI0 and dependency flag')

def build_env(sysroot):
    env=old.build_env(sysroot);env['RPM_OPT_FLAGS']=FIXED_FLAGS;return env

def build(stage,sysroot,out,threads=4):
    stage,sysroot,out=map(source.canonical,(stage,sysroot,out));need(not out.exists(),'existing build preserved');need(type(threads) is int and 1<=threads<=4,'threads1..4')
    manifest=source.verify_stage(stage);deps=old.dependency_profile(sysroot);profile=inputs.tool_profile();inputs.verify_tool_files(profile);env=build_env(sysroot)
    host=inputs.capture_host_inputs();out.mkdir(parents=True);path=out/'receipt.json'
    r=dict(schema='panda-sdk-link-build-v1',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),status='failed',stage=str(stage),sysroot=str(sysroot),output=str(out),source_manifest_sha256=inputs.sha((stage/source.MANIFEST).read_bytes()),native_sha256=source.NATIVE_PINS,tool_profile_sha256=inputs.TOOL_SHA,source_files=len(manifest['source_tree']),private_records=len(deps),fixed_rpm_opt_flags=FIXED_FLAGS,controlled_ldflags='-Wl,-z,defs',native_admitted=False,new_native_runs=0,official_model_calls=0,runtime_binding_qualified=False,stage7_complete=False)
    def save():path.write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        (out/'host-before.json').write_text(json.dumps(host,indent=2)+'\n');(out/'sysroot-files.json').write_text(json.dumps(deps,indent=2)+'\n');r['tools_before']=inputs.verify_tools(env,out/'tools-before')
        command=[sys.executable,'-B',str(stage/'makepanda/makepanda.py'),'--nothing','--use-gl','--use-x11','--no-python','--no-copy-python','--optimize','3','--threads',str(threads),'--git-commit',source.old.REVISION,'--outputdir',str(out/'sdk'),'--gl-incdir',str(sysroot/'usr/include'),'--gl-libdir',str(sysroot/'usr/lib/x86_64-linux-gnu'),'--x11-incdir',str(sysroot/'usr/include'),'--x11-libdir',str(sysroot/'usr/lib/x86_64-linux-gnu'),'--nocolor','--verbose']
        r['command']=command;r['build_environment_keys']=sorted(env);process=old.run_build(command,stage,env,out);r['process']=process;save();need(process['status']=='success','SDK build failed; raw outputs retained')
        need(source.verify_stage(stage)==manifest and old.dependency_profile(sysroot)==deps,'source/private dependency drift');need(inputs.capture_host_inputs()==host,'host header snapshot changed');r['tools_after']=inputs.verify_tools(env,out/'tools-after')
        commands=[]
        for line in (out/'makepanda.log').read_text().splitlines():
            if line.startswith(('/usr/bin/gcc ','/usr/bin/g++ ')):
                cmd=shlex.split(line)
                if '-c' in cmd:
                    verify_compile_command(cmd);need('-o' in cmd,'object output');obj=Path(cmd[cmd.index('-o')+1]);need(obj.is_relative_to(out/'sdk') and obj.suffix=='.o','owned object output required');dep=obj.with_suffix('.d');raw=source.old.base.canonical(dep).read_bytes();names=inputs.parse_dependencies(raw)
                    primary=Path(cmd[-1]);primary=(primary if primary.is_absolute() else stage/primary).resolve();need(str(primary) in {str((Path(n) if Path(n).is_absolute() else stage/n).resolve()) for n in names},'primary source missing from dependencies')
                    commands.append(dict(command=cmd,object=str(obj),dependency_file=str(dep),dependency_sha256=inputs.sha(raw),paths=names))
        need(commands,'no actual dependency-bearing compilation');closure=inputs.qualify_dependencies([n for row in commands for n in row['paths']],stage,out/'sdk',sysroot,host)
        (out/'compile-dependencies.json').write_text(json.dumps(commands,indent=2)+'\n');(out/'used-inputs.json').write_text(json.dumps(closure,indent=2)+'\n')
        image=out/'sdk/lib/libpandagl.so';inspection=old.inspect_sdk(image,out);(out/'inspection.json').write_text(json.dumps(inspection,indent=2)+'\n')
        records=source.old.base.tree_records(out/'sdk');(out/'sdk-output-manifest.json').write_text(json.dumps(records,indent=2)+'\n');need(old.tree_size(out)<=8*1024**3,'final build output budget')
        r.update(status='ABI0_SDK_COMPILE_LINK_STATIC_VERIFIED_NOT_LOADED',candidate_library=str(image),candidate_sha256=inputs.sha(image.read_bytes()),candidate_nbytes=image.stat().st_size,build_wall_seconds=process['wall_seconds'],compile_commands=len(commands),used_input_count=len(closure),used_input_origins={n:sum(x['origin']==n for x in closure) for n in ['source','generated','private','host']},host_snapshot_sha256=inputs.sha((out/'host-before.json').read_bytes()),used_inputs_sha256=inputs.sha((out/'used-inputs.json').read_bytes()),compile_dependencies_sha256=inputs.sha((out/'compile-dependencies.json').read_bytes()),build_log_sha256=inputs.sha((out/'makepanda.log').read_bytes()),sdk_output_manifest_sha256=inputs.sha((out/'sdk-output-manifest.json').read_bytes()),same_image_api_count=33,source_state_instances=1,current_build_compiler_children_recorded=True,full_host_runtime_equivalence=False)
        save();return r
    except BaseException as e:r['failure']=type(e).__name__+': '+str(e);save();raise

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',required=True);p.add_argument('--sysroot',required=True);p.add_argument('--out',required=True);p.add_argument('--threads',type=int,default=4);a=p.parse_args(argv)
    try:r=build(a.stage,a.sysroot,a.out,a.threads);print(json.dumps({k:r[k] for k in ['status','candidate_sha256','build_wall_seconds','compile_commands','used_input_count','native_admitted']}));return 0
    except (ValueError,OSError) as e:print('SDK build rejected: '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
