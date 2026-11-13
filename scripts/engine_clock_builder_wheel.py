"""Strict, bounded progressbar derivative validation. Never imports its payloads."""
import base64
import csv
from email import policy
from email.parser import BytesParser
import hashlib
import io
import re
import stat
import struct
import zlib

DIST = 'progressbar-2.5.dist-info/'
RUNTIME = {'progressbar/' + n for n in ('__init__.py', 'compat.py', 'progressbar.py', 'widgets.py')}
PINNED = RUNTIME | {DIST + 'licenses/LICENSE.txt'}
MEMBERS = PINNED | {DIST + n for n in ('METADATA', 'WHEEL', 'top_level.txt', 'RECORD')}
LIMIT = 1048576


def _need(value):
    if not value:
        raise ValueError('INVALID_WHEEL')


def _payloads(raw):
    _need(type(raw) is bytes and 22 <= len(raw) <= LIMIT)
    sig, disk, start_disk, count_disk, count, central_size, central, comment = struct.unpack_from('<4s4H2LH', raw, len(raw) - 22)
    _need(sig == b'PK\x05\x06' and disk == start_disk == comment == 0 and count_disk == count == 9
          and central + central_size == len(raw) - 22)
    cursor, local_end, total, result = central, 0, 0, {}
    for _ in range(count):
        values = struct.unpack_from('<4s6H3L5H2L', raw, cursor)
        (sig, made, needed, flags, method, time, date, crc, compressed, size,
         name_len, extra, comment, disk, internal, external, offset) = values
        _need(sig == b'PK\x01\x02' and needed in (10, 20) and flags == 0
              and method in (0, 8) and extra == comment == disk == 0
              and offset == local_end and size <= LIMIT and compressed <= LIMIT
              and stat.S_IFMT(external >> 16) in (0, stat.S_IFREG)
              and stat.S_IMODE(external >> 16) & ~0o666 == 0)
        cursor += 46
        name = raw[cursor:cursor + name_len].decode('ascii')
        cursor += name_len
        _need(name in MEMBERS and name not in result and cursor <= len(raw) - 22)
        local = struct.unpack_from('<4s5H3L2H', raw, offset)
        _need(local == (b'PK\x03\x04', needed, flags, method, time, date, crc, compressed, size, name_len, 0))
        begin = offset + 30
        _need(raw[begin:begin + name_len] == name.encode())
        begin += name_len
        local_end = begin + compressed
        _need(local_end <= central)
        data = raw[begin:local_end]
        if method == 8:
            stream = zlib.decompressobj(-15)
            data = stream.decompress(data, size + 1)
            _need(stream.eof and not stream.unused_data and not stream.unconsumed_tail)
        _need(len(data) == size and zlib.crc32(data) & 0xffffffff == crc)
        total += len(data)
        _need(total <= LIMIT)
        result[name] = data
    _need(cursor == central + central_size and local_end == central and set(result) == MEMBERS)
    return result


def _headers(data, expected):
    message = BytesParser(policy=policy.default).parsebytes(data)
    _need(not message.defects and not message.is_multipart())
    for key, value in expected.items():
        _need(message.get_all(key) == [value])
    _need(not message.get_all('Requires-Dist') and not message.get_all('Requires-External'))


def validate_wheel(raw: bytes, pins: dict) -> dict:
    """Pins are caller metadata; matching bytes do not authenticate their publisher."""
    result = {'schema': 'progressbar-wheel-byte-check-v1', 'status': 'REJECTED',
              'wheel_sha256': None, 'errors': [], 'native_admission': False,
              'image_preparation_ready': False, 'publisher_authenticated': False}
    try:
        _need(type(pins) is dict and set(pins) == PINNED and
              all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in pins.values()))
        payloads = _payloads(raw)
        _need(all(hashlib.sha256(payloads[p]).hexdigest() == digest for p, digest in pins.items()))
        _headers(payloads[DIST + 'METADATA'], {'Name': 'progressbar', 'Version': '2.5'})
        _headers(payloads[DIST + 'WHEEL'], {'Wheel-Version': '1.0', 'Root-Is-Purelib': 'true', 'Tag': 'py3-none-any'})
        _need(payloads[DIST + 'top_level.txt'] == b'progressbar\n')
        rows = list(csv.reader(io.StringIO(payloads[DIST + 'RECORD'].decode('utf-8'), newline=''), strict=True))
        seen = set()
        for row in rows:
            _need(len(row) == 3 and row[0] in MEMBERS and row[0] not in seen)
            path, digest, size = row
            seen.add(path)
            if path == DIST + 'RECORD':
                _need(digest == size == '')
            else:
                data = payloads[path]
                encoded = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
                _need(digest == 'sha256=' + encoded and size == str(len(data)))
        _need(seen == MEMBERS)
        result.update(status='WHEEL_BYTES_MATCH', wheel_sha256=hashlib.sha256(raw).hexdigest(),
                      nbytes=len(raw), member_count=len(payloads), decoded_bytes=sum(map(len, payloads.values())))
    except (ValueError, TypeError, KeyError, UnicodeError, struct.error, zlib.error, csv.Error, OverflowError):
        result['errors'] = [{'code': 'INVALID_WHEEL'}]
    return result
