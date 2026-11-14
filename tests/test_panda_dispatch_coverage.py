import copy
import json
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from tests.test_readback_elf_imports import compile_import_fixture
from scripts.readback_elf_imports import inspect_imports
try:
    from scripts import panda_dispatch_coverage as coverage
except ImportError:
    coverage = None

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'docs/evidence/panda-dispatch-coverage-01/source'


class DispatchCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='pc-cover-')
        cls.path = Path(cls.temp.name)/'unloaded.so'
        compile_import_fixture(cls.path)
        cls.image = cls.path.read_bytes()
        cls.imports = inspect_imports(cls.image)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.assertIsNotNone(coverage, 'pinned coverage scanner and gate required')

    def scan(self, text):
        return coverage.scan_source(text.encode(), 'cpu.cxx')

    def assess(self, source='', routes=('glReadPixels',), safe_names=(), mechanism='got-only'):
        return coverage.assess_coverage(self.imports, [self.scan(source)], routes, safe_names, mechanism)

    def test_comments_and_unrelated_strings_do_not_create_calls(self):
        data = self.scan('/* get_extension_func("glFake"); */\n'
                         'const char *log="get_extension_func(\\"glFake2\\")";\n'
                         '// glFake3();\nget_extension_func("glBindBuffer");\n')
        self.assertEqual([(r['name'], r['line']) for r in data['literal_lookups']], [('glBindBuffer', 4)])
        self.assertEqual(data['direct_calls'], [])

    def test_concatenated_lookup_and_computed_fallback_remain_distinct(self):
        data = self.scan('get_extension_func("glRead" /* join */ "Pixels");\n'
                         'get_system_func(name); get_extension_func(prefix + name);\n'
                         '_glXGetProcAddress(name); glXCreateContext(d,v,0,1);')
        self.assertEqual([r['name'] for r in data['literal_lookups']], ['glReadPixels'])
        self.assertEqual([r['callee'] for r in data['computed_lookups']], ['get_system_func', 'get_extension_func'])
        self.assertEqual([r['name'] for r in data['member_calls']], ['_glXGetProcAddress'])
        self.assertEqual([r['name'] for r in data['direct_calls']], ['glXCreateContext'])

    def test_declarations_definitions_and_conditional_branches(self):
        data = self.scan('void *get_extension_func(const char *name);\n'
                         'void glReadPixels(void);\n'
                         'void *get_system_func(const char *name) { return get_extension_func(name); }\n'
                         '#if MAYBE\nget_extension_func("glBindBuffer");\n#else\nget_extension_func("glBindBufferARB");\n#endif')
        self.assertEqual([r['name'] for r in data['literal_lookups']], ['glBindBuffer', 'glBindBufferARB'])
        self.assertEqual(len(data['computed_lookups']), 1)
        self.assertEqual(data['direct_calls'], [])
        self.assertFalse(data['active_compiled_paths_proven'])

    def test_parentheses_inside_literal_arguments_are_not_source_delimiters(self):
        for source,field,name in (('glDebugMessageInsert(0,0,1,0,-1,"(");','direct_calls','glDebugMessageInsert'),
                                  ('_glPushGroupMarkerEXT(1,")");','member_calls','_glPushGroupMarkerEXT'),
                                  ("glReadBuffer('(');",'direct_calls','glReadBuffer')):
            with self.subTest(source=source):
                data=self.scan(source)
                self.assertEqual([r['name'] for r in data[field]],[name])

    def test_malformed_and_unbounded_source_is_rejected(self):
        for source in (b'/* no close', b'"no close', b'get_extension_func("glReadPixels";',
                       b'get_ext\\\nension_func("glReadPixels");', b'R"(glReadPixels())"',
                       b'x'*(1024*1024+1)):
            with self.subTest(size=len(source)), self.assertRaises(ValueError):
                coverage.scan_source(source, 'cpu.cxx')

    def test_missing_legacy_context_and_buffer_delete_are_actionable_blockers(self):
        result = self.assess('get_extension_func("glDeleteBuffers");', routes=('glReadPixels', 'glPixelStorei'))
        self.assertEqual(result['missing_required_routes'], ['glDeleteBuffers', 'glXCreateContext'])
        self.assertIn('MISSING_CAPTURE_STATE_ROUTES', result['blockers'])
        self.assertFalse(result['runtime_admission_ready'])

    def test_got_only_cannot_cover_private_or_fallback_resolver(self):
        result = self.assess('get_system_func(name); _glXGetProcAddress(name);',
                             routes=('glReadPixels', 'glXCreateContext', 'glPixelStorei'))
        self.assertTrue(result['name_classification_complete'])
        self.assertIn('GOT_CANNOT_COVER_PRIVATE_OR_FALLBACK_RESOLVERS', result['blockers'])
        self.assertFalse(result['installation_qualified'])
        self.assertFalse(result['native_admitted'])

    def test_source_integrated_name_plan_never_becomes_runtime_admission(self):
        result = self.assess(routes=('glReadPixels', 'glXCreateContext', 'glPixelStorei'), mechanism='source-integrated')
        self.assertTrue(result['name_classification_complete'])
        self.assertFalse(result['runtime_admission_ready'])
        self.assertIn('INSTALLATION_UNQUALIFIED', result['blockers'])

    def test_safe_names_cannot_admit_known_mutators_or_exceed_caps(self):
        for safe in (('glDeleteBuffers',), ('glNamedFramebufferReadBufferEXT',), ('glXCopyContext',),
                     ('glDrawArrays', 'glDrawArrays'), tuple(f'glSafe{i}' for i in range(257)),
                     ('gl'+'A'*62,), ('not_gl',)):
            with self.subTest(safe_count=len(safe)), self.assertRaises(ValueError):
                self.assess(safe_names=safe)

    def test_safe_ordinary_name_classifies_only_that_explicit_name(self):
        result = self.assess('get_extension_func("glDrawArrays"); get_extension_func("glDrawElements");',
                             routes=('glReadPixels', 'glXCreateContext', 'glPixelStorei'), safe_names=('glDrawArrays',))
        self.assertEqual(result['unclassified_names'], ['glDrawElements'])
        self.assertFalse(result['name_classification_complete'])

    def test_source_union_budget_pressure_is_reported_without_auto_allowlisting(self):
        source='\n'.join(f'get_extension_func("glPotential{i}");' for i in range(257))
        result=self.assess(source, routes=('glReadPixels', 'glXCreateContext', 'glPixelStorei'))
        self.assertEqual(len(result['unclassified_names']), 257)
        self.assertIn('CONSERVATIVE_NAME_UNION_EXCEEDS_SAFE_CAP', result['blockers'])
        self.assertEqual(result['safe_names_count'], 0)

    def test_caller_flags_cannot_elevate_planning_into_native_authority(self):
        imports=copy.deepcopy(self.imports);imports['runtime_admission_ready']=True
        source=self.scan('get_system_func(name);');source['active_compiled_paths_proven']=True
        result=coverage.assess_coverage(imports,[source],('glReadPixels',),(), 'source-integrated')
        self.assertFalse(result['runtime_admission_ready'])
        self.assertFalse(result['active_compiled_paths_proven'])

    def test_delivery_route_parser_uses_actual_declarations_and_rejects_duplicates(self):
        routes=coverage.delivery_routes((ROOT/'native/readback_call_delivery.c').read_bytes())
        self.assertEqual(len(routes),17)
        self.assertIn('glXCreateNewContext',routes)
        self.assertNotIn('glXCreateContext',routes)
        with self.assertRaises(ValueError):
            coverage.delivery_routes(b'ROUTE("glReadPixels",read,wrap),ROUTE("glReadPixels",read,wrap)')

    def test_pinned_sources_expose_posix_fallback_and_legacy_context(self):
        inputs={p.name:p.read_bytes() for p in SOURCE.glob('*.cxx')}
        sources=coverage.qualify_sources(inputs)
        legacy=next(s for s in sources if s['file']=='glxGraphicsStateGuardian.cxx')
        self.assertIn('glXCreateContext',{r['name'] for r in legacy['direct_calls']})
        posix=next(s for s in sources if s['file']=='posixGraphicsStateGuardian.cxx')
        self.assertIn('get_system_func',{r['callee'] for r in posix['computed_lookups']})
        inputs['glxGraphicsStateGuardian.cxx']+=b'\n'
        with self.assertRaises(ValueError):
            coverage.qualify_sources(inputs)

    def test_foreign_image_cannot_be_qualified_as_panda(self):
        inputs={p.name:p.read_bytes() for p in SOURCE.glob('*.cxx')}
        with self.assertRaises(ValueError):
            coverage.qualify(self.image,inputs,(ROOT/'native/readback_call_delivery.c').read_bytes())

    def test_cli_rejects_foreign_and_symlink_inputs_without_creating_success_output(self):
        with tempfile.TemporaryDirectory(prefix='pc-cli-') as folder:
            folder=Path(folder);link=folder/'linked.so';link.symlink_to(self.path)
            for index,path in enumerate((self.path,link)):
                output=folder/f'result-{index}'
                p=subprocess.run([os.sys.executable,'-B','-m','scripts.panda_dispatch_coverage',
                                  '--image',str(path),'--source-dir',str(SOURCE),'--out',str(output)],
                                 cwd=ROOT,capture_output=True,text=True,timeout=10)
                self.assertEqual(p.returncode,2)
                self.assertFalse(output.exists())
                self.assertEqual(p.stdout,'')


if __name__ == '__main__':
    unittest.main()
