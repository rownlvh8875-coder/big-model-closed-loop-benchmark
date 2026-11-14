"""Pure proc/module metadata fixtures; no process or filesystem scan."""
import json
import unittest
try:from scripts import engine_clock_native_selection as s
except ImportError:s=None

class NativeSelectionTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(s,'bounded runtime selection classifier absent')
    def files(self):return {'/opt/venv/bin/python','/usr/lib/libGL.so','/usr/share/fonts/font.ttf'}
    def sources(self):return {'scripts/main.py'}
    def line(self,path,perms='r--p',inode=10):return f'1000-2000 {perms} 00000000 00:01 {inode} {path}\n'
    def test_image_source_and_registered_cache_data_are_distinct(self):
        raw=self.line('/usr/lib/libGL.so','r-xp')+self.line('/usr/share/fonts/font.ttf')+self.line('/work/repo/scripts/main.py')+self.line('/work/cache/case_00/mesa_shader_cache/index','rw-s')
        d=s.classify_maps(raw,self.files(),self.sources())
        self.assertTrue(d['accepted']);self.assertEqual(['/usr/lib/libGL.so','/usr/share/fonts/font.ttf'],d['image_files'])
        self.assertEqual(['/work/repo/scripts/main.py'],d['source_files'])
        self.assertEqual('registered-cache-data',d['runtime_mappings'][0]['category'])
    def test_unknown_deleted_or_executable_runtime_files_reject(self):
        for path,perms in [('/host/libinjected.so','r-xp'),('/work/cache/case_00/lib.so','r-xp'),('/tmp/code.so','r-xp'),('/usr/lib/libGL.so (deleted)','r-xp'),('/work/cache/other/index','r--s')]:
            d=s.classify_maps(self.line(path,perms),self.files(),self.sources())
            self.assertFalse(d['accepted']);self.assertTrue(d['rejections'])
    def test_generated_memory_is_not_reported_as_installed_binary(self):
        raw=self.line('/memfd:llvm-jit (deleted)','r-xp')+self.line('/SYSV00000000 (deleted)','rw-s')+self.line('/dev/zero (deleted)','rw-s')+self.line('[heap]','rw-p',0)+self.line('','rw-p',0)
        d=s.classify_maps(raw,self.files(),self.sources())
        self.assertTrue(d['accepted']);self.assertEqual([],d['image_files'])
        self.assertEqual({'anonymous-fd','private-ipc','anonymous-zero','kernel-region'},set(v['category'] for v in d['runtime_mappings']))
        self.assertFalse(d['generated_memory_binary_equality_proven'])
    def test_malformed_and_caps_never_return_partial_acceptance(self):
        for raw in ('bad\n',self.line('/usr/lib/libGL.so')*10001,'x'*(1024**2+1)):
            d=s.classify_maps(raw,self.files(),self.sources());self.assertFalse(d['accepted'])
            self.assertLess(len(json.dumps(d)),512*1024)
    def test_module_files_closed_and_pseudo_origins_explicit(self):
        d=s.classify_modules([('gl','/usr/lib/libGL.so','/usr/lib/libGL.so'),('app','/work/repo/scripts/main.py','/work/repo/scripts/main.py'),('frozen','<frozen>','frozen'),('sys',None,'built-in')],self.files(),self.sources())
        self.assertTrue(d['accepted']);self.assertEqual(2,len(d['module_files']))
        self.assertEqual(2,len(d['module_pseudo']))
        bad=s.classify_modules([('inject','/tmp/evil.py','/tmp/evil.py')],self.files(),self.sources())
        self.assertFalse(bad['accepted'])
        forged=s.classify_modules([('inject','/host/lib.so','frozen')],self.files(),self.sources())
        self.assertFalse(forged['accepted'])

if __name__=='__main__':unittest.main()
