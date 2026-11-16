import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from scripts import panda_sdk_cg_runpath_json as j
from scripts import accept_panda_sdk_cg_runpath as old
from scripts.panda_sdk_link_elf import inspect_elf

def gate(metadata):
    result=dict(schema='panda-sdk-cg-runpath-static-gate-v3',status='CG_EIGEN_RUNPATH_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME',candidate_sha256='a'*64,candidate_nbytes=1,offsets=dict(major=1672,minor=1676,vendor=1648),layout=dict(size=1),vtable_nbytes=1024,runpath=dict(candidate_runpath='$ORIGIN'),reasons=[],selected_layout_match=True,unknown_wheel_class_sizes=True,provider_audit=dict(root_strong_symbols_available=True,missing=[],weak_unresolved=[],provider_records={'/image/libfixture.so':dict(path='/image/libfixture.so',nbytes=1,sha256='b'*64,data_path='/producer/data',native_admitted=False)},provider_audits={'/image/libfixture.so':dict(missing=['retained'])}),loader_metadata=metadata)
    for key in ['full_object_abi_qualified','full_dependency_closure_qualified','runtime_mapping_qualified','previous_abort_fixed','candidate_installed','native_admitted','stage7_complete','external_build_origin_authenticated']:result[key]=False
    return result

class JsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();root=Path(cls.temp.name)
        (root/'provider.c').write_text('int provide(void){return 7;}\n');(root/'consumer.c').write_text('extern int provide(void);int consume(void){return provide();}\n');(root/'version.map').write_text('ABI_1 { global: provide; local: *; };\n')
        for argv in [['/usr/bin/gcc','-nostdlib','-shared','-fPIC','provider.c','-Wl,--version-script=version.map','-Wl,-soname,libfixture.so','-o','libfixture.so'],['/usr/bin/gcc','-nostdlib','-shared','-fPIC','consumer.c','-L.','-lfixture','-o','consumer.so']]:subprocess.run(argv,cwd=root,check=True,capture_output=True)
        cls.metadata={'root':inspect_elf((root/'consumer.so').read_bytes()),'provider':inspect_elf((root/'libfixture.so').read_bytes())}
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_real_version_table_json_roundtrip_fixes_only_new_receiver(self):
        self.assertTrue(self.metadata['root']['version_needs']);self.assertIs(type(next(iter(self.metadata['root']['version_needs']))),int)
        recomputed=gate(copy.deepcopy(self.metadata));claimed=json.loads(json.dumps(recomputed));recomputed['provider_audit']['provider_records']['/image/libfixture.so']['data_path']='/consumer/data'
        with self.assertRaises(ValueError):old.validate_reported_gate(claimed,recomputed,claimed['provider_audit'],claimed['loader_metadata'])
        j.validate_reported_gate(claimed,recomputed,claimed['provider_audit'],claimed['loader_metadata']);self.assertEqual(j.canonical_metadata(self.metadata),j.canonical_metadata(json.loads(json.dumps(self.metadata))))
    def test_semantic_changes_are_not_normalized(self):
        recomputed=gate(copy.deepcopy(self.metadata));claimed=json.loads(json.dumps(recomputed));key=next(iter(claimed['loader_metadata']['root']['version_needs']))
        changes=[lambda r:r['loader_metadata']['root']['version_needs'][key].update(name='ABI_2'),lambda r:r['loader_metadata']['root']['version_needs'][key].update(library='forged.so'),lambda r:r['loader_metadata']['root'].update(data_path='/hidden/change'),lambda r:r['provider_audit']['provider_audits']['/image/libfixture.so'].update(missing=[]),lambda r:r['provider_audit'].update(root_strong_symbols_available=False),lambda r:r['offsets'].update(major=0),lambda r:r['runpath'].update(candidate_runpath='/tmp')]
        for change in changes:
            with self.subTest(change=change):
                bad=copy.deepcopy(claimed);change(bad)
                with self.assertRaises(ValueError):j.validate_reported_gate(bad,recomputed,bad['provider_audit'],bad['loader_metadata'])
    def test_scalar_types_and_list_order_remain_significant(self):
        for left,right in [(1,True),(1,1.0),([1,2],[2,1]),(None,False)]:
            actual=gate({'root':{'ordinary':left}});claimed=json.loads(json.dumps(actual));claimed['loader_metadata']['root']['ordinary']=right
            with self.assertRaises(ValueError):j.validate_reported_gate(claimed,actual,claimed['provider_audit'],claimed['loader_metadata'])
    def test_version_index_types_range_and_collisions(self):
        for key in [True,-1,1.0,'01','-1','32768',None]:
            with self.subTest(key=key),self.assertRaises(ValueError):j.canonical_metadata({'root':{'version_needs':{key:{'name':'ABI_1'}}}})
        with self.assertRaises(ValueError):j.canonical_metadata({'root':{'version_needs':{1:{'name':'a'},'1':{'name':'a'}}}})
        self.assertEqual(j.canonical_metadata({'root':{'version_definitions':{0:'base',32767:'last'}}})['root']['version_definitions'],{'0':'base','32767':'last'})
        with self.assertRaises(ValueError):j.canonical_metadata({'root':{'ordinary':{1:'not a version key'}}})
    def test_scoped_location_exception_cannot_hide_other_fields(self):
        actual=gate({});claimed=json.loads(json.dumps(actual));claimed['provider_audit']['provider_records']['/image/libfixture.so']['data_path']='/another/location';j.validate_reported_gate(claimed,actual,claimed['provider_audit'],claimed['loader_metadata'])
        for value in ['relative','/bad/../path',None,1]:
            bad=copy.deepcopy(claimed);bad['provider_audit']['provider_records']['/image/libfixture.so']['data_path']=value
            with self.assertRaises(ValueError):j.validate_reported_gate(bad,actual,bad['provider_audit'],bad['loader_metadata'])
        actual['provider_audit']['provider_audits']['data_path']='/a';claimed=json.loads(json.dumps(actual));claimed['provider_audit']['provider_audits']['data_path']='/b'
        with self.assertRaises(ValueError):j.validate_reported_gate(claimed,actual,claimed['provider_audit'],claimed['loader_metadata'])
    def test_bounded_and_supported_json_only(self):
        for value in [float('nan'),float('inf'),set(),(1,2),'x'*4097,'é'*2049]:
            with self.subTest(kind=type(value).__name__),self.assertRaises(ValueError):j.canonical_metadata({'root':{'value':value}})
        deep={};cursor=deep
        for _ in range(65):cursor['next']={};cursor=cursor['next']
        with self.assertRaises(ValueError):j.canonical_metadata({'root':deep})
        with self.assertRaises(ValueError):j.canonical_metadata({'root':{'values':[None]*1000001}})
        with self.assertRaises(ValueError):j.parse(b'{"version_needs":{"1":{},"1":{}}}')
    def test_no_matching_claim_can_grant_runtime_authority(self):
        for key in ['native_admitted','stage7_complete','full_object_abi_qualified','full_dependency_closure_qualified','previous_abort_fixed','candidate_installed','runtime_mapping_qualified']:
            actual=gate({});actual[key]=True;claimed=copy.deepcopy(actual)
            with self.assertRaises(ValueError):j.validate_reported_gate(claimed,actual,claimed['provider_audit'],claimed['loader_metadata'])
    def test_own_source_ci_uses_distinct_branch_and_attempt(self):
        source='a'*40;registrations=[dict(event='push',run_id=1),dict(event='pull_request',run_id=2)];proofs=[]
        for item in registrations:
            run=dict(id=item['run_id'],head_sha=source,head_branch=j.SOURCE_BRANCH,event=item['event'],workflow_id=411705464,path='.github/workflows/ci.yml',run_attempt=1,status='completed',conclusion='success',repository=dict(full_name=j.REPO))
            jobs=dict(total_count=2,jobs=[dict(name=name,run_id=item['run_id'],status='completed',conclusion='success') for name in ['synthetic-unit','onnx-interface-test']]);proofs.append(dict(run=run,jobs=jobs,artifacts=dict(total_count=0,artifacts=[])))
        j.validate_audit_ci(source,registrations,proofs)
        for field,value in [('head_branch','feature/panda-sdk-cg-runpath-candidate-v3'),('run_attempt',True),('run_attempt',2),('head_sha','b'*40)]:
            bad=copy.deepcopy(proofs);bad[0]['run'][field]=value
            with self.assertRaises(ValueError):j.validate_audit_ci(source,registrations,bad)

if __name__=='__main__':unittest.main()
