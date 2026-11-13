"""One-use remote provider-free preparation; inactive without a bound request/run."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tarfile
from time import monotonic, perf_counter
import urllib.parse
import urllib.request

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_builder_staging as staging
from scripts import engine_clock_builder_sandbox as sandbox
from scripts import engine_clock_builder_wheel as wheel_check

REPOSITORY = 'rownlvh8875-coder/big-model-closed-loop-benchmark'
TEMPLATE = 'docs/proposals/engine-clock-builder-preparation.workflow.json'
PROGRESS = 'docs/evidence/STAGE7_ENGINE_CLOCK_PROGRESSBAR_BUILD_INPUTS.json'
POLICY = 'docs/evidence/STAGE7_ENGINE_CLOCK_PROGRESSBAR_BUILD_POLICY.json'
PYTHON_INPUT = 'docs/evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_INPUTS.json'
PYTHON_MEMBERS = 'docs/evidence/engine-clock-python-bootstrap/archive-members.json'
OS_PLAN = 'docs/evidence/engine-clock-os-inputs/package-plan.json'
OS_MEMBERS = 'docs/evidence/engine-clock-os-inputs/package-members.json'
SOURCE_INSPECTION = 'docs/evidence/engine-clock-progressbar/static-inspection.json'
CLOSURE_PATHS = frozenset([TEMPLATE, PROGRESS, POLICY, PYTHON_INPUT, PYTHON_MEMBERS, OS_PLAN,
    OS_MEMBERS, SOURCE_INSPECTION, 'scripts/__init__.py',
    'docs/evidence/STAGE7_ENGINE_CLOCK_OS_INPUTS.json',
    'docs/evidence/STAGE7_ENGINE_CLOCK_OS_BINDING.json',
    'docs/evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_BINDING.json',
    'docs/superpowers/specs/2026-11-13-engine-clock-builder-staging-design.md',
    *['scripts/engine_clock_builder_' + n + '.py' for n in ('staging', 'sandbox', 'wheel', 'driver', 'preparation')],
    *['tests/test_engine_clock_builder_' + n + '.py' for n in ('staging', 'sandbox', 'wheel', 'driver', 'preparation')]])


def _need(ok, code):
    if not ok:raise ValueError(code)


def _digest(value, length=64):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def _pairs(rows):
    result = {}
    for k, v in rows:
        _need(k not in result, 'INVALID_JSON')
        result[k] = v
    return result


def _json(raw):
    _need(type(raw) is bytes and len(raw) <= 16777216, 'INVALID_JSON')
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('INVALID_JSON')))


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def git_blob_sha(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def _deb_id(name):
    # Debian names can contain '+' and '.', which are outside staging IDs.
    return 'deb-' + hashlib.sha256(name.encode('ascii')).hexdigest()[:32]


def public_url_allowed(url):
    try:
        p = urllib.parse.urlsplit(url)
        return (p.scheme == 'https' and p.hostname in {'github.com', 'release-assets.githubusercontent.com',
                'files.pythonhosted.org', 'snapshot.ubuntu.com'} and p.port in (None, 443)
                and p.username is None and p.password is None and not p.fragment)
    except (TypeError, ValueError):return False


def validate_request(value):
    try:
        _need(type(value) is dict and set(value) == {'schema', 'request_id', 'repository', 'branch',
              'workflow_path', 'reviewed_source_sha', 'budget', 'source_closure', 'inputs'}, 'INVALID_REQUEST')
        _need(value['schema'] == 'builder-preparation-request-v1' and value['repository'] == REPOSITORY
              and type(value['request_id']) is str and re.fullmatch(r'builder-[0-9]{8}-[0-9]{2}', value['request_id'])
              and value['branch'] == 'prepare/engine-clock-' + value['request_id']
              and value['workflow_path'] == '.github/workflows/engine-clock-builder-preparation.yml'
              and _digest(value['reviewed_source_sha'], 40), 'INVALID_REQUEST')
        _need(type(value['budget']) is dict and set(value['budget']) == {'runs', 'attempts', 'builds'}
              and all(type(v) is int and v == 1 for v in value['budget'].values()), 'INVALID_REQUEST')
        _need(type(value['source_closure']) is dict and set(value['source_closure']) == CLOSURE_PATHS
              and all(_digest(d) for d in value['source_closure'].values()), 'INVALID_REQUEST')
        _need(type(value['inputs']) is list and len(value['inputs']) <= 64, 'INVALID_REQUEST')
        names, ids = set(), set()
        for row in value['inputs']:
            _need(type(row) is dict and set(row) == {'id', 'filename', 'url', 'nbytes', 'sha256', 'kind'}
                  and type(row['id']) is str and re.fullmatch('[a-z0-9-]{1,64}', row['id'])
                  and row['id'] not in ids and type(row['filename']) is str
                  and re.fullmatch('[A-Za-z0-9_.+~-]{1,200}', row['filename']) and row['filename'] not in names
                  and type(row['nbytes']) is int and 0 < row['nbytes'] <= 100000000
                  and _digest(row['sha256']) and row['kind'] in ('python', 'deb', 'input')
                  and public_url_allowed(row['url']), 'INVALID_REQUEST')
            ids.add(row['id']);names.add(row['filename'])
        return value
    except (ValueError, TypeError, KeyError, OverflowError):raise ValueError('INVALID_REQUEST') from None


def validate_context(request, run, listing, *, run_id, head):
    try:
        _need(type(run_id) is int and run_id > 0 and _digest(head, 40), 'INVALID_RUN_CONTEXT')
        expected = {'id': run_id, 'run_attempt': 1, 'head_sha': head, 'head_branch': request['branch'],
                    'event': 'push', 'path': request['workflow_path']}
        _need(all(type(run[k]) is type(v) and run[k] == v for k, v in expected.items())
              and run['repository']['full_name'] == REPOSITORY, 'INVALID_RUN_CONTEXT')
        _need(type(listing['total_count']) is int and listing['total_count'] == 1
              and type(listing['workflow_runs']) is list and len(listing['workflow_runs']) == 1
              and all(listing['workflow_runs'][0].get(k) == v for k, v in expected.items()), 'INVALID_RUN_CONTEXT')
        return head
    except (ValueError, TypeError, KeyError, AttributeError):raise ValueError('INVALID_RUN_CONTEXT') from None


def verify_source_closure(root, request, tree):
    try:
        _need(tree['truncated'] is False, 'SOURCE_CLOSURE_MISMATCH')
        blobs = {}
        for row in tree['tree']:
            if row['type'] == 'blob':
                _need(row['path'] not in blobs, 'SOURCE_CLOSURE_MISMATCH')
                blobs[row['path']] = row['sha']
        for path, digest in request['source_closure'].items():
            p = root / path
            _need(not p.is_symlink() and p.is_file() and p.stat().st_size <= 16777216, 'SOURCE_CLOSURE_MISMATCH')
            raw = p.read_bytes()
            _need(hashlib.sha256(raw).hexdigest() == digest and blobs.get(path) == git_blob_sha(raw), 'SOURCE_CLOSURE_MISMATCH')
    except (OSError, ValueError, TypeError, KeyError):raise ValueError('SOURCE_CLOSURE_MISMATCH') from None


def require_remote_environment(env):
    try:
        _need(env.get('GITHUB_ACTIONS') == 'true' and env.get('GITHUB_REPOSITORY') == REPOSITORY
              and env.get('GITHUB_RUN_ATTEMPT') == '1' and _digest(env.get('GITHUB_SHA'), 40)
              and type(env.get('GITHUB_RUN_ID')) is str and env['GITHUB_RUN_ID'].isdigit()
              and int(env['GITHUB_RUN_ID']) > 0 and bool(env.get('GH_TOKEN')), 'INVALID_REMOTE_ENVIRONMENT')
    except (ValueError, TypeError, KeyError):raise ValueError('INVALID_REMOTE_ENVIRONMENT') from None


def request_path(request):
    return 'docs/requests/engine-clock-' + request['request_id'] + '.json'


def render_workflow(template, request):
    raw = json.dumps(template).replace('__PREPARE_BRANCH__', request['branch']).replace('__REQUEST_ID__', request['request_id'])
    return json.loads(raw)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):raise ValueError('API_REDIRECT_REJECTED')


class _PublicRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self):self.count = 0
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        _need(self.count <= 5 and public_url_allowed(newurl), 'DOWNLOAD_REDIRECT_REJECTED')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def api_json(path, token):
    _need(path.startswith('/repos/' + REPOSITORY + '/') and not any(c in path for c in ('\r', '\n', '#')), 'API_PATH_REJECTED')
    request = urllib.request.Request('https://api.github.com' + path, headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'engine-clock-builder-preparation'})
    with urllib.request.build_opener(_NoRedirect()).open(request, timeout=20) as response:
        _need(response.status == 200, 'API_REJECTED')
        return _json(response.read(16777217))


def expected_inputs(root):
    py, tools, os_plan = [_json((root / p).read_bytes()) for p in (PYTHON_INPUT, PROGRESS, OS_PLAN)]
    a = py['archive']
    result = [{'id': 'python', 'filename': a['name'], 'nbytes': a['nbytes'], 'sha256': a['sha256'], 'kind': 'python',
               'url': 'https://github.com/actions/python-versions/releases/download/3.11.18-40260280589/' + a['name']}]
    for p in os_plan['packages']:
        result.append({'id': _deb_id(p['name']), 'filename': p['filename'].rsplit('/', 1)[1],
                       'nbytes': p['nbytes'], 'sha256': p['sha256'], 'kind': 'deb', 'url': os_plan['snapshot_root'] + p['filename']})
    for p in [tools['source'], *tools['tools']]:
        result.append({'id': 'input-' + ('source' if p is tools['source'] else p['name']),
                       **{k: p[k] for k in ('filename', 'nbytes', 'sha256', 'url')}, 'kind': 'input'})
    return result


def authenticate(root, request, env):
    require_remote_environment(env)
    validate_request(request)
    _need(env.get('GITHUB_REF') == 'refs/heads/' + request['branch']
          and env.get('GITHUB_WORKFLOW_REF') == REPOSITORY + '/' + request['workflow_path'] + '@refs/heads/' + request['branch'], 'INVALID_REMOTE_ENVIRONMENT')
    _need(Path(env.get('GITHUB_WORKSPACE', '')).resolve() == root.resolve(), 'INVALID_REMOTE_ENVIRONMENT')
    base = '/repos/' + REPOSITORY
    run = api_json(base + '/actions/runs/' + env['GITHUB_RUN_ID'], env['GH_TOKEN'])
    listing = api_json(base + '/actions/workflows/' + request['workflow_path'].rsplit('/', 1)[1]
                       + '/runs?branch=' + urllib.parse.quote(request['branch'], safe='') + '&per_page=2', env['GH_TOKEN'])
    validate_context(request, run, listing, run_id=int(env['GITHUB_RUN_ID']), head=env['GITHUB_SHA'])
    tree = api_json(base + '/git/trees/' + env['GITHUB_SHA'] + '?recursive=1', env['GH_TOKEN'])
    verify_source_closure(root, request, tree)
    blobs = {r['path']: r['sha'] for r in tree['tree'] if r['type'] == 'blob'}
    for path in (request_path(request), request['workflow_path']):
        _need(blobs.get(path) == git_blob_sha((root / path).read_bytes()), 'SOURCE_CLOSURE_MISMATCH')
    _need(_json((root / request['workflow_path']).read_bytes()) == render_workflow(_json((root / TEMPLATE).read_bytes()), request), 'WORKFLOW_MISMATCH')
    _need(request['inputs'] == expected_inputs(root), 'INPUT_REGISTRATION_MISMATCH')
    return {'repository': REPOSITORY, 'run_id': int(env['GITHUB_RUN_ID']), 'run_attempt': 1,
            'head_sha': env['GITHUB_SHA'], 'workflow_path': request['workflow_path'],
            'request_sha256': hashlib.sha256((root / request_path(request)).read_bytes()).hexdigest()}


def download_input(row, store, stop):
    partial = store / (row['filename'] + '.partial')
    redirect = _PublicRedirect()
    start, total, digest = monotonic(), 0, hashlib.sha256()
    _need(public_url_allowed(row['url']), 'DOWNLOAD_URL_REJECTED')
    request = urllib.request.Request(row['url'], headers={'User-Agent': 'engine-clock-builder-preparation', 'Accept': 'application/octet-stream'})
    with partial.open('xb') as output, urllib.request.build_opener(redirect).open(request, timeout=20) as response:
        _need(response.status == 200, 'DOWNLOAD_HTTP_REJECTED')
        while True:
            _need(monotonic() < stop and monotonic() - start < 120, 'DOWNLOAD_DEADLINE')
            block = response.read(min(1048576, row['nbytes'] - total + 1))
            if not block:break
            total += len(block);_need(total <= row['nbytes'], 'DOWNLOAD_SIZE_MISMATCH')
            digest.update(block);output.write(block)
    _need(total == row['nbytes'] and digest.hexdigest() == row['sha256'], 'DOWNLOAD_CONTENT_MISMATCH')
    partial.rename(store / row['filename'])
    return {'id': row['id'], 'nbytes': total, 'sha256': digest.hexdigest(), 'http_status': 200,
            'redirects': redirect.count, 'application_retries': 0}


def _clean_row(row):
    keys = {'path', 'kind', 'mode', 'nbytes'} | ({'sha256'} if row['kind'] == 'file' else {'target'} if row['kind'] == 'symlink' else set())
    return {k: row[k] for k in keys}


def tar_members(sid, archive, expected):
    lookup, seen = {r['path']: r for r in expected}, set()
    for member in archive:
        path = member.name
        while path.startswith('./'):path = path[2:]
        path = path.rstrip('/') or '.'
        kind = 'file' if member.isfile() else 'directory' if member.isdir() else 'symlink' if member.issym() else 'unsupported'
        row = {'path': path, 'kind': kind, 'mode': member.mode, 'nbytes': member.size if kind == 'file' else 0}
        if kind == 'file' and path in lookup:row['sha256'] = lookup[path].get('sha256')
        if kind == 'symlink':row['target'] = member.linkname
        _need(path in lookup and path not in seen and row == lookup[path], 'ARCHIVE_HEADER_MISMATCH')
        seen.add(path)
        stream = archive.extractfile(member) if kind == 'file' else None
        try:yield sid, row, stream
        finally:
            if stream is not None:stream.close()
    _need(seen == set(lookup), 'ARCHIVE_HEADER_MISMATCH')


def _generated(root, request):
    tools = _json((root / PROGRESS).read_bytes())
    inspection = _json((root / SOURCE_INSPECTION).read_bytes())
    config = {'tool_filenames': [p['filename'] for p in tools['tools']],
              'source_rows': [{'path': r['path'].split('/', 1)[1], 'sha256': r['sha256']}
                              for r in inspection['source_members'] if r['kind'] == 'file']}
    payloads = {'etc/passwd': b'root:x:0:0:builder:/build/home:/nonexistent\n',
                'etc/group': b'root:x:0:\n', 'etc/nsswitch.conf': b'passwd: files\ngroup: files\nhosts: files\n',
                'etc/hosts': b'127.0.0.1 localhost\n::1 localhost\n', 'etc/resolv.conf': b'', 'etc/timezone': b'Etc/UTC\n',
                'run/builder/driver.py': (root / 'scripts/engine_clock_builder_driver.py').read_bytes(),
                'run/builder/sandbox.py': (root / 'scripts/engine_clock_builder_sandbox.py').read_bytes(),
                'run/builder/config.json': canonical(config),
                'run/builder/tools.txt': ''.join(p['name'] + '==' + p['version'] + ' --hash=sha256:' + p['sha256'] + '\n' for p in tools['tools']).encode(),
                'run/builder/source.txt': ('progressbar @ file:///inputs/progressbar-2.5.tar.gz --hash=sha256:' + tools['source']['sha256'] + '\n').encode()}
    rows = [{'path': p, 'kind': 'file', 'mode': 0o644, 'nbytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()} for p, b in payloads.items()]
    rows += [{'path': p, 'kind': 'directory', 'mode': 0o755, 'nbytes': 0} for p in ('build', 'proc', 'dev', 'sys')]
    rows.append({'path': 'etc/localtime', 'kind': 'symlink', 'mode': 0o777, 'nbytes': 0, 'target': '/usr/share/zoneinfo/Etc/UTC'})
    return {'id': 'recipe', 'prefix': '.', 'archive_sha256': hashlib.sha256(canonical(rows)).hexdigest(), 'entries': rows}, payloads


def make_sources(root, request):
    python = _json((root / PYTHON_MEMBERS).read_bytes())
    packages = _json((root / OS_MEMBERS).read_bytes())['packages']
    generated, payloads = _generated(root, request)
    sources = [{'id': 'python', 'prefix': '/opt/hostedtoolcache/Python/3.11.18/x64'.lstrip('/'),
                'archive_sha256': python['archive_sha256'], 'entries': [_clean_row(r) for r in python['entries']]}]
    for package in packages:
        sources.append({'id': _deb_id(package['package']), 'prefix': '.', 'archive_sha256': package['deb_sha256'],
                        'entries': [_clean_row(r) for r in package['members']]})
    for row in request['inputs']:
        if row['kind'] == 'input':
            sources.append({'id': row['id'], 'prefix': 'inputs', 'archive_sha256': row['sha256'],
                            'entries': [{'path': row['filename'], 'kind': 'file', 'mode': 0o644,
                                         'nbytes': row['nbytes'], 'sha256': row['sha256']}]})
    return sources + [generated], payloads


def input_members(sources, request, store, generated):
    inputs = {r['id']: r for r in request['inputs']}
    for source in sources:
        sid = source['id']
        if sid == 'recipe':
            for row in source['entries']:
                yield sid, row, io.BytesIO(generated[row['path']]) if row['kind'] == 'file' else None
        elif inputs[sid]['kind'] == 'input':
            row = source['entries'][0]
            with (store / row['path']).open('rb') as stream:yield sid, row, stream
        elif sid == 'python':
            with tarfile.open(store / inputs[sid]['filename'], mode='r|gz') as archive:
                yield from tar_members(sid, archive, source['entries'])
        else:
            # dpkg-deb is a trusted host decoder only; maintainer scripts never run.
            process = subprocess.Popen(['/usr/bin/dpkg-deb', '--fsys-tarfile', str(store / inputs[sid]['filename'])],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env=sandbox.HOST_ENV, close_fds=True, start_new_session=True)
            try:
                with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
                    yield from tar_members(sid, archive, source['entries'])
                _need(process.wait(timeout=5) == 0, 'DEB_DECODER_FAILED')
            finally:
                try:os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:pass
                process.stdout.close();process.wait(timeout=5)


def capability_probe(work, facts=None):
    tool = Path('/usr/bin/bwrap')
    _need(tool.is_file() and not tool.stat().st_mode & 0o6000 and tool.stat().st_size <= 1048576, 'UNSUPPORTED_HOST_TOOL')
    if facts is None:facts = {}
    facts.update(bwrap_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(), kernel=os.uname().release,
                 host_source_sha256='9760d007363e3abba7c747489910f9f82d9fca53ba3bd3282e396fa3c97a3314')
    facts['version_process'], version = sandbox.capture(['/usr/bin/bwrap', '--version'], timeout=5)
    _need(facts['version_process']['status'] == 'EXITED' and facts['version_process']['returncode'] == 0
          and version == b'bubblewrap 0.12.0\n', 'UNSUPPORTED_HOST_TOOL')
    facts['version'] = '0.12.0'
    help_receipt, raw = sandbox.capture(['/usr/bin/bwrap', '--help'], timeout=5)
    facts['help'] = help_receipt
    _need(help_receipt['status'] == 'EXITED' and help_receipt['returncode'] == 0
          and sandbox.supported_options(raw.decode('utf-8')), 'UNSUPPORTED_HOST_OPTIONS')
    root = work / 'trusted-probe-root';root.mkdir()
    for p in ('usr', 'lib', 'lib64', 'proc', 'dev', 'build'):(root / p).mkdir()
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        argv = sandbox.launch_argv(fd);at = argv.index('--')
        argv = argv[:at] + ['--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64', '--', '/usr/bin/true']
        facts['trusted_true'], _ = sandbox.capture(argv, timeout=10, pass_fds=(fd,))
    finally:os.close(fd)
    _need(facts['trusted_true']['status'] == 'EXITED' and facts['trusted_true']['returncode'] == 0, 'UNSUPPORTED_HOST_NAMESPACE')
    return facts


def run_preparation(root, request, env):
    out = root / 'output/stage7-builder-preparation' / request['request_id']
    out.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': 'builder-preparation-result-v1', 'status': 'FAILED_OR_INCOMPLETE', 'errors': [],
               'request_id': request['request_id'], 'source_execution_attempted': False, 'target_execution_verified': False,
               'image_preparation_ready': False, 'native_admission': False, 'full_lock_ready': False,
               'official_model_calls': 0, 'transports': []}
    work = Path('/tmp/engine-clock-preparation-' + request['request_id'])
    try:
        receipt['context'] = authenticate(root, request, env)
        work.mkdir(mode=0o700, exist_ok=False)
        receipt['host'] = {}
        capability_probe(work, receipt['host'])
        store = work / 'inputs';store.mkdir()
        stop = monotonic() + 300
        for row in request['inputs']:receipt['transports'].append(download_input(row, store, stop))
        sources, payloads = make_sources(root, request)
        plan = staging.compile_plan(sources)
        (out / 'root-files.json').write_bytes(canonical(plan))
        receipt['staging'] = staging.stage_tree(work / 'root', plan, input_members(sources, request, store, payloads), deadline=perf_counter() + 180)
        _need(receipt['staging']['status'] == 'STAGED_CONTENT_MATCH', 'STAGING_FAILED')
        receipt['verification'] = staging.verify_tree(work / 'root', plan, deadline=perf_counter() + 180)
        _need(receipt['verification']['status'] == 'STAGED_CONTENT_MATCH', 'ROOT_VERIFICATION_FAILED')
        fd = os.open(work / 'root', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            receipt['open_root_verification'] = staging.verify_open_tree(fd, plan, deadline=perf_counter() + 180)
            _need(receipt['open_root_verification']['status'] == 'STAGED_CONTENT_MATCH', 'ROOT_VERIFICATION_FAILED')
            receipt['source_execution_attempted'] = True
            receipt['execution'], raw = sandbox.capture(sandbox.launch_argv(fd), timeout=180, pass_fds=(fd,))
        finally:os.close(fd)
        if receipt['execution']['status'] == 'EXITED' and receipt['execution']['returncode'] != 0:
            receipt['driver_failure_claim'] = sandbox.failure_code(raw)
        _need(receipt['execution']['status'] == 'EXITED' and receipt['execution']['returncode'] == 0, 'BUILDER_EXECUTION_FAILED')
        receipt['driver'], wheel = sandbox.decode_wire(raw)
        policy = _json((root / POLICY).read_bytes())['output_policy']
        pins = {**policy['runtime_files'], 'progressbar-2.5.dist-info/licenses/LICENSE.txt': policy['license_bytes_sha256']}
        receipt['wheel'] = wheel_check.validate_wheel(wheel, pins)
        _need(receipt['wheel']['status'] == 'WHEEL_BYTES_MATCH', 'WHEEL_REJECTED')
        (out / policy['expected_filename']).write_bytes(wheel)
        receipt.update(status='BUILT_WHEEL_VERIFIED', target_execution_verified=True)
    except ValueError as exc:
        allowed = {'UNSUPPORTED_HOST_TOOL', 'UNSUPPORTED_HOST_OPTIONS', 'UNSUPPORTED_HOST_NAMESPACE',
                   'DOWNLOAD_URL_REJECTED', 'DOWNLOAD_REDIRECT_REJECTED', 'DOWNLOAD_HTTP_REJECTED',
                   'DOWNLOAD_DEADLINE', 'DOWNLOAD_SIZE_MISMATCH', 'DOWNLOAD_CONTENT_MISMATCH',
                   'STAGING_FAILED', 'ROOT_VERIFICATION_FAILED', 'BUILDER_EXECUTION_FAILED',
                   'WHEEL_REJECTED', 'INVALID_DRIVER_WIRE', 'INVALID_RUN_CONTEXT', 'INVALID_REMOTE_ENVIRONMENT',
                   'SOURCE_CLOSURE_MISMATCH', 'WORKFLOW_MISMATCH', 'INPUT_REGISTRATION_MISMATCH'}
        receipt['errors'] = [{'code': str(exc) if str(exc) in allowed else 'PREPARATION_FAILED'}]
    except Exception:
        receipt['errors'] = [{'code': 'PREPARATION_FAILED'}]
    finally:
        (out / 'source-closure.json').write_bytes(canonical(request))
        (out / 'preparation.json').write_bytes(canonical(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True);parser.add_argument('--guard-only', action='store_true')
    args = parser.parse_args()
    try:
        require_remote_environment(os.environ)
        root = Path(__file__).resolve().parent.parent
        _need(args.request.startswith('docs/requests/') and Path(args.request).name == args.request.split('/')[-1]
              and '..' not in args.request.split('/'), 'INVALID_REQUEST_PATH')
        request = validate_request(_json((root / args.request).read_bytes()))
        _need(args.request == request_path(request), 'INVALID_REQUEST_PATH')
        if args.guard_only:
            authenticate(root, request, os.environ)
            print('REGISTERED_REMOTE_CONTEXT_VALID')
            return 0
        receipt = run_preparation(root, request, os.environ)
        print(receipt['status'])
        return 0 if receipt['status'] == 'BUILT_WHEEL_VERIFIED' else 1
    except Exception:
        print('REGISTERED_REMOTE_CONTEXT_REJECTED')
        return 1


if __name__ == '__main__':raise SystemExit(main())
