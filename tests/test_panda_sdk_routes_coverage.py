from pathlib import Path
import copy,json,tempfile,unittest
try:
    from scripts import panda_sdk_routes_coverage as coverage
except ImportError:coverage=None
ROOT=Path(__file__).resolve().parents[1]
class RoutesCoverageTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(coverage,'new candidate explicit-name qualification required')
    def sources(self):
        p=ROOT/'docs/evidence/panda-sdk-integration-01/after-fix/joint/coverage'
        return {n:(p/(n+'.selected')).read_bytes() for n in coverage.SOURCE_SHA}
    def test_actual_selected_sources_have_eighteen_routes_and_explicit252(self):
        r=coverage.qualify_selected(self.sources(),(ROOT/'native/panda_sdk_routes_v2/panda_source_dispatch.cxx').read_bytes(),coverage.name_profile())
        self.assertEqual((r['lookup_count'],len(r['routed_lookup_names']),r['safe_name_count'],r['safe_cap']),(270,18,252,256));self.assertTrue(r['all_selected_names_classified']);self.assertTrue(r['computed_names_statically_closed']);self.assertEqual(r['compiled_table_names'],[]);self.assertFalse(r['runtime_resolver_origins_qualified']);self.assertFalse(r['native_admitted'])
    def test_unknown_and_unsafe_names_cannot_enter_safe_profile(self):
        a=coverage.assess_names(['glBindBufferBase','glAllowed','glUnknown'],['glBindBufferBase'],['glAllowed']);self.assertEqual(a['unclassified_names'],['glUnknown'])
        with self.assertRaises(ValueError):coverage.assess_names(['glPixelStoref'],[],['glPixelStoref'])
    def test_safe256_boundary_still_applies_after_routes(self):
        names=['glSafe%d'%i for i in range(257)];r=coverage.assess_names(names[:256]+['glBindBufferBase'],['glBindBufferBase'],names[:256]);self.assertEqual(r['safe_name_count'],256)
        with self.assertRaises(ValueError):coverage.assess_names(names,[],names)
    def test_changed_computed_forwarding_and_old_runtime_reject(self):
        s=self.sources();s['glxGraphicsStateGuardian.cxx']=s['glxGraphicsStateGuardian.cxx'].replace(b'get_system_func(funcName)',b'get_system_func(otherName)')
        with self.assertRaisesRegex(ValueError,'selected source pin'):coverage.qualify_selected(s,(ROOT/'native/panda_sdk_routes_v2/panda_source_dispatch.cxx').read_bytes(),coverage.name_profile())
        with self.assertRaisesRegex(ValueError,'runtime pin'):coverage.qualify_selected(self.sources(),(ROOT/'native/panda_source_dispatch.cxx').read_bytes(),coverage.name_profile())
    def test_changed_explicit_name_document_and_existing_output_reject(self):
        p=coverage.name_profile();p=copy.deepcopy(p);p['safe_names'].append(dict(name='glUnknown',category='query_debug'))
        with self.assertRaisesRegex(ValueError,'profile'):coverage.qualify_selected(self.sources(),(ROOT/'native/panda_sdk_routes_v2/panda_source_dispatch.cxx').read_bytes(),p)
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);(out/'keep').write_bytes(b'prior')
            with self.assertRaises(ValueError):coverage.audit_build(out,out)
            self.assertEqual((out/'keep').read_bytes(),b'prior')
    def test_preprocessing_recorded_md_command_cannot_write_dependencies(self):
        from scripts.panda_cache_adapter_cpu import cpu_environment
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'source.cxx';source.write_text('int owned = 7;\n')
            raw,record=coverage.preprocess_recorded(['/usr/bin/g++','-MD','-c','-o',str(root/'owned.o'),str(source)],root,cpu_environment(),root/'inspection')
            self.assertIn(b'int owned',raw);self.assertEqual(list(root.glob('*.d')),[]);self.assertFalse((root/'owned.o').exists());self.assertEqual(record['returncode'],0)
if __name__=='__main__':unittest.main()
