"""Handwritten CPU ELF DATA only: no fixture library is ever loaded or executed."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from scripts import panda_provider_version_witness as w
from scripts.panda_sdk_link_elf import inspect_elf,available_imports

def ci_fixture():
    source='a'*40;registrations=[dict(event='push',run_id=1),dict(event='pull_request',run_id=2)];proofs=[]
    for registration in registrations:
        rid=registration['run_id'];repository=dict(full_name=w.REPO,id=1447652055)
        run=dict(id=rid,head_sha=source,head_branch=w.BRANCH,event=registration['event'],workflow_id=411705464,path='.github/workflows/ci.yml',run_attempt=1,status='completed',conclusion='success',repository=repository,head_repository=repository)
        jobs=dict(total_count=2,jobs=[dict(id=rid*10+i,name=name,run_id=rid,head_sha=source,head_branch=w.BRANCH,run_attempt=1,status='completed',conclusion='success') for i,name in enumerate(['synthetic-unit','onnx-interface-test'])])
        proofs.append(dict(run=run,jobs=jobs,artifacts=dict(total_count=0,artifacts=[])))
    return source,registrations,proofs

class VersionWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();p=Path(cls.temp.name)
        (p/'value.c').write_text('int value(void){return 7;}\n');(p/'stub.c').write_text('int placeholder(void){return 1;}\n');(p/'use.c').write_text('extern int value(void);int call(void){return value();}\n');(p/'root.c').write_text('int outer(void){return 1;}\n')
        (p/'value.map').write_text('ABI_1 { global: value; local: *; };\n');(p/'stub.map').write_text('ABI_1 { global: placeholder; local: *; };\n')
        base=['/usr/bin/gcc','-nostdlib','-shared','-fPIC']
        commands=[['value.c','-Wl,--version-script=value.map','-Wl,-soname,liblegacy.so','-o','fulllegacy.so'],['value.c','-Wl,--version-script=value.map','-Wl,-soname,libmerged.so','-o','merged.so'],['use.c','-L.','-Wl,--no-as-needed','-l:fulllegacy.so','-Wl,-soname,libconsumer.so','-o','consumer.so'],['stub.c','-Wl,--version-script=stub.map','-L.','-Wl,--no-as-needed','-l:merged.so','-Wl,-soname,liblegacy.so','-o','stub.so'],['root.c','-L.','-Wl,--no-as-needed','-l:consumer.so','-o','root.so']]
        for arguments in commands:subprocess.run(base+arguments,cwd=p,check=True,capture_output=True,timeout=20,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
        cls.root='/cpu/root.so';cls.consumer='/cpu/libconsumer.so';cls.stub='/cpu/liblegacy.so';cls.target='/cpu/libmerged.so'
        cls.nodes={logical:dict(inspect_elf((p/name).read_bytes()),path=logical) for logical,name in [(cls.root,'root.so'),(cls.consumer,'consumer.so'),(cls.stub,'stub.so'),(cls.target,'merged.so')]}
        cls.edges=[dict(requester=a,needed=b,selected=c) for a,b,c in [(cls.root,'libconsumer.so',cls.consumer),(cls.consumer,'liblegacy.so',cls.stub),(cls.stub,'libmerged.so',cls.target)]]
        def pin(path):
            m=cls.nodes[path];return dict(path=path,soname=m['soname'],sha256=m['elf_sha256'],nbytes=m['nbytes'])
        cls.policy=dict(root=pin(cls.root),target=pin(cls.target),aliases={'liblegacy.so':dict(**pin(cls.stub),versions=['ABI_1'])},expected_legacy_missing=1,expected_legacy_blocks=1)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def data(self):return copy.deepcopy(self.nodes),copy.deepcopy(self.edges),copy.deepcopy(self.policy)
    def cannot_explain(self,nodes,edges,policy):
        try:report=w.audit_graph(nodes,edges,policy)
        except ValueError:return
        self.assertFalse(report['diagnostic_witnesses_complete'])
    def test_real_versioned_stub_and_merged_export_explain_without_changing_legacy(self):
        before=available_imports(self.nodes[self.consumer],list(self.nodes.values()));self.assertEqual([r['name'] for r in before['missing']],['value'])
        report=w.audit_graph(*self.data());self.assertTrue(report['diagnostic_witnesses_complete']);self.assertEqual((report['legacy_missing_count'],report['legacy_block_count'],report['witness_count'],report['unexplained_count']),(1,1,1,0));self.assertFalse(report['legacy_provider_blocks_removed'])
        row=report['provider_audits'][self.consumer]['witnesses'][0];self.assertEqual(row['import']['name'],'value');self.assertEqual(row['declared_library']['path'],self.stub);self.assertEqual(row['target']['path'],self.target);self.assertTrue(row['target']['symbol_indices']);self.assertEqual(available_imports(self.nodes[self.consumer],list(self.nodes.values())),before)
        for key in w.FORBIDDEN:self.assertIs(report[key],False)
        self.assertEqual(report,w.audit_graph(json.loads(json.dumps(self.nodes)),self.edges,self.policy))
    def test_both_declared_and_target_version_definitions_are_required(self):
        for path in [self.stub,self.target]:
            nodes,edges,policy=self.data();nodes[path]['version_definitions']={k:v for k,v in nodes[path]['version_definitions'].items() if v!='ABI_1'}
            with self.subTest(path=path):self.cannot_explain(nodes,edges,policy)
        nodes,edges,policy=self.data();policy['aliases']['liblegacy.so']['versions']=['ABI_2'];self.cannot_explain(nodes,edges,policy)
    def test_wrong_names_versions_ifunc_types_and_unversioned_import_do_not_explain(self):
        changes=[lambda n:n[self.target]['exports'][next(i for i,s in enumerate(n[self.target]['exports']) if s['name']=='value')].update(name='other'),lambda n:n[self.target]['exports'][next(i for i,s in enumerate(n[self.target]['exports']) if s['name']=='value')].update(version='ABI_2'),lambda n:n[self.target]['exports'][next(i for i,s in enumerate(n[self.target]['exports']) if s['name']=='value')].update(symbol_type=10),lambda n:n[self.target]['exports'][next(i for i,s in enumerate(n[self.target]['exports']) if s['name']=='value')].update(symbol_type=1),lambda n:n[self.consumer]['imports'][0].update(version=None,version_library=None),lambda n:n[self.consumer]['imports'][0].update(symbol_type=True)]
        for change in changes:
            nodes,edges,policy=self.data();change(nodes)
            with self.subTest(change=change):self.cannot_explain(nodes,edges,policy)
    def test_explicit_version_can_use_nondefault_export_but_weak_stays_separate(self):
        nodes,edges,policy=self.data()
        for row in nodes[self.target]['exports']:
            if row['name']=='value':row['default_version']=False
        self.assertTrue(w.audit_graph(nodes,edges,policy)['diagnostic_witnesses_complete'])
        nodes[self.consumer]['imports'][0]['binding']=2;policy.update(expected_legacy_missing=0,expected_legacy_blocks=0)
        report=w.audit_graph(nodes,edges,policy);self.assertEqual(report['legacy_missing_count'],0);self.assertEqual(report['witness_count'],0);self.assertEqual(len(report['provider_audits'][self.consumer]['weak_unresolved']),1);self.assertFalse(report['native_admitted'])
    def test_missing_wrong_duplicate_and_disconnected_edges_reject(self):
        for mode in ['missing','wrong','duplicate','disconnected','unrelated']:
            nodes,edges,policy=self.data()
            if mode=='missing':edges.pop()
            if mode=='wrong':edges[-1]['selected']=self.consumer
            if mode=='duplicate':edges.append(copy.deepcopy(edges[-1]))
            if mode=='disconnected':nodes['/cpu/extra.so']=dict(copy.deepcopy(nodes[self.target]),path='/cpu/extra.so')
            if mode=='unrelated':edges[-1]['selected']=self.consumer;nodes[self.stub]['needed']=['libconsumer.so'];edges[-1]['needed']='libconsumer.so'
            with self.subTest(mode=mode):self.cannot_explain(nodes,edges,policy)
    def test_wrong_pins_population_and_unsupported_features_do_not_qualify(self):
        for field,value in [('sha256','0'*64),('soname','unrelated.so'),('nbytes',True),('path','/cpu/other.so')]:
            nodes,edges,policy=self.data();policy['target'][field]=value
            with self.subTest(field=field):self.cannot_explain(nodes,edges,policy)
        nodes,edges,policy=self.data();policy['expected_legacy_missing']=2;self.cannot_explain(nodes,edges,policy)
        nodes,edges,policy=self.data();nodes[self.root]['unsupported_features']=['COPY_RELOCATIONS'];self.cannot_explain(nodes,edges,policy)
    def test_table_collisions_scalar_types_and_graph_bounds_reject(self):
        nodes,edges,policy=self.data();table=nodes[self.consumer]['version_needs'];key=next(iter(table));table[str(key)]=copy.deepcopy(table[key]);self.cannot_explain(nodes,edges,policy)
        for field,value in [('symbol_index',True),('default_version',1),('binding',1.0)]:
            nodes,edges,policy=self.data();nodes[self.consumer]['imports'][0][field]=value
            with self.subTest(field=field):self.cannot_explain(nodes,edges,policy)
        nodes,edges,policy=self.data()
        for i in range(65):nodes['/cpu/extra'+str(i)]=dict(nodes[self.root],path='/cpu/extra'+str(i))
        self.cannot_explain(nodes,edges,policy)
    def test_exact_own_ci_branch_repository_jobs_and_attempt_are_bound(self):
        source,registrations,proofs=ci_fixture();w.validate_ci(source,registrations,proofs)
        changes=[lambda p:p[0]['run'].update(head_branch='feature/panda-sdk-cg-runpath-json-audit-v1'),lambda p:p[0]['run'].update(run_attempt=True),lambda p:p[0]['run']['repository'].update(id=1),lambda p:p[0]['jobs']['jobs'][0].update(head_sha='b'*40),lambda p:p[0]['jobs']['jobs'][0].update(run_attempt=2),lambda p:p[0].update(artifacts=dict(total_count=1,artifacts=[{}]))]
        for change in changes:
            bad=copy.deepcopy(proofs);change(bad)
            with self.subTest(change=change),self.assertRaises(ValueError):w.validate_ci(source,registrations,bad)

if __name__=='__main__':unittest.main()
