from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json
from tests.test_panda_adapter_sdk_cpu import compile_cpu_sdk,ROOT
from scripts import panda_cache_adapter_cpu as cpu
from scripts import build_panda_adapter_sdk as sdk
from scripts.panda_adapter_sdk_stage import native_files
out=ROOT/'output/stage7-panda-adapter-sdk-01/cpu-final';out.mkdir(exist_ok=False)
pins={str((Path('native')/name)):hashlib.sha256(data).hexdigest() for name,data in native_files().items()}
for name in ('scripts/panda_adapter_sdk_stage.py','scripts/build_panda_adapter_sdk.py','tests/test_panda_adapter_sdk_cpu.py','tests/fixtures/panda_cache_adapter_fixture.cxx','tests/fixtures/panda_readback_caller.S'):pins[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
builds=[]
for sanitized in (False,True):
    directory=out/('sanitized' if sanitized else 'normal');profile=compile_cpu_sdk(directory,sanitized);profile['sanitized']=sanitized
    inspect=directory/'inspect';inspect.mkdir();profile['interfaces']=sdk.inspect_exports(Path(profile['library']),inspect)
    dynamic=cpu.run_command(['/usr/bin/readelf','-dW',profile['library']],ROOT,cpu.cpu_environment(),directory/'needed',30)
    neededs=[line.split('[')[1].split(']')[0] for line in dynamic['stdout'].splitlines() if '(NEEDED)' in line]
    assert not any(n.lower().startswith(('libgl','libpanda','libx11','libonnx')) for n in neededs),neededs
    profile['needed_libraries']=neededs;profile['samples']={};profile['runs']=[]
    for mode in cpu.GOOD+cpu.BAD:
        r=cpu.run_command([profile['fixture'],mode],ROOT,cpu.cpu_environment(),directory/('case-'+mode),10)
        assert r['returncode']==0 and r['stderr']=='',(mode,r)
        s=json.loads(r['stdout']);assert (s['args_ok'],s['errno_ok'],s['reads'],s['regs_ok'],s['stale_output'])==(1,1,1,1,0),(mode,s)
        assert (s['finish']==0)==(mode in cpu.GOOD) and not s['native_admitted'],(mode,s)
        profile['samples'][mode]=s;profile['runs'].append(r)
    r=cpu.run_command([profile['off']],ROOT,cpu.cpu_environment(),directory/'default-off',10)
    assert(r['returncode'],r['stdout'],r['stderr'])==(0,'CPU_DEFAULT_OFF_ORIGINAL_ONLY\n','');profile['default_off']=r
    profile['artifact_sha256']={key:hashlib.sha256(Path(profile[key]).read_bytes()).hexdigest() for key in ('library','fixture','off')};builds.append(profile)
assert builds[0]['samples']==builds[1]['samples']
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in pins.items())
r=dict(schema='panda-adapter-shared-cpu-v1',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),source_sha256=pins,builds=builds,scenarios_per_build=51,total_cpu_executions=102,normal_sanitized_identical=True,real_panda_loaded=False,native_admitted=False,runtime_binding_qualified=False,stage7_complete=False)
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(total_cpu_executions=102,normal_sanitized_identical=True,real_panda_loaded=False,native_admitted=False)))
