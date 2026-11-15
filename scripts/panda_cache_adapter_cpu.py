"""Run fully defined CPU fake originals; Panda candidate is inspected as DATA ONLY."""
import argparse
from datetime import datetime,timezone,timedelta
import hashlib,json,os
from pathlib import Path
import subprocess,sys,time,struct
from scripts.panda_source_dispatch import canonical,need,ROOT
from scripts.panda_dispatch_coverage import read_input
from scripts.build_panda_source_dispatch import stop_build_group
from scripts.readback_elf_imports import inspect_imports
from scripts.readback_process_mapping import elf_ranges
from scripts.panda_readback_abi import qualify_elf

CANDIDATE_SHA='228b2d88e91fa9c5ded10cfe8e93f9b9519de881a37765a0e8681af6e36cf96b'
DEFAULT_CANDIDATE=ROOT/'docs/evidence/panda-source-dispatch-01/after-fix/build/candidate-libpandagl.so.data'
IMMUTABLE={
 'native/panda_source_dispatch.h':'f2e869a8c7a2719d6a7eb7fbc1a350873793265fb1c1a7a32aa0e43e00eca7e9',
 'native/panda_source_dispatch.cxx':'50bb0428619654444f050d2c9f88b4a81d6d3411748050335d2c4ca59be7a8d7',
 'native/readback_command_state.h':'4c64a2059cd722fa9a35d6e4ed81ac80bd4c89bdd8bac8ff73b00213b81db2b8',
 'native/readback_command_state.c':'49e986eca295519f180e6b96477ab1752f6bd0996bdf9f9f535bcfc5c17e3bc2',
 'tests/fixtures/panda_readback_caller.S':'7d46b3bb4f50c448e833fab746bcdd7b1e229f9cd15eb30817a2be76bdbf746d'}
IMMUTABLE.update({
 'native/readback_return_core.h':'1a78841638968a7c9d08fe845b1d0b3b7976ab0808edcc22ff6cfd631e0ee58f',
 'scripts/build_panda_source_dispatch.py':'dfcf9dc81bfcacd604210854f750c357889dcfd0031fb1d07ad9ba47731f0a3c',
 'scripts/panda_source_dispatch.py':'e04876adbac9c102d2eed4f4f73ffbb53690f6421ab28c76da290c1ca56b2f1c',
 'scripts/panda_dispatch_coverage.py':'e3806fcb46852fc417c370e66b7afc47a6f73c0986aaa0376fc82a3f75f4d9ba',
 'scripts/readback_elf_imports.py':'63c8d06ed9ba8fa7a6ae69253e77271802457ef77aaf7b0087ae79f11e9ece96',
 'scripts/readback_process_mapping.py':'de7992f3251fbd9300f8b5054a9d949bb95cc57e1d1a10d8b1e9420815d5e4f7',
 'scripts/panda_readback_abi.py':'a0129175e1bac26629a0d2832b3f25e3e84126e6a70f3eee753af1bc213241b3',
})
GOOD=('bootstrap','live','preserve','aliases','delete_mutate','unrelated_delete','zero_delete','empty_delete','two_contexts','failed_switch','failed_create','new','attribs','sgix','pending_destroy','pending_release','draw_delete','after_finish','install_twice','truthy_current','observe')
BAD=('no_attach','dirty_cache','double_attach','shared','display','unknown_context','livecap','lifetimes','pending_rebind','double_destroy','fbo_deleted','fbo_mutate','source_error','source_reentry','source_thread','adapter_thread','eventcap','delete_bad','delete_negative','forged','original_snapshot','identity','downstream','double_finish','overlap','external_finish','nonzero_error','pending_known','pending_unknown')
SOURCES=tuple(IMMUTABLE)+('native/panda_source_activity.h','native/panda_source_activity.cxx','native/panda_cache_adapter.h','native/panda_cache_adapter.cxx','tests/fixtures/panda_cache_adapter_fixture.cxx','scripts/panda_cache_adapter_cpu.py')

def cpu_environment():
    env=os.environ.copy()
    for key in ('CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS','CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','LIBRARY_PATH','GCC_EXEC_PREFIX','COMPILER_PATH','LD_PRELOAD','LD_AUDIT','LD_LIBRARY_PATH','PYTHONPATH','ASAN_OPTIONS','UBSAN_OPTIONS','LSAN_OPTIONS'):
        env.pop(key,None)
    env.update(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    return env

def run_command(command,cwd,env,prefix,timeout,byte_limit=1024*1024):
    prefix=canonical(prefix);stdout=Path(str(prefix)+'.stdout');stderr=Path(str(prefix)+'.stderr');start=time.perf_counter()
    with stdout.open('xb') as out,stderr.open('xb') as err:
        process=subprocess.Popen(command,cwd=cwd,env=env,stdout=out,stderr=err,start_new_session=True)
        try:
            while process.poll() is None:
                need(time.perf_counter()-start<=timeout,'CPU command timeout')
                need(stdout.stat().st_size+stderr.stat().st_size<=byte_limit,'CPU command output budget')
                time.sleep(.01)
        finally:stop_build_group(process)
    need(time.perf_counter()-start<=timeout,'CPU command timeout')
    need(stdout.stat().st_size+stderr.stat().st_size<=byte_limit,'CPU command output budget')
    result=dict(command=list(command),returncode=process.returncode,wall_seconds=time.perf_counter()-start,
                stdout=stdout.read_text(),stderr=stderr.read_text())
    return result

def inspect_cpu_data(path,symbols,dynamic_symbols):
    path=canonical(path);data=read_input(path,64*1024*1024);loader=inspect_imports(data);loads=elf_ranges(data)
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

def inspect_cpu_candidate(path,out):
    path=canonical(path);out=canonical(out);tool=Path('/usr/bin/readelf');digest=hashlib.sha256(tool.read_bytes()).hexdigest()
    commands=[]
    for suffix,flags in (('symbols',['-WsW']),('dynamic-symbols',['--dyn-syms','-W'])):
        r=run_command([str(tool),*flags,str(path)],ROOT,cpu_environment(),out/('inspect-'+suffix),30)
        need(r['returncode']==0 and r['stderr']=='','bounded candidate inspection failed');commands.append(r)
    need(hashlib.sha256(tool.read_bytes()).hexdigest()==digest,'inspection tool changed')
    static=inspect_cpu_data(path,commands[0]['stdout'],commands[1]['stdout'])
    static['source_activity_extension_present']=any(len(f:=line.split())>=8 and f[3]=='FUNC' and f[4]=='GLOBAL' and f[6]!='UND' and f[7]=='psd_source_idle' for line in commands[1]['stdout'].splitlines())
    return dict(static=static,commands=commands,tool=dict(path=str(tool),resolved=str(tool.resolve()),sha256=digest))

def sources():
    result={name:hashlib.sha256(read_input(canonical(ROOT/name),1024*1024)).hexdigest() for name in SOURCES}
    need(all(result[p]==sha for p,sha in IMMUTABLE.items()),'immutable source pin mismatch')
    return result

def compile_fixture(out,sanitize=False):
    out=canonical(out);need(not out.exists(),'existing CPU compile output preserved');out.mkdir(parents=True)
    flags=['-O1' if sanitize else '-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'native')]
    if sanitize:flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie']
    caller=out/'caller.S';caller.write_bytes(read_input(ROOT/'tests/fixtures/panda_readback_caller.S',1024*1024).replace(b'pb_entry',b'psd_read_pixels'))
    binary=out/'fixture';obj=out/'cache.o'
    common=['-Dpb_fixture_call=pca_fixture_call','-Dpb_fixture_return=pca_fixture_return']
    receipts=[];objects=[];dependencies=set()
    units=[('cache','/usr/bin/gcc','c11','native/readback_command_state.c'),
           ('activity','/usr/bin/g++','c++11','native/panda_source_activity.cxx'),
           ('adapter','/usr/bin/g++','c++11','native/panda_cache_adapter.cxx'),
           ('fixture','/usr/bin/g++','c++11','tests/fixtures/panda_cache_adapter_fixture.cxx')]
    for name,compiler,standard,source in units:
        obj=out/(name+'.o');dep=out/(name+'.d')
        command=[compiler,'-std='+standard,*flags,*common,'-MMD','-MF',str(dep),'-c',str(ROOT/source),'-o',str(obj)]
        r=run_command(command,ROOT,cpu_environment(),out/('compile-'+name),30);receipts.append(r)
        need(r['returncode']==0 and r['stderr']=='','CPU fixture compile failed; raw logs retained');objects.append(str(obj))
        import shlex
        text=dep.read_text().replace('\\\n',' ')
        for item in shlex.split(text.split(':',1)[1]):
            path=Path(item).resolve()
            if path.is_relative_to(ROOT):dependencies.add(str(path.relative_to(ROOT)))
        need(dependencies<=set(SOURCES),'unrecorded project compiler dependency')
    command=['/usr/bin/g++','-std=c++11',*flags,*common,*objects,str(caller),'-o',str(binary)]
    r=run_command(command,ROOT,cpu_environment(),out/'link',30);receipts.append(r)
    need(r['returncode']==0 and r['stderr']=='','CPU fixture link failed; raw logs retained')
    return dict(sanitized=sanitize,binary=str(binary),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),commands=receipts,project_dependencies=sorted(dependencies))

def output_budget(out):need(sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=64*1024*1024,'CPU evidence output budget')

def run_cpu(out,candidate=DEFAULT_CANDIDATE):
    out,candidate=canonical(out),canonical(candidate);need(not out.exists(),'existing CPU proof output preserved')
    data=read_input(candidate,64*1024*1024);need(hashlib.sha256(data).hexdigest()==CANDIDATE_SHA,'exact data-only Panda candidate required')
    pins=sources()
    out.mkdir(parents=True)
    report=dict(schema='panda-cache-adapter-cpu-v1',status='RUNNING',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),
                candidate_path=str(candidate),candidate_sha256=CANDIDATE_SHA,source_sha256=pins,builds=[],scenarios_per_build=len(GOOD)+len(BAD),
                native_admitted=False,runtime_admission_ready=False,candidate_adapter_link_qualified=False,source_activity_extension_required=True,stage7_complete=False,new_native_runs=0,new_gl_calls=0,new_provider_runs=0,new_model_runs=0,new_official_ort_runs=0)
    receipt=out/'receipt.json'
    def save():receipt.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        report['inspection']=inspect_cpu_candidate(candidate,out);report['candidate_static']=report['inspection']['static']
        tools=[]
        for name in ('gcc','g++'):
            path=Path('/usr/bin')/name;r=run_command([str(path),'--version'],ROOT,cpu_environment(),out/('tool-'+name.replace('+','p')),10)
            need(r['returncode']==0,'compiler version failed');tools.append(dict(path=str(path),resolved=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),version=r['stdout']))
        report['tools']=tools
        for sanitized in (False,True):
            build=compile_fixture(out/('sanitized' if sanitized else 'normal'),sanitized);build['samples']={};build['runs']=[];report['builds'].append(build);output_budget(out)
            for mode in GOOD+BAD:
                r=run_command([build['binary'],mode],ROOT,cpu_environment(),out/('sanitized' if sanitized else 'normal')/mode,10)
                build['runs'].append(r);need(r['returncode']==0 and r['stderr']=='','CPU scenario failed: '+mode)
                s=json.loads(r['stdout']);build['samples'][mode]=s
                need((s['args_ok'],s['errno_ok'],s['reads'],s['regs_ok'],s['stale_output'])==(1,1,1,1,0) and s['native_admitted'] is False,'CPU forwarding/output contract: '+mode)
                need((s['finish']==0)==(mode in GOOD) and (s['adapter_error']==0)==(mode in GOOD),'CPU metadata acceptance contract: '+mode)
                output_budget(out)
            save()
        need(report['builds'][0]['samples']==report['builds'][1]['samples'],'normal/sanitized results differ')
        need(sources()==pins and hashlib.sha256(read_input(candidate,64*1024*1024)).hexdigest()==CANDIDATE_SHA,'CPU source/candidate changed during verification')
        report.update(status='CPU_CONTRACT_VERIFIED_NATIVE_BLOCKED',normal_sanitized_identical=True)
        save();output_budget(out);return report
    except BaseException as exc:
        report.update(status='FAILED_OR_INCOMPLETE',failure=type(exc).__name__+': '+str(exc));save();raise

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);parser.add_argument('--candidate',default=str(DEFAULT_CANDIDATE));args=parser.parse_args(argv)
    try:
        r=run_cpu(args.out,args.candidate);print(json.dumps(dict(status=r['status'],out=str(canonical(args.out)),scenarios_per_build=r['scenarios_per_build'],normal_sanitized_identical=True,native_admitted=False)));return 0
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('CPU adapter verification rejected: '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
