"""Native execution is confined to handwritten nostdlib CPU fixtures, never SDK."""
import copy,json,os,shutil,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import panda_loader_cpu_fixture as f
from tests.test_panda_provider_version_witness import ci_fixture as previous_ci

HOST_LOADER=Path('/lib64/ld-linux-x86-64.so.2').resolve()

class CpuLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name);cls.fixture=cls.root/'fixture';cls.manifest=f.build_fixture(cls.fixture);cls.report=f.run_cases(HOST_LOADER,cls.fixture,cls.manifest,cls.root/'host-only-probes')
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_real_host_loader_observes_two_version_obligations_and_nondefault_export(self):
        r=self.report;self.assertEqual(r['status'],'FOUR_CPU_LOADER_VERSION_CASES_OBSERVED_NOT_SDK_RUNTIME');self.assertEqual((r['loader_start_attempts'],r['loader_invocations'],r['verified_fixture_entries'],r['controlled_loader_failures']),(4,4,2,2));self.assertFalse(r['sdk_target_execution']);self.assertEqual(r['scientific_native_runs'],0)
        rows={row['case']:row for row in r['cases']};self.assertEqual(rows['same_library']['command']['returncode'],7);self.assertEqual(rows['merged_nondefault']['command']['returncode'],7);self.assertEqual(rows['same_library']['observation']['bound_provider'],'libstage7_cpu_legacy.so');self.assertEqual(rows['merged_nondefault']['observation']['bound_provider'],'libstage7_cpu_merged.so')
        self.assertEqual(rows['missing_library_version']['observation']['failure_kind'],'DECLARED_LIBRARY_VERSION_MISSING');self.assertEqual(rows['wrong_symbol_version']['observation']['failure_kind'],'EXPLICIT_SYMBOL_VERSION_MISSING')
        for row in r['cases']:self.assertTrue(row['command']['streams_complete']);self.assertTrue(row['command']['owned_group_reaped'])
        self.assertFalse(self.manifest['cases']['merged_nondefault']['target_default_version']);f.validate_fixture(self.fixture,self.manifest)
    def test_sanitized_environment_resists_loader_and_compiler_injection(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,dict(LD_PRELOAD='/no/such/preload.so',LD_AUDIT='/no/such/audit.so',LD_LIBRARY_PATH='/no/such/lib',GCC_EXEC_PREFIX='/no/such/compiler/',CFLAGS='invalid-option',CC='/bin/false')):
            root=Path(d);manifest=f.build_fixture(root/'fixture');r=f.run_cases(HOST_LOADER,root/'fixture',manifest,root/'probes');self.assertEqual(r['loader_invocations'],4);self.assertEqual(r['status'],'FOUR_CPU_LOADER_VERSION_CASES_OBSERVED_NOT_SDK_RUNTIME')
            for row in r['cases']:
                trace=(root/'probes'/row['case']/'stderr.log').read_text();self.assertNotIn('/no/such',trace)
    def test_extra_bytes_symlink_and_parent_alias_are_rejected_before_execution(self):
        for mode in ['bytes','extra','file-link','parent-link']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=Path(d);fixture=root/'fixture';manifest=f.build_fixture(fixture);path=fixture/'cases/same_library/root.so'
                if mode=='bytes':raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
                if mode=='extra':(fixture/'cases/same_library/extra.so').write_bytes(b'bad')
                if mode=='file-link':path.rename(root/'saved');path.symlink_to(root/'saved')
                if mode=='parent-link':(fixture/'cases').rename(root/'saved-dir');(fixture/'cases').symlink_to(root/'saved-dir',target_is_directory=True)
                with self.assertRaises(ValueError):f.validate_fixture(fixture,manifest)
                r=f.run_cases(HOST_LOADER,fixture,manifest,root/'probes');self.assertEqual(r['status'],'FAILED');self.assertEqual(r['loader_start_attempts'],0);self.assertEqual(r['loader_invocations'],0)
    def test_even_rehashed_changed_entry_code_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            fixture=Path(d)/'fixture';manifest=f.build_fixture(fixture)
            for name in manifest['files']:
                if name.endswith('/root.so'):
                    p=fixture/name;raw=p.read_bytes();needle=bytes.fromhex('89c7b83c0000000f05');self.assertIn(needle,raw);raw=raw.replace(needle,bytes.fromhex('89c7b83c0000000f0b'));p.write_bytes(raw);manifest['files'][name]=dict(nbytes=len(raw),sha256=f.sha(raw))
            for case,row in manifest['cases'].items():row['files']['root.so']=manifest['files']['cases/'+case+'/root.so']
            (fixture/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
            with self.assertRaises(ValueError):f.validate_fixture(fixture,manifest)
    def _replace_role(self,fixture,manifest,role,raw):
        record=dict(nbytes=len(raw),sha256=f.sha(raw))
        (fixture/'build'/role).write_bytes(raw);manifest['files']['build/'+role]=record
        for case,layout in f.LAYOUT.items():
            for name,source in layout.items():
                if source==role:
                    (fixture/'cases'/case/name).write_bytes(raw);manifest['files']['cases/'+case+'/'+name]=record;manifest['cases'][case]['files'][name]=record
        (fixture/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    def test_symbol_zero_and_packed_relocations_are_rejected_as_data_before_spawn(self):
        normal='int impl(void){return 7;} __asm__(".symver impl,cpu_probe_value@CPU_ABI_1");\n'
        variants={'relative':normal+'void *retained_pointer=(void*)impl;\n',
                  'irelative':normal+'typedef int(*Fn)(void);static int resolved(void){return 13;}static Fn resolver(void){return resolved;}static int hidden(void) __attribute__((ifunc("resolver")));Fn retained_pointer=hidden;\n',
                  'relr':normal+'void *retained_pointer=(void*)impl;\n',
                  'unparsed-relative-count':normal}
        for kind,source in variants.items():
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/'target.c').write_text(source);(root/'v.map').write_text('CPU_ABI_1 {global:cpu_probe_value;local:*;};\n')
                argv=['/usr/bin/gcc','-nostdlib','-shared','-fPIC','-O2','-fcf-protection=none','-Wl,--version-script=v.map','-Wl,-soname,libstage7_cpu_merged.so','target.c','-o','target.so']
                if kind=='relr':argv.append('-Wl,-z,pack-relative-relocs')
                if kind=='unparsed-relative-count':argv.append('-Wl,--spare-dynamic-tags=6')
                subprocess.run(argv,cwd=root,check=True,capture_output=True,timeout=20,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
                raw=(root/'target.so').read_bytes()
                if kind=='unparsed-relative-count':
                    raw=bytearray(raw);h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);ph=[struct.unpack_from('<IIQQQQQQ',raw,h[5]+56*i) for i in range(h[10])];dyn=next(p for p in ph if p[0]==2);at=next(i for i in range(dyn[2],dyn[2]+dyn[5],16) if struct.unpack_from('<q',raw,i)[0]==0);self.assertLessEqual(at+80,dyn[2]+dyn[5])
                    for index,(tag,value) in enumerate([(7,0),(8,0),(9,24),(0x6ffffff9,1),(0,0)]):struct.pack_into('<qQ',raw,at+index*16,tag,value)
                    raw=bytes(raw)
                meta=f.inspect_elf(raw);self.assertEqual(meta['relocation_kinds'],[]);self.assertEqual(meta['ifunc_exports'],0)
                if kind not in ['relr','unparsed-relative-count']:self.assertGreater(meta['relocation_count'],0)
                with self.assertRaises(ValueError):f._validate_binary(raw,'target1.so')
                # This line is reached only after the data-only guard rejected it.
                fixture=root/'fixture';manifest=f.build_fixture(fixture);self._replace_role(fixture,manifest,'target1.so',raw);r=f.run_cases(HOST_LOADER,fixture,manifest,root/'blocked');self.assertEqual(r['loader_start_attempts'],0);self.assertEqual(r['status'],'FAILED')
    def test_mapping_aliases_and_nonwritable_got_are_rejected_as_data_before_spawn(self):
        original=(self.fixture/'build/root.so').read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',original);records=[list(struct.unpack_from('<IIQQQQQQ',original,h[5]+56*i)) for i in range(h[10])]
        meta=f.inspect_elf(original);entry=next(s for s in meta['exports'] if s['name']=='_start')['value']
        def offset(va):
            p=next(p for p in records if p[0]==1 and p[3]<=va< p[3]+p[5]);return p[2]+va-p[3]
        for kind in ['rounded-alias','incongruent','writable-code','executable-got']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                raw=bytearray(original);ph=copy.deepcopy(records)
                if kind in ['rounded-alias','incongruent']:
                    slot=next(i for i,p in enumerate(ph) if p[0]==0x6474e551);va=(entry&~4095)+0xf00;file_offset=0x2f00
                    self.assertLess(file_offset+9,len(raw));ph[slot]=[1,5,file_offset+(kind=='incongruent'),va,va,8,8,1 if kind=='incongruent' else 4096]
                    slots=[i for i,p in enumerate(ph) if p[0]==1];ordered=sorted((ph[i] for i in slots),key=lambda p:p[3])
                    for i,p in zip(slots,ordered):ph[i]=p
                elif kind=='writable-code':
                    next(p for p in ph if p[0]==1 and p[3]<=entry<p[3]+p[5])[1]|=2
                else:
                    dyn=next(p for p in ph if p[0]==2);tags={}
                    for at in range(dyn[2],dyn[2]+dyn[5],16):
                        tag,value=struct.unpack_from('<qQ',raw,at)
                        if tag==0:break
                        tags[tag]=value
                    body=offset(entry);target=entry+9+struct.unpack_from('<i',raw,body+5)[0];struct.pack_into('<i',raw,offset(target)+2,entry-(target+6));struct.pack_into('<Q',raw,offset(tags[23]),entry)
                for i,p in enumerate(ph):struct.pack_into('<IIQQQQQQ',raw,h[5]+56*i,*p)
                f.inspect_elf(bytes(raw))  # Frozen byte-span parser accepts this data.
                with self.assertRaises(ValueError):f._validate_binary(bytes(raw),'root.so')
                fixture=Path(d)/'fixture';manifest=f.build_fixture(fixture);self._replace_role(fixture,manifest,'root.so',bytes(raw));r=f.run_cases(HOST_LOADER,fixture,manifest,Path(d)/'blocked');self.assertEqual(r['loader_start_attempts'],0);self.assertEqual(r['status'],'FAILED')
    def test_trace_status_stream_and_ownership_contradictions_reject(self):
        for row in self.report['cases']:
            trace=(self.root/'host-only-probes'/row['case']/'stderr.log').read_text();command=row['command'];paths=f.case_paths(self.fixture,row['case']);f.validate_observation(row['case'],command,trace,paths)
            for field,value in [('streams_complete',False),('owned_group_reaped',False),('status','TIMEOUT'),('returncode',0)]:
                bad=copy.deepcopy(command);bad[field]=value
                with self.subTest(case=row['case'],field=field),self.assertRaises(ValueError):f.validate_observation(row['case'],bad,trace,paths)
            with self.assertRaises(ValueError):f.validate_observation(row['case'],command,'',paths)
        row=self.report['cases'][1];trace=(self.root/'host-only-probes'/row['case']/'stderr.log').read_text().replace('libstage7_cpu_merged.so','unrelated.so');bad=copy.deepcopy(row['command']);bad['streams']['stderr'].update(sha256=f.sha(trace.encode()),observed_nbytes=len(trace.encode()),saved_nbytes=len(trace.encode()))
        with self.assertRaises(ValueError):f.validate_observation(row['case'],bad,trace,f.case_paths(self.fixture,row['case']))
    def test_late_fixture_drift_preserves_one_observed_call_without_retry(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);fixture=root/'fixture';manifest=f.build_fixture(fixture);real=f.run_owned
            def call_and_poison(*args,**kwargs):
                result=real(*args,**kwargs);p=fixture/'cases/merged_nondefault/root.so';raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw);return result
            with patch.object(f,'run_owned',side_effect=call_and_poison):r=f.run_cases(HOST_LOADER,fixture,manifest,root/'probes')
            self.assertEqual(r['status'],'FAILED');self.assertEqual((r['loader_start_attempts'],r['loader_invocations']),(1,1));self.assertEqual(len(r['cases']),1);self.assertEqual(r,json.loads((root/'probes/ledger.json').read_text()))
    def test_wrong_loader_and_reused_probe_output_never_start_a_case(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'probes';r=f.run_cases(Path('/usr/bin/true'),self.fixture,self.manifest,out);self.assertEqual(r['status'],'FAILED');self.assertEqual(r['loader_start_attempts'],0)
            with self.assertRaises(ValueError):f.run_cases(HOST_LOADER,self.fixture,self.manifest,out)
    def test_write_failure_after_real_call_retains_parseable_attempt_bounds(self):
        code="""
import json,resource,signal,sys
from pathlib import Path
from unittest.mock import patch
from scripts import panda_loader_cpu_fixture as f
root=Path(sys.argv[1]);fixture=root/'fixture';manifest=f.build_fixture(fixture);real=f.run_owned
signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
def actual_call_then_block_writes(*args,**kwargs):
    result=real(*args,**kwargs)
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,resource.getrlimit(resource.RLIMIT_FSIZE)[1]))
    return result
with patch.object(f,'run_owned',side_effect=actual_call_then_block_writes):r=f.run_cases(Path('/lib64/ld-linux-x86-64.so.2').resolve(),fixture,manifest,root/'probes')
saved=json.loads((root/'probes/ledger.json').read_text())
assert r['status']==saved['status']=='FAILED'
assert r['loader_invocations']==1 and saved['loader_start_attempts']==1
assert saved['loader_invocations'] is None and saved['loader_invocations_lower_bound']==0 and saved['loader_invocations_upper_bound']==1
"""
        with tempfile.TemporaryDirectory() as d:
            r=subprocess.run([sys.executable,'-B','-c',code,d],cwd=f.ROOT,capture_output=True,text=True,timeout=30);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_exact_new_source_ci_namespace_is_required(self):
        source,registrations,proofs=previous_ci()
        for proof in proofs:
            proof['run']['head_branch']=f.BRANCH
            for job in proof['jobs']['jobs']:job['head_branch']=f.BRANCH
        f.validate_ci(source,registrations,proofs);proofs[0]['run']['head_branch']='feature/panda-provider-version-witness-v1'
        with self.assertRaises(ValueError):f.validate_ci(source,registrations,proofs)

if __name__=='__main__':unittest.main()
