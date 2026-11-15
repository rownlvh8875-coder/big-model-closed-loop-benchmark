from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path.cwd();out=root/'output/stage7-panda-cache-adapter-01';ev=root/'docs/evidence/panda-cache-adapter-01';pre=ev/'before-review';pre.mkdir(parents=True,exist_ok=False)
def copy(src,name):
    p=pre/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,p)
for p in (out/'before-review-cpu').rglob('*'):
    if p.is_file():
        name=str(p.relative_to(out/'before-review-cpu'));name=name+'.data' if name.endswith(('.o','/fixture')) else name
        copy(p,'cpu/'+name)
for p in (out/'preservation-before-review').iterdir():copy(p,'preservation/'+p.name)
for name in ('pa-baseline.log','pa-runtime-red.log','pa-runtime-green.log','pa-task1-green.log','pa-harness-red.log','pa-focused-green.log','pa-cpu-cli.log','pa-preservation-before-review.log'):copy(Path('/tmp')/name,'tests/'+name)
for name in ('adapter-object.o','adapter-sections.txt','adapter-undefined.txt'):copy(out/name,name+'.data' if name.endswith('.o') else name)
copy(Path('/tmp/verify-pa-preservation.py'),'preservation/reproducer.py')
copy(Path('/tmp/package-pa.py'),'package-reproducer.py')
(ev/'README.md').write_text('''# Panda source observer/cache CPU evidence

before-review/ retains actual compiled C cache and C++ runtime/adapter/fake-original binaries, normal/sanitized48-case receipts and per-command raw logs, object sections/imports, test RED/GREEN and preservation. There are96CPU scenario executions. CPU binaries have .data suffixes in Git; ELF objects are data only. The separately pinned prior Panda SDK ELF must NEVER be loaded/imported/executed. This task does not build/activate a new Panda SDK or arm capture.

The harness pins immutable psd/cache/caller sources and prior candidate SHA228b2d88e91fa9c5ded10cfe8e93f9b9519de881a37765a0e8681af6e36cf96b as data. Compiler/source/candidate/output identities and commands are retained. Only normally returning fully defined CPU originals execute. New output is required; original evidence/source/SDK is preserved. A CPU contract success means bounded command metadata, not driver/camera/native admission. Counter, lifecycle, bootstrap and deletion behavior is described in RESULT/LEDGER/CONTINUATION.

Full raw output remains output/stage7-panda-cache-adapter-01/. proof-index.json hashes all versioned proof files except itself. Subsequent one-review/fix/final records are separate; before-review remains immutable. Native allowance0, inherited strict0/4FAIL/Stage7INCOMPLETE; actual build branch/name/safe256profile, full image/mapped ABI/allocation/camera/lifetime/environment/receipt and fresh ON/OFF contract remain gates.
''')
print('packaged CPU and preservation proof')
