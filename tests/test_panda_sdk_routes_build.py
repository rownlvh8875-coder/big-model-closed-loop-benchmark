from pathlib import Path
import hashlib,os,shlex,subprocess,tempfile,unittest
from unittest.mock import patch
try:
    from scripts import panda_sdk_routes_inputs as inputs
    from scripts import panda_sdk_routes_stage as stage
    from scripts import build_panda_sdk_routes as build
except ImportError:inputs=stage=build=None
ROOT=Path(__file__).resolve().parents[1]
class RoutesBuildTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(inputs,'new SDK source/dependency build required')
    def test_gnu_dependency_continuations_and_escaped_spaces(self):
        a=inputs.parse_dependencies(b'/tmp/a.o: panda/a.cxx \\\n /usr/include/a.h path\\ with\\ spaces.h\n')
        self.assertEqual(a,['panda/a.cxx','/usr/include/a.h','path with spaces.h'])
        for raw in (b'a.o a.cxx',b'a.o: a.cxx\nb.o: b.cxx\n',b'a.o: \x00a.h',b'a.o:',b'\xff'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):inputs.parse_dependencies(raw)
    def fixture(self,root):
        paths={n:root/n for n in ['source','sdk','sysroot','host']}
        for p in paths.values():p.mkdir()
        (paths['source']/'main.c').write_text('#include "owned.h"\nint owned(void){return NUMBER;}\n');(paths['host']/'owned.h').write_text('#define NUMBER 7\n')
        return paths
    def test_actual_dependency_file_binds_header_before_after(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.fixture(Path(t));before=inputs.capture_host_inputs([p['host']]);obj=p['sdk']/'main.o'
            subprocess.run(['/usr/bin/gcc','-nostdinc','-I'+str(p['host']),'-MD','-c',str(p['source']/'main.c'),'-o',str(obj)],check=True,capture_output=True,timeout=10)
            deps=inputs.parse_dependencies(obj.with_suffix('.d').read_bytes());rows=inputs.qualify_dependencies(deps,p['source'],p['sdk'],p['sysroot'],before)
            self.assertEqual({x['origin'] for x in rows},{'source','host'});self.assertEqual(len(rows),2)
            (p['host']/'owned.h').write_text('#define NUMBER 8\n')
            with self.assertRaisesRegex(ValueError,'host input changed'):inputs.qualify_dependencies(deps,p['source'],p['sdk'],p['sysroot'],before)
    def test_unregistered_and_missing_dependencies_reject(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.fixture(Path(t));before=inputs.capture_host_inputs([p['host']]);outside=Path(t)/'outside.h';outside.write_bytes(b'outside')
            for deps in [[str(outside)],[str(p['source']/'missing.h')]]:
                with self.subTest(deps=deps),self.assertRaises(ValueError):inputs.qualify_dependencies(deps,p['source'],p['sdk'],p['sysroot'],before)
    def test_nonregular_host_header_is_rejected_without_opening(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t);os.mkfifo(r/'header.h')
            with self.assertRaisesRegex(ValueError,'regular input'):inputs.capture_host_inputs([r])
    def test_changed_versioned_native_rejects_before_stage_creation(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);d=root/'native/panda_sdk_routes_v2';d.mkdir(parents=True)
            for f in (ROOT/'native/panda_sdk_routes_v2').iterdir():(d/f.name).write_bytes(f.read_bytes())
            (d/'panda_source_dispatch.h').write_bytes(b'changed')
            with patch.object(stage,'ROOT',root),self.assertRaisesRegex(ValueError,'native pin'):stage.stage(root/'upstream',root/'stage')
            self.assertFalse((root/'stage').exists())
    def test_existing_stage_and_build_evidence_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t);(r/'keep').write_bytes(b'original')
            with self.assertRaises(ValueError):stage.stage(r,r)
            with self.assertRaises(ValueError):build.build(r,r,r)
            self.assertEqual((r/'keep').read_bytes(),b'original')
    def test_fixed_dependency_flags_drop_ambient_header_injection_in_c_and_cxx(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t);poison=r/'poison.h';poison.write_text('int external_definition(void){return 99;}\n')
            with patch.dict(os.environ,{'RPM_OPT_FLAGS':'-include '+str(poison),'CPATH':str(r),'CXXFLAGS':'-include '+str(poison)}):env=build.build_env(ROOT/'output/stage7-panda-source-dispatch-01/sysroot')
            for compiler,ext in [('/usr/bin/gcc','c'),('/usr/bin/g++','cxx')]:
                source=r/('owned.'+ext);source.write_text('int owned_definition(void){return 7;}\n');obj=source.with_suffix('.o')
                p=subprocess.run([compiler,*shlex.split(env['RPM_OPT_FLAGS']),'-c',str(source),'-o',str(obj)],env=env,capture_output=True,text=True,timeout=10);self.assertEqual((p.returncode,p.stderr),(0,''))
                symbols=subprocess.check_output(['/usr/bin/readelf','-WsW',str(obj)],text=True)
                self.assertIn('owned_definition',symbols);self.assertNotIn('external_definition',symbols);self.assertTrue(obj.with_suffix('.d').is_file());self.assertNotIn('poison.h',obj.with_suffix('.d').read_text())
if __name__=='__main__':unittest.main()
