"""One-use model-free namespace diagnosis; no host policy or network changes."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import struct
import sys
import time
import urllib.parse

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_builder_preparation as prep
from scripts import engine_clock_builder_sandbox as sandbox

REQUEST_ID = 'namespace-diagnostic-20261113-01'
BRANCH = 'diagnose/engine-clock-namespace-20261113-01'
WORKFLOW = '.github/workflows/engine-clock-namespace-diagnostic.yml'
REQUEST_PATH = 'docs/requests/engine-clock-' + REQUEST_ID + '.json'
CASES = ('USER_NET', 'USER_NET_DROP_BOUNDING', 'USER_NET_DROP_ALL_CAPS')
CLOSURE = frozenset([WORKFLOW, 'scripts/__init__.py',
    *['scripts/engine_clock_builder_' + x + '.py' for x in ('preparation', 'staging', 'sandbox', 'wheel', 'driver')],
    'scripts/engine_clock_namespace_diagnostic.py', 'tests/test_engine_clock_namespace_diagnostic.py',
    'docs/superpowers/specs/2026-11-13-engine-clock-namespace-diagnostic-design.md',
    'docs/superpowers/plans/2026-11-13-engine-clock-namespace-diagnostic.md'])


def profile_value(raw):
    known = raw.strip().decode('ascii', 'ignore')
    allowed = ('unconfined', 'unprivileged_userns', 'unprivileged_userns (enforce)',
               'docker-default (enforce)', 'bwrap (enforce)')
    return {'known': known if known in allowed else None, 'nbytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def _read(path, limit=16384):
    try:
        with path.open('rb') as f: return f.read(limit)
    except OSError: return b''


def namespace_ids(proc=Path('/proc')):
    result = {}
    for name in ('user', 'net'):
        try:
            st = (proc / 'self/ns' / name).stat()
            result[name] = [st.st_dev, st.st_ino]
        except OSError: result[name] = None
    return result


def facts(proc=Path('/proc')):
    result = {'namespaces': namespace_ids(proc), 'effective_uid': os.geteuid(),
              'effective_gid': os.getegid(), 'status': {}, 'sysctls': {},
              'profile': profile_value(_read(proc / 'self/attr/current'))}
    for line in _read(proc / 'self/status').decode('ascii', 'ignore').splitlines():
        key, sep, value = line.partition(':'); value = value.strip()
        if key in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb') and re.fullmatch('[0-9a-f]{16}', value):
            result['status'][key] = value
        elif key in ('NoNewPrivs', 'Seccomp', 'Seccomp_filters') and value.isdigit():
            result['status'][key] = int(value)
    for name in ('user/max_user_namespaces', 'kernel/unprivileged_userns_clone',
                 'kernel/apparmor_restrict_unprivileged_userns', 'kernel/cap_last_cap'):
        raw = _read(proc / 'sys' / name, 32).strip()
        result['sysctls'][name] = int(raw) if raw.isdigit() else None
    return result


def parse_ack(raw, seq):
    if len(raw) < 36: raise ValueError('INVALID_NETLINK_ACK')
    length, kind, flags, actual_seq, pid = struct.unpack_from('=IHHII', raw)
    if length != len(raw) or kind != 2 or actual_seq != seq:
        raise ValueError('INVALID_NETLINK_ACK')
    error, = struct.unpack_from('=i', raw, 16)
    if not -4095 <= error <= 0: raise ValueError('INVALID_NETLINK_ACK')
    return -error


class Linux:
    def __init__(self):
        self.uid, self.gid = os.getuid(), os.getgid()
        self.libc = ctypes.CDLL(None, use_errno=True)

    def namespaces(self): return namespace_ids()
    def facts(self): return facts()

    def _call(self, name, *args):
        if getattr(self.libc, name)(*args) != 0:
            number = ctypes.get_errno()
            raise OSError(number, 'SYSCALL_FAILED')

    def unshare(self): self._call('unshare', ctypes.c_int(0x10000000 | 0x40000000))

    def map_ids(self):
        Path('/proc/self/setgroups').write_text('deny\n')
        Path('/proc/self/uid_map').write_text('0 ' + str(self.uid) + ' 1\n')
        Path('/proc/self/gid_map').write_text('0 ' + str(self.gid) + ' 1\n')
        if os.geteuid() != 0 or os.getegid() != 0: raise OSError(1, 'MAPPING_FAILED')

    def drop_bounding(self):
        last = _read(Path('/proc/sys/kernel/cap_last_cap'), 16).strip()
        if not last.isdigit() or not 0 <= int(last) <= 63: raise OSError(22, 'INVALID_CAP_RANGE')
        for cap in range(int(last) + 1): self._call('prctl', 24, cap, 0, 0, 0)

    def clear_capabilities(self):
        # Linux capability v3: two 32-bit effective/permitted/inheritable words.
        header = (ctypes.c_uint32 * 2)(0x20080522, 0)
        data = (ctypes.c_uint32 * 6)()
        self._call('capset', ctypes.byref(header), ctypes.byref(data))

    def _netlink(self, kind, payload, seq):
        # Only called by run_worker after both namespace IDs changed.
        header = struct.pack('=IHHII', 16 + len(payload), kind, 1 | 4 | (0x600 if kind == 20 else 0), seq, 0)
        with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, socket.NETLINK_ROUTE) as sock:
            sock.settimeout(3)
            sock.bind((0, 0))
            sock.sendto(header + payload, (0, 0))
            raw, peer = sock.recvfrom(4096)
            if peer[0] != 0: raise ValueError('INVALID_NETLINK_PEER')
            error = parse_ack(raw, seq)
            if error: raise OSError(error, 'NETLINK_FAILED')

    def address(self):
        index = socket.if_nametoindex('lo')
        attr = lambda kind: struct.pack('=HH', 8, kind) + socket.inet_aton('127.0.0.1')
        self._netlink(20, struct.pack('=BBBBI', socket.AF_INET, 8, 0, 254, index) + attr(1) + attr(2), 1)

    def link(self):
        self._netlink(16, struct.pack('=BBHiII', 0, 0, 0, socket.if_nametoindex('lo'), 1, 1), 2)


def run_worker(case, backend=None):
    if case not in CASES: raise ValueError('INVALID_CASE')
    backend = backend or Linux()
    result = {'case': case, 'pid': os.getpid(), 'status': 'FAILED', 'stage': 'START',
              'errno': None, 'isolation_proven': False, 'before': backend.facts()}
    before = backend.namespaces()
    try:
        result['stage'] = 'UNSHARE'; backend.unshare()
        after = backend.namespaces()
        if not all(before.get(k) is not None and after.get(k) is not None and before[k] != after[k] for k in ('user', 'net')):
            result['status'] = 'ISOLATION_NOT_PROVEN'
            return result
        result['isolation_proven'] = True
        result['stage'] = 'MAPPING'; backend.map_ids()
        result['after_mapping'] = backend.facts()
        result['stage'] = 'INTERVENTION'
        if case == 'USER_NET_DROP_BOUNDING': backend.drop_bounding()
        elif case == 'USER_NET_DROP_ALL_CAPS': backend.clear_capabilities()
        result['after_intervention'] = backend.facts()
        result['stage'] = 'ADDRESS'; backend.address()
        result['stage'] = 'LINK'; backend.link()
        result['stage'] = result['status'] = 'COMPLETE'
    except OSError as exc:
        result['errno'] = exc.errno if type(exc.errno) is int and 0 < exc.errno <= 4095 else None
    except ValueError:
        result['status'] = 'PROTOCOL_FAILED'
    result['after'] = backend.facts()
    return result


def filter_denials(raw, pids):
    rows = []
    for line in raw.splitlines():
        try:
            message = json.loads(line).get('MESSAGE', '')
            if not isinstance(message, str) or not all(x in message for x in ('apparmor="DENIED"', 'operation="capable"', 'capname="net_admin"')): continue
            match = re.search(r'\bpid=([0-9]+)\b', message)
            if not match or int(match[1]) not in pids: continue
            label = re.search(r'\bprofile="([^"]*)"', message)
            rows.append({'pid': int(match[1]), 'capname': 'net_admin', 'operation': 'capable',
                         'profile': profile_value(label[1].encode() if label else b''),
                         'message_sha256': hashlib.sha256(message.encode()).hexdigest()})
            if len(rows) >= 32: break
        except (ValueError, TypeError, AttributeError): continue
    return rows


def validate_request(value):
    try:
        prep._need(type(value) is dict and set(value) == {'schema', 'request_id', 'repository', 'branch',
                   'workflow_path', 'reviewed_source_sha', 'budget', 'source_closure'}, 'INVALID_REQUEST')
        expected = {'schema': 'namespace-diagnostic-request-v1', 'request_id': REQUEST_ID,
                    'repository': prep.REPOSITORY, 'branch': BRANCH, 'workflow_path': WORKFLOW}
        prep._need(all(value[k] == v for k, v in expected.items()) and prep._digest(value['reviewed_source_sha'], 40), 'INVALID_REQUEST')
        budget = value['budget']
        prep._need(type(budget) is dict and budget == {'runs': 1, 'attempts': 1, 'workers': 3}
                   and all(type(v) is int for v in budget.values()), 'INVALID_REQUEST')
        prep._need(type(value['source_closure']) is dict and set(value['source_closure']) == CLOSURE
                   and all(prep._digest(d) for d in value['source_closure'].values()), 'INVALID_REQUEST')
        return value
    except (ValueError, TypeError, KeyError): raise ValueError('INVALID_REQUEST') from None


def authenticate(root, env):
    prep.require_remote_environment(env)
    request = validate_request(prep._json((root / REQUEST_PATH).read_bytes()))
    prep._need(env.get('GITHUB_REF') == 'refs/heads/' + BRANCH and env.get('GITHUB_WORKFLOW_REF') ==
               prep.REPOSITORY + '/' + WORKFLOW + '@refs/heads/' + BRANCH and
               Path(env.get('GITHUB_WORKSPACE', '')).resolve() == root.resolve(), 'INVALID_REMOTE_ENVIRONMENT')
    base = '/repos/' + prep.REPOSITORY
    api = lambda path: prep.api_json(base + path, env['GH_TOKEN'])
    run = api('/actions/runs/' + env['GITHUB_RUN_ID'])
    listing = api('/actions/workflows/engine-clock-namespace-diagnostic.yml/runs?branch=' + urllib.parse.quote(BRANCH, safe='') + '&per_page=2')
    prep.validate_context(request, run, listing, run_id=int(env['GITHUB_RUN_ID']), head=env['GITHUB_SHA'])
    tree = api('/git/trees/' + env['GITHUB_SHA'] + '?recursive=1')
    prep.verify_source_closure(root, request, tree)
    prep.verify_source_closure(root, request, api('/git/trees/' + request['reviewed_source_sha'] + '?recursive=1'))
    blobs = {row['path']: row['sha'] for row in tree['tree'] if row['type'] == 'blob'}
    prep._need(blobs.get(REQUEST_PATH) == prep.git_blob_sha((root / REQUEST_PATH).read_bytes()), 'SOURCE_CLOSURE_MISMATCH')
    return {'request': request, 'run_id': int(env['GITHUB_RUN_ID']), 'head_sha': env['GITHUB_SHA'],
            'run_attempt': 1, 'request_sha256': hashlib.sha256((root / REQUEST_PATH).read_bytes()).hexdigest()}


def run(root, env):
    binding = authenticate(root, env)
    start = int(time.time())
    result = {'schema': 'namespace-diagnostic-result-v1', 'binding': binding, 'host': facts(),
              'kernel': os.uname().release, 'cases': [], 'model_execution': False, 'build_execution': False,
              'full_sandbox_verified': False, 'status': 'DIAGNOSTIC_INCOMPLETE'}
    image = env.get('ImageVersion', '')
    result['image_version'] = image if re.fullmatch(r'[0-9.\-]{1,64}', image) else None
    pids = set()
    for case in CASES:
        receipt, raw = sandbox.capture(['/usr/bin/python3', '-I', '-S', '-B', str(root / 'scripts/engine_clock_namespace_diagnostic.py'),
                                        '--worker', case], timeout=20, stdout_limit=32768, stderr_limit=8192)
        item = {'case': case, 'transport': receipt, 'observation': None}
        if receipt['status'] == 'EXITED' and receipt['returncode'] == 0:
            value = prep._json(raw)
            prep._need(type(value) is dict and value.get('case') == case and type(value.get('pid')) is int and value['pid'] > 0, 'INVALID_WORKER_RESULT')
            item['observation'] = value; pids.add(value['pid'])
        result['cases'].append(item)
    end = int(time.time()) + 1
    receipt, raw = sandbox.capture(['/usr/bin/sudo', '-n', '/usr/bin/journalctl', '-k', '--since', '@' + str(start),
                                    '--until', '@' + str(end), '--no-pager', '-o', 'json'],
                                   timeout=10, stdout_limit=1048576, stderr_limit=8192)
    result['kernel_log'] = {'transport': receipt, 'availability': 'UNKNOWN', 'matching_denials': []}
    if receipt['status'] == 'EXITED' and receipt['returncode'] == 0:
        result['kernel_log'].update(availability='READ_COMPLETE', matching_denials=filter_denials(raw, pids))
    if all(x['observation'] is not None for x in result['cases']): result['status'] = 'DIAGNOSTIC_COMPLETE_NOT_BUILD_READY'
    output = root / 'output/stage7-namespace-diagnostic' / REQUEST_ID
    output.mkdir(parents=True, exist_ok=False)
    raw = prep.canonical(result)
    prep._need(len(raw) <= 131072, 'RESULT_TOO_LARGE')
    (output / 'diagnostic.json').write_bytes(raw)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', choices=CASES)
    args = parser.parse_args()
    try:
        if args.worker: sys.stdout.buffer.write(prep.canonical(run_worker(args.worker)))
        else: run(Path(__file__).resolve().parent.parent, dict(os.environ))
    except Exception:
        # No exception text/paths/credentials from the authenticated parent.
        print('NAMESPACE_DIAGNOSTIC_FAILED', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__': raise SystemExit(main())
