import sys, json, hashlib, subprocess, tempfile, os
from pathlib import Path
sys.path.insert(0,'/workspace/big-model-closed-loop-benchmark')
from scripts.panda_dispatch_coverage import scan_source, assess_coverage
from scripts.readback_elf_imports import inspect_imports
from tests.test_readback_elf_imports import dynamic_locations, changed_tag
root=Path('/workspace/big-model-closed-loop-benchmark')
blob=(root/'docs/evidence/panda-dispatch-coverage-01/before-review-final/cpu-imports.so').read_bytes()
tags={t:v for _,t,v in dynamic_locations(blob) if t}
print('I1 original imports:',[x['name'] for x in inspect_imports(blob)['imports']])
print('I1 DT_SYMTAB=DT_STRTAB imports:',inspect_imports(changed_tag(blob,6,tags[5]))['imports'])
for data in [b'get_\\\nextension_func("glDeleteBuffers");',b'glDeleteBuffers\\\r\n(1, buffers);']:
 print('I2 source:',repr(data),'inventory:',scan_source(data,'case.cxx'))
source=scan_source(b'glPopAttrib(); glClientAttribDefaultEXT(1);','case.cxx')
r=assess_coverage({'schema':'readback-loader-imports-v1','imports':[]},[source],(),['glPopAttrib','glClientAttribDefaultEXT'])
print('I3 mutator safe classification:',json.dumps(r))
with tempfile.TemporaryDirectory(prefix='pc-review-') as d:
 p=Path(d)/'fifo';os.mkfifo(p)
 cmd=[sys.executable,'-B','-m','scripts.panda_dispatch_coverage','--image',str(p),'--source-dir',str(root/'docs/evidence/panda-dispatch-coverage-01/source'),'--out',str(Path(d)/'result')]
 try:
  p=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=2);print('I4 FIFO returned:',p.returncode,p.stderr)
 except subprocess.TimeoutExpired:
  print('I4 FIFO CLI hung for 2 seconds; timeout killed subprocess; no output:',not (Path(d)/'result').exists())
idx=json.loads((root/'docs/evidence/panda-dispatch-coverage-01/proof-index.json').read_text())
for r in idx['files']+idx['retained_not_in_git']:
 b=(root/r['path']).read_bytes();assert len(b)==r['nbytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
for p,h in idx['source_pins'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p
upstream=json.loads((root/'docs/evidence/panda-dispatch-coverage-01/upstream-source-verification.json').read_text())
for r in upstream['files']:
 b=(root/'docs/evidence/panda-dispatch-coverage-01/source'/Path(r['path']).name).read_bytes()
 assert len(b)==r['nbytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
print('Integrity: 67 indexed proofs, 7 retained inputs, 9 source pins, 5 upstream SHA256/Git blob identities verified.')
