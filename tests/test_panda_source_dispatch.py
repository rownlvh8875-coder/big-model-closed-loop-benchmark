from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
MODES=('off','basic','closed','createfail','normalize','preserve','aliases','null','mismatch','unknown','safe',
       'mutate_name','paths','delete','delete_bad','glerror','thread','reentry','callback_reentry','callbackfail','cap')
FAIL={'mismatch','unknown','delete_bad','glerror','thread','reentry','callback_reentry','callbackfail','cap'}

def compile_source_dispatch(path,sanitize=False):
    caller=Path(str(path)+'-caller.S')
    caller.write_text((ROOT/'tests/fixtures/panda_readback_caller.S').read_text().replace('pb_entry','psd_read_pixels'))
    cmd=[shutil.which('g++'),'-std=c++11','-O1' if sanitize else '-O2','-Wall','-Wextra','-Werror','-pthread',
         '-I',str(ROOT/'native'),'-Dpb_fixture_call=psd_fixture_call','-Dpb_fixture_return=psd_fixture_return']
    if sanitize:cmd+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie']
    cmd += [str(ROOT/'native/panda_source_dispatch.cxx'),str(ROOT/'tests/fixtures/panda_source_dispatch_fixture.cxx'),str(caller),'-o',str(path)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    if p.returncode:raise AssertionError(p.stderr)
    return cmd

class PandaSourceDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=None;cls.exe=None
        if (ROOT/'native/panda_source_dispatch.h').exists() and (ROOT/'native/panda_source_dispatch.cxx').exists():
            cls.temp=tempfile.TemporaryDirectory(prefix='psd-cpu-');cls.exe=Path(cls.temp.name)/'fixture';compile_source_dispatch(cls.exe)
    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()
    def setUp(self):self.assertIsNotNone(self.exe,'source-integrated dispatch runtime required')
    def sample(self,mode):
        p=subprocess.run([str(self.exe),mode],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stderr,'');return json.loads(p.stdout)
    def test_default_off_and_closed_forward_without_observation(self):
        for mode,want in (('off',0),('closed',1)):
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual(s['observer_calls'],want);self.assertEqual(s['originals'],2)
    def test_normalized_arguments_actual_returns_and_errno_are_preserved(self):
        for mode in ('basic','normalize','preserve','createfail','delete'):
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual((s['args_ok'],s['errno_ok'],s['normalized_ok'],s['snapshot_ok'],s['finish']),(1,1,1,1,0))
    def test_resolver_alias_null_name_snapshot_and_safe_paths_preserve_capabilities(self):
        for mode in ('aliases','null','mutate_name','safe','paths'):
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual((s['args_ok'],s['errno_ok'],s['finish']),(1,1,0));self.assertGreater(s['lookups'],0)
    def test_failures_poison_metadata_while_originals_and_tail_continue(self):
        for mode in FAIL:
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual((s['args_ok'],s['errno_ok'],s['reads'],s['regs_ok']),(1,1,1,1));self.assertNotEqual(s['finish'],0)
    def test_read_tail_keeps_original_stack_arguments_and_callee_saved_registers(self):
        for mode in MODES:
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual((s['reads'],s['regs_ok']),(1,1));self.assertFalse(s['native_admitted'])
    def test_known_state_restoration_is_not_a_safe_configuration(self):
        p=subprocess.run([str(self.exe),'unsafe_config'],capture_output=True,timeout=10)
        self.assertEqual((p.returncode,p.stdout,p.stderr),(3,b'',b''))
    def test_invalid_event_shape_rejects_before_reading_delete_arguments(self):
        with tempfile.TemporaryDirectory(prefix='psd-invalid-') as folder:
            exe=Path(folder)/'fixture';compile_source_dispatch(exe,sanitize=True)
            p=subprocess.run([str(exe),'badshape'],capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stderr,'')
            s=json.loads(p.stdout);self.assertNotEqual(s['finish'],0);self.assertEqual((s['reads'],s['args_ok']),(1,1))

if __name__=='__main__':unittest.main()
