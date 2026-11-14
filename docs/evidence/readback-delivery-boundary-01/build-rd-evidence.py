import dataclasses
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

root = Path('/workspace/big-model-closed-loop-benchmark')
sys.path.insert(0, str(root))
from tests.test_readback_call_delivery import compile_delivery, sample, decode
from tests.test_readback_process_mapping import symbol_ranges
from scripts.readback_producer_channel import run_cpu_probe, CODE_NAMES, MODES

out = root / 'output/stage7-readback-delivery-boundary-01'
out.mkdir(parents=True, exist_ok=True)
standalone_modes = ('basic','aliases','safe','null','delete','attrib','createfail','failedswitch','makeboth','preserve',
                    'mismatch','unknown','glerror','invalidate','display','thread','reentrant','shared','cap','destroy','pbo','footerfail','off','offinvalid')
rejected = {'mismatch','unknown','glerror','invalidate','display','thread','reentrant','shared','cap','destroy','pbo','footerfail','offinvalid'}
positive_channel = {'basic','aliases','preserve','off'}
builds, cases = [], []
for sanitize in (False, True):
    variant = 'asan-ubsan' if sanitize else 'plain'
    folder = out / variant
    folder.mkdir(exist_ok=True)
    exe = folder / 'fixture'
    start = time.perf_counter()
    command = compile_delivery(exe, sanitize=sanitize)
    wall = time.perf_counter() - start
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    profile = symbol_ranges(exe, CODE_NAMES)
    build = dict(variant=variant, command=command, build_wall_seconds=wall, exe_sha256=sha, codeprofile=profile)
    (folder/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    builds.append(build)
    for mode in standalone_modes:
        raw, status = sample(exe, mode)
        (folder/(mode+'.rbr')).write_bytes(raw)
        (folder/(mode+'.json')).write_text(json.dumps(status,indent=2)+'\n')
        assert status['args_ok'] == status['errno_ok'] == status['regs_ok'] == 1
        assert status['original_calls'] == 2
        try:
            decoded = decode(raw, status, mode)
        except ValueError:
            assert mode in rejected, mode
            accepted = False
        else:
            assert mode not in rejected, mode
            assert decoded['cpu_window_closed']
            accepted = True
        cases.append(dict(kind='standalone',variant=variant,mode=mode,cpu_stream_accepted=accepted,
                          stream_sha256=hashlib.sha256(raw).hexdigest(),stream_nbytes=len(raw)))
        if sanitize:
            assert raw == (out/'plain'/(mode+'.rbr')).read_bytes()
            assert status == json.loads((out/'plain'/(mode+'.json')).read_text())
    rejections=[]
    for name in ('glNamedFramebufferReadBuffer','glNamedFramebufferReadBufferEXT','glFramebufferReadBufferEXT','glXCopyContext'):
        p=subprocess.run([str(exe),'safe',name],capture_output=True,timeout=15)
        assert p.returncode==3 and not p.stdout and not p.stderr,(variant,name,p.returncode,p.stderr)
        row=dict(kind='unsafe-allowlist',variant=variant,name=name,exit_code=p.returncode,rejected=True)
        rejections.append(row);cases.append(row)
    (folder/'unsafe-allowlist-rejections.json').write_text(json.dumps(rejections,indent=2)+'\n')
    for mode in sorted(MODES):
        import os
        nonce = os.urandom(32)
        try:
            result = run_cpu_probe(exe,sha,mode,profile,nonce,timeout=15)
        except ValueError as exc:
            assert mode not in positive_channel, (mode,str(exc))
            summary = dict(mode=mode,rejected=True,reason=str(exc),nonce=nonce.hex(),native_admitted=False)
        else:
            assert mode in positive_channel, mode
            (folder/('channel-'+mode+'.rbr')).write_bytes(result.pop('stream'))
            decoded = result.pop('decoded')
            result['decoded_summary'] = {k:v for k,v in decoded.items() if k!='records'}
            result['decoded_summary']['record_count'] = len(decoded['records'])
            summary = dict(mode=mode,rejected=False,result=result)
        (folder/('channel-'+mode+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
        cases.append(dict(kind='channel',variant=variant,mode=mode,rejected=summary['rejected']))
for command, name in ((['cc','--version'],'compiler.txt'),(['nm','--version'],'binutils.txt')):
    (out/name).write_bytes(subprocess.check_output(command))
result = dict(schema='readback-delivery-cpu-evidence-v1',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),
              builds=builds,build_wall_seconds=sum(b['build_wall_seconds'] for b in builds),cases=cases,
              case_count=len(cases),sanitizers='ASan+UBSan; no recover; all subprocesses exited as expected',
              native_admitted=False,driver_state_proven=False,original_gpu_bytes_observed=False,new_native_runs=0,
              build_timing_scope='compilation/link only; excludes tests,review,CI,development; not native instrumentation overhead')
(out/'cpu-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('case_count','build_wall_seconds','new_native_runs')}))
