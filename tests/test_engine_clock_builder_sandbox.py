"""Trusted host child fixtures; no downloaded Python/source is executed."""
import base64
import json
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from time import monotonic
import unittest

try:
    from scripts import engine_clock_builder_sandbox as sandbox
except ImportError:
    sandbox = None


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(sandbox, 'namespace protocol implementation missing')

    def test_fixed_profile_has_mandatory_isolation_and_literal_environment(self):
        args = sandbox.launch_argv(17, 18)
        for flag in ('--unshare-user', '--unshare-pid', '--unshare-net', '--unshare-ipc',
                     '--unshare-uts', '--disable-userns', '--assert-userns-disabled',
                     '--die-with-parent', '--new-session', '--clearenv'):
            self.assertIn(flag, args)
        self.assertEqual(['17', '/'], args[args.index('--ro-bind-fd') + 1:args.index('--ro-bind-fd') + 3])
        self.assertEqual(['18', '/build'], args[args.index('--bind-fd') + 1:args.index('--bind-fd') + 3])
        self.assertEqual(1, args.count('--bind-fd'))
        self.assertEqual(['ALL'], args[args.index('--cap-drop') + 1:args.index('--cap-drop') + 2])
        for forbidden in ('--share-net', '--unshare-user-try', '--bind', '--dev-bind', '--not-a-security-boundary'):
            self.assertNotIn(forbidden, args)
        self.assertEqual(sandbox.PYTHON, args[-6])
        self.assertEqual(['-I', '-S', '-B', '/run/builder/driver.py'], args[-5:-1])
        self.assertNotIn('TOKEN', ' '.join(args))

    def test_capability_required_options_fail_closed(self):
        help_text = ' '.join(sandbox.REQUIRED_OPTIONS)
        self.assertTrue(sandbox.supported_options(help_text))
        for flag in sandbox.REQUIRED_OPTIONS:
            self.assertFalse(sandbox.supported_options(help_text.replace(flag, '')))

    def test_invalid_root_descriptors(self):
        for value in (-1, True, '17', None):
            with self.assertRaises(ValueError):
                sandbox.launch_argv(value, 18)
            with self.assertRaises(ValueError):sandbox.launch_argv(17, value)

    def test_writable_descriptor_requires_real_tmpfs_quota_facts(self):
        facts = {'filesystem': 'tmpfs', 'bytes': 268435456, 'readonly': False,
                 'options': ['rw', 'nosuid', 'nodev', 'noexec'], 'owner_matches': True,
                 'device_matches': True, 'named_inode_matches': True, 'empty': True}
        self.assertTrue(sandbox.supported_tmpfs(facts))
        for key, value in [('filesystem', 'ext4'), ('bytes', 268435457), ('readonly', True),
                           ('options', ['rw']), ('owner_matches', False), ('device_matches', False),
                           ('named_inode_matches', False), ('empty', False)]:
            self.assertFalse(sandbox.supported_tmpfs({**facts, key: value}))

    def test_capture_success_and_closed_environment(self):
        code = 'import os; print(os.getenv("SECRET_TOKEN", "absent")); print(os.getenv("HTTPS_PROXY", "absent"))'
        os.environ['SECRET_TOKEN'] = 'SECRET_SENTINEL'
        self.addCleanup(os.environ.pop, 'SECRET_TOKEN', None)
        receipt, raw = sandbox.capture([sys.executable, '-I', '-S', '-B', '-c', code], timeout=5)
        self.assertEqual('EXITED', receipt['status'])
        self.assertEqual(0, receipt['returncode'])
        self.assertEqual(b'absent\nabsent\n', raw)
        self.assertNotIn('SECRET_SENTINEL', str(receipt))

    def test_stderr_not_persisted(self):
        r, data = sandbox.capture([sys.executable, '-I', '-S', '-B', '-c', 'import sys;sys.stderr.write("SECRET_SENTINEL")'], timeout=5)
        self.assertEqual(15, r['stderr_bytes'])
        self.assertNotIn('SECRET_SENTINEL', str(r))
        self.assertEqual(b'', data)

    def test_actual_pipe_flood_is_bounded(self):
        for pipe in ('stdout', 'stderr'):
            r, raw = sandbox.capture([sys.executable, '-I', '-S', '-B', '-c',
                                      'import sys;getattr(sys,"' + pipe + '").buffer.write(b"x"*1000000)'],
                                     timeout=5, stdout_limit=4096, stderr_limit=4096)
            self.assertEqual('OUTPUT_LIMIT', r['status'])
            self.assertLessEqual(len(raw), 4096)
            self.assertLessEqual(r[pipe + '_bytes'], 4096 + 65536)

    def test_timeout_reaps_child_and_pipe_holding_descendant(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'should-not-exist'
            code = ('import os,time;pid=os.fork();'
                    'time.sleep(1);open(' + repr(str(marker)) + ',"w").write("bad")')
            start = monotonic()
            r, _ = sandbox.capture([sys.executable, '-I', '-S', '-B', '-c', code], timeout=.1)
            self.assertEqual('TIMEOUT', r['status'])
            self.assertLess(monotonic() - start, 6)
            self.assertFalse(marker.exists())

    def test_spawn_error_no_raw_exception(self):
        r, raw = sandbox.capture(['/SECRET_SENTINEL/no-such-file'], timeout=1)
        self.assertEqual('SPAWN_FAILED', r['status'])
        self.assertNotIn('SECRET_SENTINEL', str(r))
        self.assertEqual(b'', raw)

    def test_failed_driver_claim_is_sanitized_and_never_echoes_unknown_text(self):
        valid = {'schema': 'builder-driver-failure-v1', 'status': 'FAILED', 'code': 'SOURCE_PAYLOAD_MISMATCH', 'steps': []}
        self.assertEqual('SOURCE_PAYLOAD_MISMATCH', sandbox.failure_code(json.dumps(valid).encode()))
        for raw in (b'SECRET_SENTINEL', json.dumps({**valid, 'code': 'SECRET_SENTINEL'}).encode(),
                    json.dumps({**valid, 'extra': 'SECRET_SENTINEL'}).encode()):
            self.assertEqual('UNAVAILABLE', sandbox.failure_code(raw))

    def test_invalid_capture_budgets(self):
        for kwargs in ({'timeout': True}, {'timeout': float('nan')}, {'timeout': 181},
                       {'timeout': 1, 'stdout_limit': 3145729}, {'timeout': 1, 'stderr_limit': 0}):
            with self.assertRaises(ValueError):
                sandbox.capture(['/usr/bin/true'], **kwargs)

    def wire(self):
        files = {'setup.py': '0' * 64}
        digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        snapshots = {'schema': 'source-snapshots-v1', 'status': 'SOURCE_SNAPSHOTS_VERIFIED',
                     'source_relative': 'pip-wheel-fixture/progressbar_' + 'a' * 32,
                     'source_identity': {'device': 1, 'inode': 1},
                     'before': {'files': 1, 'snapshot_sha256': digest, 'files_sha256': files},
                     'after': {'files': 1, 'snapshot_sha256': digest, 'files_sha256': files},
                     'logs': {'stdout_bytes': 0, 'stderr_bytes': 0, 'stdout_sha256': '0' * 64, 'stderr_sha256': '0' * 64}}
        value = {'schema': 'builder-driver-v1', 'status': 'BUILT', 'python': '3.11.18',
                'steps': [{'stage': stage, 'status': 'EXITED', 'returncode': 0,
                           'stdout_bytes': 0, 'stderr_bytes': 0,
                           'stdout_sha256': '0' * 64, 'stderr_sha256': '0' * 64}
                          for stage in ('VENV', 'ENSUREPIP', 'TOOLS', 'BUILD', 'SMOKE')],
                'tools_verified': True, 'source_verified': True,
                'verification': {name: {'snapshot_sha256': '0' * 64, 'files': 1,
                                       **({'payload_files': 1, 'installed_files': 1} if name != 'source' else {})}
                                 for name in ('bootstrap', 'tools', 'source')},
                'smoke_verified': True, 'wheel_b64': base64.b64encode(b'fixture').decode(), 'source_snapshots': snapshots}
        value['verification']['source']['snapshot_sha256'] = digest
        return value

    def test_wire_rejects_missing_or_duplicate_phase_evidence(self):
        for stages in ([], self.wire()['steps'][:-1], self.wire()['steps'][:1] * 5):
            value = self.wire();value['steps'] = stages
            with self.assertRaisesRegex(ValueError, '^INVALID_DRIVER_WIRE$'):
                sandbox.decode_wire(json.dumps(value).encode())

    def test_child_capture_preserves_only_fixed_builder_environment(self):
        r, raw = sandbox.capture([sys.executable, '-I', '-S', '-B', '-c',
                                  'import os;print(os.getenv("TMPDIR"));print(os.getenv("SOURCE_DATE_EPOCH"))'],
                                 timeout=5, child_environment=True)
        self.assertEqual(0, r['returncode'])
        self.assertEqual(b'/build/tmp\n315532800\n', raw)

    def test_wire_decodes_only_closed_schema(self):
        raw = json.dumps(self.wire()).encode()
        value, data = sandbox.decode_wire(raw)
        self.assertEqual('BUILT', value['status'])
        self.assertNotIn('wheel_b64', value)
        self.assertEqual(b'fixture', data)

    def test_wire_rejects_duplicates_nan_unknown_and_malformed(self):
        cases = [b'{}{}', b'{"x":NaN}', b'{"x":0,"x":1}', b'SECRET_SENTINEL', b'x' * 3145729]
        for key, value in [('python', '3.11.17'), ('tools_verified', 1), ('extra', 'SECRET_SENTINEL'),
                           ('wheel_b64', '!'), ('steps', [{'SECRET_SENTINEL': 1}])]:
            body = self.wire();body[key] = value;cases.append(json.dumps(body).encode())
        for raw in cases:
            with self.assertRaisesRegex(ValueError, '^INVALID_DRIVER_WIRE$'):
                sandbox.decode_wire(raw)

    def test_source_manifests_cannot_hide_hash_changes_unknown_paths_or_missing_evidence(self):
        import copy
        for mode in ('digest', 'unknown', 'missing', 'unknown_before'):
            value = copy.deepcopy(self.wire())
            snapshot = value['source_snapshots']['after']
            if mode == 'digest':snapshot['files_sha256']['setup.py'] = '1' * 64
            elif mode == 'missing':del value['source_snapshots']['before']
            elif mode == 'unknown_before':
                for name in ('before', 'after'):
                    row = value['source_snapshots'][name]
                    row['files_sha256'] = {'SECRET_SENTINEL': '0' * 64}
                    row['snapshot_sha256'] = hashlib.sha256(json.dumps(row['files_sha256'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
                value['verification']['source']['snapshot_sha256'] = value['source_snapshots']['after']['snapshot_sha256']
            else:
                snapshot['files_sha256']['SECRET_SENTINEL'] = '1' * 64
                snapshot['files'] = len(snapshot['files_sha256'])
                snapshot['snapshot_sha256'] = hashlib.sha256(json.dumps(snapshot['files_sha256'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
            with self.assertRaisesRegex(ValueError, '^INVALID_DRIVER_WIRE$'):
                sandbox.decode_wire(json.dumps(value).encode())


if __name__ == '__main__':
    unittest.main()
