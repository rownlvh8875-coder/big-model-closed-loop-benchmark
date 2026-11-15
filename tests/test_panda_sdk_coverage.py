"""Compiler output remains data; no Panda or GL code is loaded."""
from pathlib import Path
import hashlib,subprocess,tempfile,unittest
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
    def test_compile_output_binding_ignores_link_input_but_rejects_changed_flags(self):
        cmd=['/usr/bin/g++','-c','-o','/tmp/a.o','-O2','a.cxx']
        log='/usr/bin/g++ -c -o /tmp/a.o -O2 a.cxx\n/usr/bin/g++ -shared -o /tmp/liba.so /tmp/a.o\n'
        coverage.verify_commands(log,[cmd])
        with self.assertRaisesRegex(ValueError,'compile command'):coverage.verify_commands(log.replace('-O2','-O0'),[cmd])
    def test_tab_and_indented_markers_cannot_contaminate_selected_source(self):
        for marker in ('#\t1 "foreign/x.cxx"',' # 1 "foreign/x.cxx"','#1 "foreign/x.cxx"','\t# 1 "foreign/x.cxx"'):
            raw=('# 1 "source/x.cxx"\nget_extension_func("glGood");\n'+marker+'\nget_extension_func("glBad");\n').encode()
            with self.subTest(marker=marker),self.assertRaises(ValueError):coverage.select_sources(raw,{'x.cxx':'source/x.cxx'})
    def tool_profile(self,directory):
        driver=directory/'driver';child=directory/'cc1plus';driver.write_bytes(b'unchanged-driver');child.write_bytes(b'known-child')
        return dict(driver_path=str(driver),driver_realpath=str(driver),driver_sha256=hashlib.sha256(b'unchanged-driver').hexdigest(),cc1plus_path=str(child),cc1plus_sha256=hashlib.sha256(b'known-child').hexdigest(),selection_absent_paths=[str(directory/'specs')])
    def test_child_tool_mutation_rejects_while_driver_is_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            profile=self.tool_profile(Path(t));coverage.verify_preprocessor_inputs(profile)
            Path(profile['cc1plus_path']).write_bytes(b'changed-child')
            with self.assertRaisesRegex(ValueError,'preprocessor tool pin'):coverage.verify_preprocessor_inputs(profile)
    def test_new_compiler_selection_specs_reject_before_driver_query(self):
        with tempfile.TemporaryDirectory() as t:
            profile=self.tool_profile(Path(t));Path(profile['selection_absent_paths'][0]).write_bytes(b'injected selection')
            with self.assertRaisesRegex(ValueError,'compiler selection'):coverage.verify_preprocessor_inputs(profile)
    def test_unrelated_log_mutation_rejects_with_expected_commands_intact(self):
        raw=b'original diagnostic\n/usr/bin/g++ -c -o /tmp/a.o a.cxx\n'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'build.log';p.write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
            coverage.verify_build_log(p,sha,len(raw))
            changed=raw.replace(b'original',b'modified');p.write_bytes(changed)
            coverage.verify_commands(changed.decode(),[['/usr/bin/g++','-c','-o','/tmp/a.o','a.cxx']])
            with self.assertRaisesRegex(ValueError,'build log pin'):coverage.verify_build_log(p,sha,len(raw))
if __name__=='__main__':unittest.main()
