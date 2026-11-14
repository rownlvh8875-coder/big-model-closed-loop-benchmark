from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
from scripts.readback_return_codec import decode_stream,normalize_rgb
from tests.test_readback_return_core import NONCE,split_records
from tests.test_readback_return_codec import finalization_receipt
ROOT=Path(__file__).resolve().parents[1]
def compile_state(out,*,sanitize=False):
    cmd=[shutil.which('cc'),'-std=c11','-O1' if sanitize else '-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'native')]
    if sanitize:cmd+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie']
    cmd += [str(ROOT/p) for p in ('native/readback_return_core.c','native/panda_readback_bridge.c','native/panda_readback_bridge.S','native/readback_command_state.c','tests/fixtures/panda_readback_caller.S','tests/fixtures/readback_state_fixture.c')]+['-o',str(out)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    if p.returncode:raise AssertionError(p.stderr)
    return cmd
def sample(exe,mode):
    p=subprocess.run([str(exe),mode],capture_output=True,timeout=15)
    if p.returncode:raise AssertionError(p.stderr.decode(errors='replace')[:1000])
    return p.stdout,json.loads(p.stderr)
def decode(raw,s,mode):
    return decode_stream(raw,expected_nonce=NONCE,expected_windows=12 if mode=='windows' else 1,reads_per_window=2,enabled=not mode.startswith('off'),producer_receipt=finalization_receipt(raw,s))
class ReadbackCommandStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=None;cls.exe=None
        if all((ROOT/p).exists() for p in ('native/readback_command_state.h','native/readback_command_state.c')):
            cls.temp=tempfile.TemporaryDirectory(prefix='rs-test-');cls.exe=Path(cls.temp.name)/'fixture';compile_state(cls.exe)
    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()
    def setUp(self):self.assertIsNotNone(self.exe,'compiled command-state supplier required')
    def test_command_callback_drives_actual_bridge_without_driver_authority(self):
        raw,s=sample(self.exe,'basic');r=decode(raw,s,'basic')['records']
        self.assertEqual([(x.context_tag,x.read_fbo,x.producer_camera,x.capacity) for x in r],[(1,8,1,4096),(1,9,2,4096)])
        self.assertEqual(normalize_rgb(r[0])[:3],bytes([12,1,77]));self.assertTrue(s['commands_only']);self.assertFalse(s['driver_state_proven'])
    def test_forwarding_and_errno_cover_original_overwrite_and_unchanged(self):
        for mode in ('basic','preserve','badalign','unknownctx','thread','eventcap'):
            _,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertEqual((s['args_ok'],s['regs_ok'],s['errno_ok'],s['source_ok'],s['original_calls']),(1,1,1,1,2))
    def test_pack_padding_and_unrelated_unpack_buffer_do_not_corrupt_read_layout(self):
        raw,s=sample(self.exe,'packed');r=decode(raw,s,'packed')['records'][0]
        self.assertEqual((r.alignment,r.row_length,r.skip_rows,r.skip_pixels,r.row_stride,r.first_pixel_offset),(8,8,2,1,24,51))
        self.assertEqual(normalize_rgb(r)[:3],bytes([12,1,77]))
        raw,s=sample(self.exe,'unpack');self.assertEqual(decode(raw,s,'unpack')['records'][0].alignment,4)
    def test_draw_binding_and_deletion_leave_read_source(self):
        for mode,draw in (('draw',99),('delete_draw',0)):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertTrue(decode(raw,s,mode)['cpu_window_closed']);self.assertEqual((s['read_fbo'],s['draw_fbo'],s['read_selector']),(9,draw,0x8ce0))
    def test_context_switch_failure_preserves_previous_and_reuse_gets_new_tag(self):
        for mode,tag,created in (('failedswitch',1,1),('restore',1,2),('reuse',2,2)):
            raw,s=sample(self.exe,mode);r=decode(raw,s,mode)['records']
            with self.subTest(mode=mode):self.assertEqual(r[0].context_tag,tag);self.assertEqual(s['contexts_created'],created)
    def test_unknown_shared_duplicate_dead_contexts_and_resource_caps_reject(self):
        for mode in ('unknownctx','shared','duplicatectx','destroy','livecap','lifetimes','fbocap','eventcap','thread','invalidate'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):
                self.assertNotEqual(s['cache_error'],0);self.assertEqual(s['captured'],1 if mode=='eventcap' else 0)
                with self.assertRaises(ValueError):decode(raw,s,mode)
    def test_invalid_pack_pbo_and_missing_or_unsupported_read_selection_reject(self):
        for mode in ('badalign','rowoverflow','swap','unknownenum','pbo','missingselector','defaultfbo','readnone'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertEqual(s['captured'],0);self.assertNotEqual(s['finish'],0)
    def test_deleted_binding_and_mutated_delete_input_do_not_restore_stale_selector(self):
        for mode in ('delete_bound','delete_mutate'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertEqual(s['captured'],0);self.assertNotEqual(s['finish'],0);self.assertEqual(s['args_ok'],1)
    def test_off_cache_error_and_full_footer_failure_cannot_close(self):
        raw,s=sample(self.exe,'off');self.assertEqual(decode(raw,s,'off')['records'],())
        for mode in ('offinvalid','footerfail'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode),self.assertRaises(ValueError):decode(raw,s,mode)
        raw,s=sample(self.exe,'offinvalid');_,f=split_records(raw);self.assertEqual((s['error'],f[9]),(0,0));self.assertNotEqual(s['cache_error'],0)
    def test_twelve_windows_keep24_records_bounded(self):
        raw,s=sample(self.exe,'windows');r=decode(raw,s,'windows')['records']
        self.assertEqual((len(r),len(raw)),(24,5016));self.assertLess(s['events'],10000)
    def test_python_registry_private64bit_handles_reach_cache_and_assembly(self):
        from tests.test_readback_camera_registry import provider,registry
        r=registry.CameraRegistry(provider(),NONCE);r.guard(1,1)
        process=subprocess.run([str(self.exe),'basic',*map(str,r.native_binding())],capture_output=True,timeout=15)
        self.assertEqual(process.returncode,0);stats=json.loads(process.stderr)
        rows=decode(process.stdout,stats,'basic')['records']
        self.assertEqual([(x.producer_camera,x.requested_camera) for x in rows],[(1,1),(2,1)])
        self.assertEqual((stats['finish'],stats['args_ok'],stats['regs_ok']),(0,1,1))
    def test_context_pack_isolation_unbinding_and_read_target(self):
        for mode in ('isolation','pbo_reset','read_target','selector_restore'):
            raw,s=sample(self.exe,mode);r=decode(raw,s,mode)['records']
            with self.subTest(mode=mode):self.assertEqual((r[0].alignment,r[0].pack_buffer,r[0].context_tag),(4,0,1))
            if mode=='read_target':self.assertEqual(s['draw_fbo'],99)
            if mode=='selector_restore':self.assertEqual(s['first_selector'],0x8ce1)
        for mode in ('unbound','foreignidentity','reentrant','failed_delete'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertNotEqual(s['cache_error'],0);self.assertEqual(s['captured'],0);self.assertEqual((s['args_ok'],s['errno_ok']),(1,1))

if __name__=='__main__':unittest.main()
