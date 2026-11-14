"""Assembled SysV CPU caller -> real bridge/core -> strict wire consumer."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
from tests.test_readback_return_core import NONCE,split_records
from tests.test_readback_return_codec import finalization_receipt
from scripts.readback_return_codec import decode_stream,normalize_rgb

ROOT=Path(__file__).resolve().parents[1]
def compile_bridge(out,*,sanitize=False):
    cc=shutil.which('cc')
    command=[cc,'-std=c11','-O1' if sanitize else '-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'native')]
    if sanitize:command+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie']
    command += [str(ROOT/p) for p in ('native/readback_return_core.c','native/panda_readback_bridge.c','native/panda_readback_bridge.S','tests/fixtures/panda_readback_caller.S','tests/fixtures/panda_readback_fixture.c')]+['-o',str(out)]
    r=subprocess.run(command,capture_output=True,text=True,timeout=30)
    if r.returncode:raise AssertionError(r.stderr)
    return command
def sample(exe,mode):
    r=subprocess.run([str(exe),mode],capture_output=True,timeout=20)
    if r.returncode:raise AssertionError(f'CPU fixture rc={r.returncode}: '+r.stderr.decode(errors='replace')[:2000])
    return r.stdout,json.loads(r.stderr)
def decode_sample(raw,stats,mode='basic'):
    return decode_stream(raw,expected_nonce=NONCE,expected_windows=12 if mode=='max' else 1,reads_per_window=2,enabled=not mode.startswith('off'),producer_receipt=finalization_receipt(raw,stats))

class PandaReadbackBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=None;cls.exe=None
        if all((ROOT/p).exists() for p in ('native/panda_readback_bridge.h','native/panda_readback_bridge.c','native/panda_readback_bridge.S')):
            cls.temp=tempfile.TemporaryDirectory(prefix='pb-test-');cls.exe=Path(cls.temp.name)/'fixture';compile_bridge(cls.exe)
    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()
    def setUp(self):self.assertIsNotNone(self.exe,'assembled Panda ABI transport required')
    def test_original_signed_args_stack_pointer_errno_and_callee_saved_registers(self):
        raw,s=sample(self.exe,'basic');rows,_=split_records(raw)
        self.assertEqual((s['original_calls'],s['args_ok'],s['regs_ok'],s['errno_ok'],s['source_ok'],s['finish']),(2,1,1,1,1,0))
        self.assertEqual(rows[0][0][10:14],(-2147483631,2147483624,5,3))
        self.assertEqual(rows[0][0][25],4096);self.assertEqual(s['callbacks'],2)
    def test_observer_cannot_change_original_incoming_or_unchanged_errno(self):
        for mode in ('errno_keep','errno_check','offerrno_keep'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):
                self.assertEqual((s['incoming_ok'],s['errno_ok'],s['args_ok'],s['regs_ok'],s['finish']),(1,1,1,1,0))
                self.assertTrue(decode_sample(raw,s,mode)['cpu_window_closed'])
    def test_captured_register_extent_and_registered_producer_replace_callback_claims(self):
        raw,s=sample(self.exe,'basic');r=decode_sample(raw,s)['records']
        self.assertEqual([(x.capacity,x.producer_camera,x.label_basis,x.requested_camera) for x in r],[(4096,1,1,1),(4096,2,1,1)])
        self.assertEqual(normalize_rgb(r[0])[:3],bytes([12,1,77]))
    def test_pack_padding_and_formats_interoperate_with_core_codec(self):
        for mode in ('packed','rgb','rgba'):
            raw,s=sample(self.exe,mode);r=decode_sample(raw,s)['records']
            with self.subTest(mode=mode):self.assertEqual(normalize_rgb(r[0])[:3],bytes([12,1,77]));self.assertEqual(s['source_ok'],1)
    def test_off_does_not_dereference_pixel_or_call_null_state_supplier(self):
        raw,s=sample(self.exe,'off');r=decode_sample(raw,s,'off')
        self.assertEqual((s['callbacks'],s['captured'],s['attempts'],s['original_calls'],s['finish']),(0,0,0,2,0))
        self.assertEqual(r['records'],())
    def test_off_bridge_error_invalidates_even_a_successful_core_footer(self):
        raw,s=sample(self.exe,'offwrongreturn');rows,footer=split_records(raw)
        self.assertEqual((rows,s['error'],footer[9]),([],0,0));self.assertNotEqual(s['bridge_error'],0)
        with self.assertRaises(ValueError):decode_sample(raw,s,'offwrongreturn')
    def test_outside_window_reads_only_forward_and_are_excluded_from_scoped_counts(self):
        raw,s=sample(self.exe,'outside');r=decode_sample(raw,s)
        self.assertEqual((s['original_calls'],s['forwards'],s['callbacks'],s['captured'],s['finish']),(4,2,2,2,0))
        self.assertTrue(r['cpu_window_closed'])
    def test_wrong_return_and_identities_fail_before_observer_but_originals_forward(self):
        for mode in ('wrongreturn','texture','gsg','image','zero','overflow','z','view','thread','reentrant'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):
                self.assertEqual((s['original_calls'],s['args_ok'],s['regs_ok'],s['errno_ok']),(2,1,1,1))
                self.assertNotEqual(s['finish'],0);self.assertEqual(s['captured'],0)
                if mode!='reentrant':self.assertEqual(s['callbacks'],0)
                with self.assertRaises(ValueError):decode_sample(raw,s)
    def test_bad_state_or_short_register_extent_cannot_become_capture(self):
        for mode in ('statefail','unknown','pbo','short'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertEqual(s['original_calls'],2);self.assertEqual(s['captured'],0);self.assertNotEqual(s['finish'],0)
    def test_window_and_global_caps_preserve_forwarding(self):
        for mode,count,captured in (('limit',2,1),('bytes',2,0),('excess',3,2),('nested',2,0),('shortwindow',1,1)):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertEqual(s['original_calls'],count);self.assertEqual(s['captured'],captured);self.assertNotEqual(s['finish'],0)
    def test_partial_and_complete_footer_failure_never_close_cpu_window(self):
        for mode in ('partial','footerfail'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode),self.assertRaises(ValueError):decode_sample(raw,s)
    def test_failed_or_duplicate_install_does_not_destroy_valid_binding(self):
        for mode in ('initbad','duplicate'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertEqual(s['finish'],0);self.assertTrue(decode_sample(raw,s)['cpu_window_closed'])
    def test_max_window_preserves_requester_and_producer_separation(self):
        raw,s=sample(self.exe,'max');r=decode_sample(raw,s,'max')['records']
        self.assertEqual((len(r),len(raw)),(24,55900512))
        self.assertEqual([(x.host_call,x.requested_camera,x.producer_camera) for x in r[2:4]],[(2,2,1),(2,2,2)])

if __name__=='__main__':unittest.main()
