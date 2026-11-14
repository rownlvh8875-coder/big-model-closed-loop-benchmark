from pathlib import Path
import json,shutil,subprocess,tempfile,unittest
from tests.test_readback_return_core import NONCE
from tests.test_readback_return_codec import finalization_receipt
from scripts.readback_return_codec import decode_stream,normalize_rgb
ROOT=Path(__file__).resolve().parents[1]
def compile_delivery(out,*,sanitize=False):
    sources=('native/readback_return_core.c','native/panda_readback_bridge.c','native/panda_readback_bridge.S','native/readback_command_state.c','native/readback_call_delivery.c','native/readback_delivery_entry.S','tests/fixtures/panda_readback_caller.S','tests/fixtures/readback_delivery_fixture.c')
    cmd=[shutil.which('cc'),'-std=c11','-O1' if sanitize else '-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'native'),'-Dpb_fixture_call=rd_fixture_call','-Dpb_fixture_return=rd_fixture_return']
    # Only the old caller assembly gets symbol substitutions; production PB stays intact.
    caller=Path(str(out)+'-caller.S');caller.write_text((ROOT/sources[-2]).read_text().replace('pb_entry','rd_read_pixels'))
    paths=[str(ROOT/p) for p in sources if p!='tests/fixtures/panda_readback_caller.S']+[str(caller)]
    if sanitize:cmd+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie']
    cmd+=paths+['-o',str(out)];p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    if p.returncode:raise AssertionError(p.stderr)
    return cmd
def sample(exe,mode):
    p=subprocess.run([str(exe),mode],capture_output=True,timeout=15)
    if p.returncode:raise AssertionError(p.stderr.decode(errors='replace')[:2000])
    return p.stdout,json.loads(p.stderr)
def decode(raw,s,mode):return decode_stream(raw,expected_nonce=NONCE,expected_windows=1,reads_per_window=2,enabled=not mode.startswith('off'),producer_receipt=finalization_receipt(raw,s))
class CallDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=None;cls.exe=None
        if all((ROOT/p).exists() for p in ('native/readback_call_delivery.h','native/readback_call_delivery.c','native/readback_delivery_entry.S')):
            cls.temp=tempfile.TemporaryDirectory(prefix='rd-test-');cls.exe=Path(cls.temp.name)/'fixture';compile_delivery(cls.exe)
    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()
    def setUp(self):self.assertIsNotNone(self.exe,'typed delivery/bootstrap/tail required')
    def test_bootstrap_replay_has_no_extra_original_calls_and_tail_keeps_panda_abi(self):
        raw,s=sample(self.exe,'basic');r=decode(raw,s,'basic')['records']
        self.assertEqual((s['args_ok'],s['errno_ok'],s['regs_ok'],s['finish']),(1,1,1,0));self.assertEqual(s['original_calls'],2)
        self.assertEqual(s['replayed'],5);self.assertEqual(normalize_rgb(r[0])[:3],bytes([12,1,77]));self.assertFalse(s['runtime_admission_ready'])
    def test_alias_and_allowlisted_resolver_routes_preserve_results(self):
        for mode in ('aliases','safe','null','delete'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertTrue(decode(raw,s,mode)['cpu_window_closed']);self.assertEqual((s['args_ok'],s['errno_ok']),(1,1))
    def test_known_unsupported_selector_and_context_copy_cannot_be_safe_names(self):
        for name in ('glNamedFramebufferReadBuffer','glNamedFramebufferReadBufferEXT',
                     'glFramebufferReadBufferEXT','glXCopyContext'):
            p=subprocess.run([str(self.exe),'safe',name],capture_output=True,timeout=15)
            with self.subTest(name=name):
                self.assertEqual(p.returncode,3,'unsafe allowlist must reject installation')
                self.assertEqual((p.stdout,p.stderr),(b'',b''))
        raw,status=sample(self.exe,'safe')
        self.assertTrue(decode(raw,status,'safe')['cpu_window_closed'])
    def test_original_context_returns_determine_creation_and_current_events(self):
        for mode in ('attrib','createfail','failedswitch','makeboth'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):self.assertTrue(decode(raw,s,mode)['cpu_window_closed']);self.assertEqual((s['args_ok'],s['errno_ok']),(1,1))
    def test_original_incoming_and_unchanged_errno_survive_every_layer(self):
        raw,s=sample(self.exe,'preserve');self.assertEqual((s['args_ok'],s['errno_ok'],s['regs_ok']),(1,1,1));self.assertTrue(decode(raw,s,'preserve')['cpu_window_closed'])
    def test_delivery_failures_continue_originals_but_reject_completion(self):
        for mode in ('mismatch','unknown','glerror','invalidate','display','thread','reentrant','shared','cap','destroy','pbo','footerfail'):
            raw,s=sample(self.exe,mode)
            with self.subTest(mode=mode):
                self.assertEqual((s['args_ok'],s['errno_ok'],s['regs_ok'],s['original_calls']),(1,1,1,2));self.assertNotEqual(s['finish'],0)
                with self.assertRaises(ValueError):decode(raw,s,mode)
    def test_off_error_is_not_hidden_by_core_footer(self):
        raw,s=sample(self.exe,'off');self.assertEqual(decode(raw,s,'off')['records'],())
        raw,s=sample(self.exe,'offinvalid')
        with self.assertRaises(ValueError):decode(raw,s,'offinvalid')

if __name__=='__main__':unittest.main()
