"""Real-diagnostic archive limits; no model or native runtime is invoked."""
import hashlib
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
import zipfile
from unittest.mock import patch

try:
    from bigbench import full_s_recorded_archive as archive
except ImportError:
    archive=None
from bigbench import recorded_worker_archive as canary


class RecordedArchiveTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(archive,'larger recorded-model archive receiver missing')

    def make(self,path,rows):
        with zipfile.ZipFile(path,'w') as z:
            for name,data in rows:
                info=zipfile.ZipInfo();info.filename=name;info.orig_filename=name;info.create_system=3
                info.external_attr=(stat.S_IFREG|0o644)<<16;info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,data)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_honest_recurrent_payload_above_canary_expanded_limit_uses_separate_caps(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'real-shapes.zip';block=b'x'*(8*1024**2)
            digest=self.make(path,[(f'step-{i:06d}/state.bin',block) for i in range(17)])
            with self.assertRaises(ValueError):canary.extract_archive(path,root/'old',expected_sha256=digest)
            result=archive.extract_archive(path,root/'new',expected_sha256=digest)
            self.assertEqual(sum(p.stat().st_size for p in result.rglob('*') if p.is_file()),136*1024**2)
            self.assertEqual((result/'step-000016/state.bin').read_bytes(),block)
            self.assertEqual(canary.CAP,64*1024**2)
            self.assertEqual(archive.CAP,384*1024**2)

    def test_count_member_total_limits_checked_before_extracting_or_allocating_zip_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'bad.zip';digest=self.make(path,[('small',b'x')]);raw=bytearray(path.read_bytes())
            end=raw.rfind(b'PK\x05\x06');struct.pack_into('<HH',raw,end+8,513,513);path.write_bytes(raw)
            with patch.object(zipfile,'ZipFile',side_effect=AssertionError('central allocation before limits')):
                with self.assertRaises(ValueError):archive.extract_archive(path,root/'out',expected_sha256=hashlib.sha256(raw).hexdigest())
            self.assertFalse((root/'out').exists())
            digest=self.make(path,[('huge',b'0'*(16*1024**2+1))])
            with self.assertRaises(ValueError):archive.extract_archive(path,root/'out',expected_sha256=digest)
            block=b'0'*(16*1024**2)
            digest=self.make(path,[(f'state-{i}.bin',block) for i in range(33)])
            with self.assertRaises(ValueError):archive.extract_archive(path,root/'out',expected_sha256=digest)
            self.assertFalse((root/'out').exists())

    def test_unsafe_raw_names_aliases_and_unsupported_compression_leave_no_output(self):
        rows=([('A',b'x'),('a',b'y')],[('x',b'x'),('x/y',b'y')],[('NUL',b'x')],[('a\\b',b'x')],
              [('../escape',b'x')],[('file.',b'x')],[('/escape',b'x')])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'bad.zip'
            for members in rows:
                digest=self.make(path,members)
                with self.subTest(names=[n for n,_ in members]),self.assertRaises(ValueError):archive.extract_archive(path,root/'out',expected_sha256=digest)
                self.assertFalse((root/'out').exists())
            digest=self.make(path,[('entry',b'x')]);raw=bytearray(path.read_bytes());cd=raw.find(b'PK\x01\x02')
            struct.pack_into('<H',raw,8,14);struct.pack_into('<H',raw,cd+10,14);path.write_bytes(raw)
            with self.assertRaises(ValueError):archive.extract_archive(path,root/'out',expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_late_bad_crc_or_stream_never_publishes_partial_destination_and_retry_works(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'artifact.zip';digest=self.make(path,[('first',b'ok'),('second',b'x'*100)])
            original=path.read_bytes();raw=bytearray(original);cd=raw.rfind(b'PK\x01\x02');offset=struct.unpack_from('<I',raw,cd+42)[0]
            wrong=12345;struct.pack_into('<I',raw,cd+16,wrong);struct.pack_into('<I',raw,offset+14,wrong);path.write_bytes(raw)
            with self.assertRaises(ValueError):archive.extract_archive(path,root/'out',expected_sha256=hashlib.sha256(raw).hexdigest())
            self.assertFalse((root/'out').exists());self.assertEqual(list(root.glob('.out-partial-*')),[])
            path.write_bytes(original);archive.extract_archive(path,root/'out',expected_sha256=digest)
            self.assertEqual((root/'out/second').read_bytes(),b'x'*100)


if __name__=='__main__':unittest.main()
