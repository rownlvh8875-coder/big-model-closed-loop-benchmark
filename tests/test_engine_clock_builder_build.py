"""Production source-snapshot orchestration with owned dependency fixtures."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

try:
    from scripts import engine_clock_builder_build as build
except ImportError:
    build = None


class BuildSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(build, 'owned pre-execution source hook missing')
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name);self.tmp_root = self.base / 'tmp';self.tmp_root.mkdir()
        self.location = self.tmp_root / 'pip-wheel-fixture' / ('progressbar_' + 'a' * 32)
        self.location.mkdir(parents=True)
        self.payloads = {'README.txt': b'readme', 'setup.py': b'setup', 'LICENSE.txt': b'license',
                         'progressbar/__init__.py': b'runtime'}
        self.rows = [{'path': p, 'sha256': hashlib.sha256(b).hexdigest()} for p, b in self.payloads.items()]
        def unpack(link, location, *args, **kwargs):
            for p, b in self.payloads.items():
                path = Path(location) / p;path.parent.mkdir(exist_ok=True, parents=True);path.write_bytes(b)
            return 'unpacked'
        self.original = unpack
        self.prepare = SimpleNamespace(unpack_url=unpack)

    def run_build(self, pip_main):
        return build.run_with_snapshots(self.prepare, pip_main, self.rows,
                                        tmp_root=self.tmp_root, evidence_root=self.base)

    def test_before_manifest_exists_before_any_source_callback_and_after_is_retained(self):
        def pip_main(args):
            self.assertNotIn('--no-compile', args)
            self.assertIn('--require-hashes', args)
            self.assertEqual('unpacked', self.prepare.unpack_url('fixture', str(self.location), None, 0))
            before = json.loads((self.base / 'source-before.json').read_bytes())
            self.assertEqual({r['path']: r['sha256'] for r in self.rows}, before['files_sha256'])
            (self.location / 'README.txt').write_bytes(b'generated')
            path = self.location / 'build/lib/progressbar/__init__.py';path.parent.mkdir(parents=True);path.write_bytes(b'runtime')
            print('SECRET_SENTINEL')
            return 0
        result = self.run_build(pip_main)
        self.assertEqual('SOURCE_SNAPSHOTS_VERIFIED', result['status'])
        self.assertEqual(4, result['before']['files'])
        self.assertEqual(5, result['after']['files'])
        self.assertNotEqual(result['before']['files_sha256']['README.txt'], result['after']['files_sha256']['README.txt'])
        self.assertNotIn('SECRET_SENTINEL', json.dumps(result))
        self.assertTrue((self.base / 'source-after.json').exists())
        self.assertIs(self.original, self.prepare.unpack_url)

    def test_wrong_unpacked_source_prevents_source_callback(self):
        self.payloads['setup.py'] = b'changed'
        executed = []
        def pip_main(args):
            self.prepare.unpack_url('fixture', str(self.location), None, 0)
            executed.append(True)
            return 0
        with self.assertRaisesRegex(ValueError, '^SOURCE_PAYLOAD_MISMATCH$'):self.run_build(pip_main)
        self.assertEqual([], executed)
        self.assertIs(self.original, self.prepare.unpack_url)

    def test_missing_multiple_or_wrong_layout_is_not_admitted(self):
        for mode in ('missing', 'multiple', 'layout'):
            def pip_main(args):
                if mode == 'missing':return 0
                location = self.location if mode == 'multiple' else self.tmp_root / 'pip-req-build-wrong'
                self.prepare.unpack_url('fixture', str(location), None, 0)
                self.prepare.unpack_url('fixture', str(location), None, 0)
                return 0
            with self.assertRaises(ValueError):self.run_build(pip_main)
            self.assertIs(self.original, self.prepare.unpack_url)

    def test_unexpected_source_mutation_rejects_and_actual_files_remain(self):
        def pip_main(args):
            self.prepare.unpack_url('fixture', str(self.location), None, 0)
            (self.location / 'setup.py').write_bytes(b'changed')
            return 0
        with self.assertRaises(ValueError):self.run_build(pip_main)
        self.assertEqual(b'changed', (self.location / 'setup.py').read_bytes())
        self.assertTrue((self.base / 'source-before.json').exists())
        after = json.loads((self.base / 'source-after.json').read_bytes())
        self.assertEqual(hashlib.sha256(b'changed').hexdigest(), after['files_sha256']['setup.py'])

    def test_linked_location_cannot_escape_to_host_tree(self):
        external = self.base / 'external';external.mkdir();(external / 'sentinel').write_bytes(b'safe')
        self.location.rmdir();self.location.symlink_to(external)
        def pip_main(args):
            self.prepare.unpack_url('fixture', str(self.location), None, 0)
            return 0
        with self.assertRaises(ValueError):self.run_build(pip_main)
        self.assertEqual([self.base / 'external/sentinel'], list(external.iterdir()))


if __name__ == '__main__':unittest.main()
