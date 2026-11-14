"""Offline data decoder boundaries; no renderer or GL context."""
import importlib
import io
from pathlib import Path
import pickle
import struct
import sys
import time
import unittest

try:r=importlib.import_module('scripts.gl_trace_reader')
except ModuleNotFoundError as exc:
    if exc.name!='scripts.gl_trace_reader':raise
    r=None


class TraceReaderTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(r,'bounded offline trace decoder required')
    def test_pointer_is_the_only_permitted_pickle_global(self):
        payload=b'\x80\x02cunpickle\nPointer\nK*\x85\x81.'
        values=list(r.read_pickles(io.BytesIO(payload)))
        self.assertIsInstance(values[0],r.Pointer);self.assertEqual(values[0],42)
        with self.assertRaises(ValueError):list(r.read_pickles(io.BytesIO(pickle.dumps(len))))
    def test_truncated_record_is_not_normal_end_of_stream(self):
        payload=pickle.dumps((1,'glReadPixels',[],None,0),protocol=4)
        with self.assertRaises(ValueError):list(r.read_pickles(io.BytesIO(payload[:-1])))
        self.assertEqual(list(r.read_pickles(io.BytesIO(b''))),[])
    def test_byte_budget_and_oversized_pickle_request_fail_closed(self):
        with self.assertRaises(ValueError):list(r.read_pickles(io.BytesIO(pickle.dumps(b'x'*100)),max_bytes=30))
        huge=b'\x80\x04B'+struct.pack('<I',512*1024*1024+1)
        with self.assertRaises(ValueError):list(r.read_pickles(io.BytesIO(huge)))
        with self.assertRaises(ValueError):r.Limited(io.BytesIO(),2*1024**3).read(512*1024**2+1)
    def test_known_192mib_upload_request_fits_bounded_reader(self):
        # Empty backing data avoids allocating the retained blob in unit CI.
        self.assertEqual(r.Limited(io.BytesIO(),2*1024**3).read(192*1024**2),b'')
        self.assertEqual(r.Limited(io.BytesIO(),2*1024**3).read(507510784),b'')
    def test_thread_metadata_requires_single_gl_thread_and_order(self):
        lines=[b'// process.name = "original"\n',b'0 @0 glXCreateContext(dpy = NULL) = 0x42\n',b'2 @0 glBindFramebuffer(target = 1)\n']
        d=r.scan_threads(lines);self.assertEqual((d['thread_id'],d['calls']),(0,2))
        for tail in (b'3 @1 glReadPixels()\n',b'2 @0 glReadPixels()\n',b'3 glReadPixels()\n'):
            with self.subTest(tail=tail),self.assertRaises(ValueError):r.scan_threads(lines+[tail])
    def test_thread_metadata_line_byte_and_call_budgets(self):
        for lines,kwargs in (([b'x'*21],dict(max_line=20)),([b'0 @0 glReadPixels()\n'],dict(max_bytes=4)),
                            ([b'0 @0 glReadPixels()\n',b'1 @0 glReadPixels()\n'],dict(max_calls=1))):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):r.scan_threads(lines,**kwargs)
    def test_commands_allow_only_offline_modes_and_literal_paths(self):
        tool=Path('/tmp/apitrace');trace=Path('/tmp/$(not-a-command).trace')
        cmd=r.decoder_command(tool,'pickle',trace)
        self.assertEqual(cmd,[str(tool),'pickle',str(trace)])
        self.assertEqual(r.decoder_command(tool,'dump',trace)[-1],str(trace))
        self.assertIn('--verbose',r.decoder_command(tool,'dump',trace),'default dump omits recorded verbose calls')
        for mode in ('replay','trace','dump;replay'):
            with self.subTest(mode=mode),self.assertRaises(ValueError):r.decoder_command(tool,mode,trace)
    def test_wrong_binary_is_rejected_before_starting_decoder(self):
        with self.assertRaises(ValueError):r.verify_tool(Path(sys.executable),Path(sys.executable))
    def test_real_cpu_child_output_and_nonzero_exit_are_checked(self):
        cmd=[sys.executable,'-I','-S','-B','-c','import pickle,sys;sys.stdout.buffer.write(pickle.dumps((1,"glReadPixels",[],None,0)))']
        with r.process_stdout(cmd,timeout=2) as pipe:self.assertEqual(list(r.read_pickles(pipe))[0][1],'glReadPixels')
        with self.assertRaises(ValueError):
            with r.process_stdout([sys.executable,'-I','-S','-B','-c','raise SystemExit(3)'],timeout=2) as pipe:list(r.read_pickles(pipe))
    def test_stalled_cpu_decoder_is_terminated_with_timeout(self):
        start=time.monotonic()
        with self.assertRaises(ValueError):
            with r.process_stdout([sys.executable,'-I','-S','-B','-c','import time;time.sleep(5)'],timeout=.1) as pipe:pipe.read()
        self.assertLess(time.monotonic()-start,2)
    def test_primary_consumer_exception_survives_process_cleanup(self):
        original=RuntimeError('consumer stopped')
        try:
            with r.process_stdout([sys.executable,'-I','-S','-B','-c','import time;time.sleep(5)'],timeout=2):raise original
        except RuntimeError as exc:self.assertIs(exc,original)
        else:self.fail('consumer failure swallowed')


if __name__=='__main__':unittest.main()
