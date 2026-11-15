from datetime import datetime,timezone,timedelta
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

root=Path('/workspace/big-model-closed-loop-benchmark');sys.path.insert(0,str(root))
from tests.test_readback_elf_imports import compile_import_fixture
from scripts.panda_dispatch_coverage import SOURCE_PINS,DELIVERY_SHA
from scripts.readback_elf_imports import inspect_imports

out=root/'output/stage7-panda-dispatch-coverage-01'
folder=out/sys.argv[1];folder.mkdir()
src=root/'docs/evidence/panda-dispatch-coverage-01/source'
image=root/'output/stage7-readback-return-core/source-audit/libpandagl.so'
exe=folder/'cpu-imports.so';started=time.perf_counter();command=compile_import_fixture(exe);build_wall=time.perf_counter()-started
cpu=inspect_imports(exe.read_bytes());(folder/'cpu-imports.json').write_text(json.dumps(cpu,indent=2)+'\n')
for path,prefix in ((image,'panda'),(exe,'cpu')):
 for flags,name in ((['-rW'],'relocations.txt'),(['-dW'],'dynamic.txt'),(['-WsW'],'symbols.txt')):
  (folder/(prefix+'-'+name)).write_bytes(subprocess.check_output(['readelf',*flags,str(path)]))
# Independent binutils slot/name comparison for all105pinned GL imports.
actual=inspect_imports(image.read_bytes());readelf=(folder/'panda-relocations.txt').read_text();independent=[]
function_names=set()
for line in (folder/'panda-symbols.txt').read_text().splitlines():
 fields=line.split()
 if len(fields)>=8 and fields[3] in ('FUNC','IFUNC','NOTYPE') and fields[6]=='UND':
  function_names.add(fields[7].split('@')[0])
for line in readelf.splitlines():
 fields=line.split()
 if len(fields)>=5 and fields[2] in ('R_X86_64_JUMP_SLOT','R_X86_64_GLOB_DAT') and fields[4].startswith('gl') and fields[4].split('@')[0] in function_names:
  independent.append((fields[4].split('@')[0],int(fields[0],16)))
expected=[(r['name'],r['slot_vaddr']) for r in actual['imports'] if r['name'].startswith('gl')]
assert sorted(independent)==sorted(expected) and len(expected)==105

base=[sys.executable,'-B','-m','scripts.panda_dispatch_coverage','--image',str(image),'--source-dir',str(src)]
cases=[]
def run(name,args=(),ok=False,base_command=None):
 target=folder/name
 cmd=(base_command or base)+list(args)+['--out',str(target)]
 p=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=20)
 assert p.returncode==(0 if ok else 2),(name,p.returncode,p.stdout,p.stderr)
 if ok:
  report=json.loads((target/'report.json').read_text())
  assert report['runtime_admission_ready'] is False and report['native_admitted'] is False
  assert not report['assessment']['installation_qualified'] and report['assessment']['blockers']
 else:
  assert not target.exists() and not p.stdout,(name,p.stdout)
 row=dict(name=name,argv=cmd,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,audit_completed=ok,
          native_admitted=False,runtime_admission_ready=False)
 cases.append(row);(folder/(name+'-process.json')).write_text(json.dumps(row,indent=2)+'\n')
 return target

first=run('got-only',ok=True)
run('source-integrated',args=('--mechanism','source-integrated'),ok=True)
with tempfile.TemporaryDirectory(prefix='pc-mutation-') as tmp:
 tmp=Path(tmp)
 for name,value in (('ordinary-safe',['glDrawArrays']),('unsafe-safe',['glNamedFramebufferReadBufferEXT']),
                    ('duplicate-safe',['glDrawArrays','glDrawArrays']),('oversized-safe',[f'glPotential{i}' for i in range(257)])):
  path=tmp/(name+'.json');path.write_text(json.dumps(value));run(name,('--safe-names',str(path)),ok=name=='ordinary-safe')
 foreign=tmp/'foreign.so';data=image.read_bytes();foreign.write_bytes(data[:-1]+bytes([data[-1]^1]))
 run('image-mutation',base_command=[*base[:5],str(foreign),*base[6:]])
 link=tmp/'linked.so';link.symlink_to(image)
 run('symlink-image',base_command=[*base[:5],str(link),*base[6:]])
 delivery=tmp/'delivery.c';delivery.write_bytes((root/'native/readback_call_delivery.c').read_bytes()+b'\n')
 run('delivery-mutation',('--delivery',str(delivery)))
 badsrc=tmp/'source';shutil.copytree(src,badsrc);p=badsrc/'glxGraphicsStateGuardian.cxx';p.write_bytes(p.read_bytes()+b'\n')
 run('source-mutation',base_command=[*base[:7],str(badsrc)])
 run('missing-input',base_command=[*base[:5],str(tmp/'missing.so'),*base[6:]])
 # Existing evidence must survive an attempted output reuse byte-for-byte.
 pinned={p.name:sha256(p.read_bytes()).hexdigest() for p in first.iterdir()}
 p=subprocess.run(base+['--out',str(first)],cwd=root,capture_output=True,text=True,timeout=20)
 assert p.returncode==2 and not p.stdout
 assert pinned=={p.name:sha256(p.read_bytes()).hexdigest() for p in first.iterdir()}
 row=dict(name='existing-output',exit_code=p.returncode,stderr=p.stderr,existing_evidence_preserved=True,native_admitted=False)
 cases.append(row);(folder/'existing-output-process.json').write_text(json.dumps(row,indent=2)+'\n')

report=json.loads((first/'report.json').read_text());assessment=report['assessment']
summary=dict(schema='panda-dispatch-cpu-evidence-v1',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),
             cpu_elf_command=command,cpu_elf_sha256=sha256(exe.read_bytes()).hexdigest(),build_wall_seconds=build_wall,
             build_timing_scope='CPU fixture compilation/link only; excludes tests,review,CI,development; no native overhead measurement',
             cases=cases,case_count=len(cases),pinned_loader_function_imports=len(actual['imports']),
             pinned_gl_imports=len(expected),independent_readelf_gl_slots_matched=True,
             literal_source_names=len(assessment['source_literal_names']),direct_source_names=len(assessment['direct_source_names']),
             conservative_potential_names=len(assessment['potential_name_union']),unclassified_names=len(assessment['unclassified_names']),
             current_profile_missing_names=assessment['missing_required_routes'],new_native_runs=0,new_gl_calls=0,
             new_provider_runs=0,new_model_runs=0,new_official_ort_runs=0,runtime_admission_ready=False,native_admitted=False)
(folder/'cpu-evidence.json').write_text(json.dumps(summary,indent=2)+'\n')
source_pins=dict(upstream_commit='470e352ab87ceae6e30429720e4690c8371f5a55',annotated_tag_sha='06c4a519ca89c4d5a981f1cdaaf7c9fe8d6b086e',
                 files={name:dict(nbytes=size,sha256=sha) for name,(size,sha) in SOURCE_PINS.items()},
                 delivery=dict(path='native/readback_call_delivery.c',sha256=DELIVERY_SHA),
                 image=dict(path=str(image.relative_to(root)),nbytes=image.stat().st_size,sha256=sha256(image.read_bytes()).hexdigest()))
(out/'source-pins.json').write_text(json.dumps(source_pins,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('case_count','build_wall_seconds','pinned_loader_function_imports','pinned_gl_imports','literal_source_names','direct_source_names','conservative_potential_names','unclassified_names')}))
