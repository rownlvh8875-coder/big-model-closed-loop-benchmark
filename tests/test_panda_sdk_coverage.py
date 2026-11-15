"""Compiler output remains data; no Panda or GL code is loaded."""
from pathlib import Path
import subprocess,tempfile,unittest
try:
    from scripts import panda_sdk_coverage as coverage
except ImportError:coverage=None
ROOT=Path(__file__).resolve().parents[1]
class SelectedCoverageTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(coverage,'compiled-candidate coverage inspector required')
    def test_actual_preprocessor_excludes_inactive_lookup(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'fixture.cxx';p.write_text('#if 0\nget_extension_func("glBindBufferBase");\n#else\nget_extension_func("glHarmless");\n#endif\n')
            r=subprocess.run(['/usr/bin/g++','-E',str(p)],capture_output=True,check=True,timeout=10)
            selected=coverage.select_sources(r.stdout,{'fixture.cxx':str(p)})
            report=coverage.assess_selected(selected,(ROOT/'native/panda_source_dispatch.cxx').read_bytes())
            self.assertEqual(report['lookup_names'],['glHarmless']);self.assertEqual(report['required_safe_count'],1)
    def test_header_basename_cannot_masquerade_as_selected_source(self):
        raw=b'# 1 "source/x.cxx"\nget_extension_func("glGood");\n# 1 "foreign/x.cxx"\nget_extension_func("glBad");\n'
        with self.assertRaisesRegex(ValueError,'source origin'):coverage.select_sources(raw,{'x.cxx':'source/x.cxx'})
    def test_malformed_marker_and_unselected_source_reject(self):
        for raw in (b'# 1 "source/x.cxx"garbage\n',b'# 1 "header.h"\nget_extension_func("glBad");\n',b'\xff'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):coverage.select_sources(raw,{'x.cxx':'source/x.cxx'})
    def test_cap_counts_lookup_names_after_real_routes(self):
        runtime=(ROOT/'native/panda_source_dispatch.cxx').read_bytes()
        def make(n):return {'x.cxx':('\n'.join('get_extension_func("glSafe%d");'%i for i in range(n))+'\nget_extension_func("glBindBuffer");').encode()}
        a=coverage.assess_selected(make(256),runtime);b=coverage.assess_selected(make(257),runtime)
        self.assertEqual((a['required_safe_count'],b['required_safe_count']),(256,257));self.assertNotIn('SAFE_NAME_CAP_EXCEEDED',a['blockers']);self.assertIn('SAFE_NAME_CAP_EXCEEDED',b['blockers'])
    def test_prefix_prohibited_and_computed_lookup_stay_blocked(self):
        a=coverage.assess_selected({'x.cxx':b'get_extension_func("glBindBufferBase"); get_extension_func(variable);'},(ROOT/'native/panda_source_dispatch.cxx').read_bytes())
        self.assertEqual(a['unsupported_prefix_names'],['glBindBufferBase']);self.assertIn('COMPUTED_LOOKUP_REQUIRES_BINDING',a['blockers']);self.assertFalse(a['native_admitted'])
    def test_changed_runtime_cannot_supply_forged_routes(self):
        with self.assertRaisesRegex(ValueError,'runtime pin'):coverage.assess_selected({'x.cxx':b'get_extension_func("glSafe");'},b'PSD_ROUTE("glSafe",0,0,0)')
    def test_compiled_table_is_separate_from_lookups(self):
        raw=b'void *get_extension_func(const char *name) { static struct { const char *name; void *p; } compiled_function_table[] = { {"glTable",(void *)&glTable}, {nullptr,nullptr} }; return do_get_extension_func(name); }\nget_extension_func("glLiteral");'
        a=coverage.assess_selected({'x.cxx':raw},(ROOT/'native/panda_source_dispatch.cxx').read_bytes())
        self.assertEqual(a['compiled_table_names'],['glTable']);self.assertEqual(a['lookup_names'],['glLiteral']);self.assertFalse(a['runtime_paths_observed'])
if __name__=='__main__':unittest.main()
