from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,subprocess
from tests.test_panda_source_dispatch import compile_source_dispatch,MODES,FAIL
from scripts.build_panda_source_dispatch import inspect_candidate,verify_stage
root=Path.cwd();out=root/'output/stage7-panda-source-dispatch-01';cpu=out/'cpu-review-fixed';cpu.mkdir(exist_ok=False)
results=[]
for sanitized in (False,True):
    exe=cpu/('fixture-sanitized' if sanitized else 'fixture-normal');command=compile_source_dispatch(exe,sanitized)
    samples={}
    for mode in MODES+('badshape',):
        p=subprocess.run([str(exe),mode],capture_output=True,text=True,timeout=15)
        assert p.returncode==0 and p.stderr=='',(mode,p.returncode,p.stderr)
        s=json.loads(p.stdout)
        assert s['reads']==1 and s['regs_ok']==1 and s['args_ok']==1 and not s['native_admitted'],(mode,s)
        assert (s['finish']!=0)==(mode in FAIL or mode=='badshape'),(mode,s)
        samples[mode]=s
    p=subprocess.run([str(exe),'unsafe_config'],capture_output=True,text=True,timeout=15)
    assert (p.returncode,p.stdout,p.stderr)==(3,'','')
    results.append(dict(sanitized=sanitized,command=command,sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),samples=samples,unsafe_config_returncode=3))
assert results[0]['samples']==results[1]['samples']
(cpu/'verification.json').write_text(json.dumps(dict(checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),scenarios_per_build=25,normal_sanitized_identical=True,builds=results,native_admitted=False),indent=2)+'\n')
manifest=verify_stage(out/'candidate-source-review-fixed')
static=inspect_candidate(out/'build-review-fixed/sdk/lib/libpandagl.so')
(out/'build-review-fixed/candidate-static-check.json').write_text(json.dumps(static,indent=2)+'\n')
command=['/usr/bin/g++','-std=c++11','-O2','-fPIC','-fno-exceptions','-DPSD_PANDA_BUILD','-I'+str(out/'sysroot/usr/include'),'-I'+str(root/'native'),'-c',str(root/'native/panda_source_dispatch.cxx'),'-o',str(out/'runtime-glx-types-review-fixed.o')]
subprocess.run(command,check=True,capture_output=True)
sections=subprocess.check_output(['readelf','-SW',str(out/'runtime-glx-types-review-fixed.o')],text=True)
assert '.init_array' not in sections and '.ctors' not in sections
(out/'runtime-sections-review-fixed.txt').write_text(sections)
(out/'static-verification-review-fixed.json').write_text(json.dumps(dict(checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),candidate=static,source_files=len(manifest['source_tree']),runtime_object_command=command,runtime_object_sha256=hashlib.sha256((out/'runtime-glx-types-review-fixed.o').read_bytes()).hexdigest(),runtime_object_no_custom_constructor=True,candidate_not_loaded=True),indent=2)+'\n')
print(json.dumps(dict(cpu_scenarios=50,unsafe_config_rejections=2,candidate=static,source_files=len(manifest['source_tree']),no_runtime_init_array=True)))
