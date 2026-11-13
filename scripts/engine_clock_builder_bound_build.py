"""Explicit legacy-bound owned pip unpack boundary; no pip execution on import."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import sys


def _driver():
    # The entry driver is a namespace/stage adapter; snapshot API is immutable legacy.
    path=Path(__file__).with_name('legacy-driver.py')
    spec=importlib.util.spec_from_file_location('owned_driver_snapshot',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    required=('source_snapshot','_check_source_map','pip_wheel_args','validate_snapshots')
    if not all(callable(getattr(module,name,None)) for name in required):raise ValueError('UNSUPPORTED_OWNED_DRIVER')
    return module


class _DigestText(io.TextIOBase):
    def __init__(self):self.nbytes = 0;self.digest = hashlib.sha256()
    @property
    def encoding(self):return 'utf-8'
    def writable(self):return True
    def write(self, text):
        if type(text) is not str or len(text) > 1048576:raise ValueError('BUILD_LOG_LIMIT')
        raw = text.encode('utf-8')
        if self.nbytes + len(raw) > 1048576:raise ValueError('BUILD_LOG_LIMIT')
        self.nbytes += len(raw);self.digest.update(raw)
        return len(text)


def _location(path, tmp_root):
    path = Path(path)
    try:relative = path.relative_to(tmp_root).as_posix()
    except ValueError:raise ValueError('SOURCE_LOCATION_MISMATCH') from None
    if re.fullmatch(r'pip-wheel-[a-z0-9_-]{1,64}/progressbar_[0-9a-f]{32}', relative) is None:
        raise ValueError('SOURCE_LOCATION_MISMATCH')
    current = tmp_root
    for part in Path(relative).parts:
        current = current / part
        s = current.lstat()
        if not stat.S_ISDIR(s.st_mode):raise ValueError('SOURCE_LOCATION_MISMATCH')
    return path, relative


def _write_manifest(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
    if len(raw) > 1048576:raise ValueError('SOURCE_MANIFEST_LIMIT')
    with path.open('xb') as stream:stream.write(raw)


def run_with_snapshots(prepare, pip_main, source_rows, *, tmp_root=Path('/build/tmp'), evidence_root=Path('/build')):
    """Hook verified pip immediately after unpack, before source metadata execution."""
    driver = _driver()
    original = prepare.unpack_url
    captured, stdout, stderr = [], _DigestText(), _DigestText()
    def unpack(link, location, *args, **kwargs):
        if captured:raise ValueError('MULTIPLE_SOURCE_UNPACKS')
        path, relative = _location(location, tmp_root)
        if any(path.iterdir()):raise ValueError('SOURCE_LOCATION_NOT_EMPTY')
        unpacked = original(link, location, *args, **kwargs)
        before = driver.source_snapshot(path)
        identity = path.lstat()
        _write_manifest(evidence_root / 'source-before.json', before)
        driver._check_source_map(before['files_sha256'], {r['path']: r['sha256'] for r in source_rows}, before=True)
        captured.append((path, relative, identity.st_dev, identity.st_ino, before))
        return unpacked
    prepare.unpack_url = unpack
    try:
        failed, code = False, None
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = pip_main(driver.pip_wheel_args())
        except BaseException:
            failed = True
            if not captured:raise ValueError('SOURCE_PAYLOAD_MISMATCH') from None
        if len(captured) != 1:raise ValueError('MISSING_SOURCE_UNPACK')
        path, relative, device, inode, before = captured[0]
        identity = path.lstat()
        if not stat.S_ISDIR(identity.st_mode) or (identity.st_dev, identity.st_ino) != (device, inode):
            raise ValueError('SOURCE_LOCATION_CHANGED')
        after = driver.source_snapshot(path)
        _write_manifest(evidence_root / 'source-after.json', after)
        if failed or type(code) is not int or code != 0:raise ValueError('PIP_WHEEL_FAILED')
        result = {'schema': 'source-snapshots-v1', 'status': 'SOURCE_SNAPSHOTS_VERIFIED',
                  'source_relative': relative, 'source_identity': {'device': device, 'inode': inode},
                  'before': before, 'after': after,
                  'logs': {'stdout_bytes': stdout.nbytes, 'stderr_bytes': stderr.nbytes,
                           'stdout_sha256': stdout.digest.hexdigest(), 'stderr_sha256': stderr.digest.hexdigest()}}
        return driver.validate_snapshots(result, source_rows)
    finally:
        prepare.unpack_url = original


def record_failure(exc):
    allowed={'UNSUPPORTED_OWNED_DRIVER','SOURCE_LOCATION_MISMATCH','SOURCE_LOCATION_NOT_EMPTY','MULTIPLE_SOURCE_UNPACKS',
             'SOURCE_PAYLOAD_MISMATCH','MISSING_SOURCE_UNPACK','SOURCE_LOCATION_CHANGED','PIP_WHEEL_FAILED',
             'BUILD_LOG_LIMIT','SOURCE_MANIFEST_LIMIT','INVALID_SOURCE_SNAPSHOTS'}
    code=str(exc) if isinstance(exc,ValueError) and str(exc) in allowed else 'SOURCE_SNAPSHOT_FAILED'
    result={'schema':'source-failure-v2','status':'FAILED','code':code}
    try:_write_manifest(Path('/build/source-failure.json'),result)
    except Exception:pass
    return result


def main():
    if sys.argv != [sys.argv[0], '--registered-pip-wheel-v1'] or sys.version_info[:3] != (3, 11, 18):return 2
    try:
        from pip._internal.cli.main import main as pip_main
        from pip._internal.operations import prepare
        config = json.loads(Path('/run/builder/config.json').read_bytes())
        result = run_with_snapshots(prepare, pip_main, config['source_rows'])
        sys.stdout.write(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n')
        return 0
    except Exception as exc:
        record_failure(exc)
        sys.stdout.write('{"schema":"source-snapshot-failure-v1","code":"SOURCE_SNAPSHOT_FAILED"}\n')
        return 1


if __name__ == '__main__':raise SystemExit(main())
