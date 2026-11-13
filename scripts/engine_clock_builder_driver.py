"""Owned sandbox driver. Importing this module never launches a build."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
from time import monotonic
import zipfile

BASE = '/opt/hostedtoolcache/Python/3.11.18/x64/bin/python3.11'
VENV = '/build/env/bin/python'
OUTPUT = '/build/out/progressbar-2.5-py3-none-any.whl'
MAX_FILES = 20000


def _need(ok, code):
    if not ok:raise ValueError(code)


def _safe(path):
    return type(path) is str and path and not path.startswith('/') and '\\' not in path and all(p not in ('', '.', '..') for p in path.split('/'))


def _snapshot(root):
    rows = {}
    for parent, directories, files in os.walk(root, followlinks=False):
        _need(len(rows) <= MAX_FILES, 'TREE_LIMIT')
        for name in directories:
            _need(not (Path(parent) / name).is_symlink(), 'TREE_LINK')
        for name in files:
            _need(len(rows) < MAX_FILES, 'TREE_LIMIT')
            path = Path(parent) / name
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                info = os.fstat(fd)
                _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 4194304, 'TREE_FILE')
                data = bytearray()
                while len(data) <= 4194304:
                    block = os.read(fd, 65536)
                    if not block:break
                    data.extend(block)
                _need(len(data) == info.st_size, 'TREE_FILE')
                rows[path.relative_to(root).as_posix()] = hashlib.sha256(data).hexdigest()
            finally:os.close(fd)
    return rows


def _receipt(rows, **extra):
    raw = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
    return {'snapshot_sha256': hashlib.sha256(raw).hexdigest(), 'files': len(rows), **extra}


def verify_tools(site, wheels):
    try:
        expected, distributions = {}, set()
        for path in wheels:
            with zipfile.ZipFile(path) as archive:
                for entry in archive.infolist():
                    name = entry.filename
                    _need(_safe(name) and not entry.is_dir() and entry.file_size <= 4194304
                          and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG), 'TOOL_PAYLOAD_MISMATCH')
                    if '.dist-info/' in name:distributions.add(name.split('/')[0])
                    if name.endswith('.dist-info/RECORD'):continue
                    _need(name not in expected, 'TOOL_PAYLOAD_MISMATCH')
                    expected[name] = hashlib.sha256(archive.read(entry)).hexdigest()
        rows = _snapshot(site)
        _need(all(rows.get(p) == h for p, h in expected.items()), 'TOOL_PAYLOAD_MISMATCH')
        for path in set(rows) - set(expected):
            metadata = any(path == d + '/' + n for d in distributions for n in ('RECORD', 'INSTALLER', 'REQUESTED'))
            parts = Path(path)
            pyc = (parts.parent.name == '__pycache__' and parts.name.endswith('.cpython-311.pyc')
                   and (parts.parent.parent / (parts.name[:-len('.cpython-311.pyc')] + '.py')).as_posix() in expected)
            _need(metadata or pyc, 'TOOL_PAYLOAD_MISMATCH')
            if pyc:_need((site / path).read_bytes()[:4] == importlib.util.MAGIC_NUMBER, 'TOOL_PAYLOAD_MISMATCH')
        return _receipt(rows, installed_files=len(rows), payload_files=len(expected))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        raise ValueError('TOOL_PAYLOAD_MISMATCH') from None


def verify_source(root, source_rows):
    try:
        rows = _snapshot(root)
        expected = {row['path']: row['sha256'] for row in source_rows}
        _need(len(expected) == len(source_rows) and all(_safe(p) for p in expected), 'SOURCE_PAYLOAD_MISMATCH')
        for path, digest in expected.items():
            mutable = path == 'README.txt' or path.startswith('progressbar.egg-info/')
            _need(path in rows and (mutable or rows[path] == digest), 'SOURCE_PAYLOAD_MISMATCH')
        for path in set(rows) - set(expected):
            _need(path.startswith('build/') or path.startswith('progressbar.egg-info/'), 'SOURCE_PAYLOAD_MISMATCH')
        return _receipt(rows)
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError('SOURCE_PAYLOAD_MISMATCH') from None


def commands():
    pip = [VENV, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', '--no-input', '--no-cache-dir']
    offline = ['--no-index', '--no-deps', '--require-hashes', '--no-compile']
    return {'VENV': [BASE, '-I', '-S', '-B', '-m', 'venv', '--without-pip', '--symlinks', '/build/env'],
            'ENSUREPIP': [VENV, '-I', '-B', '-m', 'ensurepip', '--upgrade'],
            'TOOLS': pip + ['install'] + offline + ['--find-links', '/inputs', '-r', '/run/builder/tools.txt'],
            'BUILD': pip + ['wheel'] + offline + ['--no-build-isolation', '--no-clean', '--wheel-dir', '/build/out', '-r', '/run/builder/source.txt'],
            'SMOKE': [VENV, '-I', '-B', '-c', 'import sys;sys.path.insert(0,"' + OUTPUT + '");import progressbar;assert progressbar.__version__=="2.5";print("progressbar2.5-import-ok")']}


def _namespace_checks():
    _need(os.getuid() == os.getgid() == 0, 'UNSUPPORTED_NAMESPACE')
    for root in ('/', '/proc', '/dev', '/dev/pts'):
        _need(os.statvfs(root).f_flag & os.ST_RDONLY, 'UNSUPPORTED_NAMESPACE')
    fs = os.statvfs('/build')
    _need(0 < fs.f_blocks * fs.f_frsize <= 268435456 and not fs.f_flag & os.ST_RDONLY, 'UNSUPPORTED_QUOTA')
    mounts = Path('/proc/self/mountinfo').read_text().splitlines()
    _need(any(line.split()[4] == '/build' and ' - tmpfs ' in line for line in mounts), 'UNSUPPORTED_QUOTA')
    # bwrap sets1 in the outer namespace, then enters its single permitted
    # child and explicitly tests another unshare fails. The visible value is1.
    _need(Path('/proc/sys/user/max_user_namespaces').read_text().strip() in ('0', '1'), 'UNSUPPORTED_NAMESPACE')
    status = Path('/proc/self/status').read_text().splitlines()
    _need(any(line.startswith('CapEff:') and int(line.split()[1], 16) == 0 for line in status), 'UNSUPPORTED_CAPABILITIES')
    _need(set(os.listdir('/sys/class/net')) <= {'lo'} if Path('/sys/class/net').exists() else True, 'UNSUPPORTED_NETWORK')
    _need(len(Path('/proc/net/route').read_text().splitlines()) == 1, 'UNSUPPORTED_NETWORK')


def main():
    # All target work is behind this exact invocation and runtime/namespace checks.
    if sys.argv != [sys.argv[0], '--registered-builder-v1']:
        return 2
    result = {'schema': 'builder-driver-failure-v1', 'status': 'FAILED', 'code': 'DRIVER_FAILED', 'steps': []}
    try:
        _need(sys.version_info[:3] == (3, 11, 18) and sys.flags.isolated and sys.flags.no_site, 'UNSUPPORTED_PYTHON')
        _namespace_checks()
        helper_spec = importlib.util.spec_from_file_location('owned_sandbox', '/run/builder/sandbox.py')
        helper = importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
        config = json.loads(Path('/run/builder/config.json').read_bytes())
        for name in ('tmp', 'out', 'home'):Path('/build', name).mkdir()
        stop = monotonic() + 175
        site = Path('/build/env/lib/python3.11/site-packages')
        verification = {}
        for stage, argv in commands().items():
            receipt, raw = helper.capture(argv, timeout=max(.001, stop - monotonic()), child_environment=True)
            result['steps'].append({'stage': stage, **receipt})
            _need(receipt['status'] == 'EXITED' and receipt['returncode'] == 0, 'COMMAND_FAILED')
            if stage == 'ENSUREPIP':
                bundles = list(Path(BASE).parent.parent.joinpath('lib/python3.11/ensurepip/_bundled').glob('*.whl'))
                _need(len(bundles) == 2, 'BOOTSTRAP_MISMATCH')
                verification['bootstrap'] = verify_tools(site, bundles)
            elif stage == 'TOOLS':
                verification['tools'] = verify_tools(site, [Path('/inputs', n) for n in config['tool_filenames']])
            elif stage == 'BUILD':
                sources = list(Path('/build/tmp').glob('pip-req-build-*'))
                _need(len(sources) == 1, 'SOURCE_PAYLOAD_MISMATCH')
                verification['source'] = verify_source(sources[0], config['source_rows'])
            elif stage == 'SMOKE':
                _need(raw == b'progressbar2.5-import-ok\n', 'SMOKE_FAILED')
        wheel = Path(OUTPUT).read_bytes()
        _need(0 < len(wheel) <= 1048576 and sorted(p.name for p in Path('/build/out').iterdir()) == [Path(OUTPUT).name], 'OUTPUT_MISMATCH')
        result = {'schema': 'builder-driver-v1', 'status': 'BUILT', 'python': '3.11.18',
                  'steps': result['steps'], 'tools_verified': True, 'source_verified': True,
                  'smoke_verified': True, 'wheel_b64': base64.b64encode(wheel).decode(), 'verification': verification}
    except ValueError as exc:
        if str(exc) in {'UNSUPPORTED_PYTHON', 'UNSUPPORTED_NAMESPACE', 'UNSUPPORTED_QUOTA',
                        'UNSUPPORTED_CAPABILITIES', 'UNSUPPORTED_NETWORK', 'COMMAND_FAILED',
                        'BOOTSTRAP_MISMATCH', 'TOOL_PAYLOAD_MISMATCH', 'SOURCE_PAYLOAD_MISMATCH',
                        'SMOKE_FAILED', 'OUTPUT_MISMATCH'}:
            result['code'] = str(exc)
    except Exception:
        # No exception text, package logs or environment is ever serialized.
        pass
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n')
    return 0 if result['status'] == 'BUILT' else 1


if __name__ == '__main__':
    raise SystemExit(main())
