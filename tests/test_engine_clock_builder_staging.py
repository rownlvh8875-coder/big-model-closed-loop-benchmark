"""Synthetic filesystem fixtures; never stage or execute a downloaded runtime."""
import copy
import hashlib
import io
import os
from pathlib import Path
import signal
import stat
import tempfile
from time import perf_counter
import unittest
from unittest.mock import patch

try:
    from scripts import engine_clock_builder_staging as staging
except ImportError:
    staging = None


def file_row(path, data=b'abc', mode=0o644):
    return {'path': path, 'kind': 'file', 'mode': mode, 'nbytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def fixture():
    rows = [{'path': '.', 'kind': 'directory', 'mode': 0o755, 'nbytes': 0},
            {'path': 'usr/bin', 'kind': 'directory', 'mode': 0o755, 'nbytes': 0},
            {'path': 'bin', 'kind': 'symlink', 'mode': 0o777, 'nbytes': 0, 'target': 'usr/bin'},
            file_row('bin/tool', b'abc', 0o4755),
            file_row('usr/lib/data', b'data'),
            {'path': 'usr/lib/absolute', 'kind': 'symlink', 'mode': 0o777,
             'nbytes': 0, 'target': '/usr/lib/data'}]
    source = {'id': 'fixture', 'prefix': '.', 'archive_sha256': '0' * 64, 'entries': rows}
    payloads = {'bin/tool': b'abc', 'usr/lib/data': b'data'}
    return [source], payloads


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(staging, 'builder staging implementation is missing')
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / 'root'
        self.addCleanup(self.cleanup)
        self.sources, self.payloads = fixture()

    def cleanup(self):
        if self.root.exists() and not self.root.is_symlink():
            for current, _, _ in os.walk(self.root, followlinks=False):
                os.chmod(current, 0o700)
        self.tmp.cleanup()

    def members(self, sources=None, payloads=None):
        for source in self.sources if sources is None else sources:
            for row in source['entries']:
                data = (self.payloads if payloads is None else payloads).get(row['path'])
                yield source['id'], copy.deepcopy(row), io.BytesIO(data) if data is not None else None

    def plan(self):
        return staging.compile_plan(self.sources)

    def stage(self, members=None, plan=None):
        return staging.stage_tree(self.root, self.plan() if plan is None else plan,
                                  self.members() if members is None else members,
                                  deadline=perf_counter() + 10)

    def verify(self, plan=None):
        return staging.verify_tree(self.root, self.plan() if plan is None else plan,
                                   deadline=perf_counter() + 10)

    def test_alias_parent_is_canonicalized_without_host_traversal(self):
        result = self.stage()
        self.assertEqual('STAGED_CONTENT_MATCH', result['status'])
        self.assertEqual(b'abc', (self.root / 'usr/bin/tool').read_bytes())
        self.assertEqual('usr/bin', os.readlink(self.root / 'bin'))
        self.assertEqual('/usr/lib/data', os.readlink(self.root / 'usr/lib/absolute'))
        self.assertEqual('STAGED_CONTENT_MATCH', self.verify()['status'])
        self.assertFalse(result['native_admission'])
        self.assertFalse(result['image_preparation_ready'])

    def test_normalized_modes_remove_special_bits_and_writes(self):
        self.stage()
        self.assertEqual(0o555, stat.S_IMODE((self.root / 'usr/bin/tool').stat().st_mode))
        self.assertEqual(0o444, stat.S_IMODE((self.root / 'usr/lib/data').stat().st_mode))
        self.assertEqual(0o555, stat.S_IMODE(self.root.stat().st_mode))

    def test_source_prefix_is_a_real_staged_directory(self):
        self.sources[0]['prefix'] = 'opt/python'
        # Absolute source links stay candidate-root absolute; make this one relative.
        self.sources[0]['entries'][-1]['target'] = 'data'
        self.assertEqual('STAGED_CONTENT_MATCH', self.stage()['status'])
        self.assertEqual(b'abc', (self.root / 'opt/python/usr/bin/tool').read_bytes())

    def test_identical_overlapping_payloads_are_verified_not_overwritten(self):
        second = copy.deepcopy(self.sources[0]); second['id'] = 'second'
        self.sources.append(second)
        self.assertEqual('STAGED_CONTENT_MATCH', self.stage()['status'])
        self.assertEqual(1, (self.root / 'usr/lib/data').stat().st_nlink)

    def test_conflicting_payloads_reject_before_root_creation(self):
        second = copy.deepcopy(self.sources[0]); second['id'] = 'second'
        second['entries'][4] = file_row('usr/lib/data', b'changed')
        self.sources.append(second)
        with self.assertRaises(ValueError): self.plan()
        self.assertFalse(self.root.exists())

    def test_missing_member_does_not_admit_partial_root(self):
        rows = list(self.members())[:-1]
        self.assertEqual('FAILED_OR_INCOMPLETE', self.stage(iter(rows))['status'])
        self.assertTrue(self.root.exists())

    def test_extra_member_rejects_without_persisting_secret_name(self):
        rows = list(self.members())
        rows.append(('fixture', file_row('secret-GH_TOKEN-sentinel'), io.BytesIO(b'abc')))
        result = self.stage(iter(rows))
        self.assertEqual('FAILED_OR_INCOMPLETE', result['status'])
        self.assertNotIn('GH_TOKEN', str(result))

    def test_duplicate_member_rejects(self):
        rows = list(self.members()); rows.append(rows[0])
        self.assertEqual('FAILED_OR_INCOMPLETE', self.stage(iter(rows))['status'])

    def test_wrong_payload_hash_rejects(self):
        self.payloads['usr/lib/data'] = b'evil'
        self.assertEqual('FAILED_OR_INCOMPLETE', self.stage()['status'])

    def test_short_or_long_stream_rejects(self):
        for bad in (b'ab', b'abcd'):
            with self.subTest(data=bad):
                root = self.base / ('r' + str(len(bad)))
                result = staging.stage_tree(root, self.plan(), self.members(payloads={**self.payloads, 'bin/tool': bad}), deadline=perf_counter() + 10)
                self.assertEqual('FAILED_OR_INCOMPLETE', result['status'])
                for current, _, _ in os.walk(root, followlinks=False): os.chmod(current, 0o700)

    def test_changed_header_is_not_accepted_even_with_valid_bytes(self):
        rows = list(self.members()); rows[3][1]['mode'] = 0o644
        self.assertEqual('FAILED_OR_INCOMPLETE', self.stage(iter(rows))['status'])

    def test_existing_root_is_never_overwritten(self):
        self.root.mkdir(); (self.root / 'keep').write_bytes(b'keep')
        self.assertEqual('FAILED_OR_INCOMPLETE', self.stage()['status'])
        self.assertEqual(b'keep', (self.root / 'keep').read_bytes())

    def test_root_symlink_is_not_followed(self):
        outside = self.base / 'outside'; outside.mkdir(); self.root.symlink_to(outside, target_is_directory=True)
        self.assertEqual('FAILED_OR_INCOMPLETE', self.stage()['status'])
        self.assertEqual([], list(outside.iterdir()))

    def test_parent_symlink_is_not_followed(self):
        outside = self.base / 'outside'; outside.mkdir(); alias = self.base / 'alias'; alias.symlink_to(outside, target_is_directory=True)
        result = staging.stage_tree(alias / 'root', self.plan(), self.members(), deadline=perf_counter() + 10)
        self.assertEqual('FAILED_OR_INCOMPLETE', result['status'])
        self.assertEqual([], list(outside.iterdir()))

    def test_directory_replacement_cannot_redirect_a_write(self):
        outside = self.base / 'outside'; outside.mkdir(); (outside / 'tool').write_bytes(b'keep')
        def raced():
            for sid, row, stream in self.members():
                if row['path'] == 'bin/tool':
                    (self.root / 'usr/bin').rename(self.root / 'usr/bin-old')
                    (self.root / 'usr/bin').symlink_to(outside, target_is_directory=True)
                yield sid, row, stream
        self.assertEqual('FAILED_OR_INCOMPLETE', self.stage(raced())['status'])
        self.assertEqual(b'keep', (outside / 'tool').read_bytes())

    def test_verifier_rejects_extra_missing_tampered_and_mode_changed_files(self):
        self.stage(); target = self.root / 'usr/lib/data'
        target.chmod(0o644); target.write_bytes(b'EVIL'); target.chmod(0o444)
        self.assertEqual('FAILED_OR_INCOMPLETE', self.verify()['status'])
        target.chmod(0o644); target.write_bytes(b'data'); target.chmod(0o444)
        self.assertEqual('STAGED_CONTENT_MATCH', self.verify()['status'])
        (self.root / 'usr/lib').chmod(0o755); extra = self.root / 'usr/lib/extra'; extra.write_bytes(b'x')
        self.assertEqual('FAILED_OR_INCOMPLETE', self.verify()['status'])
        extra.unlink(); (self.root / 'usr/lib').chmod(0o555); target.chmod(0o644)
        self.assertEqual('FAILED_OR_INCOMPLETE', self.verify()['status'])
        target.chmod(0o444); (self.root / 'usr/lib').chmod(0o755); target.unlink(); (self.root / 'usr/lib').chmod(0o555)
        self.assertEqual('FAILED_OR_INCOMPLETE', self.verify()['status'])

    def test_verifier_rejects_link_target_substitution(self):
        self.stage(); parent = self.root / 'usr/lib'; parent.chmod(0o755)
        (parent / 'absolute').unlink(); (parent / 'absolute').symlink_to('/etc/passwd'); parent.chmod(0o555)
        self.assertEqual('FAILED_OR_INCOMPLETE', self.verify()['status'])

    def test_verifier_rejects_external_hardlink_alias(self):
        self.stage(); os.link(self.root / 'usr/lib/data', self.base / 'alias-data')
        self.assertEqual('FAILED_OR_INCOMPLETE', self.verify()['status'])

    def test_expired_deadline_does_not_create_root(self):
        result = staging.stage_tree(self.root, self.plan(), self.members(), deadline=perf_counter() - 1)
        self.assertEqual('FAILED_OR_INCOMPLETE', result['status']); self.assertFalse(self.root.exists())

    def test_invalid_deadlines_reject_without_creating_root(self):
        for value in (True, float('inf'), float('nan'), 'later'):
            result = staging.stage_tree(self.root, self.plan(), self.members(), deadline=value)
            self.assertEqual('FAILED_OR_INCOMPLETE', result['status'])
        self.assertFalse(self.root.exists())

    def test_busy_real_timer_is_not_replaced(self):
        old = signal.getsignal(signal.SIGALRM)
        signal.setitimer(signal.ITIMER_REAL, 20)
        try:
            self.assertEqual('FAILED_OR_INCOMPLETE', self.stage()['status'])
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)
            self.assertEqual(old, signal.getsignal(signal.SIGALRM))
        finally: signal.setitimer(signal.ITIMER_REAL, 0)

    def test_plan_digest_tampering_rejects(self):
        plan = self.plan(); plan['entries'][-1]['mode'] = 0o777
        self.assertEqual('FAILED_OR_INCOMPLETE', self.stage(plan=plan)['status'])

    def test_path_and_type_ambiguities_reject(self):
        for path in ('../escape', '/absolute', 'a//b', 'a/./b', 'a\\b', 'x\x00y', 'a/' * 65 + 'x'):
            with self.subTest(path=path):
                sources, _ = fixture(); sources[0]['entries'][3]['path'] = path
                with self.assertRaises(ValueError): staging.compile_plan(sources)
        for key, value in (('mode', True), ('nbytes', True), ('sha256', 'f' * 63), ('kind', 'fifo')):
            sources, _ = fixture(); sources[0]['entries'][3][key] = value
            with self.assertRaises(ValueError): staging.compile_plan(sources)

    def test_duplicate_sources_members_and_unknown_fields_reject(self):
        for mutate in (lambda s: s.append(copy.deepcopy(s[0])),
                       lambda s: s[0]['entries'].append(copy.deepcopy(s[0]['entries'][0])),
                       lambda s: s[0].update(unexpected=True),
                       lambda s: s[0]['entries'][0].update(unexpected=True)):
            sources, _ = fixture(); mutate(sources)
            with self.assertRaises(ValueError): staging.compile_plan(sources)

    def test_escape_loop_dangling_and_file_ancestor_reject(self):
        for target in ('../../escape', 'missing', 'absolute'):
            sources, _ = fixture(); sources[0]['entries'][-1]['target'] = target
            with self.assertRaises(ValueError): staging.compile_plan(sources)
        sources, _ = fixture(); sources[0]['entries'].append(file_row('usr/lib/data/child'))
        with self.assertRaises(ValueError): staging.compile_plan(sources)

    def test_declared_size_and_node_limits_reject_without_data_allocation(self):
        sources, _ = fixture(); sources[0]['entries'][3]['nbytes'] = 134217729
        with self.assertRaises(ValueError): staging.compile_plan(sources)
        sources, _ = fixture(); sources[0]['entries'] = [file_row('x' + str(i), b'') for i in range(20001)]
        with self.assertRaises(ValueError): staging.compile_plan(sources)

    def test_absolute_candidate_link_is_never_read_from_host(self):
        self.assertEqual('STAGED_CONTENT_MATCH', self.stage()['status'])
        with patch('builtins.open', side_effect=AssertionError('host path read')):
            self.assertEqual('STAGED_CONTENT_MATCH', self.verify()['status'])


    def test_symlink_owner_group_or_device_mismatch_is_rejected(self):
        self.stage()
        original = os.stat
        for field in (2, 3, 4, 5):  # device, link count, owner, group
            def changed(path, *args, **kwargs):
                value = original(path, *args, **kwargs)
                if path == 'absolute' and kwargs.get('follow_symlinks') is False:
                    parts = list(value); parts[field] += 1
                    return os.stat_result(parts)
                return value
            with self.subTest(field=field), patch.object(os, 'stat', side_effect=changed):
                self.assertEqual('FAILED_OR_INCOMPLETE', self.verify()['status'])

    def test_invalid_plan_digest_does_not_echo_secret_input(self):
        result = self.stage(plan={'plan_sha256': 'ghp_SECRET_SENTINEL'})
        self.assertEqual('FAILED_OR_INCOMPLETE', result['status'])
        self.assertNotIn('SECRET_SENTINEL', str(result))

    def test_iterator_cleanup_error_cannot_escape_as_raw_exception(self):
        rows = iter(list(self.members()))
        class Closing:
            def __iter__(self): return self
            def __next__(self): return next(rows)
            def close(self): raise ValueError('secret-proxy-sentinel')
        result = self.stage(Closing())
        self.assertEqual('FAILED_OR_INCOMPLETE', result['status'])
        self.assertNotIn('secret-proxy', str(result))


if __name__ == '__main__': unittest.main()
