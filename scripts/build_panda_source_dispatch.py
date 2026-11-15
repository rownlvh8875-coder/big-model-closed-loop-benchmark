"""Compile a pinned separate candidate; inspect ELF data, never load/run Panda."""
import argparse
from datetime import datetime,timezone,timedelta
import hashlib
import json
import os
import signal
from pathlib import Path
import stat
import struct
import subprocess
import sys
import time

from scripts.panda_source_dispatch import ROOT,REVISION,MEMBERS,canonical,need,tree_records,transform_sources
from scripts.readback_elf_imports import inspect_imports
from scripts.readback_process_mapping import elf_ranges
from scripts.panda_dispatch_coverage import read_input
from scripts.panda_readback_abi import qualify_elf

UPSTREAM_TREE='6081b4b6fae45013d48930264bc15532f165422f'
RUNTIME=('panda/src/glstuff/panda_source_dispatch.h','panda/src/glstuff/panda_source_dispatch.cxx')

def inspect_candidate(path):
    path=canonical(path);data=read_input(path,64*1024*1024);loader=inspect_imports(data);loads=elf_ranges(data)
    symbols=subprocess.check_output(['readelf','-WsW',str(path)],timeout=30).decode()
    dynamic_symbols=subprocess.check_output(['readelf','--dyn-syms','-W',str(path)],timeout=30).decode()
    for name in ('psd_configure','psd_resolved','psd_finish'):
        need(any(len(f:=line.split())>=8 and f[3]=='FUNC' and f[4]=='GLOBAL' and f[5]=='DEFAULT' and f[6]!='UND' and f[7]==name
                 for line in dynamic_symbols.splitlines()),'candidate dynamic control missing: '+name)
    def symbol(name,kind,size):
        rows={(int(f[1],16),int(f[2])) for line in symbols.splitlines() if len(f:=line.split())>=8 and f[3]==kind and f[6]!='UND' and f[7]==name}
        need(len(rows)==1,'unique defined candidate symbol required: '+name)
        address,nbytes=rows.pop();need(nbytes==size,'candidate symbol extent: '+name);return address
    tail,target=symbol('psd_read_pixels','FUNC',6),symbol('psd_read_target','OBJECT',8)
    def offset(va,size,executable=False):
        matches=[p for p in loads if p['vaddr']<=va and va+size<=p['vaddr']+p['filesz']]
        need(len(matches)==1,'candidate file-backed span')
        p=matches[0]
        if executable:need(p['flags']&1 and not p['flags']&2,'candidate executable protection')
        return p['offset']+va-p['vaddr']
    tail_offset=offset(tail,6,True);code=data[tail_offset:tail_offset+6]
    need(code[:2]==b'\xff\x25' and tail+6+struct.unpack('<i',code[2:])[0]==target,'candidate bare tail target mismatch')
    offset(target,8)
    # Inspect the original-only R_X86_64_64 binding from actual PT_DYNAMIC tables,
    # not section headers or the older reader's narrower GLOB_DAT/JUMP_SLOT list.
    header=struct.unpack_from('<16sHHIQQQIHHHHHH',data);dynamic=[]
    for i in range(header[10]):
        ph=struct.unpack_from('<IIQQQQQQ',data,header[5]+i*56)
        if ph[0]==2:dynamic.append(ph)
    need(len(dynamic)==1,'candidate dynamic table')
    ph=dynamic[0];tags={}
    for at in range(ph[2],ph[2]+ph[5],16):
        tag,value=struct.unpack_from('<qQ',data,at)
        if tag==0:break
        if tag!=1:tags[tag]=value
    def virtual(va,size):at=offset(va,size);return data[at:at+size]
    hits=[]
    for va_key,size_key in ((7,8),(23,2)):
        if not tags.get(size_key):continue
        raw=virtual(tags[va_key],tags[size_key])
        for at in range(0,len(raw),24):
            slot,info,addend=struct.unpack_from('<QQq',raw,at)
            if slot==target:hits.append((info,addend))
    need(len(hits)==1 and hits[0][0]&0xffffffff==1 and hits[0][1]==0,'unique original-read R_X86_64_64 binding required')
    index=hits[0][0]>>32;need(index<loader['dynamic_symbol_count'],'read binding symbol bound')
    name_index,attributes,visibility,section,value,size=struct.unpack('<IBBHQQ',virtual(tags[6]+24*index,24))
    strings=virtual(tags[5],tags[10]);need(name_index<len(strings),'read symbol string bound')
    end=strings.find(b'\0',name_index);need(end>=name_index,'read symbol termination')
    need(strings[name_index:end]==b'glReadPixels' and attributes>>4==1 and attributes&15 in (0,2) and visibility==0 and section==0 and value==0,
         'read target is not the exact original GL import')
    rejected=False
    try:qualify_elf(data)
    except ValueError:rejected=True
    need(rejected,'old pinned ABI must not admit candidate')
    return dict(schema='panda-source-dispatch-static-candidate-v1',sha256=hashlib.sha256(data).hexdigest(),nbytes=len(data),
                read_tail_va=tail,read_target_va=target,read_tail_file_offset=tail_offset,read_tail_original_binding=True,
                read_relocation_type='R_X86_64_64',old_abi_profile_rejected=True,loader_function_imports_supported_6_7=len(loader['imports']),
                runtime_admission_ready=False,candidate_panda_abi_qualified=False,native_admitted=False)

def blob_id(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def git_tree(entries):
    root={}
    for path,mode,digest in entries:
        node=root;parts=path.split('/')
        for part in parts[:-1]:
            node=node.setdefault(part,{})
            need(type(node) is dict,'source tree path collision')
        need(parts[-1] not in node,'source tree duplicate path');node[parts[-1]]=(mode,digest)
    def pack(node):
        payload=b''
        for name,value in sorted(node.items(),key=lambda row:os.fsencode(row[0])+(b'/' if isinstance(row[1],dict) else b'\0')):
            if isinstance(value,dict):mode,digest='40000',pack(value)
            else:mode,digest=value
            payload+=mode.encode()+b' '+os.fsencode(name)+b'\0'+bytes.fromhex(digest)
        return hashlib.sha1(b'tree '+str(len(payload)).encode()+b'\0'+payload).hexdigest()
    return pack(root)

def verify_stage(stage):
    stage=canonical(stage);path=stage/'source-dispatch-manifest.json'
    need(path.is_file() and not path.is_symlink() and path.stat().st_size<=16*1024*1024,'bounded source manifest required')
    manifest=json.loads(path.read_text())
    need(manifest.get('schema')=='panda-source-dispatch-transform-v1' and manifest.get('upstream_revision')==REVISION and
         manifest.get('runtime_admission_ready') is False and manifest.get('native_admitted') is False,'pinned non-admitting source manifest required')
    records=[r for r in tree_records(stage) if r['path']!='source-dispatch-manifest.json']
    need(records and records==manifest.get('source_tree'),'source tree changed or partial')
    original_root=ROOT/'docs/evidence/panda-dispatch-coverage-01/source'
    originals={name:(original_root/name).read_bytes() for name in MEMBERS}
    changed,_=transform_sources(originals)
    reverse={member:name for name,member in MEMBERS.items()}
    entries=[]
    for row in records:
        relative=row['path'];file=stage/relative
        if relative in RUNTIME:
            need(file.read_bytes()==(ROOT/'native'/file.name).read_bytes(),'staged runtime changed');continue
        if row['kind']=='symlink':mode,data='120000',os.fsencode(os.readlink(file))
        else:
            mode='100755' if file.stat().st_mode & stat.S_IXUSR else '100644';data=file.read_bytes()
        if relative in reverse:
            name=reverse[relative];need(data==changed[name],'staged source hooks changed');data=originals[name]
        entries.append((relative,mode,blob_id(data)))
    need(git_tree(entries)==UPSTREAM_TREE,'reconstructed upstream Git tree mismatch')
    return manifest

def build_environment(sysroot):
    sysroot=canonical(sysroot);env=os.environ.copy()
    for key in ('CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS','CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','LIBRARY_PATH','LD_PRELOAD','LD_LIBRARY_PATH','PYTHONPATH'):
        env.pop(key,None)
    env.update(PATH=str(sysroot/'usr/bin')+':/usr/bin:/bin',LANG='C',LC_ALL='C',CC='/usr/bin/gcc',CXX='/usr/bin/g++',
               PKG_CONFIG_LIBDIR=str(sysroot/'usr/lib/x86_64-linux-gnu/pkgconfig')+':'+str(sysroot/'usr/share/pkgconfig'),PKG_CONFIG_SYSROOT_DIR=str(sysroot),
               BISON_PKGDATADIR=str(sysroot/'usr/share/bison'),M4=str(sysroot/'usr/bin/m4'))
    return env

def stop_build_group(process):
    # makepanda launches shells and compilers. The session leader may already
    # have exited; its descendants still need both signals before any receipt.
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:
        try:process.wait(timeout=.5)
        except subprocess.TimeoutExpired:pass
    finally:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait(timeout=15)

def build_bytes(out):
    return sum(p.stat().st_size for p in out.rglob('*') if p.is_file())

def build(stage,sysroot,out,threads=4,resume=False):
    need(type(threads) is int and 1<=threads<=4,'threads must be1..4')
    stage,sysroot,out=canonical(stage),canonical(sysroot),canonical(out)
    if out.exists():
        need(resume and (out/'build-receipt.json').is_file(),'existing build output preserved')
        prior=json.loads((out/'build-receipt.json').read_text())
        need(prior.get('status')=='failed' and prior.get('stage')==str(stage),'only same-stage failed build can resume')
    else:need(not resume,'cannot resume absent build')
    manifest=verify_stage(stage)
    for relative in ('usr/include/GL/gl.h','usr/include/GL/glx.h','usr/include/X11/Xlib.h','usr/lib/x86_64-linux-gnu/libGL.so','usr/lib/x86_64-linux-gnu/libX11.so'):
        need((sysroot/relative).is_file(),'builder dependency missing: '+relative)
    out.mkdir(parents=True,exist_ok=True)
    attempts=sorted(out.glob('makepanda-*.log'));attempt=len(attempts)+1
    command=[sys.executable,'-B',str(stage/'makepanda/makepanda.py'),'--nothing','--use-gl','--use-x11','--no-python','--no-copy-python',
             '--optimize','3','--threads',str(threads),'--git-commit',REVISION,'--outputdir',str(out/'sdk'),
             '--gl-incdir',str(sysroot/'usr/include'),'--gl-libdir',str(sysroot/'usr/lib/x86_64-linux-gnu'),
             '--x11-incdir',str(sysroot/'usr/include'),'--x11-libdir',str(sysroot/'usr/lib/x86_64-linux-gnu'),'--nocolor']
    env=build_environment(sysroot)
    log=out/f'makepanda-{attempt}.log';start=time.perf_counter()
    process=None;failure=None;disk_limit_exceeded=False
    try:
        with log.open('xb') as stream:
            process=subprocess.Popen(command,cwd=stage,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            while process.poll() is None:
                if build_bytes(out)>8*1024**3:
                    disk_limit_exceeded=True;break
                time.sleep(1)
    except BaseException as exc:failure=exc
    finally:
        if process is not None:stop_build_group(process)
    final_output_bytes=build_bytes(out)
    disk_limit_exceeded=disk_limit_exceeded or final_output_bytes>8*1024**3
    elapsed=time.perf_counter()-start
    receipt=dict(schema='panda-source-dispatch-build-v1',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),
                 stage=str(stage),upstream_revision=REVISION,upstream_tree=UPSTREAM_TREE,source_manifest_sha256=hashlib.sha256((stage/'source-dispatch-manifest.json').read_bytes()).hexdigest(),
                 command=command,attempt=attempt,returncode=process.returncode if process else None,build_wall_seconds=elapsed,log=log.name,
                 final_output_bytes=final_output_bytes,disk_limit_exceeded=disk_limit_exceeded,
                 failure_reason=type(failure).__name__ if failure else ('disk_limit' if disk_limit_exceeded else None),
                 build_scope='minimal GL/X11/noPython compile/link only; no renderer, driver query, model or library loading',
                 status='failed',runtime_admission_ready=False,native_admitted=False,candidate_panda_abi_qualified=False,
                 old_image_replaced=False,new_native_runs=0,new_gl_calls=0,new_provider_runs=0,new_model_runs=0,new_official_ort_runs=0)
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if failure is not None:raise failure
    need(not disk_limit_exceeded,'candidate build disk limit exceeded; group stopped and failed output preserved')
    need(process.returncode==0,'candidate build failed; raw log/partial outputs preserved')
    need(verify_stage(stage)==manifest,'staged source manifest changed during build')
    library=(out/'sdk/lib/libpandagl.so').resolve()
    need(library.is_relative_to(out) and library.is_file(),'candidate libpandagl missing')
    data=library.read_bytes();imports=inspect_imports(data)
    static_candidate=inspect_candidate(library)
    (out/'candidate-static-check.json').write_text(json.dumps(static_candidate,indent=2)+'\n')
    symbols=subprocess.check_output(['readelf','-WsW',str(library)],timeout=30).decode()
    for name in ('psd_configure','psd_resolved','psd_finish'):
        need(any(line.split()[-1:]==[name] and ' UND ' not in line for line in symbols.splitlines()),'candidate hook export missing: '+name)
    (out/'candidate-symbols.txt').write_text(symbols)
    for flags,name in ((['-rW'],'candidate-relocations.txt'),(['-dW'],'candidate-dynamic.txt')):
        (out/name).write_bytes(subprocess.check_output(['readelf',*flags,str(library)],timeout=30))
    (out/'candidate-imports.json').write_text(json.dumps(imports,indent=2)+'\n')
    receipt.update(status='compile_link_verified_not_loaded',candidate_library=str(library),candidate_nbytes=len(data),
                   candidate_sha256=hashlib.sha256(data).hexdigest(),loader_function_imports=len(imports['imports']),source_files_verified=len(manifest['source_tree']),static_candidate=static_candidate)
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True);parser.add_argument('--sysroot',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--threads',type=int,default=4);parser.add_argument('--resume',action='store_true');args=parser.parse_args(argv)
    try:
        result=build(args.stage,args.sysroot,args.out,args.threads,args.resume);print(json.dumps(result));return 0
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('candidate build rejected: '+str(exc),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
