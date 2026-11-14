"""Point-in-time bytes for reviewed ELF ranges in an owned Linux CPU process.

This does not establish a Panda ABI, an installed GL interposer, driver state,
or subsequent code immutability. Profiles and their provenance are caller inputs.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
import struct

MAX_FILE = 64 * 1024 * 1024
MAX_MAPS = 1024 * 1024
MAX_RANGE = 1024 * 1024
_MAP = re.compile(rb'([0-9a-f]+)-([0-9a-f]+) ([r-][w-][x-][ps]) ([0-9a-f]+) ([0-9a-f]+):([0-9a-f]+) ([0-9]+)(?: +(.*))?')


def _integer(value, low=0, high=2**64 - 1):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('invalid bounded integer')
    return value


def parse_maps(raw):
    if type(raw) is not bytes or not raw or len(raw) > MAX_MAPS:
        raise ValueError('maps byte budget')
    lines = raw.splitlines()
    if len(lines) > 4096:
        raise ValueError('maps row budget')
    rows = []
    previous = 0
    for line in lines:
        match = _MAP.fullmatch(line)
        if not match:
            raise ValueError('malformed maps row')
        a, b, perms, offset, major, minor, inode, path = match.groups()
        start, end = int(a, 16), int(b, 16)
        if not previous <= start < end <= 2**64 - 1 or start % 4096 or end % 4096:
            raise ValueError('overlapping or unaligned maps row')
        previous = end
        rows.append(dict(start=start, end=end, perms=perms.decode('ascii'), offset=int(offset, 16),
                         major=int(major, 16), minor=int(minor, 16), inode=int(inode),
                         path=os.fsdecode(path or b'')))
    return tuple(rows)


def elf_ranges(blob):
    if type(blob) is not bytes or not 64 <= len(blob) <= MAX_FILE:
        raise ValueError('ELF byte budget')
    if blob[:7] != b'\x7fELF\x02\x01\x01':
        raise ValueError('ELF64 little endian required')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', blob)
    _, kind, machine, version, _, phoff, _, _, ehsize, phsize, phnum, _, _, _ = header
    if kind not in (2, 3) or machine != 62 or version != 1 or ehsize != 64 or phsize != 56 or not 1 <= phnum <= 64:
        raise ValueError('unsupported ELF program headers')
    if phoff < 64 or phoff + phsize * phnum > len(blob):
        raise ValueError('truncated ELF program headers')
    result = []
    for i in range(phnum):
        typ, flags, offset, vaddr, _, filesz, memsz, align = struct.unpack_from('<IIQQQQQQ', blob, phoff + i * phsize)
        if typ != 1:
            continue
        if filesz > memsz or offset + filesz > len(blob) or vaddr + memsz >= 2**64:
            raise ValueError('invalid ELF load span')
        if align not in (0, 1) and (align & (align - 1) or (offset - vaddr) % align):
            raise ValueError('invalid ELF load alignment')
        result.append(dict(offset=offset, vaddr=vaddr, filesz=filesz, memsz=memsz, flags=flags, align=align))
    if not result:
        raise ValueError('ELF has no load ranges')
    return tuple(result)


def _profile(ranges, addresses):
    if type(ranges) is not dict or not 1 <= len(ranges) <= 32 or type(addresses) is not dict or set(ranges) != set(addresses):
        raise ValueError('exact named ranges and addresses required')
    total = 0
    for name, span in ranges.items():
        if type(name) is not str or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,127}', name):
            raise ValueError('invalid range name')
        if type(span) is not dict or set(span) != {'vaddr', 'size'}:
            raise ValueError('invalid range profile')
        va, size = _integer(span['vaddr']), _integer(span['size'], 1, MAX_RANGE)
        if va + size >= 2**64:
            raise ValueError('range overflow')
        _integer(addresses[name], 1)
        total += size
    if total > 2 * MAX_RANGE:
        raise ValueError('total memory budget')


def check_code_ranges(blob, maps, file_key, ranges, addresses, read_memory):
    """Pure span/identity validation; read_memory supplies exact process bytes."""
    _profile(ranges, addresses)
    loads = elf_ranges(blob)
    major, minor, inode, path = file_key
    result, bias = {}, None
    for name, span in ranges.items():
        va, size, address = span['vaddr'], span['size'], addresses[name]
        segments = [p for p in loads if p['vaddr'] <= va and va + size <= p['vaddr'] + p['filesz'] and p['flags'] & 1 and not p['flags'] & 2]
        if len(segments) != 1:
            raise ValueError('range is not unique executable ELF data')
        segment = segments[0]
        offset = segment['offset'] + va - segment['vaddr']
        rows = [m for m in maps if m['start'] <= address and address + size <= m['end']]
        if len(rows) != 1:
            raise ValueError('range is not contained in one process mapping')
        row = rows[0]
        if (row['major'], row['minor'], row['inode'], row['path']) != file_key or row['perms'] != 'r-xp':
            raise ValueError('code mapping identity or protection mismatch')
        if row['offset'] + address - row['start'] != offset:
            raise ValueError('code file offset mismatch')
        current_bias = address - va
        if current_bias < 0 or current_bias % 4096 or (bias is not None and bias != current_bias):
            raise ValueError('inconsistent ELF load bias')
        bias = current_bias
        for alias in maps:
            if (alias['major'], alias['minor'], alias['inode']) == (major, minor, inode) and 'w' in alias['perms']:
                if max(offset, alias['offset']) < min(offset + size, alias['offset'] + alias['end'] - alias['start']):
                    raise ValueError('writable alias of code range')
        expected = blob[offset:offset + size]
        actual = read_memory(address, size)
        if type(actual) is not bytes or actual != expected:
            raise ValueError('mapped code bytes mismatch')
        result[name] = dict(vaddr=va, file_offset=offset, size=size, sha256=hashlib.sha256(expected).hexdigest())
    return result


def _read_bounded(path, limit):
    with open(path, 'rb', buffering=0) as stream:
        chunks, size = [], 0
        while True:
            chunk = stream.read(min(65536, limit + 1 - size))
            if not chunk:
                return b''.join(chunks)
            chunks.append(chunk)
            size += len(chunk)
            if size > limit:
                raise ValueError('proc byte budget')


def _starttime(pid):
    raw = _read_bounded(f'/proc/{pid}/stat', 4096)
    closing = raw.rfind(b')')
    fields = raw[closing + 2:].split()
    if closing < 0 or len(fields) < 20 or raw.split(b' ', 1)[0] != str(pid).encode():
        raise ValueError('invalid process stat')
    if fields[0] in (b'Z', b'X', b'x'):
        raise ValueError('process no longer live')
    return int(fields[19])  # field22; state starts at field3


def _stat_key(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def verify_process_code(pid, path, expected_sha, ranges, reported_addresses):
    """Check a live process twice around bounded code reads; fail on observed races."""
    _integer(pid, 1, 2**31 - 1)
    _profile(ranges, reported_addresses)
    path = os.path.abspath(os.fspath(path))
    if os.path.realpath(path) != path or not re.fullmatch('[0-9a-f]{64}', expected_sha):
        raise ValueError('canonical nonsymlink file and exact SHA256 required')
    fd = mem = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 64 <= before.st_size <= MAX_FILE:
            raise ValueError('bounded regular ELF required')
        blob = os.pread(fd, before.st_size, 0)
        if len(blob) != before.st_size or hashlib.sha256(blob).hexdigest() != expected_sha:
            raise ValueError('file SHA256 mismatch')
        starttime = _starttime(pid)
        exe_before = os.stat(f'/proc/{pid}/exe')
        maps = parse_maps(_read_bounded(f'/proc/{pid}/maps', MAX_MAPS))
        key = os.major(before.st_dev), os.minor(before.st_dev), before.st_ino, path
        mem = os.open(f'/proc/{pid}/mem', os.O_RDONLY | os.O_CLOEXEC)
        checked = check_code_ranges(blob, maps, key, ranges, reported_addresses,
                                    lambda address, size: os.pread(mem, size, address))
        after_maps = parse_maps(_read_bounded(f'/proc/{pid}/maps', MAX_MAPS))
        target = lambda rows: tuple(m for m in rows if (m['major'], m['minor'], m['inode']) == key[:3] or m['path'] == path)
        if target(maps) != target(after_maps) or _starttime(pid) != starttime:
            raise ValueError('process mapping or starttime changed')
        if _stat_key(os.stat(f'/proc/{pid}/exe')) != _stat_key(exe_before):
            raise ValueError('process executable changed')
        if _stat_key(os.fstat(fd)) != _stat_key(before) or _stat_key(os.stat(path, follow_symlinks=False)) != _stat_key(before):
            raise ValueError('file identity changed')
        return dict(schema='readback-process-code-v1', process_code_verified=True, pid=pid,
                    starttime=starttime, file_sha256=expected_sha, ranges=checked,
                    native_admitted=False, panda_runtime_mapping_verified=False)
    except (OSError, OverflowError, TypeError) as exc:
        raise ValueError('process code unavailable or invalid') from exc
    finally:
        if mem is not None:
            os.close(mem)
        if fd is not None:
            os.close(fd)
