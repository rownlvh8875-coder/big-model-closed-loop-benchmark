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
 put(root/'reports/sdk-output-manifest.json',outputs);logs=root/'logs';logs.mkdir();log=('\n'.join(shlex.join(cmd) for cmd in compiled['link_commands'].values())+'\n').encode();(logs/'makepanda.log').write_bytes(log);compiled['command']['streams']=dict(stdout=dict(saved_nbytes=len(log),observed_nbytes=len(log),sha256=e.sha(log)))
 work=Path(q['root']).parent;repo=work.parents[3]
 for name in ['tools-before','tools-after']:
  profile=json.loads((root/'reports'/str(name+'.json')).read_text());path=work/'tool-profile.json' if name=='tools-before' else work/'tool-rechecks/3/profile.json';profile['evidence_path']=str(path)
  for index,query in enumerate(profile['queries']):
   folder=path.parent/(path.stem+'-queries')/str(index);query['stdout_path']=str(folder/'stdout.log');query['stderr_path']=str(folder/'stderr.log');query['result']['cwd']=str(repo)
  put(root/'reports'/str(name+'.json'),profile)
 macro=b'#define HAVE_CG 1\n#define HAVE_EIGEN 1\n#define HAVE_X11 1\n#define LINMATH_ALIGN 1\n#define MEMORY_HOOK_ALIGNMENT 16\n#define _GLIBCXX_USE_CXX11_ABI 0\n';effective=json.loads((root/'reports/effective-configuration.json').read_text());effective.update(schema='panda-cg-eigen-effective-config-v2',macro_stdout_sha256=e.sha(macro));put(root/'reports/effective-configuration.json',effective);compiled['effective_configuration']=copy.deepcopy(effective);compiled['layout']['effective_configuration']=copy.deepcopy(effective)
 layout=compiled['layout'];macro_argv=[x for x in layout['command']['argv'][:-2] if x not in ('-c','-MD')]+['-E','-dM'];layout['macro_command']=dict(argv=macro_argv,cwd=str(repo),status='EXITED',returncode=0,owned_group_reaped=True,streams_complete=True,elapsed_seconds=.01,streams={name:dict(saved_nbytes=len(body),observed_nbytes=len(body),sha256=e.sha(body)) for name,body in [('stdout',macro),('stderr',b'')]});layout['command']['streams']={name:dict(saved_nbytes=0,observed_nbytes=0,sha256=e.sha(b'')) for name in ['stdout','stderr']}
 from scripts import panda_sdk_cg_eigen_layout as literal
 measured=literal.verify_pair((root/'candidate/layout-contract.o.data').read_bytes(),(root/'candidate/layout-descriptor.data').read_bytes());put(root/'reports/layout.json',measured);put(root/'reports/gate.json',dict(layout=measured));extraction=literal.extract_literal((root/'candidate/layout-contract.o.data').read_bytes());extraction.pop('raw');layout['extraction']=extraction;put(root/'reports/layout-extraction.json',extraction)
 extra={'work/build/layout-build/compile/command.json':(json.dumps(layout['command'],indent=2)+'\n').encode(),'work/build/layout-build/compile/stdout.log':b'','work/build/layout-build/compile/stderr.log':b'','work/build/layout-build/effective-macros/command.json':(json.dumps(layout['macro_command'],indent=2)+'\n').encode(),'work/build/layout-build/effective-macros/stdout.log':macro,'work/build/layout-build/effective-macros/stderr.log':b''};retained_host(root,receipt,extra);return receipt

def retained_host(root,receipt,extra=None):
 q=json.loads((root/'reports/inputs.json').read_text());work=Path(q['root']).parent;items={}
 for name in ['tools-before','tools-after']:
  profile=json.loads((root/'reports'/str(name+'.json')).read_text());path=Path(profile['evidence_path']);items['work/'+str(path.relative_to(work))]=(json.dumps(profile,indent=2)+'\n').encode()
  for query in profile['queries']:
   for stream in ['stdout','stderr']:items['work/'+str(Path(query[stream+'_path']).relative_to(work))]=query[stream].encode()
   folder=Path(query['stdout_path']).parent;items['work/'+str((folder/'command.json').relative_to(work))]=(json.dumps(query['result'],indent=2)+'\n').encode()
 items.update(extra or {});make=(root/'logs/makepanda.log').read_bytes();rows=[dict(path='work/build/makepanda/stdout.log',observed_nbytes=len(make),saved_nbytes=len(make),truncated=False)];host=bytearray()
 for name,data in sorted(items.items()):host.extend(name.encode()+b'\n'+data);rows.append(dict(path=name,observed_nbytes=len(data),saved_nbytes=len(data),truncated=False))
 (root/'logs/host.log').write_bytes(host);receipt['diagnostics']=dict(streams=rows,truncated=False,omitted_members=[])

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

class ReviewToolEvidenceTests(unittest.TestCase):
 def test_owned_tool_paths_cwd_and_host_records_are_required(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);receipt=success_shaped(root);self.assertTrue(v.validate_build_evidence(receipt,root)['records_coherent'])
   mutations=[lambda p:p.update(evidence_path=p['evidence_path'].replace('runpath-candidate-03','eigen-candidate-02')),lambda p:p['queries'][0].update(stdout_path='/cpu/stdout.log'),lambda p:p['queries'][0].update(stderr_path='/cpu/stderr.log'),lambda p:p['queries'][0]['result'].update(cwd='/old/repo'),lambda p:p['queries'][0]['result'].pop('cwd')]
   for name in ['tools-before','tools-after']:
    path=root/'reports'/str(name+'.json');original=path.read_bytes()
    for mutate in mutations:
     value=json.loads(original);mutate(value);put(path,value)
     try:
      with self.assertRaises(ValueError):v.validate_build_evidence(receipt,root)
     finally:path.write_bytes(original)
   host=root/'logs/host.log';original=host.read_bytes();host.write_bytes(original.replace(b'13.3.0',b'99.0.0',1))
   with self.assertRaises(ValueError):v.validate_build_evidence(receipt,root)
   host.write_bytes(original);bad=copy.deepcopy(receipt);bad['diagnostics']['streams'][1]['saved_nbytes']+=1
   with self.assertRaises(ValueError):v.validate_build_evidence(bad,root)

class ReviewMacroEvidenceTests(unittest.TestCase):
 def test_macro_receipt_bytes_and_all_layout_reports_must_agree(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);receipt=success_shaped(root);self.assertTrue(v.validate_build_evidence(receipt,root)['records_coherent'])
   for label,mutate in [('missing',lambda x:x['layout'].pop('macro_command')),('failed',lambda x:x['layout']['macro_command'].update(returncode=9)),('argv',lambda x:x['layout']['macro_command']['argv'].append('--help')),('hash',lambda x:x['layout']['macro_command']['streams']['stdout'].update(sha256='0'*64)),('nested',lambda x:x['layout']['effective_configuration'].update(vector_alignment=8)),('top',lambda x:x['effective_configuration']['macros'].update(HAVE_EIGEN=None))]:
    with self.subTest(label=label):
     bad=copy.deepcopy(receipt);mutate(bad['compiler_build'])
     with self.assertRaises(ValueError):v.validate_build_evidence(bad,root)
   for name,mutate in [('layout',lambda x:x['offsets'].update(major=0)),('gate',lambda x:x['layout'].update(gsg_size=1)),('effective-configuration',lambda x:x.update(macro_stdout_sha256='0'*64)),('layout-extraction',lambda x:x.update(parent_sha256='0'*64)),('configuration',lambda x:x.update(HAVE_EIGEN=False)),('configuration-delta',lambda x:x.clear())]:
    path=root/'reports'/str(name+'.json');original=path.read_bytes();value=json.loads(original);mutate(value);put(path,value)
    try:
     with self.subTest(report=name),self.assertRaises(ValueError):v.validate_build_evidence(receipt,root)
    finally:path.write_bytes(original)
   host=root/'logs/host.log';host.write_bytes(host.read_bytes().replace(b'#define HAVE_EIGEN 1',b'#define HAVE_EIGEN 0'))
   with self.assertRaises(ValueError):v.validate_build_evidence(receipt,root)
   for name in ['candidate/build-libpanda.so.data','candidate/layout-descriptor.data','logs/makepanda.log']:
    path=root/name;original=path.read_bytes();path.write_bytes(original+b'changed')
    try:
     with self.assertRaises(ValueError,msg=name):v.validate_build_evidence(receipt,root)
    finally:path.write_bytes(original)

if __name__=='__main__':unittest.main()
