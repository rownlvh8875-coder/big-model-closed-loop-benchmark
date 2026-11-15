import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

try:
    from scripts import panda_source_dispatch as patcher
except ImportError:
    patcher=None
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/evidence/panda-dispatch-coverage-01/source'

class PandaSourcePatchTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(patcher,'exact pinned source integration required')
        self.sources={p.name:p.read_bytes() for p in SOURCE.glob('*.cxx')}
    def test_actual_sources_transform_once_and_manifest_keeps_native_blocked(self):
        original=dict(self.sources);changed,manifest=patcher.transform_sources(self.sources)
        self.assertEqual(self.sources,original);self.assertEqual(set(changed),set(original))
        self.assertEqual(manifest['direct_replacements']['glXCreateContext'],1)
        self.assertGreater(manifest['direct_replacements']['glPixelStorei'],0)
        self.assertGreater(manifest['direct_replacements']['glReadPixels'],0)
        self.assertEqual(manifest['unified_returns'],2);self.assertEqual(manifest['glx_path_returns'],3);self.assertEqual(manifest['posix_path_returns'],1)
        self.assertFalse(manifest['runtime_admission_ready'])
        for name,data in changed.items():
            self.assertEqual(manifest['files'][name]['original_sha256'],hashlib.sha256(original[name]).hexdigest())
            self.assertEqual(manifest['files'][name]['candidate_sha256'],hashlib.sha256(data).hexdigest())
    def test_mutated_and_already_patched_sources_reject(self):
        changed,_=patcher.transform_sources(self.sources)
        for name in self.sources:
            bad=dict(self.sources);bad[name]+=b'\n'
            with self.subTest(name=name),self.assertRaises(ValueError):patcher.transform_sources(bad)
        with self.assertRaises(ValueError):patcher.transform_sources(changed)
    def test_lexical_call_edits_preserve_comments_literals_and_execute_original_once(self):
        source=b'int main(){ /* glPixelStorei(0,9); */ const char *label="glPixelStorei("; glPixelStorei(3,4); std::printf("%u %s",n,label); }'
        changed,counts=patcher.rewrite_calls(source)
        self.assertEqual(counts,{'glPixelStorei':1})
        prefix=b'#include "panda_source_dispatch.h"\n#include <cstdio>\nunsigned n;void glPixelStorei(unsigned a,int b){if(a==3&&b==4)++n;}\n'
        with tempfile.TemporaryDirectory(prefix='psd-patch-') as folder:
            folder=Path(folder);cpp=folder/'main.cxx';cpp.write_bytes(prefix+changed);exe=folder/'cpu'
            subprocess.run([shutil.which('g++'),'-std=c++11','-O2','-pthread','-I',str(ROOT/'native'),str(ROOT/'native/panda_source_dispatch.cxx'),str(cpp),'-o',str(exe)],check=True,capture_output=True,timeout=30)
            self.assertEqual(subprocess.check_output([str(exe)],timeout=5),b'1 glPixelStorei(')
    def test_transformed_real_unified_method_covers_compiled_and_runtime_paths(self):
        changed,_=patcher.transform_sources(self.sources);text=changed['glGraphicsStateGuardian_src.cxx'].decode()
        start=text.index('void *CLP(GraphicsStateGuardian)::\nget_extension_func(');end=text.index('\n/**',start)
        method=text[start:end]
        import re
        names=set(re.findall(r'&\s*(gl[A-Za-z0-9_]+)',method))
        prefix='''#include "panda_source_dispatch.h"
#include <cstdio>
#include <cstring>
#include <cerrno>
unsigned compiled_calls,runtime_calls,lookups,events;
void glBindBuffer(unsigned a,unsigned b){if(a==1&&b==2)++compiled_calls;errno=EDOM;}
void runtime_fbo(unsigned a,unsigned b){if(a==1&&b==2)++runtime_calls;errno=EDOM;}
int observed(const psd_event*,void*){++events;errno=EIO;return 0;}
class GSG {public:void *get_extension_func(const char*);void *do_get_extension_func(const char*){++lookups;errno=EDOM;return (void*)runtime_fbo;}};
#define CLP(x) GSG
#define EXPECT_GL_VERSION_1_5
'''+''.join('void '+n+'(){}\n' for n in sorted(names-{'glBindBuffer'}))
        suffix='''int main(){if(psd_configure(observed,nullptr,nullptr,0,10000))return 1;GSG g;
errno=ERANGE;void *a=g.get_extension_func("glBindBuffer");if(errno!=ERANGE)return 2;
errno=ERANGE;((void(*)(unsigned,unsigned))a)(1,2);if(errno!=EDOM)return 3;
errno=ERANGE;void *b=g.get_extension_func("glBindFramebufferEXT");if(errno!=EDOM)return 4;
errno=ERANGE;((void(*)(unsigned,unsigned))b)(1,2);if(errno!=EDOM)return 5;
std::printf("%u %u %u %u %d",compiled_calls,runtime_calls,lookups,events,psd_finish());}
'''
        with tempfile.TemporaryDirectory(prefix='psd-method-') as folder:
            folder=Path(folder);cpp=folder/'main.cxx';cpp.write_text(prefix+method+suffix);exe=folder/'cpu'
            p=subprocess.run([shutil.which('g++'),'-std=c++11','-O2','-pthread','-I',str(ROOT/'native'),str(ROOT/'native/panda_source_dispatch.cxx'),str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(subprocess.check_output([str(exe)],timeout=5),b'1 1 1 4 0')
    def test_foreign_upstream_cli_rejects_without_creating_tree(self):
        with tempfile.TemporaryDirectory(prefix='psd-stage-') as folder:
            dest=Path(folder)/'candidate'
            p=subprocess.run([shutil.which('python3'),'-B','-m','scripts.panda_source_dispatch','--upstream',str(ROOT),'--out',str(dest)],cwd=ROOT,capture_output=True,timeout=10)
            self.assertEqual(p.returncode,2);self.assertFalse(dest.exists())
    def test_existing_output_survives_stage_rejection(self):
        with tempfile.TemporaryDirectory(prefix='psd-existing-') as folder:
            dest=Path(folder)/'candidate';dest.mkdir();sentinel=dest/'keep';sentinel.write_bytes(b'prior evidence')
            with self.assertRaises(ValueError):patcher.stage(ROOT,dest)
            self.assertEqual(list(dest.iterdir()),[sentinel]);self.assertEqual(sentinel.read_bytes(),b'prior evidence')

if __name__=='__main__':unittest.main()
