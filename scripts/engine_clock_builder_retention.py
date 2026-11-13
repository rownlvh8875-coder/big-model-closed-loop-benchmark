"""Bounded nofollow archive of available remote workspaces; no target execution."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from time import perf_counter
import tarfile

if __name__ == '__main__':sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_builder_staging as staging

MAX_BYTES = 800 * 1024 * 1024
MAX_ARCHIVE = 900 * 1024 * 1024
MAX_TAR = 900 * 1024 * 1024


def _need(ok, code):
    if not ok:raise ValueError(code)


def _signature(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_nlink, s.st_uid, s.st_gid, s.st_mtime_ns, s.st_ctime_ns)


class _Writer:
    def __init__(self, stream, limit, check):
        self.stream, self.limit, self.check, self.nbytes = stream, limit, check, 0
        self.digest = hashlib.sha256()
    def write(self, data):
        self.check();_need(self.nbytes + len(data) <= self.limit, 'ARCHIVE_LIMIT')
        size = self.stream.write(data)
        _need(size == len(data), 'ARCHIVE_WRITE')
        self.nbytes += size
        self.digest.update(data)
        return size
    def flush(self):return self.stream.flush()


class _Reader:
    def __init__(self, fd, check):self.fd, self.check, self.nbytes, self.digest = fd, check, 0, hashlib.sha256()
    def read(self, size):
        data = bytearray()
        while len(data) < size:
            self.check();block = os.read(self.fd, min(1048576, size - len(data)))
            if not block:break
            data.extend(block)
        self.nbytes += len(data);self.digest.update(data)
        return bytes(data)


def _write_json_exclusive(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    _need(len(raw) <= 16777216, 'INVENTORY_LIMIT')
    with path.open('xb') as stream:stream.write(raw)


def preserve_workspaces(roots, out, *, deadline, max_bytes=MAX_BYTES, max_archive=MAX_ARCHIVE,
                        max_nodes=40000, max_file=128 * 1024 * 1024):
    result = {'schema': 'builder-workspace-retention-v1', 'status': 'PRESERVATION_INCOMPLETE',
              'errors': [], 'missing_roots': [], 'native_admission': False, 'image_preparation_ready': False}
    entries, total, compressed = [], 0, None
    out = Path(out)
    partial, destination = out / 'retained-workspaces.tar.gz.partial', out / 'retained-workspaces.tar.gz'
    try:
        _need(type(roots) is dict and 0 < len(roots) <= 8
              and all(type(k) is str and re.fullmatch('[a-z][a-z0-9-]{0,63}', k) for k in roots), 'ROOTS_INVALID')
        _need(all(type(v) is int and 0 < v <= cap for v, cap in ((max_bytes, MAX_BYTES),
              (max_archive, MAX_ARCHIVE), (max_nodes, 40000), (max_file, 128 * 1024 * 1024))), 'BUDGET_INVALID')
        _need(not destination.exists(), 'OUTPUT_EXISTS')
        with staging._guard(deadline) as check:
            with partial.open('xb') as output:
                compressed = _Writer(output, max_archive, check)
                with gzip.GzipFile(fileobj=compressed, mode='wb', filename='', mtime=0, compresslevel=1) as gz:
                    decoded = _Writer(gz, MAX_TAR, check)
                    with tarfile.open(fileobj=decoded, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                        def add(fd, name, before, device):
                            nonlocal total
                            check()
                            _need(len(entries) < max_nodes and len(name.encode()) <= 4096 and len(name.split('/')) <= 64,
                                  'NODE_OR_PATH_LIMIT')
                            _need(before.st_dev == device, 'UNREGISTERED_MOUNT')
                            info = tarfile.TarInfo(name)
                            info.mode, info.uid, info.gid, info.mtime = stat.S_IMODE(before.st_mode), before.st_uid, before.st_gid, int(before.st_mtime)
                            row = {'path': name, 'mode': info.mode, 'uid': info.uid, 'gid': info.gid, 'nbytes': 0}
                            if stat.S_ISDIR(before.st_mode):
                                row['kind'] = 'directory';entries.append(row)
                                _need(_signature(before) == _signature(os.fstat(fd)), 'WORKSPACE_CHANGED')
                                info.type = tarfile.DIRTYPE;archive.addfile(info)
                                with os.scandir(fd) as children:
                                    names = sorted(e.name for e in children)
                                for child in names:
                                    check();s = os.stat(child, dir_fd=fd, follow_symlinks=False)
                                    if stat.S_ISLNK(s.st_mode):
                                        _need(len(entries) < max_nodes and len((name + '/' + child).encode()) <= 4096, 'NODE_OR_PATH_LIMIT')
                                        link = os.readlink(child, dir_fd=fd)
                                        _need(len(link.encode()) <= 4096 and s.st_dev == device, 'LINK_LIMIT')
                                        member = tarfile.TarInfo(name + '/' + child);member.type = tarfile.SYMTYPE;member.linkname = link
                                        member.mode, member.uid, member.gid, member.mtime = stat.S_IMODE(s.st_mode), s.st_uid, s.st_gid, int(s.st_mtime)
                                        archive.addfile(member)
                                        entries.append({'path': member.name, 'kind': 'symlink', 'mode': member.mode,
                                                        'uid': member.uid, 'gid': member.gid, 'nbytes': 0, 'target': link})
                                        _need(_signature(s) == _signature(os.stat(child, dir_fd=fd, follow_symlinks=False)), 'WORKSPACE_CHANGED')
                                    else:
                                        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                                        if stat.S_ISDIR(s.st_mode):flags |= os.O_DIRECTORY
                                        _need(stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode), 'WORKSPACE_SPECIAL')
                                        childfd = os.open(child, flags, dir_fd=fd)
                                        try:add(childfd, name + '/' + child, s, device)
                                        finally:os.close(childfd)
                                _need(_signature(before) == _signature(os.fstat(fd)), 'WORKSPACE_CHANGED')
                            else:
                                _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= max_file,
                                      'FILE_LIMIT_OR_ALIAS')
                                _need(_signature(before) == _signature(os.fstat(fd)), 'WORKSPACE_CHANGED')
                                total += before.st_size;_need(total <= max_bytes, 'DECODED_BYTE_LIMIT')
                                reader = _Reader(fd, check);info.size = before.st_size;archive.addfile(info, reader)
                                _need(reader.nbytes == before.st_size and _signature(before) == _signature(os.fstat(fd)), 'WORKSPACE_CHANGED')
                                entries.append({**row, 'kind': 'file', 'nbytes': reader.nbytes, 'sha256': reader.digest.hexdigest()})
                        for label, path in sorted(roots.items()):
                            path = Path(path)
                            if not path.exists() and not path.is_symlink():result['missing_roots'].append(label);continue
                            fd = staging._absolute_dir(path)
                            try:
                                before = os.fstat(fd);add(fd, label, before, before.st_dev)
                            finally:os.close(fd)
        partial.rename(destination)
        result.update(status='PRESERVED_AVAILABLE_WORKSPACES', archive_bytes=compressed.nbytes,
                      file_bytes=total, entries=len(entries))
        result['archive_sha256'] = compressed.digest.hexdigest()
    except Exception:
        result['errors'] = [{'code': 'RETENTION_FAILED'}]
    try:
        _write_json_exclusive(out / 'retained-inventory.json', {'schema': 'builder-retained-inventory-v1',
                             'complete': result['status'] == 'PRESERVED_AVAILABLE_WORKSPACES', 'entries': entries})
    except Exception:
        result.update(status='PRESERVATION_INCOMPLETE', errors=[{'code': 'INVENTORY_NOT_PERSISTED'}])
    try:_write_json_exclusive(out / 'retention.json', result)
    except Exception:
        result.update(status='PRESERVATION_INCOMPLETE', errors=[{'code': 'RETENTION_RECEIPT_NOT_PERSISTED'}])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--request-id', required=True)
    args = parser.parse_args()
    if (re.fullmatch(r'builder-[0-9]{8}-[0-9]{2}', args.request_id) is None
            or os.environ.get('GITHUB_ACTIONS') != 'true'
            or os.environ.get('GITHUB_RUN_ATTEMPT') != '1'
            or os.environ.get('GITHUB_REPOSITORY') != 'rownlvh8875-coder/big-model-closed-loop-benchmark'):
        print('RETENTION_CONTEXT_REJECTED');return 1
    root = Path(__file__).resolve().parent.parent
    out = root / 'output/stage7-builder-preparation' / args.request_id;out.mkdir(parents=True, exist_ok=True)
    result = preserve_workspaces({'workspace': Path('/tmp/engine-clock-preparation-' + args.request_id),
                                 'build': Path('/tmp/engine-clock-build-' + args.request_id),
                                 'host-helper': Path('/tmp/engine-clock-bwrap-source')}, out,
                                 deadline=perf_counter() + 180)
    print(result['status'])
    return 0 if result['status'] == 'PRESERVED_AVAILABLE_WORKSPACES' else 1


if __name__ == '__main__':raise SystemExit(main())
