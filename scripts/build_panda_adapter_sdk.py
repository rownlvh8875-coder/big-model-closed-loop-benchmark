"""Compile/link one activity/cache Panda image; inspect it as DATA ONLY."""
import argparse,hashlib,io,json,os,stat,subprocess,sys,tarfile,time
from datetime import datetime,timezone,timedelta
from pathlib import Path,PurePosixPath
from scripts import panda_adapter_sdk_stage as source
from scripts import panda_cache_adapter_cpu as cpu
from scripts.build_panda_source_dispatch import build_environment,stop_build_group
from scripts.panda_dispatch_coverage import read_input
ROOT=Path(__file__).resolve().parents[1]
need=source.need
canonical=source.canonical
DEPS_SHA='a336ed49bf83b5440f1021a32a6ec42cae098fd67c1278245eec7af2ca6360ce'
API=tuple('pca_context_size pca_install pca_attach pca_observer pca_snapshot pca_observe pca_finish pca_get_stats rc_context_size rc_init rc_context_new rc_context_current rc_context_destroy rc_invalidate rc_pixel_store rc_bind_buffer rc_bind_framebuffer rc_read_buffer rc_delete_framebuffers rc_observe rc_snapshot rc_finalize rc_get_stats psd_configure psd_finish psd_get_stats psd_bind_read psd_before psd_after psd_lookup_begin psd_resolved psd_path psd_source_idle'.split())

def build_env(sysroot):
    old=build_environment(sysroot)
    # Allow only ordinary process context plus fixed locale/sanitizer settings.
    # makepanda also consumes RPM_OPT_FLAGS/MAKEPANDA_* outside CFLAGS.
    allowed=('HOME','TMPDIR','TMP','TEMP','PATH','LANG','LC_ALL','ASAN_OPTIONS','UBSAN_OPTIONS')
    env={key:value for key,value in cpu.cpu_environment().items() if key in allowed}
    env['PYTHONNOUSERSITE']='1'
    for key in ('PATH','CC','CXX','PKG_CONFIG_LIBDIR','PKG_CONFIG_SYSROOT_DIR','BISON_PKGDATADIR','M4'):env[key]=old[key]
    env['LDFLAGS']='-Wl,-z,defs';return env

def safe_relative(name):
    while name.startswith('./'):name=name[2:]
    p=PurePosixPath(name);need(name and not p.is_absolute() and '..' not in p.parts,'unsafe dependency archive path');return str(p)

def archive_files(data):
    need(data.startswith(b'!<arch>\n'),'Debian ar archive required');at=8;payload=None
    while at<len(data):
        header=data[at:at+60];need(len(header)==60 and header[-2:]==b'`\n','Debian ar header')
        name=header[:16].decode().strip().rstrip('/');size=int(header[48:58]);at+=60;need(size>=0 and at+size<=len(data),'Debian ar extent')
        if name.startswith('data.tar'):need(payload is None,'duplicate Debian data archive');payload=data[at:at+size]
        at+=size+(size%2)
    need(payload is not None,'Debian data archive missing');result={};total=0
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:*') as tar:
        for member in tar:
            if member.isdir():continue
            name=safe_relative(member.name);total+=member.size;need(total<=256*1024*1024 and len(result)<30000,'dependency archive budget')
            if member.issym():result[name]=dict(kind='symlink',target=member.linkname)
            else:
                need(member.isfile() or member.islnk(),'unsupported dependency member');stream=tar.extractfile(member);need(stream is not None and member.size<=64*1024*1024,'dependency file extent');raw=stream.read(64*1024*1024+1);need(len(raw)<=64*1024*1024,'dependency file budget')
                result[name]=dict(kind='file',nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    return result

def verify_sysroot(sysroot,packages,hostlinks):
    sysroot=canonical(sysroot);expected={}
    for row in packages:
        path=Path(row['path']);path=path if path.is_absolute() else ROOT/path;data=read_input(path,8*1024*1024)
        need(len(data)==row['nbytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'dependency archive pin mismatch');expected.update(archive_files(data))
    for row in hostlinks:
        relative=row.get('relative') or row['path'].split('/sysroot/',1)[1];relative=safe_relative(relative)
        target=Path(row['target']);need(target.is_absolute(),'absolute qualified host link required')
        need(hashlib.sha256(read_input(target.resolve(),64*1024*1024)).hexdigest()==row['sha256'],'host runtime link pin mismatch')
        expected[relative]=dict(kind='symlink',target=row['target'])
    actual={}
    for path in sorted(sysroot.rglob('*')):
        relative=str(path.relative_to(sysroot))
        if path.is_symlink():actual[relative]=dict(kind='symlink',target=os.readlink(path))
        elif path.is_file():
            size=path.stat().st_size;need(size<=64*1024*1024,'sysroot file budget');data=read_input(path,64*1024*1024) if size else b''
            actual[relative]=dict(kind='file',nbytes=size,sha256=hashlib.sha256(data).hexdigest())
        else:need(path.is_dir(),'unsupported sysroot entry')
    need(actual==expected,'extracted sysroot does not match pinned packages/host links');return actual

def dependency_profile(sysroot):
    path=ROOT/'docs/evidence/panda-source-dispatch-01/before-review/dependency-inputs.json';data=read_input(path,1024*1024)
    need(hashlib.sha256(data).hexdigest()==DEPS_SHA,'fixed dependency profile changed');profile=json.loads(data)
    return verify_sysroot(sysroot,profile['packages'],profile['host_runtime_links'])

def tree_size(path):return sum(p.stat().st_size for p in path.rglob('*') if p.is_file())

def run_build(command,cwd,env,out,timeout=900,max_bytes=8*1024**3,max_log=32*1024**2):
    out=canonical(out);log=out/'makepanda.log';start=time.perf_counter();process=None;failure=None;reason=None
    try:
        with log.open('xb') as stream:
            process=subprocess.Popen(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            while process.poll() is None:
                if time.perf_counter()-start>timeout:reason='timeout';break
                if tree_size(out)>max_bytes:reason='disk_budget';break
                if log.stat().st_size>max_log:reason='log_budget';break
                time.sleep(.05)
    except BaseException as exc:failure=exc
    finally:
        if process is not None:stop_build_group(process)
    size=tree_size(out);elapsed=time.perf_counter()-start
    reason=reason or ('disk_budget' if size>max_bytes else 'log_budget' if log.exists() and log.stat().st_size>max_log else 'timeout' if elapsed>timeout else None)
    r=dict(command=command,returncode=process.returncode if process else None,wall_seconds=elapsed,output_nbytes=size,limit_failure=reason,status='failed' if failure or reason or process is None or process.returncode else 'success',exception=type(failure).__name__ if failure else None)
    (out/'process.json').write_text(json.dumps(r,indent=2)+'\n')
    if failure is not None:raise failure
    return r

def interface_data(symbols,dynamic):
    definitions={}
    for line in dynamic.splitlines():
        f=line.split()
        if len(f)>=8 and f[3]=='FUNC' and f[4]=='GLOBAL' and f[5]=='DEFAULT' and f[6]!='UND' and int(f[2])>0:definitions[f[7]]=dict(value=int(f[1],16),nbytes=int(f[2]))
    need(all(name in definitions for name in API),'required same-image API missing/undefined')
    states={(int(f[1],16),int(f[2])) for line in symbols.splitlines() if len(f:=line.split())>=8 and f[3]=='OBJECT' and f[6]!='UND' and f[7]=='_ZN12_GLOBAL__N_11SE'}
    objects=[line.strip() for line in symbols.splitlines() if len(f:=line.split())>=8 and f[3]=='OBJECT']
    need(len(states)==1,'exactly one source state object required; observed objects: '+repr(objects))
    return dict(required_exports={name:definitions[name] for name in API},same_image_interfaces_verified=True,source_state_instances=len(states),runtime_binding_qualified=False,native_admitted=False)

def inspect_exports(image,out):
    image,out=canonical(image),canonical(out);results=[]
    for name,flags in (('symbols',['-WsW']),('dynamic',['--dyn-syms','-W'])):
        r=cpu.run_command(['/usr/bin/readelf',*flags,str(image)],ROOT,cpu.cpu_environment(),out/('interfaces-'+name),30)
        need(r['returncode']==0 and r['stderr']=='','interface readelf failed');results.append(r)
    result=interface_data(results[0]['stdout'],results[1]['stdout']);result['commands']=results;result['sha256']=hashlib.sha256(read_input(image,64*1024*1024)).hexdigest();return result

def inspect_sdk(image,out):
    result=cpu.inspect_cpu_candidate(image,out);need(result['static']['source_activity_extension_present'],'activity API missing')
    result['interfaces']=interface_data(result['commands'][0]['stdout'],result['commands'][1]['stdout'])
    for suffix,flags in (('relocations',['-rW']),('dynamic',['-dW'])):
        r=cpu.run_command(['/usr/bin/readelf',*flags,str(image)],ROOT,cpu.cpu_environment(),Path(out)/('candidate-'+suffix),30)
        need(r['returncode']==0 and r['stderr']=='','candidate dynamic inspection failed');result[suffix]=r
    result.update(adapter_static_link_verified=True,runtime_binding_qualified=False,native_admitted=False);return result

def build(stage,sysroot,out,threads=4):
    need(type(threads) is int and 1<=threads<=4,'threads must be1..4');stage,sysroot,out=canonical(stage),canonical(sysroot),canonical(out)
    need(not out.exists(),'existing SDK build preserved');manifest=source.verify_stage(stage);deps=dependency_profile(sysroot)
    out.mkdir(parents=True);receipt=dict(schema='panda-adapter-sdk-build-v1',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),stage=str(stage),status='failed',runtime_admission_ready=False,native_admitted=False,runtime_binding_qualified=False,stage7_complete=False,new_native_runs=0,new_gl_calls=0,new_provider_runs=0,new_model_runs=0,new_official_ort_runs=0,old_image_replaced=False,source_manifest_sha256=hashlib.sha256((stage/'adapter-sdk-manifest.json').read_bytes()).hexdigest(),source_files=len(manifest['source_tree']))
    command=[sys.executable,'-B',str(stage/'makepanda/makepanda.py'),'--nothing','--use-gl','--use-x11','--no-python','--no-copy-python','--optimize','3','--threads',str(threads),'--git-commit',source.REVISION,'--outputdir',str(out/'sdk'),'--gl-incdir',str(sysroot/'usr/include'),'--gl-libdir',str(sysroot/'usr/lib/x86_64-linux-gnu'),'--x11-incdir',str(sysroot/'usr/include'),'--x11-libdir',str(sysroot/'usr/lib/x86_64-linux-gnu'),'--nocolor','--verbose']
    path=out/'receipt.json'
    def save():path.write_text(json.dumps(receipt,indent=2)+'\n')
    save()
    try:
        tool_paths=['/usr/bin/gcc','/usr/bin/g++','/usr/bin/readelf','/usr/bin/ld','/usr/bin/as','/usr/bin/ar','/usr/bin/ranlib',sys.executable]
        tool_pins={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in tool_paths}
        (out/'sysroot-files.json').write_text(json.dumps(deps,indent=2)+'\n');receipt.update(tool_sha256=tool_pins,controlled_ldflags='-Wl,-z,defs',command=command)
        env=build_env(sysroot);receipt['build_environment_keys']=sorted(env)
        process=run_build(command,stage,env,out);receipt['process']=process;save();need(process['status']=='success','SDK compile/link failed; raw output preserved')
        need(source.verify_stage(stage)==manifest and dependency_profile(sysroot)==deps,'SDK source/dependencies changed during build')
        need(all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in tool_pins.items()),'SDK build tools changed')
        library=(out/'sdk/lib/libpandagl.so').resolve();need(library.is_relative_to(out) and library.is_file(),'candidate SDK library missing')
        inspection=inspect_sdk(library,out);(out/'inspection.json').write_text(json.dumps(inspection,indent=2)+'\n')
        need(tree_size(out)<=8*1024**3,'final SDK output disk budget')
        receipt.update(status='SDK_COMPILE_LINK_STATIC_VERIFIED_NOT_LOADED',candidate_library=str(library),candidate_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),candidate_nbytes=library.stat().st_size,adapter_static_link_verified=True,source_state_instances=1,required_api_count=len(API),build_wall_seconds=process['wall_seconds'],sdk_scope='minimal GLX/X11/noPython, no image parity or runtime admission')
        save();return receipt
    except BaseException as exc:receipt.update(status='failed',failure=type(exc).__name__+': '+str(exc));save();raise

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True);parser.add_argument('--sysroot',required=True);parser.add_argument('--out',required=True);parser.add_argument('--threads',type=int,default=4);args=parser.parse_args(argv)
    try:print(json.dumps(build(args.stage,args.sysroot,args.out,args.threads)));return 0
    except (ValueError,OSError,subprocess.SubprocessError,tarfile.TarError) as exc:print('adapter SDK rejected: '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
