import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

try:
    from scripts.readback_elf_imports import inspect_imports
except ImportError:
    inspect_imports = None

ROOT = Path(__file__).resolve().parents[1]


def compile_import_fixture(path):
    command = [shutil.which('cc'), '-shared', '-fPIC', '-O2', '-Wl,-z,now',
               str(ROOT/'tests/fixtures/readback_import_fixture.c'), '-o', str(path)]
    subprocess.run(command, check=True, capture_output=True, timeout=20)
    return command


def dynamic_locations(blob):
    phoff = struct.unpack_from('<Q', blob, 32)[0]
    phnum = struct.unpack_from('<H', blob, 56)[0]
    for index in range(phnum):
        ph = struct.unpack_from('<IIQQQQQQ', blob, phoff + 56*index)
        if ph[0] == 2:
            offset, size = ph[2], ph[5]
            return [(i, *struct.unpack_from('<qQ', blob, i)) for i in range(offset, offset+size, 16)]
    raise AssertionError('fixture missing dynamic table')


def changed_tag(blob, tag, value):
    result = bytearray(blob)
    row = next(row for row in dynamic_locations(blob) if row[1] == tag)
    struct.pack_into('<Q', result, row[0]+8, value)
    return bytes(result)


class ElfImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='pc-elf-')
        cls.path = Path(cls.temp.name)/'imports.so'
        compile_import_fixture(cls.path)
        cls.blob = cls.path.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.assertIsNotNone(inspect_imports, 'loader-backed ELF import reader required')

    def test_actual_cpu_elf_imports_include_address_taken_function(self):
        result = inspect_imports(self.blob)
        gl = {row['name']: row for row in result['imports'] if row['name'].startswith('gl')}
        self.assertEqual(set(gl), {'glReadPixels', 'glXCreateContext', 'glPixelStorei'})
        self.assertEqual(gl['glPixelStorei']['relocation_type'], 6)
        self.assertEqual(gl['glReadPixels']['relocation_type'], 7)
        self.assertEqual(gl['glXCreateContext']['relocation_type'], 7)
        self.assertIn('libc.so.6', result['needed_libraries'])
        self.assertEqual(result['elf_sha256'], hashlib.sha256(self.blob).hexdigest())
        self.assertFalse(result['runtime_admission_ready'])
        # Independent binutils output must name the same literal imports at those slots.
        output = subprocess.check_output(['readelf', '-rW', str(self.path)], text=True)
        for name, row in gl.items():
            lines = [line for line in output.splitlines() if name in line]
            self.assertEqual(len(lines), 1)
            self.assertEqual(int(lines[0].split()[0], 16), row['slot_vaddr'])

    def test_loader_tables_work_without_any_section_headers(self):
        blob = bytearray(self.blob)
        struct.pack_into('<Q', blob, 40, 0)
        struct.pack_into('<HHH', blob, 58, 0, 0, 0)
        result = inspect_imports(bytes(blob))
        self.assertEqual({x['name'] for x in result['imports'] if x['name'].startswith('gl')},
                         {'glReadPixels', 'glXCreateContext', 'glPixelStorei'})

    def test_foreign_truncated_and_corrupt_loader_inputs_reject(self):
        bad_machine = bytearray(self.blob)
        struct.pack_into('<H', bad_machine, 18, 3)
        for blob in (b'', self.blob[:63], b'BAD!' + self.blob[4:], bytes(bad_machine),
                     self.blob[:4096], changed_tag(self.blob, 5, 2**64-8),
                     changed_tag(self.blob, 6, 2**64-8), changed_tag(self.blob, 11, 16),
                     changed_tag(self.blob, 9, 16), changed_tag(self.blob, 20, 17),
                     changed_tag(self.blob, 10, 4*1024*1024+1), changed_tag(self.blob, 2, 25)):
            with self.subTest(size=len(blob)), self.assertRaises(ValueError):
                inspect_imports(blob)

    def test_duplicate_and_unterminated_dynamic_entries_reject(self):
        locations = dynamic_locations(self.blob)
        nonnull = [row for row in locations if row[1]]
        duplicate = bytearray(self.blob)
        # Replace a benign unique entry with a second DT_SYMTAB; never trust first/last-wins.
        struct.pack_into('<qQ', duplicate, nonnull[0][0], 6, next(row[2] for row in locations if row[1] == 6))
        missing_null = bytearray(self.blob)
        for offset, tag, value in locations:
            if tag == 0:
                struct.pack_into('<qQ', missing_null, offset, 1, 1)
        for blob in (bytes(duplicate), bytes(missing_null)):
            with self.assertRaises(ValueError):
                inspect_imports(blob)

    def test_loader_table_overlap_and_unmapped_slot_reject(self):
        locations = dynamic_locations(self.blob)
        tags = {tag: value for _, tag, value in locations if tag}
        overlap = changed_tag(self.blob, 23, tags[7])
        bad_slot = bytearray(self.blob)
        # This small CPU fixture's read-only JMPREL VA equals its file offset.
        struct.pack_into('<Q', bad_slot, tags[23], 2**64-8)
        for blob in (overlap, bytes(bad_slot)):
            with self.assertRaises(ValueError):
                inspect_imports(blob)


if __name__ == '__main__':
    unittest.main()
