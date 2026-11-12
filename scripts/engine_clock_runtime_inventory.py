"""Bounded verification of an explicitly supplied root and installed manifest.

No scan occurs at import. No CLI, native import, subprocess, image/API admission
or actual-driver claim is provided. A match covers the declared caller tree.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import signal
import stat
import threading
from time import perf_counter

BASE_ROOTS = ('/etc', '/lib', '/lib64', '/opt/python', '/opt/venv', '/usr')
RUNTIME_EXCLUSIONS = ('/etc/hostname', '/etc/hosts', '/etc/mtab', '/etc/resolv.conf')
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_INSTALLED_BYTES = 3 * 1024 ** 3
MAX_READ_BYTES = 4 * 1024 ** 3
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_NODES = 100000
MAX_DEPTH = 256
MAX_LINKS = 40
MAX_PATH_BYTES = 4096
MAX_SECONDS = 180
MAX_PREFIX = 64
MAX_PREFIX_BYTES = 256 * 1024
READ_CHUNK = 1024 * 1024


class _InventoryError(ValueError):
    """Controlled metadata message, safe for the result receipt."""


class _InventoryTimeout(TimeoutError):
    """Controlled watchdog message, safe for the result receipt."""


def _fields(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise _InventoryError('missing or unregistered inventory fields')


def _path(value):
    if (type(value) is not str or not value.startswith('/') or value.startswith('//')
            or '\0' in value or '..' in value.split('/')
            or PurePosixPath(value).as_posix() != value or value == '/'):
        raise _InventoryError('noncanonical absolute inventory path')
    try:
        encoded = value.encode('utf-8')
    except UnicodeError:
        raise _InventoryError('invalid UTF-8 inventory path') from None
    if len(encoded) > MAX_PATH_BYTES or len(value.split('/')) - 1 > MAX_DEPTH:
        raise _InventoryError('inventory path length or depth limit')
    return value


def _target(value):
    if type(value) is not str or not value or '\0' in value:
        raise _InventoryError('invalid symlink target')
    try:
        size = len(value.encode('utf-8'))
    except UnicodeError:
        raise _InventoryError('invalid UTF-8 symlink target') from None
    if size > MAX_PATH_BYTES:
        raise _InventoryError('symlink target length limit')


def _inside(path):
    return any(path == root or path.startswith(root + '/') for root in BASE_ROOTS)


def _excluded(path):
    return any(path == root or path.startswith(root + '/') for root in RUNTIME_EXCLUSIONS)


def _prefix_allowed(path):
    return path == '/' or _inside(path) or any(root.startswith(path + '/') for root in BASE_ROOTS)


def _canonical(value, check=lambda: None):
    chunks = []
    size = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    try:
        for chunk in encoder.iterencode(value):
            check()
            raw = chunk.encode('utf-8')
            size += len(raw)
            if size > MAX_JSON_BYTES:
                raise _InventoryError('inventory JSON byte limit')
            chunks.append(raw)
    except (TypeError, RecursionError, OverflowError):
        raise _InventoryError('invalid inventory JSON metadata') from None
    return b''.join(chunks)


def _parents(path):
    parts = path.split('/')[1:]
    return ['/' + '/'.join(parts[:i]) for i in range(1, len(parts))]


def _add(graph, path, node):
    if path not in graph and len(graph) >= MAX_NODES:
        raise _InventoryError('inventory node limit')
    if path in graph and graph[path].get('kind') != 'directory':
        raise _InventoryError('inventory entry below a file or symlink')
    graph[path] = node


def _resolve(path, graph, check=lambda: None):
    """Resolve logical components in order; never follow host symlink paths."""
    pending = path.split('/')[1:]
    resolved = []
    followed = 0
    states = set()
    while pending:
        check()
        component, pending = pending[0], pending[1:]
        if component in ('', '.'):
            continue
        if component == '..':
            if resolved:
                resolved.pop()
            continue
        resolved.append(component)
        current = '/' + '/'.join(resolved)
        if len(resolved) > MAX_DEPTH or not _prefix_allowed(current) or _excluded(current):
            raise _InventoryError('symlink scope or depth escape')
        node = graph.get(current, {})
        if node.get('kind') == 'symlink':
            state = (current, tuple(pending))
            followed += 1
            if state in states or followed > MAX_LINKS:
                raise _InventoryError('symlink cycle or expansion limit')
            states.add(state)
            target = node['target']
            resolved = [] if target.startswith('/') else resolved[:-1]
            pending = target.split('/') + pending
        elif node.get('kind') == 'file' and pending:
            raise _InventoryError('symlink target traverses a regular file')
    result = '/' + '/'.join(resolved)
    if not _inside(result) or _excluded(result):
        raise _InventoryError('symlink target outside approved roots')
    return result


def _validate(document, check):
    _fields(document, {'schema', 'roots', 'runtime_exclusions', 'entries'})
    if document['schema'] != 'installed-files-v1':
        raise _InventoryError('unsupported installed inventory schema')
    roots = document['roots']
    if type(roots) is not list or not roots or len(roots) > MAX_NODES:
        raise _InventoryError('invalid inventory roots')
    for root in roots:
        check()
        _path(root)
        if not _inside(root) or _excluded(root):
            raise _InventoryError('unsupported inventory root')
    if roots != sorted(set(roots)) or not set(BASE_ROOTS).issubset(roots):
        raise _InventoryError('required sorted unique roots missing')
    exclusions = document['runtime_exclusions']
    if type(exclusions) is not list or exclusions != list(RUNTIME_EXCLUSIONS):
        raise _InventoryError('unsupported runtime exclusions')
    entries = document['entries']
    if type(entries) is not list or len(entries) > MAX_NODES:
        raise _InventoryError('inventory entry limit')
    graph = {'/': {'kind': 'directory'}, '/opt': {'kind': 'directory'}}
    for root in roots:
        for parent in _parents(root):
            if parent not in graph:
                _add(graph, parent, {'kind': 'directory'})
        _add(graph, root, {'kind': 'directory'})
    total = 0
    previous = None
    for entry in entries:
        check()
        if type(entry) is not dict or entry.get('kind') not in ('file', 'symlink'):
            raise _InventoryError('unsupported inventory entry kind')
        kind = entry['kind']
        _fields(entry, {'path', 'kind', 'mode', 'nbytes', 'sha256'} if kind == 'file'
                else {'path', 'kind', 'target'})
        path = _path(entry['path'])
        if not _inside(path) or _excluded(path) or (previous is not None and path <= previous):
            raise _InventoryError('inventory path scope/order/duplicate error')
        previous = path
        for parent in _parents(path):
            if parent in graph and graph[parent]['kind'] != 'directory':
                raise _InventoryError('inventory payload through alias or file')
            if parent not in graph:
                _add(graph, parent, {'kind': 'directory'})
        if kind == 'file':
            if path in roots or type(entry['mode']) is not int or not 0 <= entry['mode'] <= 0o7777:
                raise _InventoryError('invalid regular file mode/root')
            size = entry['nbytes']
            if type(size) is not int or not 0 <= size <= MAX_FILE_BYTES:
                raise _InventoryError('regular file byte limit')
            digest = entry['sha256']
            if type(digest) is not str or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                raise _InventoryError('invalid file SHA256')
            total += size
            if total > MAX_INSTALLED_BYTES:
                raise _InventoryError('declared installed byte limit')
        else:
            _target(entry['target'])
        _add(graph, path, {'kind': kind, **({'target': entry['target']} if kind == 'symlink' else {})})
    for path, node in graph.items():
        if node['kind'] == 'symlink':
            _resolve(path, graph, check)
    raw = _canonical(document, check)
    return json.loads(raw), raw


def validate_inventory(document: dict) -> dict:
    """Validate and copy manifest metadata only; read no filesystem contents."""
    return _validate(document, lambda: None)[0]


def _signature(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


@contextmanager
def _opened(path, flags, parent=None):
    fd = os.open(path, flags, dir_fd=parent)
    try:
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _absolute_deadline(deadline):
    if threading.current_thread() is not threading.main_thread():
        raise _InventoryError('main-thread POSIX deadline required')
    if not all(hasattr(signal, name) for name in ('SIGALRM', 'ITIMER_REAL', 'setitimer', 'getitimer')):
        raise _InventoryError('absolute filesystem deadline unsupported')
    if signal.getitimer(signal.ITIMER_REAL) != (0., 0.):
        raise _InventoryError('concurrent process alarm prohibited')
    remaining = deadline - perf_counter()
    if remaining <= 0:
        raise _InventoryTimeout('inventory deadline exhausted')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(signum, frame):
        raise _InventoryTimeout('absolute inventory deadline exhausted')
    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, remaining)
        try:
            yield
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0.)
    finally:
        signal.signal(signal.SIGALRM, previous)


class _Collector:
    def __init__(self, deadline, result):
        self.expected = {}
        self.deadline = deadline
        self.result = result
        self.graph = {}
        self.observed = []
        self.read_payload = True
        self.device = None

    def check(self):
        if perf_counter() >= self.deadline:
            raise _InventoryTimeout('inventory deadline exhausted')

    def stage(self, name, path=None):
        self.check()
        self.result['failure_stage'] = name
        self.result['failure_path'] = path

    def node(self, path, value):
        self.check()
        _path(path) if path != '/' else None
        if path not in self.graph:
            if len(self.graph) >= MAX_NODES:
                raise _InventoryError('walk node limit')
            self.result['visited_nodes'] += 1
        elif self.graph[path] != value:
            raise _InventoryError('directory metadata changed during scan')
        self.graph[path] = value

    def matched(self, value):
        if value != self.expected.get(value['path']):
            raise _InventoryError('payload descriptor/content mismatch')
        if not self.read_payload:
            return
        self.observed.append(value)
        self.result['matched_entries'] += 1
        prefix = self.result['matched_prefix']
        if len(prefix) < MAX_PREFIX:
            candidate = prefix + [value]
            if len(_canonical(candidate, self.check)) <= MAX_PREFIX_BYTES:
                prefix.append(value)

    def regular(self, parent, name, path, before):
        self.stage('verify_file', path)
        expected = self.expected.get(path)
        if (expected is None or expected['kind'] != 'file' or before.st_size != expected['nbytes']
                or stat.S_IMODE(before.st_mode) != expected['mode']):
            raise _InventoryError('unexpected file or size/mode mismatch')
        if before.st_dev != self.device:
            raise _InventoryError('cross-filesystem file rejected')
        self.node(path, {'kind': 'file', 'signature': _signature(before)})
        if not self.read_payload:
            return
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        with _opened(name, flags, parent) as fd:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or _signature(opened) != _signature(before):
                raise _InventoryError('file identity changed before reading')
            digest = hashlib.sha256()
            remaining = opened.st_size
            while remaining:
                self.stage('hash_file', path)
                count = min(READ_CHUNK, remaining, MAX_READ_BYTES - self.result['bytes_read'])
                if count <= 0:
                    raise _InventoryError('inventory read byte limit')
                chunk = os.read(fd, count)
                self.result['bytes_read'] += len(chunk)
                if not chunk:
                    raise _InventoryError('unexpected file EOF')
                digest.update(chunk)
                remaining -= len(chunk)
            if (_signature(os.fstat(fd)) != _signature(opened)
                    or _signature(os.stat(name, dir_fd=parent, follow_symlinks=False)) != _signature(opened)):
                raise _InventoryError('file metadata changed while reading')
        value = {'path': path, 'kind': 'file', 'mode': stat.S_IMODE(opened.st_mode),
                 'nbytes': opened.st_size, 'sha256': digest.hexdigest()}
        self.matched(value)

    def entry(self, parent, name, path, depth):
        self.stage('walk', path)
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if path in RUNTIME_EXCLUSIONS:
            target = None
            if stat.S_ISLNK(before.st_mode) and path == '/etc/mtab':
                target = os.readlink(name, dir_fd=parent)
                if target not in ('/proc/mounts', '/proc/self/mounts'):
                    raise _InventoryError('invalid excluded mtab target')
            elif not stat.S_ISREG(before.st_mode):
                raise _InventoryError('excluded metadata must be regular or approved mtab link')
            if _signature(before) != _signature(os.stat(name, dir_fd=parent, follow_symlinks=False)):
                raise _InventoryError('runtime metadata kind/link changed')
            self.node(path, {'kind': 'runtime_metadata', 'target': target})
        elif stat.S_ISDIR(before.st_mode):
            if before.st_dev != self.device:
                raise _InventoryError('cross-filesystem directory rejected')
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            with _opened(name, flags, parent) as fd:
                if _signature(os.fstat(fd)) != _signature(before):
                    raise _InventoryError('directory changed before opening')
                self.walk(fd, path, depth)
        elif stat.S_ISLNK(before.st_mode):
            target = os.readlink(name, dir_fd=parent)
            _target(target)
            if before.st_dev != self.device or _signature(before) != _signature(os.stat(name, dir_fd=parent, follow_symlinks=False)):
                raise _InventoryError('symlink changed or crossed filesystem')
            self.node(path, {'kind': 'symlink', 'target': target, 'signature': _signature(before)})
            self.matched({'path': path, 'kind': 'symlink', 'target': target})
        elif stat.S_ISREG(before.st_mode):
            self.regular(parent, name, path, before)
        else:
            raise _InventoryError('special filesystem entry rejected')

    def walk(self, fd, path, depth):
        self.stage('walk', path)
        if depth > MAX_DEPTH:
            raise _InventoryError('walk depth limit')
        before = os.fstat(fd)
        self.node(path, {'kind': 'directory', 'signature': _signature(before)})
        names = []
        with os.scandir(fd) as entries:
            for entry in entries:
                self.check()
                if len(names) + len(self.graph) >= MAX_NODES:
                    raise _InventoryError('directory enumeration node limit')
                names.append(entry.name)
        for name in sorted(names):
            self.entry(fd, name, path + '/' + name, depth + 1)
        if _signature(os.fstat(fd)) != _signature(before):
            raise _InventoryError('directory changed during collection')

    def scan(self, rootfd, expected, read_payload):
        self.graph = {}
        self.read_payload = read_payload
        rootstat = os.fstat(rootfd)
        self.device = rootstat.st_dev
        self.node('/', {'kind': 'directory', 'signature': _signature(rootstat)})
        for root in BASE_ROOTS:
            self.stage('roots', root)
            if root.startswith('/opt/'):
                parent_stat = os.stat('opt', dir_fd=rootfd, follow_symlinks=False)
                if not stat.S_ISDIR(parent_stat.st_mode) or parent_stat.st_dev != self.device:
                    raise _InventoryError('root common ancestor must be a plain directory')
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
                with _opened('opt', flags, rootfd) as parent:
                    if _signature(os.fstat(parent)) != _signature(parent_stat):
                        raise _InventoryError('root common ancestor changed')
                    self.node('/opt', {'kind': 'directory', 'signature': _signature(parent_stat)})
                    self.entry(parent, root.rsplit('/', 1)[1], root, 2)
                    if _signature(os.fstat(parent)) != _signature(parent_stat):
                        raise _InventoryError('root common ancestor changed during traversal')
            else:
                self.entry(rootfd, root[1:], root, 1)
        self.stage('resolve_aliases')
        for path, node in self.graph.items():
            if node['kind'] == 'symlink':
                _resolve(path, self.graph, self.check)
        for root in expected['roots']:
            target = _resolve(root, self.graph, self.check)
            if self.graph.get(target, {}).get('kind') != 'directory':
                raise _InventoryError('declared root does not resolve to a directory')
        if _signature(os.fstat(rootfd)) != _signature(rootstat):
            raise _InventoryError('caller root changed during scan')
        return self.graph


def collect_inventory(root: Path, expected: dict, *, deadline: float) -> dict:
    """Read only the caller root; return a bounded non-admitting receipt."""
    started = perf_counter()
    result = {'schema': 'engine-clock-file-inventory-result-v1', 'status': 'FAILED_OR_INCOMPLETE',
              'complete': False, 'native_admission': False, 'inventory': None,
              'canonical_manifest_sha256': None, 'matched_entries': 0, 'matched_prefix': [],
              'bytes_read': 0, 'visited_nodes': 0, 'elapsed_s': 0.,
              'failure_stage': 'arguments', 'failure_path': None, 'error': None}
    effective_deadline = None
    try:
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise _InventoryError('finite absolute inventory deadline required')
        deadline = min(deadline, started + MAX_SECONDS)
        effective_deadline = deadline
        collector = _Collector(deadline, result)
        collector.check()
        with _absolute_deadline(deadline):
            result['failure_stage'] = 'manifest'
            expected, _ = _validate(expected, collector.check)
            collector.expected = {entry['path']: entry for entry in expected['entries']}
            collector.stage('root')
            required = ('O_DIRECTORY', 'O_NOFOLLOW', 'O_CLOEXEC', 'O_NONBLOCK')
            if os.name != 'posix' or any(not hasattr(os, name) for name in required):
                raise _InventoryError('descriptor-relative scanning unsupported')
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            with _opened(Path(root), flags) as rootfd:
                first = collector.scan(rootfd, expected, True)
                collector.stage('closed_inventory')
                if len(collector.observed) != len(expected['entries']):
                    raise _InventoryError('expected inventory payload missing')
                # Second pass reads metadata only; it does not hash payload twice.
                collector.stage('final_metadata')
                second = collector.scan(rootfd, expected, False)
                if first != second:
                    raise _InventoryError('filesystem metadata changed between verification passes')
            collector.stage('complete_inventory')
            actual = {'schema': 'installed-files-v1', 'roots': expected['roots'],
                      'runtime_exclusions': expected['runtime_exclusions'],
                      'entries': sorted(collector.observed, key=lambda entry: entry['path'])}
            raw = _canonical(actual, collector.check)
            if actual != expected:
                raise _InventoryError('closed inventory mismatch')
            result.update(status='INSTALLED_FILES_MATCH', complete=True, inventory=actual,
                          canonical_manifest_sha256=hashlib.sha256(raw).hexdigest(),
                          failure_stage=None, failure_path=None)
    except Exception as exc:
        if isinstance(exc, (_InventoryError, _InventoryTimeout)):
            detail = str(exc)[:512]
        elif isinstance(exc, OSError):
            detail = 'filesystem operation failed (errno=' + str(exc.errno) + ')'
        else:
            detail = 'inventory operation failed'
        result.update(status='FAILED_OR_INCOMPLETE', complete=False, inventory=None,
                      canonical_manifest_sha256=None,
                      failure_stage=result['failure_stage'] or 'deadline_cleanup',
                      error=type(exc).__name__ + ': ' + detail)
    finished = perf_counter()
    if result['complete'] and finished >= effective_deadline:
        result.update(status='FAILED_OR_INCOMPLETE', complete=False, inventory=None,
                      canonical_manifest_sha256=None, failure_stage='deadline_cleanup',
                      error='TimeoutError: completion exceeded inventory deadline')
    result['elapsed_s'] = finished - started
    return result
