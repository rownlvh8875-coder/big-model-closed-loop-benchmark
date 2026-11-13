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


    def test_ack_zero_embedded_request_is_rejected(self):
        raw = struct.pack('=IHHIIi', 36, 2, 0, 7, 0, 0) + bytes(16)
        with self.assertRaisesRegex(ValueError, '^INVALID_NETLINK_ACK$'):
            diag.parse_ack(raw, 7)

    def test_activation_requires_sole_reviewed_parent_and_only_new_regular_request(self):
        self.assertTrue(callable(getattr(diag, 'validate_activation', None)), 'activation delta guard missing')
        request = {'reviewed_source_sha': '1' * 40}
        prior = {'sha': '3' * 40, 'truncated': False, 'tree': [{'path': 'old.py', 'type': 'blob', 'mode': '100644', 'sha': '4' * 40}]}
        current = copy.deepcopy(prior); current['sha'] = '5' * 40
        current['tree'].append({'path': diag.REQUEST_PATH, 'type': 'blob', 'mode': '100644', 'sha': '6' * 40})
        commit = {'sha': '2' * 40, 'parents': [{'sha': '1' * 40}], 'tree': {'sha': '5' * 40}}
        self.assertIsNone(diag.validate_activation(request, '2' * 40, current, prior, commit))
        for kind in ('extra', 'wrong_parent', 'merge', 'replacement', 'symlink', 'truncated', 'wrong_tree'):
            a, b, c = copy.deepcopy(current), copy.deepcopy(prior), copy.deepcopy(commit)
            if kind == 'extra': a['tree'][0]['sha'] = '7' * 40
            elif kind == 'wrong_parent': c['parents'][0]['sha'] = '8' * 40
            elif kind == 'merge': c['parents'].append({'sha': '9' * 40})
            elif kind == 'replacement': b['tree'].append({'path': diag.REQUEST_PATH, 'type': 'blob', 'mode': '100644', 'sha': '0' * 40})
            elif kind == 'symlink': a['tree'][-1]['mode'] = '120000'
            elif kind == 'truncated': a['truncated'] = True
            else: c['tree']['sha'] = '9' * 40
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, '^INVALID_ACTIVATION$'):
                diag.validate_activation(request, '2' * 40, a, b, c)

    def test_ack_success_and_kernel_errno(self):
        request = struct.pack('=IHHII', 40, 20, 1541, 7, 0) + bytes(24)
        ack = struct.pack('=IHHIIi', 36, 2, 0, 7, 0, 0) + request[:16]
        self.assertEqual(0, diag.parse_ack(ack, 7, request=request))
        denied = struct.pack('=IHHIIi', 60, 2, 0, 7, 0, -1) + request
        self.assertEqual(1, diag.parse_ack(denied, 7, request=request))
        capped = struct.pack('=IHHIIi', 36, 2, 256, 7, 0, -1) + request[:16]
        self.assertEqual(1, diag.parse_ack(capped, 7, request=request))

    def test_malformed_or_wrong_sequence_ack_is_not_success(self):
        request = struct.pack('=IHHII', 40, 20, 1541, 7, 0) + bytes(24)
        fixtures = [b'', bytes(19), struct.pack('=IHHIIi', 36, 2, 0, 8, 0, 0) + request[:16],
                    struct.pack('=IHHIIi', 99, 2, 0, 7, 0, 0) + request[:16],
                    struct.pack('=IHHIIi', 36, 16, 0, 7, 0, 0) + request[:16]]
        for header in (bytes(16), struct.pack('=IHHII', 40, 16, 1541, 7, 0),
                       struct.pack('=IHHII', 40, 20, 1541, 8, 0)):
            fixtures.append(struct.pack('=IHHIIi', 36, 2, 0, 7, 0, 0) + header)
        fixtures.append(struct.pack('=IHHIIi', 60, 2, 0, 7, 0, -1) + request[:16] + bytes([1]) + bytes(23))
        for raw in fixtures:
            with self.assertRaisesRegex(ValueError, '^INVALID_NETLINK_ACK$'): diag.parse_ack(raw, 7, request=request)

    def test_authenticate_resolves_commit_tree_sha_and_rejects_unreviewed_parent(self):
        from scripts import engine_clock_builder_preparation as prep
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in diag.CLOSURE:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'fixture')
            request = {'schema': 'namespace-diagnostic-request-v1', 'request_id': diag.REQUEST_ID,
                       'repository': prep.REPOSITORY, 'branch': diag.BRANCH, 'workflow_path': diag.WORKFLOW,
                       'reviewed_source_sha': '1' * 40, 'budget': {'runs': 1, 'attempts': 1, 'workers': 3},
                       'source_closure': {p: hashlib.sha256(b'fixture').hexdigest() for p in diag.CLOSURE}}
            request_path = root / diag.REQUEST_PATH; request_path.parent.mkdir(parents=True, exist_ok=True)
            request_path.write_bytes(prep.canonical(request))
            prior = {'sha': '3' * 40, 'truncated': False, 'tree': [
                {'path': p, 'type': 'blob', 'mode': '100644', 'sha': prep.git_blob_sha(b'fixture')} for p in diag.CLOSURE]}
            current = copy.deepcopy(prior); current['sha'] = '5' * 40
            current['tree'].append({'path': diag.REQUEST_PATH, 'type': 'blob', 'mode': '100644', 'sha': prep.git_blob_sha(request_path.read_bytes())})
            run = {'id': 123, 'run_attempt': 1, 'head_sha': '2' * 40, 'head_branch': diag.BRANCH,
                   'event': 'push', 'path': diag.WORKFLOW, 'repository': {'full_name': prep.REPOSITORY}}
            env = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': prep.REPOSITORY, 'GITHUB_RUN_ATTEMPT': '1',
                   'GITHUB_SHA': '2' * 40, 'GITHUB_RUN_ID': '123', 'GH_TOKEN': 'SECRET_SENTINEL',
                   'GITHUB_REF': 'refs/heads/' + diag.BRANCH, 'GITHUB_WORKFLOW_REF': prep.REPOSITORY + '/' + diag.WORKFLOW + '@refs/heads/' + diag.BRANCH,
                   'GITHUB_WORKSPACE': str(root)}
            parent = ['1' * 40]
            def api(path, token):
                if '/git/commits/' in path:
                    if path.endswith('1' * 40): return {'sha': '1' * 40, 'parents': [], 'tree': {'sha': '3' * 40}}
                    return {'sha': '2' * 40, 'parents': [{'sha': parent[0]}], 'tree': {'sha': '5' * 40}}
                if '/git/trees/' in path:
                    if '3' * 40 in path: return prior
                    if '5' * 40 in path: return current
                    # Observed GitHub API resolves commit-ish tree rows but echoes input SHA.
                    value = copy.deepcopy(prior if '1' * 40 in path else current)
                    value['sha'] = '1' * 40 if '1' * 40 in path else '2' * 40
                    return value
                if '/actions/workflows/' in path: return {'total_count': 1, 'workflow_runs': [run]}
                if '/actions/runs/' in path: return run
                raise AssertionError('unexpected API route')
            with patch.object(prep, 'api_json', side_effect=api):
                try: result = diag.authenticate(root, env)
                except ValueError as exc: result = str(exc)
                self.assertIsInstance(result, dict, 'valid request-only activation rejected after commit-ish tree lookup')
                parent[0] = '9' * 40
                with self.assertRaisesRegex(ValueError, '^INVALID_ACTIVATION$'): diag.authenticate(root, env)


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
