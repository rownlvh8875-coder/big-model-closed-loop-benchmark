import ctypes
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

try:
    from scripts import readback_process_mapping as mapping
except ImportError:
    mapping = None


def symbol_ranges(path, names):
    output = subprocess.check_output(['nm', '-S', '--defined-only', str(path)], text=True)
    found = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) == 4 and fields[3] in names:
            found[fields[3]] = {'vaddr': int(fields[0], 16), 'size': int(fields[1], 16)}
    if set(found) != set(names):
        raise AssertionError('missing CPU probe symbol')
    return found


class ProcessMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='mapping-cpu-')
        cls.path = Path(cls.temp.name) / 'probe.so'
        source = cls.path.with_suffix('.c')
        source.write_text('int mapping_cpu_probe(int n) { return n + 7; }\n')
        subprocess.run([shutil.which('cc'), '-shared', '-fPIC', '-O2', str(source), '-o', str(cls.path)], check=True)
        cls.blob = cls.path.read_bytes()
        cls.sha = hashlib.sha256(cls.blob).hexdigest()
        cls.profile = symbol_ranges(cls.path, {'mapping_cpu_probe'})
        # Only this locally compiled CPU library is loaded; no renderer/provider imports.
        cls.library = ctypes.CDLL(str(cls.path))
        cls.addresses = {'mapping_cpu_probe': ctypes.cast(cls.library.mapping_cpu_probe, ctypes.c_void_p).value}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.assertIsNotNone(mapping, 'process code checker required')

    def verify(self, **overrides):
        args = dict(pid=os.getpid(), path=self.path, expected_sha=self.sha,
                    ranges=self.profile, reported_addresses=self.addresses)
        args.update(overrides)
        return mapping.verify_process_code(**args)

    def test_actual_owned_cpu_code_matches_file_and_memory(self):
        self.assertEqual(self.library.mapping_cpu_probe(5), 12)
        result = self.verify()
        self.assertTrue(result['process_code_verified'])
        self.assertFalse(result['native_admitted'])
        self.assertFalse(result['panda_runtime_mapping_verified'])
        self.assertEqual(result['file_sha256'], self.sha)
        self.assertEqual(result['ranges']['mapping_cpu_probe']['size'], self.profile['mapping_cpu_probe']['size'])

    def test_wrong_hash_address_pid_and_symlink_are_rejected(self):
        link = self.path.with_name('alias.so')
        link.symlink_to(self.path)
        try:
            for args in ({'expected_sha': '0' * 64}, {'pid': -1}, {'pid': 2**31 - 1},
                         {'path': link}, {'reported_addresses': {'mapping_cpu_probe': self.addresses['mapping_cpu_probe'] + 1}}):
                with self.subTest(args=args), self.assertRaises(ValueError):
                    self.verify(**args)
        finally:
            link.unlink()

    def test_maps_parser_rejects_malformed_overlapping_and_unbounded_rows(self):
        good = b'1000-2000 r-xp 00000000 08:01 7 /tmp/cpu.so\n'
        self.assertEqual(mapping.parse_maps(good)[0]['inode'], 7)
        for bad in (b'garbage', good + good, good.replace(b'1000-2000', b'2000-1000'),
                    good.replace(b'r-xp', b'bad!'), b'x' * (1024 * 1024 + 1), good * 4097):
            with self.subTest(length=len(bad)), self.assertRaises(ValueError):
                mapping.parse_maps(bad)

    def test_elf_parser_rejects_wrong_format_and_truncated_program_headers(self):
        self.assertTrue(mapping.elf_ranges(self.blob))
        for bad in (b'', self.blob[:63], b'BAD!' + self.blob[4:], self.blob[:100],
                    self.blob[:4] + b'\x01' + self.blob[5:], self.blob[:18] + b'\x03\x00' + self.blob[20:]):
            with self.subTest(size=len(bad)), self.assertRaises(ValueError):
                mapping.elf_ranges(bad)

    def test_pure_mapping_validator_rejects_protection_offset_identity_and_bytes(self):
        rows = mapping.parse_maps(Path('/proc/self/maps').read_bytes())
        st = self.path.stat()
        key = (os.major(st.st_dev), os.minor(st.st_dev), st.st_ino, str(self.path))
        addr = self.addresses['mapping_cpu_probe']
        selected = next(row for row in rows if row['start'] <= addr < row['end'])
        fd = os.open('/proc/self/mem', os.O_RDONLY)
        try:
            read = lambda start, size: os.pread(fd, size, start)
            self.assertTrue(mapping.check_code_ranges(self.blob, rows, key, self.profile, self.addresses, read))
            changes = ({'perms': 'rwxp'}, {'offset': selected['offset'] + 4096},
                       {'inode': st.st_ino + 1}, {'path': str(self.path) + ' (deleted)'})
            for change in changes:
                changed = tuple(dict(row, **change) if row is selected else row for row in rows)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    mapping.check_code_ranges(self.blob, changed, key, self.profile, self.addresses, read)
            for read_bad in (lambda start, size: b'\0' * size, lambda start, size: b''):
                with self.assertRaises(ValueError):
                    mapping.check_code_ranges(self.blob, rows, key, self.profile, self.addresses, read_bad)
        finally:
            os.close(fd)

    def test_range_budgets_and_exact_named_addresses(self):
        for profile, addresses in (({}, {}), (self.profile, {}),
                                   ({'mapping_cpu_probe': {'vaddr': 0, 'size': 1048577}}, self.addresses),
                                   ({'mapping_cpu_probe': {'vaddr': True, 'size': 1}}, self.addresses)):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                self.verify(ranges=profile, reported_addresses=addresses)


if __name__ == '__main__':
    unittest.main()
