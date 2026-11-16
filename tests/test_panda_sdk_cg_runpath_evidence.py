import copy,json,shlex,subprocess,tempfile,unittest
from pathlib import Path
from scripts import panda_sdk_cg_runpath_evidence as v
from scripts import build_panda_sdk_cg_runpath as b
from scripts import panda_sdk_cg_eigen_inputs as e
from tests.test_panda_sdk_cg_eigen_evidence import success_shaped as base_fixture,put,file_row

def cpu_elf(root,value='$ORIGIN',rpath=False):
 source=root/'cpu.c';source.write_text('int handwritten_cpu_fixture(void){return 1;}\n');target=root/'cpu.so';flags=[] if value is None else ['-Wl,--disable-new-dtags' if rpath else '-Wl,--enable-new-dtags','-Wl,-rpath,'+value]
 subprocess.run(['/usr/bin/gcc','-nostdlib','-shared','-fPIC',str(source),'-o',str(target),*flags],capture_output=True,check=True);return target.read_bytes()

def success_shaped(root):
 receipt=base_fixture(root);before='stage7-panda-sdk-cg-eigen-candidate-02';after='stage7-panda-sdk-cg-runpath-candidate-03'
 def adapt(x):
  if isinstance(x,str):return x.replace(before,after)
  if isinstance(x,list):return [adapt(y) for y in x]
  if isinstance(x,dict):return {adapt(k):adapt(value) for k,value in x.items()}
  return x
 receipt=adapt(receipt)
 for path in (root/'reports').glob('*.json'):put(path,adapt(json.loads(path.read_text())))
 q=json.loads((root/'reports/inputs.json').read_text());keys=['schema','status','root','contract_sha256','archive_sha256','image_authority_sha256','inventory_sha256','files','providers','target_execution','native_admitted','external_build_origin_authenticated'];q['private_before']['inputs.json']=file_row((json.dumps({k:q[k] for k in keys},indent=2)+'\n').encode());q['private_before']['eigen-inputs.json']=file_row((json.dumps(q['eigen'],indent=2)+'\n').encode());put(root/'reports/inputs.json',q)
 raw=cpu_elf(root);compiled=receipt['compiler_build'];compiled.update(schema='panda-sdk-cg-runpath-build-v3',runpath_contract_sha256=b.CONTRACT_SHA,link_environment=b.build_environment(Path(q['root'])),link_commands={})
 outputs=json.loads((root/'reports/sdk-output-manifest.json').read_text())
 for file,key,member in [('libpandagl.so.data','candidate','lib/libpandagl.so'),('build-libpanda.so.data','build_panda','lib/libpanda.so.1.10')]:
  (root/'candidate'/file).write_bytes(raw);compiled[key+'_sha256']=e.sha(raw);row=next(r for r in outputs if r['path']==member);row.update(nbytes=len(raw),sha256=e.sha(raw));compiled['link_commands'][key]=[b.TOOLS['cxx'],'-shared','-o',compiled[key],'cpu.o','-Wl,-z,defs',b.ORIGIN_ARGUMENT]
 put(root/'reports/sdk-output-manifest.json',outputs);logs=root/'logs';logs.mkdir();log=('\n'.join(shlex.join(cmd) for cmd in compiled['link_commands'].values())+'\n').encode();(logs/'makepanda.log').write_bytes(log);compiled['command']['streams']=dict(stdout=dict(saved_nbytes=len(log),observed_nbytes=len(log),sha256=e.sha(log)));return receipt

class EvidenceTests(unittest.TestCase):
 def test_v3_report_contradictions(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);receipt=success_shaped(root);result=v.validate_build_evidence(receipt,root);self.assertTrue(result['records_coherent']);self.assertFalse(result['native_admitted']);self.assertFalse(result['remote_tools_independently_remeasured'])
   for change in [lambda x:x.update(runpath_contract_sha256='0'*64),lambda x:x.update(schema='panda-sdk-cg-eigen-build-v2'),lambda x:x['link_environment'].update(LDFLAGS='-Wl,-z,defs'),lambda x:x['link_commands']['candidate'].append('-Wl,-rpath,/tmp'),lambda x:x.update(candidate=x['candidate'].replace('runpath-candidate-03','eigen-candidate-02'))]:
    bad=copy.deepcopy(receipt);change(bad['compiler_build'])
    with self.assertRaises(ValueError):v.validate_build_evidence(bad,root)
   mutations=[('inputs',lambda x:x.update(root=x['root'].replace('runpath-candidate-03','eigen-candidate-02'))),('inputs',lambda x:x['eigen'].update(header_files=1)),('inputs',lambda x:x['private_before']['usr/include/eigen3/Eigen/Core'].update(sha256='0'*64)),('tools-after',lambda x:x['files'][b.TOOLS['cc']].update(sha256='0'*64)),('host-before',lambda x:x['/usr/include/stdio.h'].update(sha256='0'*64)),('used-inputs',lambda x:x[0].update(origin='host')),('compile-dependencies',lambda x:x[0]['paths'].append('/outside/unknown.h')),('source-manifest',lambda x:x.update(upstream_revision='0'*40)),('sdk-output-manifest',lambda x:x[0].update(sha256='0'*64))]
   for name,mutate in mutations:
    path=root/'reports'/str(name+'.json');original=path.read_bytes();value=json.loads(original);mutate(value);put(path,value)
    try:
     with self.assertRaises(ValueError,msg=name):v.validate_build_evidence(receipt,root)
    finally:path.write_bytes(original)
   for name in ['candidate/build-libpanda.so.data','candidate/layout-descriptor.data','logs/makepanda.log']:
    path=root/name;original=path.read_bytes();path.write_bytes(original+b'changed')
    try:
     with self.assertRaises(ValueError,msg=name):v.validate_build_evidence(receipt,root)
    finally:path.write_bytes(original)

if __name__=='__main__':unittest.main()
