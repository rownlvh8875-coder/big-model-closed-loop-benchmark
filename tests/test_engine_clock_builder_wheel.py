"""Synthetic wheel bytes only; no installed package or source execution."""
import base64
import csv
import hashlib
import io
import struct
import unittest
import zipfile

try:
    from scripts import engine_clock_builder_wheel as wheel
except ImportError:
    wheel = None

D = 'progressbar-2.5.dist-info/'
RUNTIME = ['progressbar/' + n for n in ('__init__.py', 'compat.py', 'progressbar.py', 'widgets.py')]


def fixture(changes=None, omit=(), extra=None, compression=zipfile.ZIP_DEFLATED):
    payloads = {p: ('# ' + p + '\n').encode() for p in RUNTIME}
    payloads[D + 'licenses/LICENSE.txt'] = b'fixture license\n'
    pins = {p: hashlib.sha256(b).hexdigest() for p, b in payloads.items()}
    payloads.update({D + 'METADATA': b'Metadata-Version: 2.4\nName: progressbar\nVersion: 2.5\n\nfixture\n',
                     D + 'WHEEL': b'Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
                     D + 'top_level.txt': b'progressbar\n'})
    payloads.update(changes or {})
    payloads.update(extra or {})
    for p in omit:
        payloads.pop(p)
    record = io.StringIO(newline='')
    writer = csv.writer(record, lineterminator='\n')
    for p, b in sorted(payloads.items()):
        writer.writerow([p, 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(b).digest()).decode().rstrip('='), str(len(b))])
    writer.writerow([D + 'RECORD', '', ''])
    payloads[D + 'RECORD'] = record.getvalue().encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=compression) as z:
        for p, b in payloads.items():
            z.writestr(p, b)
    return out.getvalue(), pins


class WheelTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(wheel, 'strict wheel validator missing')

    def reject(self, raw, pins):
        r = wheel.validate_wheel(raw, pins)
        self.assertEqual('REJECTED', r['status'])
        self.assertNotIn('SECRET_SENTINEL', str(r))
        self.assertFalse(r['native_admission'])

    def test_valid_deflated_and_stored_bytes(self):
        for compression in (zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED):
            raw, pins = fixture(compression=compression)
            r = wheel.validate_wheel(raw, pins)
            self.assertEqual('WHEEL_BYTES_MATCH', r['status'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), r['wheel_sha256'])
            self.assertEqual(9, r['member_count'])
            self.assertFalse(r['image_preparation_ready'])

    def test_payload_license_and_member_closure(self):
        for kwargs in ({'changes': {RUNTIME[0]: b'changed'}},
                       {'changes': {D + 'licenses/LICENSE.txt': b'changed'}},
                       {'omit': [RUNTIME[1]]}, {'extra': {'SECRET_SENTINEL': b'x'}},
                       {'extra': {'../bad': b'x'}}):
            raw, pins = fixture(**kwargs)
            self.reject(raw, pins)

    def test_metadata_dependencies_duplicates_and_version(self):
        for fields in (b'Name: wrong\nVersion: 2.5\n', b'Name: progressbar\nVersion: 3\n',
                       b'Name: progressbar\nName: progressbar\nVersion: 2.5\n',
                       b'Name: progressbar\nVersion: 2.5\nRequires-Dist: x\n'):
            raw, pins = fixture({D + 'METADATA': fields + b'\n'})
            self.reject(raw, pins)

    def test_wheel_tag_and_purelib(self):
        for value in (b'Root-Is-Purelib: false\nTag: py3-none-any\n',
                      b'Root-Is-Purelib: true\nTag: cp311-none-linux_x86_64\n',
                      b'Root-Is-Purelib: true\nTag: py3-none-any\nTag: py3-none-any\n'):
            raw, pins = fixture({D + 'WHEEL': b'Wheel-Version: 1.0\n' + value})
            self.reject(raw, pins)

    def test_top_level(self):
        raw, pins = fixture({D + 'top_level.txt': b'other\n'})
        self.reject(raw, pins)

    def test_outer_padding_comment_truncation_and_crc(self):
        raw, pins = fixture()
        for data in (b'x' + raw, raw + b'x', raw[:-1], raw[:-2] + b'\x01\0x'):
            self.reject(data, pins)
        data = bytearray(raw)
        data[50] ^= 1
        self.reject(bytes(data), pins)

    def test_local_central_mismatch_and_extra(self):
        raw, pins = fixture()
        for offset in (6, 8, 14, 18, 22, 28):
            data = bytearray(raw)
            data[offset] ^= 1
            self.reject(bytes(data), pins)

    def test_duplicate_members(self):
        raw, pins = fixture()
        out = io.BytesIO(raw)
        with zipfile.ZipFile(out, 'a') as z:
            z.writestr(RUNTIME[0], b'x')
        self.reject(out.getvalue(), pins)

    def test_executable_special_or_link_modes_reject(self):
        raw, pins = fixture()
        central = struct.unpack_from('<I', raw, len(raw) - 6)[0]
        for mode in (0o104644, 0o100755, 0o120777):
            data = bytearray(raw)
            struct.pack_into('<I', data, central + 38, mode << 16)
            self.reject(bytes(data), pins)

    def test_record_hash_size_coverage(self):
        raw, pins = fixture()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            payloads = {p: z.read(p) for p in z.namelist()}
        original = payloads[D + 'RECORD']
        for value in (original.replace(b'sha256=', b'sha512=', 1),
                      original.split(b'\n', 1)[1], original + original.split(b'\n')[0] + b'\n',
                      original.replace(b',0\n', b',1\n') if b',0\n' in original else original.replace(b',38\n', b',39\n') + b'bad\n'):
            out = io.BytesIO()
            with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                for p, b in payloads.items():
                    z.writestr(p, value if p.endswith('/RECORD') else b)
            self.reject(out.getvalue(), pins)

    def test_hidden_compressed_tail(self):
        raw, pins = fixture()
        data = bytearray(raw)
        # Insert one hidden byte after the first compressed stream, adjusting all
        # surrounding offsets/sizes so ordinary ZipFile.read still accepts it.
        csize = struct.unpack_from('<I', data, 18)[0]
        name_len = struct.unpack_from('<H', data, 26)[0]
        end = 30 + name_len + csize
        data[end:end] = b'X'
        struct.pack_into('<I', data, 18, csize + 1)
        eocd = len(data) - 22
        central = struct.unpack_from('<I', data, eocd + 16)[0] + 1
        struct.pack_into('<I', data, eocd + 16, central)
        cursor = central
        for i in range(9):
            if i == 0:
                struct.pack_into('<I', data, cursor + 20, csize + 1)
            else:
                off = struct.unpack_from('<I', data, cursor + 42)[0]
                struct.pack_into('<I', data, cursor + 42, off + 1)
            n, x, c = struct.unpack_from('<3H', data, cursor + 28)
            cursor += 46 + n + x + c
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self.assertTrue(z.read(RUNTIME[0]))
        self.reject(bytes(data), pins)

    def test_size_limit_and_invalid_pins_do_not_echo(self):
        raw, pins = fixture()
        self.reject(b'x' * (1048576 + 1), pins)
        self.reject(raw, {'SECRET_SENTINEL': 'bad'})


if __name__ == '__main__':
    unittest.main()
