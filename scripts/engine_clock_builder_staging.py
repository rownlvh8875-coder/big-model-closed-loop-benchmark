"""Bounded caller-owned builder trees. No CLI, network, subprocess or admission."""
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import posixpath
import re
import signal
import stat
import threading
from time import perf_counter

MAX_NODES = 20000
MAX_BYTES = 512 * 1024 * 1024
MAX_FILE = 128 * 1024 * 1024
MAX_JSON = 16 * 1024 * 1024


class _Error(ValueError):
    pass


def _need(ok, code):
    if not ok:
        raise _Error(code)


def _path(value, root=False):
    _need(type(value) is str and value and '\0' not in value and '\\' not in value,
          'BAD_PATH')
    _need(len(value.encode()) <= 4096 and not value.startswith('/'), 'BAD_PATH')
    if root and value == '.':
        return value
    parts = value.split('/')
    _need(len(parts) <= 64 and all(p not in ('', '.', '..') for p in parts), 'BAD_PATH')
    return value


def _target(path, value):
    _need(type(value) is str and value and '\0' not in value and '\\' not in value
          and len(value.encode()) <= 4096, 'BAD_LINK')
    stack = [] if value.startswith('/') else path.split('/')[:-1]
    for part in value.split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            _need(stack, 'LINK_ESCAPE')
            stack.pop()
        else:
            stack.append(part)
    return _path('/'.join(stack) or '.', root=True)


def _body_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                     allow_nan=False).encode()
    _need(len(raw) <= MAX_JSON, 'PLAN_LIMIT')
    return hashlib.sha256(raw).hexdigest()


def compile_plan(sources: list[dict]) -> dict:
    """Validate caller metadata and canonicalize parent aliases, never authenticate it."""
    _need(type(sources) is list and 0 < len(sources) <= 128, 'BAD_SOURCES')
    raw, normalized, ids, count, declared = {}, [], set(), 0, 0

    def merge(path, node):
        if path in raw:
            _need(raw[path] == node, 'PATH_CONFLICT')
        else:
            raw[path] = node

    for source in sources:
        _need(type(source) is dict and set(source) == {'id', 'prefix', 'archive_sha256', 'entries'},
              'BAD_SOURCE')
        sid = source['id']
        _need(type(sid) is str and re.fullmatch(r'[a-z0-9-]{1,64}', sid) and sid not in ids,
              'BAD_SOURCE_ID')
        ids.add(sid)
        prefix = _path(source['prefix'], root=True)
        digest = source['archive_sha256']
        _need(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 'BAD_DIGEST')
        rows = source['entries']
        _need(type(rows) is list and len(rows) <= MAX_NODES, 'MEMBER_LIMIT')
        seen, clean = set(), []
        for row in rows:
            count += 1
            _need(count <= MAX_NODES and type(row) is dict, 'MEMBER_LIMIT')
            kind = row.get('kind')
            extra = {'sha256'} if kind == 'file' else {'target'} if kind == 'symlink' else set()
            _need(kind in ('file', 'directory', 'symlink') and
                  set(row) == {'path', 'kind', 'mode', 'nbytes'} | extra, 'BAD_MEMBER')
            path = _path(row['path'], root=kind == 'directory')
            _need(path not in seen, 'DUPLICATE_MEMBER')
            seen.add(path)
            _need(type(row['mode']) is int and 0 <= row['mode'] <= 0o7777 and
                  type(row['nbytes']) is int and 0 <= row['nbytes'] <= MAX_FILE,
                  'BAD_MEMBER_SIZE_OR_MODE')
            dest = path if prefix == '.' else prefix if path == '.' else prefix + '/' + path
            _path(dest, root=True)
            node = {'kind': kind, 'mode': 0o555 if kind == 'directory' else 0o777,
                    'nbytes': 0}
            if kind == 'file':
                _need(type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']),
                      'BAD_DIGEST')
                declared += row['nbytes']
                _need(declared <= MAX_BYTES, 'BYTE_LIMIT')
                node.update(mode=0o555 if row['mode'] & 0o111 else 0o444,
                            nbytes=row['nbytes'], sha256=row['sha256'])
            else:
                _need(row['nbytes'] == 0, 'BAD_MEMBER_SIZE')
                if kind == 'symlink':
                    node['target'] = row['target']
                    _target(dest, row['target'])
            merge(dest, node)
            clean.append(dict(row))
        normalized.append({'id': sid, 'prefix': prefix, 'archive_sha256': digest,
                           'entries': sorted(clean, key=lambda r: r['path'])})
    directory = {'kind': 'directory', 'mode': 0o555, 'nbytes': 0}
    raw.setdefault('.', dict(directory))
    for path in list(raw):
        parts = path.split('/')
        for end in range(1, len(parts)):
            raw.setdefault('/'.join(parts[:end]), dict(directory))

    def resolve(path, final):
        visited = set()
        for _ in range(41):
            _need(path not in visited, 'LINK_LOOP')
            visited.add(path)
            parts = [] if path == '.' else path.split('/')
            changed = False
            limit = len(parts) if final else len(parts) - 1
            for end in range(1, limit + 1):
                prefix = '/'.join(parts[:end])
                node = raw.get(prefix)
                if node and node['kind'] == 'symlink':
                    target = _target(prefix, node['target'])
                    rest = '/'.join(parts[end:])
                    path = rest if target == '.' and rest else target + '/' + rest if rest else target
                    _path(path, root=True)
                    changed = True
                    break
                _need(not node or node['kind'] != 'file' or end == len(parts), 'FILE_ANCESTOR')
            if not changed:
                return path
        raise _Error('LINK_LIMIT')

    output = {}
    for path, node in raw.items():
        dest = resolve(path, False)
        if dest in output:
            _need(output[dest] == node, 'PATH_CONFLICT')
        else:
            output[dest] = dict(node)
    for path, node in output.items():
        if node['kind'] == 'symlink':
            target = resolve(_target(path, node['target']), True)
            _need(target in output, 'DANGLING_LINK')
        if path != '.':
            parent = posixpath.dirname(path) or '.'
            _need(parent in output and output[parent]['kind'] == 'directory', 'FILE_ANCESTOR')
    _need(len(output) <= MAX_NODES, 'NODE_LIMIT')
    destinations = {}
    for source in normalized:
        for row in source['entries']:
            if row['kind'] == 'file':
                path = row['path'] if source['prefix'] == '.' else source['prefix'] + '/' + row['path']
                destinations[(source['id'], row['path'])] = resolve(path, False)
    origins = {}
    for (sid, original), dest in sorted(destinations.items()):
        origins.setdefault(dest, []).append({'source': sid, 'path': original})
    nodes = []
    for path in sorted(output):
        node = {'path': path, **output[path]}
        if node['kind'] == 'file':
            node['origins'] = origins[path]
        nodes.append(node)
    body = {'schema': 'builder-staging-plan-v1', 'sources': sorted(normalized, key=lambda s: s['id']),
            'entries': nodes, 'staged_bytes': sum(n['nbytes'] for n in nodes if n['kind'] == 'file')}
    _need(body['staged_bytes'] <= MAX_BYTES, 'BYTE_LIMIT')
    return {**body, 'plan_sha256': _body_hash(body)}


def _checked(plan):
    _need(type(plan) is dict and set(plan) == {'schema', 'sources', 'entries', 'staged_bytes', 'plan_sha256'},
          'BAD_PLAN')
    rebuilt = compile_plan(plan['sources'])
    _need(plan == rebuilt, 'PLAN_MISMATCH')
    return rebuilt


@contextlib.contextmanager
def _guard(deadline):
    _need(type(deadline) in (int, float) and math.isfinite(deadline), 'BAD_DEADLINE')
    _need(threading.current_thread() is threading.main_thread() and hasattr(signal, 'setitimer'),
          'DEADLINE_UNAVAILABLE')
    _need(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), 'TIMER_BUSY')
    _need(deadline > perf_counter(), 'DEADLINE')
    old = signal.getsignal(signal.SIGALRM)
    def alarm(*_):
        raise _Error('DEADLINE')
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, deadline - perf_counter())
    def check():
        _need(perf_counter() < deadline, 'DEADLINE')
    try:
        yield check
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK


def _absolute_dir(path):
    path = os.fspath(path)
    _need(type(path) is str and path.startswith('/') and '\0' not in path, 'BAD_ROOT')
    parts = path.split('/')[1:]
    _need(all(p not in ('', '.', '..') for p in parts), 'BAD_ROOT')
    fd = os.open('/', _FLAGS)
    try:
        for part in parts:
            nxt = os.open(part, _FLAGS, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def _directory(fd, path):
    result = os.dup(fd)
    try:
        if path != '.':
            for part in path.split('/'):
                nxt = os.open(part, _FLAGS, dir_fd=result)
                os.close(result)
                result = nxt
        return result
    except BaseException:
        os.close(result)
        raise


def _signature(s):
    return s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_nlink, s.st_mtime_ns, s.st_ctime_ns


def _scan(rootfd, plan, check):
    expected = {n['path']: n for n in plan['entries']}
    rootstat = os.fstat(rootfd)
    seen = set()
    total = 0
    def inspect(fd, path, before):
        nonlocal total
        check()
        _need(path in expected and path not in seen and len(seen) < MAX_NODES, 'TREE_SET_MISMATCH')
        seen.add(path)
        node = expected[path]
        _need(before.st_dev == rootstat.st_dev and before.st_uid == rootstat.st_uid
              and before.st_gid == rootstat.st_gid, 'TREE_OWNER_OR_DEVICE')
        kind = 'directory' if stat.S_ISDIR(before.st_mode) else 'file' if stat.S_ISREG(before.st_mode) else 'symlink' if stat.S_ISLNK(before.st_mode) else 'special'
        _need(kind == node['kind'] and stat.S_IMODE(before.st_mode) == node['mode'], 'TREE_KIND_OR_MODE')
        if kind == 'directory':
            _need(_signature(before) == _signature(os.fstat(fd)), 'TREE_CHANGED')
            with os.scandir(fd) as entries:
                for entry in entries:
                    check()
                    child = entry.name if path == '.' else path + '/' + entry.name
                    s = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
                    if stat.S_ISDIR(s.st_mode):
                        childfd = os.open(entry.name, _FLAGS, dir_fd=fd)
                        try: inspect(childfd, child, s)
                        finally: os.close(childfd)
                    elif stat.S_ISREG(s.st_mode):
                        _need(child in expected, 'TREE_SET_MISMATCH')
                        filefd = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                        try: inspect(filefd, child, s)
                        finally: os.close(filefd)
                    elif stat.S_ISLNK(s.st_mode):
                        _need(child in expected and child not in seen, 'TREE_SET_MISMATCH')
                        seen.add(child)
                        wanted = expected[child]
                        _need(s.st_dev == rootstat.st_dev and s.st_uid == rootstat.st_uid
                              and s.st_gid == rootstat.st_gid and s.st_nlink == 1
                              and wanted['kind'] == 'symlink' and stat.S_IMODE(s.st_mode) == wanted['mode']
                              and os.readlink(entry.name, dir_fd=fd) == wanted['target'], 'TREE_LINK_MISMATCH')
                        _need(_signature(s) == _signature(os.stat(entry.name, dir_fd=fd, follow_symlinks=False)), 'TREE_CHANGED')
                    else:
                        raise _Error('TREE_SPECIAL')
            _need(_signature(before) == _signature(os.fstat(fd)), 'TREE_CHANGED')
        elif kind == 'file':
            _need(_signature(before) == _signature(os.fstat(fd)) and before.st_nlink == 1
                  and before.st_size == node['nbytes'], 'TREE_CHANGED')
            h = hashlib.sha256()
            while True:
                check()
                block = os.read(fd, 1048576)
                if not block: break
                total += len(block)
                _need(total <= MAX_BYTES, 'BYTE_LIMIT')
                h.update(block)
            _need(h.hexdigest() == node['sha256'] and _signature(before) == _signature(os.fstat(fd)),
                  'TREE_CONTENT_MISMATCH')
    inspect(rootfd, '.', rootstat)
    _need(seen == set(expected), 'TREE_SET_MISMATCH')
    return total


def _receipt(plan=None):
    digest = plan.get('plan_sha256') if type(plan) is dict else None
    if type(digest) is not str or re.fullmatch('[0-9a-f]{64}', digest) is None:
        digest = None
    return {'schema': 'builder-staging-receipt-v1', 'status': 'FAILED_OR_INCOMPLETE',
            'plan_sha256': digest,
            'errors': [], 'source_origin_authenticated': False, 'source_execution_authorized': False,
            'image_preparation_ready': False, 'native_admission': False}


def stage_tree(root: Path, plan: dict, members, *, deadline: float) -> dict:
    result = _receipt(plan)
    rootfd = parentfd = None
    iterator = None
    try:
        with _guard(deadline) as check:
            plan = _checked(plan)
            root = Path(root)
            parentfd = _absolute_dir(root.parent)
            _need(root.name not in ('', '.', '..'), 'BAD_ROOT')
            os.mkdir(root.name, 0o700, dir_fd=parentfd)
            rootfd = os.open(root.name, _FLAGS, dir_fd=parentfd)
            root_signature = os.fstat(rootfd).st_dev, os.fstat(rootfd).st_ino
            directories = [n for n in plan['entries'] if n['kind'] == 'directory' and n['path'] != '.']
            for node in sorted(directories, key=lambda n: (n['path'].count('/'), n['path'])):
                check()
                parent = posixpath.dirname(node['path']) or '.'
                fd = _directory(rootfd, parent)
                try: os.mkdir(posixpath.basename(node['path']), 0o700, dir_fd=fd)
                finally: os.close(fd)
            expected = {(s['id'], e['path']): e for s in plan['sources'] for e in s['entries']}
            targets = {(o['source'], o['path']): n for n in plan['entries'] if n['kind'] == 'file' for o in n['origins']}
            seen, written = set(), set()
            iterator = iter(members)
            for sid, row, stream in iterator:
                check()
                _need(type(row) is dict and type(sid) is str and type(row.get('path')) is str,
                      'BAD_MEMBER')
                key = sid, row['path']
                _need(key in expected and key not in seen and row == expected[key], 'MEMBER_SET_OR_HEADER')
                seen.add(key)
                if row['kind'] != 'file':
                    _need(stream is None, 'UNEXPECTED_STREAM')
                    continue
                _need(stream is not None and hasattr(stream, 'read'), 'MISSING_STREAM')
                node = targets[key]
                filefd = None
                if node['path'] not in written:
                    parent = _directory(rootfd, posixpath.dirname(node['path']) or '.')
                    try: filefd = os.open(posixpath.basename(node['path']), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                    finally: os.close(parent)
                h, count = hashlib.sha256(), 0
                try:
                    while True:
                        check()
                        block = stream.read(min(1048576, row['nbytes'] - count + 1))
                        _need(type(block) is bytes, 'BAD_STREAM')
                        if not block: break
                        count += len(block)
                        _need(count <= row['nbytes'], 'MEMBER_SIZE')
                        h.update(block)
                        if filefd is not None:
                            view = memoryview(block)
                            while view:
                                check()
                                size = os.write(filefd, view)
                                _need(size > 0, 'WRITE_FAILED')
                                view = view[size:]
                    _need(count == row['nbytes'] and h.hexdigest() == row['sha256'], 'MEMBER_CONTENT')
                    if filefd is not None: os.fchmod(filefd, node['mode'])
                finally:
                    if filefd is not None: os.close(filefd)
                written.add(node['path'])
            _need(seen == set(expected), 'MEMBER_SET_OR_HEADER')
            for node in plan['entries']:
                if node['kind'] == 'symlink':
                    check()
                    parent = _directory(rootfd, posixpath.dirname(node['path']) or '.')
                    try: os.symlink(node['target'], posixpath.basename(node['path']), dir_fd=parent)
                    finally: os.close(parent)
            for node in sorted(directories, key=lambda n: n['path'].count('/'), reverse=True):
                fd = _directory(rootfd, node['path'])
                try: os.fchmod(fd, node['mode'])
                finally: os.close(fd)
            os.fchmod(rootfd, 0o555)
            result['bytes_verified'] = _scan(rootfd, plan, check)
            named = os.stat(root.name, dir_fd=parentfd, follow_symlinks=False)
            _need((named.st_dev, named.st_ino) == root_signature, 'ROOT_CHANGED')
            result.update(status='STAGED_CONTENT_MATCH', entries_verified=len(plan['entries']))
    except _Error as exc:
        result['errors'] = [{'code': str(exc)}]
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        result['errors'] = [{'code': 'FILESYSTEM_OR_INPUT_ERROR'}]
    finally:
        if iterator is not None and hasattr(iterator, 'close'):
            try: iterator.close()
            except Exception:
                result['status'] = 'FAILED_OR_INCOMPLETE'
                result['errors'].append({'code': 'INPUT_CLEANUP_ERROR'})
        if rootfd is not None: os.close(rootfd)
        if parentfd is not None: os.close(parentfd)
    return result


def verify_tree(root: Path, plan: dict, *, deadline: float) -> dict:
    result = _receipt(plan)
    fd = None
    try:
        with _guard(deadline) as check:
            plan = _checked(plan)
            fd = _absolute_dir(root)
            before = os.fstat(fd)
            result['bytes_verified'] = _scan(fd, plan, check)
            named = os.stat(root, follow_symlinks=False)
            _need((named.st_dev, named.st_ino) == (before.st_dev, before.st_ino), 'ROOT_CHANGED')
            result.update(status='STAGED_CONTENT_MATCH', entries_verified=len(plan['entries']))
    except _Error as exc:
        result['errors'] = [{'code': str(exc)}]
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        result['errors'] = [{'code': 'FILESYSTEM_OR_INPUT_ERROR'}]
    finally:
        if fd is not None: os.close(fd)
    return result


def verify_open_tree(rootfd: int, plan: dict, *, deadline: float) -> dict:
    """Check the exact already-open directory FD passed to the namespace mount."""
    result = _receipt(plan)
    fd = None
    try:
        with _guard(deadline) as check:
            _need(type(rootfd) is int and rootfd >= 0, 'BAD_ROOT_FD')
            plan = _checked(plan)
            fd = os.dup(rootfd)
            result['bytes_verified'] = _scan(fd, plan, check)
            result.update(status='STAGED_CONTENT_MATCH', entries_verified=len(plan['entries']))
    except _Error as exc:
        result['errors'] = [{'code': str(exc)}]
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        result['errors'] = [{'code': 'FILESYSTEM_OR_INPUT_ERROR'}]
    finally:
        if fd is not None:os.close(fd)
    return result
