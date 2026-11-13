"""No live namespace, netlink, model or privileged command in these fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

try:
    from scripts import engine_clock_namespace_diagnostic as diag
except ImportError:
    diag = None


class FakeLinux:
    def __init__(self, *, fail=None, unchanged=None):
        self.fail, self.unchanged, self.changed = fail, unchanged, False
        self.events = []

    def namespaces(self):
        return {k: [1, 20 if self.changed and self.unchanged != k else 10] for k in ('user', 'net')}

    def facts(self):
        return {'namespaces': self.namespaces(), 'effective_uid': 0 if self.changed else 1001}

    def unshare(self):
        self.events.append('unshare')
        if self.fail == 'unshare': raise PermissionError(1, 'SECRET_SENTINEL')
        self.changed = True

    def map_ids(self):
        self.events.append('map_ids')
        if self.fail == 'mapping': raise PermissionError(1, 'SECRET_SENTINEL')

    def drop_bounding(self): self.events.append('bounding')
    def clear_capabilities(self): self.events.append('clear')

    def address(self):
        self.events.append('address')
        if self.fail == 'address' or 'clear' in self.events: raise PermissionError(1, 'SECRET_SENTINEL')

    def link(self): self.events.append('link')


class NamespaceDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(diag, 'new model-free namespace diagnostic missing')

    def test_unshare_failure_stops_every_write(self):
        backend = FakeLinux(fail='unshare')
        result = diag.run_worker('USER_NET', backend)
        self.assertEqual(['unshare'], backend.events)
        self.assertEqual(('UNSHARE', 1), (result['stage'], result['errno']))
        self.assertNotIn('SECRET_SENTINEL', json.dumps(result))

    def test_either_unchanged_namespace_stops_mapping_and_network(self):
        for ns in ('user', 'net'):
            backend = FakeLinux(unchanged=ns)
            result = diag.run_worker('USER_NET', backend)
            self.assertEqual(['unshare'], backend.events)
            self.assertEqual('ISOLATION_NOT_PROVEN', result['status'])

    def test_failed_mapping_prevents_network(self):
        backend = FakeLinux(fail='mapping')
        result = diag.run_worker('USER_NET', backend)
        self.assertEqual(['unshare', 'map_ids'], backend.events)
        self.assertEqual('MAPPING', result['stage'])

    def test_success_requires_address_then_link(self):
        backend = FakeLinux()
        result = diag.run_worker('USER_NET', backend)
        self.assertEqual(['unshare', 'map_ids', 'address', 'link'], backend.events)
        self.assertEqual('COMPLETE', result['status'])
        self.assertTrue(result['isolation_proven'])

    def test_bounding_drop_precedes_address_but_does_not_clear_effective(self):
        backend = FakeLinux()
        result = diag.run_worker('USER_NET_DROP_BOUNDING', backend)
        self.assertEqual(['unshare', 'map_ids', 'bounding', 'address', 'link'], backend.events)
        self.assertEqual('COMPLETE', result['status'])
        self.assertIn('after_intervention', result)

    def test_cleared_caps_is_negative_control(self):
        backend = FakeLinux()
        result = diag.run_worker('USER_NET_DROP_ALL_CAPS', backend)
        self.assertEqual(['unshare', 'map_ids', 'clear', 'address'], backend.events)
        self.assertEqual(('ADDRESS', 1), (result['stage'], result['errno']))

    def test_unknown_case_never_touches_backend(self):
        backend = FakeLinux()
        with self.assertRaisesRegex(ValueError, '^INVALID_CASE$'): diag.run_worker('SECRET_SENTINEL', backend)
        self.assertEqual([], backend.events)

    def test_ack_success_and_kernel_errno(self):
        ack = struct.pack('=IHHIIi', 36, 2, 0, 7, 0, 0) + bytes(16)
        self.assertEqual(0, diag.parse_ack(ack, 7))
        denied = struct.pack('=IHHIIi', 36, 2, 0, 7, 0, -1) + bytes(16)
        self.assertEqual(1, diag.parse_ack(denied, 7))

    def test_malformed_or_wrong_sequence_ack_is_not_success(self):
        for raw in (b'', bytes(19), struct.pack('=IHHIIi', 36, 2, 0, 8, 0, 0) + bytes(16),
                    struct.pack('=IHHIIi', 99, 2, 0, 7, 0, 0) + bytes(16),
                    struct.pack('=IHHIIi', 36, 16, 0, 7, 0, 0) + bytes(16)):
            with self.assertRaisesRegex(ValueError, '^INVALID_NETLINK_ACK$'): diag.parse_ack(raw, 7)

    def test_profile_unknown_text_hashed_not_retained(self):
        self.assertEqual('unconfined', diag.profile_value(b'unconfined\n')['known'])
        value = diag.profile_value(b'SECRET_SENTINEL')
        self.assertNotIn('SECRET_SENTINEL', json.dumps(value))
        self.assertEqual(hashlib.sha256(b'SECRET_SENTINEL').hexdigest(), value['sha256'])

    def test_facts_ignore_environment_and_unknown_status_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'self/attr').mkdir(parents=True)
            (root / 'self/status').write_text('CapEff:\t0000000000001000\nSeccomp:\t2\nName:\tSECRET_SENTINEL\n')
            (root / 'self/attr/current').write_text('unconfined\n')
            value = diag.facts(root)
            self.assertEqual('0000000000001000', value['status']['CapEff'])
            self.assertEqual(2, value['status']['Seccomp'])
            self.assertNotIn('SECRET_SENTINEL', json.dumps(value))

    def test_only_matching_pid_net_admin_denial_fields_persist(self):
        message = 'audit: apparmor="DENIED" operation="capable" profile="unprivileged_userns" pid=42 comm="SECRET_SENTINEL" capability=12 capname="net_admin"'
        raw = (json.dumps({'MESSAGE': message}) + '\n' + json.dumps({'MESSAGE': message.replace('pid=42', 'pid=420')}) + '\n').encode()
        result = diag.filter_denials(raw, {42})
        self.assertEqual(1, len(result))
        self.assertEqual(42, result[0]['pid'])
        self.assertEqual('net_admin', result[0]['capname'])
        self.assertNotIn('SECRET_SENTINEL', json.dumps(result))

    def test_missing_or_unrelated_kernel_log_never_proves_no_lsm(self):
        self.assertEqual([], diag.filter_denials(b'not JSON\n{"MESSAGE":"unrelated"}\n', {42}))

    def test_request_refuses_old_id_retries_extra_fields_and_arbitrary_closure(self):
        valid = {'schema': 'namespace-diagnostic-request-v1', 'request_id': 'namespace-diagnostic-20261113-01',
                 'repository': 'rownlvh8875-coder/big-model-closed-loop-benchmark',
                 'branch': 'diagnose/engine-clock-namespace-20261113-01',
                 'workflow_path': '.github/workflows/engine-clock-namespace-diagnostic.yml',
                 'reviewed_source_sha': '1' * 40, 'budget': {'runs': 1, 'attempts': 1, 'workers': 3},
                 'source_closure': {p: '0' * 64 for p in diag.CLOSURE}}
        self.assertEqual(valid, diag.validate_request(valid))
        for key, value in [('request_id', 'builder-20261113-01'), ('branch', 'main'),
                           ('budget', {'runs': 2, 'attempts': 1, 'workers': 3}),
                           ('source_closure', {'../SECRET_SENTINEL': '0' * 64}), ('extra', 'SECRET_SENTINEL')]:
            altered = copy.deepcopy(valid); altered[key] = value
            with self.assertRaisesRegex(ValueError, '^INVALID_REQUEST$'): diag.validate_request(altered)

    def test_duplicate_run_and_second_attempt_rejected_before_execution(self):
        from scripts import engine_clock_builder_preparation as prep
        request = {'branch': 'diagnose/engine-clock-namespace-20261113-01', 'workflow_path': '.github/workflows/engine-clock-namespace-diagnostic.yml'}
        run = {'id': 123, 'run_attempt': 1, 'head_sha': '2' * 40, 'head_branch': request['branch'],
               'event': 'push', 'path': request['workflow_path'], 'repository': {'full_name': prep.REPOSITORY}}
        self.assertEqual('2' * 40, prep.validate_context(request, run, {'total_count': 1, 'workflow_runs': [run]}, run_id=123, head='2' * 40))
        for listing, attempt in [({'total_count': 2, 'workflow_runs': [run, run]}, 1), ({'total_count': 1, 'workflow_runs': [run]}, 2)]:
            with self.assertRaisesRegex(ValueError, '^INVALID_RUN_CONTEXT$'):
                prep.validate_context(request, {**run, 'run_attempt': attempt}, listing, run_id=123, head='2' * 40)


if __name__ == '__main__': unittest.main()
