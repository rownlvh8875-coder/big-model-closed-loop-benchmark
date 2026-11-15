"""Compile only handwritten CPU components and fake originals, never Panda."""
from pathlib import Path
from scripts import panda_cache_adapter_cpu as cpu
from tests.test_panda_adapter_sdk_cpu import OFF_SOURCE
ROOT=Path(__file__).resolve().parents[1]
def compile_cpu(out,native_dir=None,sanitize=False):
    native_dir=Path(native_dir) if native_dir else ROOT/'native/panda_sdk_routes_v2'
    out=Path(out);out.mkdir(parents=True,exist_ok=False);commands=[]
    flags=['-O1' if sanitize else '-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(native_dir)];san=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer'] if sanitize else []
    caller=out/'caller.S';caller.write_bytes((ROOT/'tests/fixtures/panda_readback_caller.S').read_bytes().replace(b'pb_entry',b'psd_read_pixels'))
    def run(cmd,name):
        r=cpu.run_command(cmd,ROOT,cpu.cpu_environment(),out/name,30);commands.append(r)
        if r['returncode'] or r['stderr']:raise AssertionError(r['stderr'])
    objects=[]
    for name,compiler,standard,path,extra in [('cache','/usr/bin/gcc','c11',native_dir/'readback_command_state.c',[]),('activity','/usr/bin/g++','c++11',native_dir/'panda_source_activity.cxx',['-fvisibility=hidden']),('adapter','/usr/bin/g++','c++11',native_dir/'panda_cache_adapter.cxx',[]),('caller','/usr/bin/gcc',None,caller,['-Dpb_fixture_call=pca_fixture_call','-Dpb_fixture_return=pca_fixture_return'])]:
        obj=out/(name+'.o');run([compiler,*(['-std='+standard] if standard else []),*flags,*san,*extra,'-fPIC','-c',str(path),'-o',str(obj)],'compile-'+name);objects.append(str(obj))
    library=out/'libpsd2_handwritten_cpu.so';run(['/usr/bin/g++','-shared',*flags,*san,*objects,'-Wl,-z,defs','-Wl,-soname,libpsd2_handwritten_cpu.so','-o',str(library)],'link-cpu')
    off=out/'off.cxx';off.write_text(OFF_SOURCE)
    result=dict(library=str(library),commands=commands)
    for name,source in [('routes',ROOT/'tests/fixtures/panda_sdk_routes_fixture.cxx'),('legacy',ROOT/'tests/fixtures/panda_cache_adapter_fixture.cxx'),('off',off)]:
        exe=out/name;run(['/usr/bin/g++','-std=c++11',*flags,*san,*(['-no-pie'] if sanitize else []),str(source),'-L'+str(out),'-lpsd2_handwritten_cpu','-Wl,-rpath,$ORIGIN','-o',str(exe)],'link-'+name);result[name]=str(exe)
    return result
