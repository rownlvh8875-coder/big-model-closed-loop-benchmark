import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
try:
    from scripts import panda_adapter_sdk_stage as sdk
except ImportError:sdk=None
ROOT=Path(__file__).resolve().parents[1]
class AdapterSdkStageTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(sdk,'exact activity/cache SDK source stage required')
        self.sources={p.name:p.read_bytes() for p in (ROOT/'docs/evidence/panda-dispatch-coverage-01/source').glob('*.cxx')}
        self.make=(ROOT/'docs/evidence/panda-adapter-sdk-01/source/makepanda.py.data').read_bytes()
    def test_pinned_graph_compiles_cache_as_c_adapter_as_cxx_and_links_once(self):
        changed,make,manifest=sdk.transform(self.sources,self.make)
        text=make.decode();start=text.index("if (GetTarget() not in ['windows', 'darwin'] and PkgSkip(\"GL\")==0 and PkgSkip(\"X11\")==0 and not RUNTIME):")
        block=text[start:text.index('\n#\n# DIRECTORY: panda/src/cocoadisplay/',start)]
        calls=[]
        def target(name,opts=None,input=None):calls.append((name,list(opts or []),input))
        exec(compile(block,'pinned-GLX-graph','exec'),dict(GetTarget=lambda:'linux',PkgSkip=lambda p:0,RUNTIME=False,DefSymbol=lambda *a:None,TargetAdd=target,COMMON_PANDA_LIBS=[]))
        objects=[r for r in calls if r[0] in ('pca_command_state.obj','pca_adapter.obj')]
        self.assertEqual([(n,s) for n,o,s in objects],[('pca_command_state.obj','readback_command_state.c'),('pca_adapter.obj','panda_cache_adapter.cxx')])
        self.assertTrue(all('NOHIDDEN' in o for n,o,s in objects))
        linked=[r[2] for r in calls if r[0]=='libpandagl.dll' and isinstance(r[2],list)]
        self.assertIn(['pca_command_state.obj','pca_adapter.obj'],linked)
        self.assertEqual(changed['glGraphicsStateGuardian_src.cxx'].count(b'#include "panda_source_activity.cxx"'),1)
        self.assertEqual(changed['glGraphicsStateGuardian_src.cxx'].count(b'#include "panda_source_dispatch.cxx"'),0)
        self.assertEqual(manifest['direct_replacements']['glReadPixels'],2);self.assertFalse(manifest['native_admitted'])
    def test_changed_source_build_graph_or_already_patched_inputs_reject(self):
        for sources,make in ((self.sources,self.make+b'\n'),({**self.sources,'glxGraphicsStateGuardian.cxx':self.sources['glxGraphicsStateGuardian.cxx']+b'\n'},self.make)):
            with self.assertRaises(ValueError):sdk.transform(sources,make)
        changed,make,_=sdk.transform(self.sources,self.make)
        with self.assertRaises(ValueError):sdk.transform(changed,make)
    def test_native_source_bytes_are_pinned_including_transitive_abi(self):
        files=sdk.native_files();self.assertEqual(len(files),9);self.assertIn('readback_return_core.h',files)
        with tempfile.TemporaryDirectory(prefix='as-native-') as folder:
            folder=Path(folder);native=folder/'native';native.mkdir()
            for name,data in files.items():(native/name).write_bytes(data)
            p=native/'readback_return_core.h';p.write_bytes(p.read_bytes().replace(b'255u',b'127u'))
            with patch.object(sdk,'ROOT',folder),self.assertRaises(ValueError):sdk.native_files()
    def test_foreign_upstream_and_existing_output_are_preserved(self):
        with tempfile.TemporaryDirectory(prefix='as-stage-') as folder:
            out=Path(folder)/'stage'
            with self.assertRaises(ValueError):sdk.stage(ROOT,out)
            self.assertFalse(out.exists());out.mkdir();sentinel=out/'keep';sentinel.write_bytes(b'prior')
            with self.assertRaises(ValueError):sdk.stage(ROOT,out)
            self.assertEqual(sentinel.read_bytes(),b'prior')
    def test_partial_ready_manifest_does_not_authorize_source(self):
        with tempfile.TemporaryDirectory(prefix='as-forged-') as folder:
            folder=Path(folder);(folder/'adapter-sdk-manifest.json').write_text(json.dumps(dict(schema='panda-adapter-sdk-stage-v1',runtime_admission_ready=True,source_tree=[])))
            with self.assertRaises(ValueError):sdk.verify_stage(folder)
if __name__=='__main__':unittest.main()
