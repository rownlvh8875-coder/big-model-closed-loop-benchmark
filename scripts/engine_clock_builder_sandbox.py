"""Fixed builder namespace profile and bounded non-persisting pipe transport."""
import base64
import hashlib
import json
import math
import os
import resource
import selectors
import signal
import subprocess
from time import monotonic

PYTHON = '/opt/hostedtoolcache/Python/3.11.18/x64/bin/python3.11'
HOST_ENV = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}
CHILD_ENV = {'PATH': '/build/env/bin:/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
             'TZ': 'UTC', 'TMPDIR': '/build/tmp', 'PIP_CONFIG_FILE': '/dev/null',
             'SOURCE_DATE_EPOCH': '315532800', 'PIP_NO_COMPILE': '1',
             'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0'}
REQUIRED_OPTIONS = ('--unshare-user', '--unshare-pid', '--unshare-net', '--unshare-ipc',
                    '--unshare-uts', '--disable-userns', '--assert-userns-disabled',
                    '--ro-bind-fd', '--size', '--cap-drop', '--die-with-parent',
                    '--new-session', '--clearenv', '--remount-ro', '--proc', '--dev')


def supported_options(help_text):
    return type(help_text) is str and set(REQUIRED_OPTIONS) <= set(help_text.split())


def launch_argv(rootfd):
    if type(rootfd) is not int or rootfd < 0:
        raise ValueError('INVALID_ROOT_FD')
    args = ['/usr/bin/bwrap', '--unshare-user', '--unshare-pid', '--unshare-net',
            '--unshare-ipc', '--unshare-uts', '--uid', '0', '--gid', '0',
            '--disable-userns', '--assert-userns-disabled', '--cap-drop', 'ALL',
            '--die-with-parent', '--new-session', '--clearenv',
            '--ro-bind-fd', str(rootfd), '/', '--proc', '/proc', '--remount-ro', '/proc',
            '--dev', '/dev', '--remount-ro', '/dev/pts', '--remount-ro', '/dev',
            '--size', '268435456', '--tmpfs', '/build', '--chdir', '/build']
    for key, value in CHILD_ENV.items():
        args += ['--setenv', key, value]
    return args + ['--', PYTHON, '-I', '-S', '-B', '/run/builder/driver.py', '--registered-builder-v1']


def _limits():
    for which, limit in ((resource.RLIMIT_CORE, 0), (resource.RLIMIT_FSIZE, 4194304),
                         (resource.RLIMIT_AS, 1073741824), (resource.RLIMIT_NPROC, 64),
                         (resource.RLIMIT_NOFILE, 64), (resource.RLIMIT_CPU, 181)):
        resource.setrlimit(which, (limit, limit))


def capture(argv, *, timeout, stdout_limit=3145728, stderr_limit=1048576, pass_fds=(), child_environment=False):
    """Private wire bytes stay in memory; receipt never includes subprocess text."""
    if (type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 180
            or type(stdout_limit) is not int or not 0 < stdout_limit <= 3145728
            or type(stderr_limit) is not int or not 0 < stderr_limit <= 1048576
            or type(child_environment) is not bool):
        raise ValueError('INVALID_CAPTURE_BUDGET')
    result = {'status': 'SPAWN_FAILED', 'returncode': None, 'stdout_bytes': 0, 'stderr_bytes': 0,
              'stdout_sha256': hashlib.sha256(b'').hexdigest(), 'stderr_sha256': hashlib.sha256(b'').hexdigest()}
    buffers, hashes = bytearray(), {n: hashlib.sha256() for n in ('stdout', 'stderr')}
    process, selector = None, selectors.DefaultSelector()
    start, stopped = monotonic(), None
    try:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=CHILD_ENV if child_environment else HOST_ENV, close_fds=True,
                                   pass_fds=pass_fds, start_new_session=True, preexec_fn=_limits)
        result['status'] = 'EXITED'
        for name in ('stdout', 'stderr'):
            pipe = getattr(process, name)
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, name)
        while selector.get_map() or process.poll() is None:
            now = monotonic()
            if stopped is None and now - start >= timeout:
                result['status'], stopped = 'TIMEOUT', now
            if stopped is not None:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                if now - stopped >= 5:
                    result['status'] = 'CLEANUP_FAILED'
                    break
            for key, _ in selector.select(.02):
                block = os.read(key.fileobj.fileno(), 65536)
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                name = key.data
                result[name + '_bytes'] += len(block)
                hashes[name].update(block)
                limit = stdout_limit if name == 'stdout' else stderr_limit
                if result[name + '_bytes'] > limit and stopped is None:
                    result['status'], stopped = 'OUTPUT_LIMIT', monotonic()
                if name == 'stdout' and result['stdout_bytes'] <= stdout_limit and stopped is None:
                    buffers.extend(block)
                if stopped is not None:
                    break
            if stopped is not None:
                # Stop consuming as soon as any budget fails. Counts/hashes cover
                # consumed bytes, not an unbounded post-failure drain.
                for key in list(selector.get_map().values()):
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
            if stopped is not None and process.poll() is not None and not selector.get_map():
                break
        try: result['returncode'] = process.wait(timeout=5 if stopped is None else max(.01, 5 - (monotonic() - stopped)))
        except subprocess.TimeoutExpired:
            result['status'] = 'CLEANUP_FAILED'
    except (OSError, ValueError, subprocess.SubprocessError):
        result['status'] = 'SPAWN_FAILED' if process is None else 'TRANSPORT_FAILED'
    finally:
        if process is not None:
            # Also remove descendants that closed both pipes before their parent exited.
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            for name in ('stdout', 'stderr'):
                getattr(process, name).close()
            try: process.wait(timeout=5 if stopped is None else max(.001, 5 - (monotonic() - stopped)))
            except subprocess.TimeoutExpired: result['status'] = 'CLEANUP_FAILED'
        selector.close()
        for name, digest in hashes.items():
            result[name + '_sha256'] = digest.hexdigest()
    return result, bytes(buffers) if result['status'] == 'EXITED' else b''


def _pairs(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise ValueError('INVALID_DRIVER_WIRE')
        result[key] = value
    return result


def failure_code(raw):
    """Only a fixed child claim, never a verified diagnosis or subprocess text."""
    codes = {'DRIVER_FAILED', 'UNSUPPORTED_PYTHON', 'UNSUPPORTED_NAMESPACE', 'UNSUPPORTED_QUOTA',
             'UNSUPPORTED_CAPABILITIES', 'UNSUPPORTED_NETWORK', 'COMMAND_FAILED', 'BOOTSTRAP_MISMATCH',
             'TOOL_PAYLOAD_MISMATCH', 'SOURCE_PAYLOAD_MISMATCH', 'SMOKE_FAILED', 'OUTPUT_MISMATCH'}
    try:
        if type(raw) is not bytes or len(raw) > 3145728:return 'UNAVAILABLE'
        value = json.loads(raw, object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if (type(value) is dict and set(value) == {'schema', 'status', 'code', 'steps'}
                and value['schema'] == 'builder-driver-failure-v1' and value['status'] == 'FAILED'
                and type(value['code']) is str and value['code'] in codes
                and type(value['steps']) is list and len(value['steps']) <= 5):
            return value['code']
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):pass
    return 'UNAVAILABLE'


def decode_wire(raw):
    try:
        if type(raw) is not bytes or not 0 < len(raw) <= 3145728:
            raise ValueError()
        value = json.loads(raw, object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if (type(value) is not dict or set(value) != {'schema', 'status', 'python', 'steps',
                'tools_verified', 'source_verified', 'smoke_verified', 'wheel_b64', 'verification'}
                or value['schema'] != 'builder-driver-v1' or value['status'] != 'BUILT'
                or value['python'] != '3.11.18'
                or any(value[k] is not True for k in ('tools_verified', 'source_verified', 'smoke_verified'))
                or type(value['steps']) is not list or len(value['steps']) != 5
                or [r.get('stage') if type(r) is dict else None for r in value['steps']]
                   != ['VENV', 'ENSUREPIP', 'TOOLS', 'BUILD', 'SMOKE']):
            raise ValueError()
        verification = value['verification']
        if type(verification) is not dict or set(verification) != {'bootstrap', 'tools', 'source'}:
            raise ValueError()
        for name, row in verification.items():
            keys = {'snapshot_sha256', 'files'} | (set() if name == 'source' else {'payload_files', 'installed_files'})
            if (type(row) is not dict or set(row) != keys
                    or any(type(row[k]) is not int or not 0 < row[k] <= 20000 for k in keys - {'snapshot_sha256'})
                    or type(row['snapshot_sha256']) is not str or len(row['snapshot_sha256']) != 64
                    or any(c not in '0123456789abcdef' for c in row['snapshot_sha256'])):
                raise ValueError()
        keys = {'stage', 'status', 'returncode', 'stdout_bytes', 'stderr_bytes', 'stdout_sha256', 'stderr_sha256'}
        for row in value['steps']:
            if (type(row) is not dict or set(row) != keys or row['stage'] not in ('VENV', 'ENSUREPIP', 'TOOLS', 'BUILD', 'SMOKE')
                    or row['status'] != 'EXITED' or type(row['returncode']) is not int or row['returncode'] != 0
                    or any(type(row[k]) is not int or not 0 <= row[k] <= 3145728 for k in ('stdout_bytes', 'stderr_bytes'))
                    or any(type(row[k]) is not str or len(row[k]) != 64 or any(c not in '0123456789abcdef' for c in row[k])
                           for k in ('stdout_sha256', 'stderr_sha256'))):
                raise ValueError()
        if type(value['wheel_b64']) is not str or len(value['wheel_b64']) > 1398104:
            raise ValueError()
        wheel = base64.b64decode(value.pop('wheel_b64'), validate=True)
        if not 0 < len(wheel) <= 1048576:
            raise ValueError()
        return value, wheel
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
        raise ValueError('INVALID_DRIVER_WIRE') from None
