"""Owned child processes only; no Docker, installs, network or downloaded code."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
try:
 from scripts import engine_clock_image_process as process
except ImportError:process=None

class ImageProcessTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(process,'bounded image process capture missing')
 def command(self,source):return [sys.executable,'-I','-S','-B','-c',source]
 def test_owned_stdout_stderr_retained_with_actual_counts_hashes(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'process';r=process.capture(self.command("import sys;sys.stdout.write('owned');sys.stderr.write('error')"),out,timeout=5,stdout_limit=100,stderr_limit=100)
   self.assertEqual('EXITED',r['status']);self.assertEqual(0,r['returncode']);self.assertEqual(b'owned',(out/'stdout.bin').read_bytes());self.assertEqual(b'error',(out/'stderr.bin').read_bytes());self.assertEqual(hashlib.sha256(b'owned').hexdigest(),r['stdout_sha256']);self.assertTrue(r['streams_complete'])
 def test_output_limit_preserves_bounded_prefix_and_stops_owned_child(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'process';r=process.capture(self.command("import sys;sys.stdout.buffer.write(b'x'*1000000);sys.stdout.flush()"),out,timeout=5,stdout_limit=1024,stderr_limit=1024)
   self.assertEqual('OUTPUT_LIMIT',r['status']);self.assertLessEqual((out/'stdout.bin').stat().st_size,1024);self.assertGreater(r['stdout_observed_bytes'],1024);self.assertFalse(r['streams_complete']);self.assertTrue(r['termination_attempted'])
 def test_metadata_memory_mode_never_persists_secret_streams(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'process';r=process.capture(self.command("import sys;print('SECRET_SENTINEL');sys.stderr.write('SECRET_SENTINEL')"),out,timeout=5,stdout_limit=1024,stderr_limit=1024,keep_stdout=False,keep_stderr=False)
   self.assertIn(b'SECRET_SENTINEL',r['_stdout']);self.assertFalse((out/'stdout.bin').exists());self.assertFalse((out/'stderr.bin').exists());self.assertNotIn('SECRET_SENTINEL',json.dumps(process.public_receipt(r)));self.assertFalse(any(b'SECRET_SENTINEL' in p.read_bytes() for p in out.iterdir() if p.is_file()))
 def test_timeout_has_bounded_group_termination_and_partial_receipt(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=process.capture(self.command("import time;time.sleep(5)"),Path(tmp)/'process',timeout=.05,stdout_limit=100,stderr_limit=100);self.assertEqual('TIMEOUT',r['status']);self.assertTrue(r['termination_attempted']);self.assertFalse(r['streams_complete'])
 def test_owned_child_file_limit_keeps_export_partial_within_registered_cap(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);target=root/'large';source="from pathlib import Path;Path("+repr(str(target))+").write_bytes(b'x'*100000)"
   r=process.capture(self.command(source),root/'process',timeout=5,stdout_limit=1024,stderr_limit=1024,file_size_limit=1024);self.assertNotEqual(0,r['returncode']);self.assertLessEqual(target.stat().st_size,1024)
 def test_owned_stdin_and_redaction_do_not_write_original_secret(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'input';source.write_bytes(b'SECRET_SENTINEL')
   with source.open('rb') as data:r=process.capture(self.command("import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())"),root/'process',timeout=5,stdout_limit=100,stderr_limit=100,stdin=data,redact=lambda raw:raw.replace(b'SECRET_SENTINEL',b'[REDACTED]'));self.assertFalse(data.closed)
   self.assertEqual(b'[REDACTED]',(root/'process/stdout.bin').read_bytes());self.assertTrue(r['stdout_redacted']);self.assertEqual(15,r['stdout_observed_bytes']);self.assertEqual(0,r['returncode'])

if __name__=='__main__':unittest.main()
