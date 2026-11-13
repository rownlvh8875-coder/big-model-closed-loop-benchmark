"""Remote protocol and archive fixtures; no network or target execution."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

try:
    from scripts import engine_clock_builder_preparation as prep
except ImportError:
    prep = None


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(prep, 'registered remote controller missing')
        self.request = {'schema': 'builder-preparation-request-v1', 'request_id': 'builder-20261113-01',
                        'repository': 'rownlvh8875-coder/big-model-closed-loop-benchmark',
                        'branch': 'prepare/engine-clock-builder-20261113-01',
                        'workflow_path': '.github/workflows/engine-clock-builder-preparation.yml',
                        'reviewed_source_sha': '1' * 40, 'budget': {'runs': 1, 'attempts': 1, 'builds': 1},
                        'source_closure': {p: '0' * 64 for p in prep.CLOSURE_PATHS}, 'inputs': []}
        self.run = {'id': 123, 'run_attempt': 1, 'head_sha': '2' * 40,
                    'head_branch': self.request['branch'], 'event': 'push',
                    'path': self.request['workflow_path'], 'repository': {'full_name': self.request['repository']}}
        self.listing = {'total_count': 1, 'workflow_runs': [self.run]}

    def test_request_exact_scope_and_budgets(self):
        self.assertEqual(self.request, prep.validate_request(self.request))
        for key, value in [('extra', 'SECRET_SENTINEL'), ('repository', 'other/repo'),
                           ('branch', 'main'), ('reviewed_source_sha', 'bad'),
                           ('budget', {'runs': 2, 'attempts': 1, 'builds': 1}),
                           ('source_closure', {'../SECRET_SENTINEL': '0' * 64})]:
            d = copy.deepcopy(self.request);d[key] = value
            with self.assertRaisesRegex(ValueError, '^INVALID_REQUEST$'):prep.validate_request(d)

    def test_context_exact_run_head_attempt_and_workflow(self):
        self.assertEqual('2' * 40, prep.validate_context(self.request, self.run, self.listing, run_id=123, head='2' * 40))
        for key, value in [('id', 124), ('run_attempt', 2), ('head_sha', '3' * 40),
                           ('head_branch', 'main'), ('event', 'workflow_dispatch'),
                           ('path', '.github/workflows/other.yml'), ('repository', {'full_name': 'other/repo'})]:
            d = copy.deepcopy(self.run);d[key] = value
            with self.assertRaisesRegex(ValueError, '^INVALID_RUN_CONTEXT$'):
                prep.validate_context(self.request, d, self.listing, run_id=123, head='2' * 40)

    def test_duplicate_or_opaque_listing_rejects(self):
        for listing in ({'total_count': 2, 'workflow_runs': [self.run, self.run]},
                        {'total_count': 1, 'workflow_runs': []},
                        {'total_count': 1, 'workflow_runs': [{**self.run, 'id': 124}]}):
            with self.assertRaisesRegex(ValueError, '^INVALID_RUN_CONTEXT$'):
                prep.validate_context(self.request, self.run, listing, run_id=123, head='2' * 40)

    def test_public_download_destinations_and_authenticated_api_are_separate(self):
        for url in ('https://github.com/actions/python-versions/releases/download/x/y',
                    'https://release-assets.githubusercontent.com/a?signature=opaque',
                    'https://files.pythonhosted.org/a', 'https://snapshot.ubuntu.com/ubuntu/a'):
            self.assertTrue(prep.public_url_allowed(url))
        for url in ('http://github.com/a', 'https://SECRET_SENTINEL@github.com/a',
                    'https://github.com.evil/a', 'https://api.github.com/a',
                    'https://github.com:444/a', 'file:///etc/passwd'):
            self.assertFalse(prep.public_url_allowed(url))

    def test_download_hashes_actual_bytes_without_forwarding_parent_credentials(self):
        class Response(io.BytesIO):
            status = 200
        class Opener:
            def open(inner, request, timeout):
                self.assertIsNone(request.get_header('Authorization'))
                self.assertNotIn('SECRET_SENTINEL', str(request.headers))
                return Response(b'fixture')
        row = {'id': 'fixture', 'filename': 'fixture.dat', 'url': 'https://files.pythonhosted.org/a',
               'nbytes': 7, 'sha256': hashlib.sha256(b'fixture').hexdigest(), 'kind': 'input'}
        from time import monotonic
        with tempfile.TemporaryDirectory() as tmp, patch.object(prep.urllib.request, 'build_opener', return_value=Opener()):
            store = Path(tmp)
            result = prep.download_input(row, store, monotonic() + 5)
            self.assertEqual(b'fixture', (store / 'fixture.dat').read_bytes())
            self.assertEqual(7, result['nbytes'])
            self.assertEqual(0, result['application_retries'])
        with tempfile.TemporaryDirectory() as tmp, patch.object(prep.urllib.request, 'build_opener', return_value=Opener()):
            store = Path(tmp)
            with self.assertRaisesRegex(ValueError, '^DOWNLOAD_CONTENT_MISMATCH$'):
                prep.download_input({**row, 'sha256': '0' * 64}, store, monotonic() + 5)
            self.assertTrue((store / 'fixture.dat.partial').exists())
            self.assertFalse((store / 'fixture.dat').exists())

    def test_archive_members_verified_from_stream_not_extracted_on_host(self):
        data = b'fixture'
        row = {'path': 'bin/tool', 'kind': 'file', 'mode': 0o755,
               'nbytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode='w') as t:
            info = tarfile.TarInfo('./bin/tool');info.mode = 0o755;info.size = len(data);t.addfile(info, io.BytesIO(data))
        raw.seek(0)
        with tarfile.open(fileobj=raw, mode='r|') as t:
            items = prep.tar_members('fixture', t, [row])
            sid, actual, stream = next(items)
            self.assertEqual(('fixture', row, data), (sid, actual, stream.read()))
            self.assertEqual([], list(items))
        raw.seek(0)
        with tarfile.open(fileobj=raw, mode='r|') as t:
            with self.assertRaisesRegex(ValueError, '^ARCHIVE_HEADER_MISMATCH$'):
                list(prep.tar_members('fixture', t, [{**row, 'mode': 0o644}]))

    def test_unsafe_archive_name_or_unsupported_type_rejected(self):
        for name, kind in [('../SECRET_SENTINEL', tarfile.REGTYPE), ('x', tarfile.LNKTYPE), ('x', tarfile.FIFOTYPE)]:
            raw = io.BytesIO()
            with tarfile.open(fileobj=raw, mode='w') as t:
                info = tarfile.TarInfo(name);info.type = kind;info.linkname = 'other';t.addfile(info)
            raw.seek(0)
            with tarfile.open(fileobj=raw, mode='r|') as t:
                with self.assertRaisesRegex(ValueError, '^ARCHIVE_HEADER_MISMATCH$'):
                    list(prep.tar_members('fixture', t, []))

    def test_source_closure_requires_local_bytes_and_independent_git_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);tree = {'truncated': False, 'tree': []}
            for path in prep.CLOSURE_PATHS:
                p = root / path;p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(b'fixture')
                self.request['source_closure'][path] = hashlib.sha256(b'fixture').hexdigest()
                tree['tree'].append({'path': path, 'type': 'blob', 'sha': prep.git_blob_sha(b'fixture')})
            prep.verify_source_closure(root, self.request, tree)
            (root / next(iter(prep.CLOSURE_PATHS))).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, '^SOURCE_CLOSURE_MISMATCH$'):
                prep.verify_source_closure(root, self.request, tree)

    def test_inactive_workflow_renders_only_unique_push_branch(self):
        template = json.loads(Path('docs/proposals/engine-clock-builder-preparation.workflow.json').read_bytes())
        rendered = prep.render_workflow(template, self.request)
        self.assertEqual({'push': {'branches': [self.request['branch']]}}, rendered['on'])
        self.assertNotIn('workflow_dispatch', rendered['on'])
        self.assertEqual({'contents': 'read', 'actions': 'read'}, rendered['permissions'])
        self.assertFalse(rendered['jobs']['prepare']['steps'][1]['with']['persist-credentials'])
        self.assertIn('if', rendered['jobs']['prepare']['steps'][-1])

    def test_no_registered_context_does_not_execute_or_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'out'
            with self.assertRaisesRegex(ValueError, '^INVALID_REMOTE_ENVIRONMENT$'):
                prep.require_remote_environment({})
            self.assertFalse(out.exists())

    def test_required_host_disk_capacity_is_measured_and_failure_facts_survive(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            observed = prep.check_host_capacity(Path(tmp))
            self.assertEqual(1073741824, observed['required_free_bytes'])
            self.assertGreaterEqual(observed['available_bytes'], 1073741824)
            facts = {}
            with patch.object(prep.os, 'statvfs', return_value=SimpleNamespace(f_bavail=1, f_frsize=4096)):
                with self.assertRaisesRegex(ValueError, '^HOST_CAPACITY_INSUFFICIENT$'):
                    prep.check_host_capacity(Path(tmp), facts)
            self.assertEqual(4096, facts['available_bytes'])
            self.assertTrue(facts['checked_before_input_transport'])

    def test_real_input_metadata_compiles_without_staging_or_execution(self):
        root = Path(__file__).resolve().parent.parent
        request = copy.deepcopy(self.request);request['inputs'] = prep.expected_inputs(root)
        prep.validate_request(request)
        sources, _ = prep.make_sources(root, request)
        from scripts import engine_clock_builder_staging
        plan = engine_clock_builder_staging.compile_plan(sources)
        self.assertEqual(52, len(sources))
        self.assertGreater(len(plan['entries']), 12000)
        self.assertLess(plan['staged_bytes'], 512 * 1024 * 1024)
        self.assertLess(len(prep.canonical(plan)), 16 * 1024 * 1024)


if __name__ == '__main__':unittest.main()
