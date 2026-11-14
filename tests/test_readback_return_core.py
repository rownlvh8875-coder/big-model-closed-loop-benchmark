"""Compiled CPU fake originals. No GL/Panda import, linkage, context or execution."""
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
NONCE=bytes(range(1,33))
HEADER=struct.Struct('<8sIIQ32sIIIIQiiiiIIIIIIIIQQQQ')
FOOTER=struct.Struct('<8sII32sQQQQQII')

def compile_fixture(out,*,sanitize=False):
    cc=shutil.which('cc')
    if not cc:raise RuntimeError('CPU C compiler required')
    command=[cc,'-std=c11','-O1' if sanitize else '-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'native'),
        str(ROOT/'native/readback_return_core.c'),str(ROOT/'tests/fixtures/readback_return_fixture.c'),'-o',str(out)]
    if sanitize:command[1:1]=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie']
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    if result.returncode:raise RuntimeError(result.stderr)
    return command

def fixture_result(executable,mode):
    p=subprocess.run([str(executable),mode],capture_output=True,timeout=15)
    if p.returncode:raise AssertionError(p.stderr.decode(errors='replace')[:1000])
    return p.stdout,json.loads(p.stderr)

def split_records(raw):
    rows=[];offset=0
    while raw[offset:offset+8]==b'RBRET001':
        header=HEADER.unpack_from(raw,offset);n=header[22];payload=raw[offset+HEADER.size:offset+HEADER.size+n]
        if len(payload)!=n:raise AssertionError('short fixture payload')
        rows.append((header,payload));offset+=HEADER.size+n
    tail=FOOTER.unpack_from(raw,offset)
    if offset+FOOTER.size!=len(raw):raise AssertionError('extra fixture bytes')
    return rows,tail

class ReturnCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=None;cls.executable=None
        if all((ROOT/p).exists() for p in ('native/readback_return_core.h','native/readback_return_core.c')):
            cls.temp=tempfile.TemporaryDirectory(prefix='rb-core-test-');cls.executable=Path(cls.temp.name)/'fixture'
            compile_fixture(cls.executable)
    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()
    def setUp(self):self.assertIsNotNone(self.executable,'C return-buffer core required')
    def test_exact_original_forwarding_and_independent_wire_layout(self):
        raw,s=fixture_result(self.executable,'basic');rows,tail=split_records(raw)
        self.assertEqual((HEADER.size,FOOTER.size),(160,96));self.assertEqual(len(rows),2)
        self.assertEqual((s['original_calls'],s['args_ok'],s['source_unchanged'],s['errno_ok'],s['error']),(2,1,1,1,0))
        h,p=rows[0];self.assertEqual(h[:8],(b'RBRET001',1,160,1,NONCE,1,1,1))
        self.assertEqual(h[8:16],(8,101,-7,11,5,3,0x80e0,0x1401));self.assertEqual(p[:3],bytes([77,1,10]))
        self.assertEqual(tail[:4],(b'RBEND001',1,96,NONCE));self.assertEqual(tail[4:9],(2,2,2,len(raw)-96,1))
        self.assertEqual(tail[9:],(0,1))
    def test_off_never_reads_even_invalid_metadata_or_source_pointer(self):
        raw,s=fixture_result(self.executable,'off');rows,tail=split_records(raw)
        self.assertEqual(rows,[]);self.assertEqual(s['original_calls'],2);self.assertEqual(s['error'],0)
        self.assertEqual((s['captured'],s['attempts'],s['emits']),(0,0,1));self.assertEqual(tail[9:],(0,0))
    def test_pack_padding_and_skip_bytes_are_not_serialized(self):
        raw,s=fixture_result(self.executable,'packed');rows,_=split_records(raw);h,p=rows[0]
        self.assertEqual(s['error'],0);self.assertEqual((h[16],h[17],h[18],h[19]),(4,8,1,2))
        self.assertEqual((h[22],h[23],h[24]),(60,32,68));self.assertNotIn(238,p);self.assertEqual(p[:4],bytes([77,1,10,201]))
    def test_rgb_rgba_bgr_bgra_component_bytes_preserved(self):
        for mode,want in [('rgb',[10,1,77]),('rgba',[10,1,77,201]),('bgra',[77,1,10,201]),('basic',[77,1,10])]:
            raw,s=fixture_result(self.executable,mode);rows,_=split_records(raw)
            with self.subTest(mode=mode):self.assertEqual(s['error'],0);self.assertEqual(rows[0][1][:len(want)],bytes(want))
    def test_unsupported_state_pbo_extent_alias_and_overlap_fail_but_forward(self):
        for mode in ('unknown','pbo','short','alias','overlap'):
            raw,s=fixture_result(self.executable,mode)
            with self.subTest(mode=mode):
                self.assertEqual(s['original_calls'],2);self.assertEqual(s['args_ok'],1);self.assertEqual(s['errno_ok'],1)
                self.assertNotEqual(s['error'],0);self.assertEqual(s['captured'],0)
    def test_observer_budget_failure_never_retries_or_suppresses_original(self):
        for mode,count in [('limit',1),('bytes',0)]:
            _,s=fixture_result(self.executable,mode)
            with self.subTest(mode=mode):self.assertEqual(s['original_calls'],2);self.assertEqual(s['captured'],count);self.assertNotEqual(s['error'],0)
    def test_emitter_failure_is_sticky_and_original_errno_survives(self):
        raw,s=fixture_result(self.executable,'emitfail');self.assertEqual(s['original_calls'],2)
        self.assertEqual(s['captured'],0);self.assertNotEqual(s['error'],0);self.assertEqual(s['errno_ok'],1)
        self.assertFalse(raw.endswith(b'RBEND001'))
    def test_wrong_thread_and_reentrant_paths_only_forward_and_fail(self):
        for mode in ('thread','reentrant'):
            _,s=fixture_result(self.executable,mode)
            with self.subTest(mode=mode):self.assertEqual(s['original_calls'],2);self.assertEqual(s['captured'],0);self.assertNotEqual(s['error'],0)
    def test_state_is_snapshotted_before_original_mutates_metadata(self):
        raw,s=fixture_result(self.executable,'mutate');rows,_=split_records(raw)
        self.assertEqual(s['error'],0);self.assertEqual(len(rows),2);self.assertEqual(rows[0][0][25],8*1024*1024)
    def test_nested_scope_and_missing_original_call_cannot_complete(self):
        for mode in ('nested','shortwindow'):
            _,s=fixture_result(self.executable,mode)
            with self.subTest(mode=mode):self.assertNotEqual(s['error'],0);self.assertNotEqual(s['finish'],0)
    def test_excess_reads_forward_without_exceeding_per_window_copy_budget(self):
        for mode,limit,forwards in (('excess1',1,2),('excess2',2,3)):
            raw,s=fixture_result(self.executable,mode);rows,tail=split_records(raw)
            with self.subTest(mode=mode):
                self.assertEqual(s['original_calls'],forwards);self.assertEqual(s['forwards'],forwards)
                self.assertEqual((s['args_ok'],s['errno_ok'],s['source_unchanged']),(1,1,1))
                self.assertEqual((s['captured'],s['attempts'],len(rows)),(limit,limit,limit))
                self.assertNotEqual(s['error'],0);self.assertNotEqual(tail[9],0)

if __name__=='__main__':unittest.main()
