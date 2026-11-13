"""Driver verification on owned fixture files, without bootstrap execution."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

try:
    from scripts import engine_clock_builder_driver as driver
except ImportError:
    driver = None


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(driver, 'owned driver missing')
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_tool_payloads_match_and_generated_metadata_is_recorded(self):
        site = self.root / 'site';site.mkdir()
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as z:
            z.writestr('tool/__init__.py', b'original')
            z.writestr('tool-1.dist-info/RECORD', b'old record')
        whl = self.root / 'tool.whl';whl.write_bytes(raw.getvalue())
        (site / 'tool').mkdir();(site / 'tool/__init__.py').write_bytes(b'original')
        (site / 'tool-1.dist-info').mkdir();(site / 'tool-1.dist-info/RECORD').write_bytes(b'new record')
        (site / 'tool-1.dist-info/INSTALLER').write_bytes(b'pip\n')
        receipt = driver.verify_tools(site, [whl])
        self.assertEqual(1, receipt['payload_files'])
        self.assertEqual(3, receipt['installed_files'])
        for relative, data in [('tool/__init__.py', b'changed'), ('extra.py', b'extra')]:
            p = site / relative;p.write_bytes(data)
            with self.assertRaisesRegex(ValueError, '^TOOL_PAYLOAD_MISMATCH$'):
                driver.verify_tools(site, [whl])
            if relative == 'extra.py':p.unlink()
            else:p.write_bytes(b'original')

    def test_symlink_or_unsafe_wheel_cannot_supply_tool_bytes(self):
        site = self.root / 'site';site.mkdir();(site / 'x').symlink_to('/etc/passwd')
        whl = self.root / 'tool.whl'
        for name in ('x', '../x'):
            with zipfile.ZipFile(whl, 'w') as z:z.writestr(name, b'data')
            with self.assertRaises(ValueError):driver.verify_tools(site, [whl])

    def rows(self):
        return [{'path': p, 'sha256': hashlib.sha256(b).hexdigest()}
                for p, b in [('setup.py', b'setup'), ('LICENSE.txt', b'license'),
                             ('progressbar/__init__.py', b'runtime'), ('README.txt', b'readme')]]

    def make_source(self):
        for row in self.rows():
            p = self.root / row['path'];p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes({'setup.py': b'setup', 'LICENSE.txt': b'license',
                           'progressbar/__init__.py': b'runtime', 'README.txt': b'readme'}[row['path']])

    def test_source_immutable_payload_and_recorded_allowed_generated_files(self):
        self.make_source()
        before = driver.verify_source(self.root, self.rows())
        (self.root / 'README.txt').write_bytes(b'generated readme')
        (self.root / 'build/lib/progressbar').mkdir(parents=True)
        (self.root / 'build/lib/progressbar/__init__.py').write_bytes(b'runtime')
        after = driver.verify_source(self.root, self.rows())
        self.assertNotEqual(before['snapshot_sha256'], after['snapshot_sha256'])
        self.assertEqual(5, after['files'])
        for relative in ('setup.py', 'LICENSE.txt', 'progressbar/__init__.py', 'unknown.py'):
            p = self.root / relative;old = p.read_bytes() if p.exists() else None;p.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, '^SOURCE_PAYLOAD_MISMATCH$'):
                driver.verify_source(self.root, self.rows())
            if old is None:p.unlink()
            else:p.write_bytes(old)

    def test_source_rejects_missing_and_links(self):
        self.make_source();p = self.root / 'setup.py';p.unlink()
        with self.assertRaises(ValueError):driver.verify_source(self.root, self.rows())
        p.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):driver.verify_source(self.root, self.rows())

    def test_snapshot_file_count_is_enforced_inside_one_directory(self):
        for name in ('a.py', 'b.py'):(self.root / name).write_bytes(b'data')
        rows = [{'path': name, 'sha256': hashlib.sha256(b'data').hexdigest()} for name in ('a.py', 'b.py')]
        with patch.object(driver, 'MAX_FILES', 1):
            with self.assertRaises(ValueError):driver.verify_source(self.root, rows)
    def test_commands_are_offline_hash_pinned_without_source_rewrite(self):
        commands = driver.commands()
        self.assertEqual(['VENV', 'ENSUREPIP', 'TOOLS', 'BUILD', 'SMOKE'], list(commands))
        self.assertIn('--without-pip', commands['VENV'])
        for flag in ('--no-index', '--no-deps', '--require-hashes', '--no-compile'):
            self.assertIn(flag, commands['TOOLS'])
        build = driver.pip_wheel_args()
        contract = json.loads(Path('docs/proposals/engine-clock-pip-wheel-static-contract.json').read_bytes())
        self.assertEqual('fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70', contract['wheel_sha256'])
        self.assertNotIn('no_compile', contract['observed_cmdoptions_factories'])
        self.assertNotIn(contract['install_only_rejected_flag'], build)
        self.assertTrue({v for v in build if v.startswith('-')} <= set(contract['supported_recipe_flags']))
        self.assertIn('--no-build-isolation', build)
        self.assertIn('--no-clean', build)
        self.assertNotIn('-S', commands['ENSUREPIP'])
        self.assertIn('-I', commands['SMOKE'])


if __name__ == '__main__':unittest.main()
