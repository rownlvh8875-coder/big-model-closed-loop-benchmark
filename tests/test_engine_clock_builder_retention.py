"""Actual bounded workspace archives, including partial-failure fixtures."""
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
from time import perf_counter
import unittest

try:
    from scripts import engine_clock_builder_retention as retention
except ImportError:
    retention = None


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(retention, 'bounded workspace preservation missing')
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name);self.work = self.base / 'work';self.work.mkdir()
        self.out = self.base / 'out';self.out.mkdir()

    def preserve(self, **kwargs):
        return retention.preserve_workspaces({'workspace': self.work}, self.out,
                    deadline=perf_counter() + 10, **kwargs)

    def test_original_partial_download_and_partial_root_are_retained(self):
        (self.work / 'inputs').mkdir();(self.work / 'root/usr').mkdir(parents=True)
        (self.work / 'inputs/original.tar.gz').write_bytes(b'original')
        (self.work / 'inputs/source.whl.partial').write_bytes(b'partial')
        (self.work / 'root/usr/file').write_bytes(b'partially staged')
        result = self.preserve()
        self.assertEqual('PRESERVED_AVAILABLE_WORKSPACES', result['status'])
        with tarfile.open(self.out / 'retained-workspaces.tar.gz', 'r:gz') as archive:
            self.assertEqual(b'original', archive.extractfile('workspace/inputs/original.tar.gz').read())
            self.assertEqual(b'partial', archive.extractfile('workspace/inputs/source.whl.partial').read())
            self.assertEqual(b'partially staged', archive.extractfile('workspace/root/usr/file').read())
        inventory = json.loads((self.out / 'retained-inventory.json').read_bytes())
        entry = next(e for e in inventory['entries'] if e['path'].endswith('source.whl.partial'))
        self.assertEqual(hashlib.sha256(b'partial').hexdigest(), entry['sha256'])
        self.assertFalse(result['native_admission'])

    def test_links_are_archived_as_links_without_reading_host_targets(self):
        sentinel = self.base / 'host-sentinel';sentinel.write_bytes(b'SECRET_SENTINEL')
        (self.work / 'absolute').symlink_to(sentinel)
        result = self.preserve();self.assertEqual('PRESERVED_AVAILABLE_WORKSPACES', result['status'])
        with tarfile.open(self.out / 'retained-workspaces.tar.gz', 'r:gz') as archive:
            member = archive.getmember('workspace/absolute')
            self.assertTrue(member.issym());self.assertEqual(str(sentinel), member.linkname)
            self.assertNotIn(b'SECRET_SENTINEL', b''.join(archive.extractfile(m).read() for m in archive if m.isfile()))

    def test_decoded_file_node_archive_and_deadline_caps_leave_partial_evidence(self):
        for kind, kwargs in [('decoded', {'max_bytes': 3}), ('file', {'max_file': 3}),
                             ('nodes', {'max_nodes': 1}), ('archive', {'max_archive': 16})]:
            out = self.base / kind;out.mkdir()
            (self.work / 'data').write_bytes(b'larger than cap')
            result = retention.preserve_workspaces({'workspace': self.work}, out,
                        deadline=perf_counter() + 10, **kwargs)
            self.assertEqual('PRESERVATION_INCOMPLETE', result['status'])
            self.assertTrue((out / 'retention.json').exists())
            self.assertTrue((self.work / 'data').exists())
        out = self.base / 'deadline';out.mkdir()
        result = retention.preserve_workspaces({'workspace': self.work}, out, deadline=perf_counter() - 1)
        self.assertEqual('PRESERVATION_INCOMPLETE', result['status'])

    def test_missing_roots_are_explicit_and_existing_output_never_overwritten(self):
        result = retention.preserve_workspaces({'workspace': self.work, 'build': self.base / 'missing'},
                    self.out, deadline=perf_counter() + 10)
        self.assertEqual(['build'], result['missing_roots'])
        original = (self.out / 'retained-workspaces.tar.gz').read_bytes()
        second = self.preserve()
        self.assertEqual('PRESERVATION_INCOMPLETE', second['status'])
        self.assertEqual(original, (self.out / 'retained-workspaces.tar.gz').read_bytes())


if __name__ == '__main__':unittest.main()
