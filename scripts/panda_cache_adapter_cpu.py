"""Run fully defined CPU fake originals; Panda candidate is inspected as DATA ONLY."""
import argparse
from datetime import datetime,timezone,timedelta
import hashlib,json,os
from pathlib import Path
import subprocess,sys,time
from scripts.panda_source_dispatch import canonical,need,ROOT
from scripts.panda_dispatch_coverage import read_input
from scripts.build_panda_source_dispatch import inspect_candidate,stop_build_group

CANDIDATE_SHA='228b2d88e91fa9c5ded10cfe8e93f9b9519de881a37765a0e8681af6e36cf96b'
DEFAULT_CANDIDATE=ROOT/'docs/evidence/panda-source-dispatch-01/after-fix/build/candidate-libpandagl.so.data'
IMMUTABLE={
 'native/panda_source_dispatch.h':'f2e869a8c7a2719d6a7eb7fbc1a350873793265fb1c1a7a32aa0e43e00eca7e9',
 'native/panda_source_dispatch.cxx':'50bb0428619654444f050d2c9f88b4a81d6d3411748050335d2c4ca59be7a8d7',
 'native/readback_command_state.h':'4c64a2059cd722fa9a35d6e4ed81ac80bd4c89bdd8bac8ff73b00213b81db2b8',
 'native/readback_command_state.c':'49e986eca295519f180e6b96477ab1752f6bd0996bdf9f9f535bcfc5c17e3bc2',
 'tests/fixtures/panda_readback_caller.S':'7d46b3bb4f50c448e833fab746bcdd7b1e229f9cd15eb30817a2be76bdbf746d'}
GOOD=('bootstrap','live','preserve','aliases','delete_mutate','unrelated_delete','zero_delete','empty_delete','two_contexts','failed_switch','failed_create','new','attribs','sgix','pending_destroy','pending_release','draw_delete','after_finish','install_twice','truthy_current','observe')
BAD=('no_attach','dirty_cache','double_attach','shared','display','unknown_context','livecap','lifetimes','pending_rebind','double_destroy','fbo_deleted','fbo_mutate','source_error','source_reentry','source_thread','adapter_thread','eventcap','delete_bad','delete_negative','forged','original_snapshot','identity','downstream','double_finish','overlap','external_finish','nonzero_error')
SOURCES=tuple(IMMUTABLE)+('native/panda_cache_adapter.h','native/panda_cache_adapter.cxx','tests/fixtures/panda_cache_adapter_fixture.cxx','scripts/panda_cache_adapter_cpu.py')

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
    commands=[['/usr/bin/gcc','-std=c11',*flags,'-c',str(ROOT/'native/readback_command_state.c'),'-o',str(obj)],
              ['/usr/bin/g++','-std=c++11',*flags,'-Dpb_fixture_call=pca_fixture_call','-Dpb_fixture_return=pca_fixture_return',str(ROOT/'native/panda_source_dispatch.cxx'),str(ROOT/'native/panda_cache_adapter.cxx'),str(ROOT/'tests/fixtures/panda_cache_adapter_fixture.cxx'),str(caller),str(obj),'-o',str(binary)]]
    receipts=[]
    for index,command in enumerate(commands):
        r=run_command(command,ROOT,cpu_environment(),out/f'compile-{index}',30);receipts.append(r)
        need(r['returncode']==0 and r['stderr']=='','CPU fixture compile failed; raw logs retained')
    return dict(sanitized=sanitize,binary=str(binary),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),commands=receipts)

def output_budget(out):need(sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=64*1024*1024,'CPU evidence output budget')

def run_cpu(out,candidate=DEFAULT_CANDIDATE):
    out,candidate=canonical(out),canonical(candidate);need(not out.exists(),'existing CPU proof output preserved')
    data=read_input(candidate,64*1024*1024);need(hashlib.sha256(data).hexdigest()==CANDIDATE_SHA,'exact data-only Panda candidate required')
    static=inspect_candidate(candidate);pins=sources()
    out.mkdir(parents=True)
    report=dict(schema='panda-cache-adapter-cpu-v1',status='RUNNING',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),
                candidate_path=str(candidate),candidate_static=static,source_sha256=pins,builds=[],scenarios_per_build=len(GOOD)+len(BAD),
                native_admitted=False,runtime_admission_ready=False,stage7_complete=False,new_native_runs=0,new_gl_calls=0,new_provider_runs=0,new_model_runs=0,new_official_ort_runs=0)
    receipt=out/'receipt.json'
    def save():receipt.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
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
