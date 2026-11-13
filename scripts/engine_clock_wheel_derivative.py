"""Pure bounded metadata derivation; caller pins are not upstream authentication.

No filesystem/network/package import or CLI. Only explicit archive bytes are
processed. Returned bytes never authorize installation, image or native work.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import math
import re
import stat
import struct
from time import perf_counter
from zipfile import ZipFile, ZipInfo, ZIP_STORED, ZIP_DEFLATED

MAX_SOURCE_BYTES = 64 * 1024 ** 2
MAX_EXPANDED_BYTES = 256 * 1024 ** 2
MAX_MEMBER_BYTES = 64 * 1024 ** 2
MAX_METADATA_BYTES = 1024 ** 2
MAX_MEMBERS = 20000
MAX_OUTPUT_BYTES = 512 * 1024 ** 2
MAX_READ_BYTES = 512 * 1024 ** 2
MAX_PATH_BYTES = 4096
MAX_SECONDS = 180
READ_CHUNK = 1024 ** 2
DIST = 'metadrive_simulator-0.4.3.dist-info/'
META, WHEEL, RECORD = (DIST + name for name in ('METADATA', 'WHEEL', 'RECORD'))
PROOF = DIST + 'ENGINE_CLOCK_DERIVATION.json'
MUTABLE = frozenset((META, WHEEL, RECORD))
BUILD = '1headless'
FILENAME = 'metadrive_simulator-0.4.3-1headless-py3-none-any.whl'
POLICY = {'schema': 'engine-clock-wheel-metadata-policy-v1',
          'distribution': 'metadrive-simulator', 'version': '0.4.3',
          'old_requires_dist': 'opencv-python',
          'new_requires_dist': 'opencv-python-headless==5.0.0.93',
          'build': BUILD, 'generator': 'engine-clock-wheel-derivative (metadata-v1)',
          'mutable_members': sorted(MUTABLE), 'added_member': PROOF,
          'output_compression': 'ZIP_STORED', 'output_timestamp': '1980-01-01T00:00:00',
          'source_origin_authenticated': False, 'implementation_authenticated': False}


class _Rejected(Exception):
    def __init__(self, code):
        self.code = code


def _require(condition, code):
    if not condition:
        raise _Rejected(code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('utf-8')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _name(name, directory=False):
    _require(type(name) is str and name and not name.startswith('/')
             and not any(ord(c) < 32 or ord(c) == 127 for c in name)
             and '\\' not in name and ':' not in name, 'BAD_PATH')
    raw = name.encode('utf-8')
    _require(len(raw) <= MAX_PATH_BYTES, 'PATH_LIMIT')
    path = name[:-1] if directory and name.endswith('/') else name
    _require(all(c not in ('', '.', '..') for c in path.split('/')), 'BAD_PATH')
    return path


def _headers(raw):
    _require(len(raw) <= MAX_METADATA_BYTES and b'\r' not in raw and b'\0' not in raw,
             'BAD_METADATA_ENCODING')
    raw.decode('utf-8')
    head, separator, body = raw.partition(b'\n\n')
    _require(bool(separator), 'BAD_METADATA_HEADERS')
    fields = {}
    last = None
    for line in head.split(b'\n'):
        if line.startswith((b' ', b'\t')):
            _require(last is not None, 'BAD_METADATA_HEADERS')
            fields[last][-1] += b'\n' + line
        else:
            match = re.fullmatch(rb'([A-Za-z0-9-]+): (.*)', line)
            _require(match is not None, 'BAD_METADATA_HEADERS')
            last = match[1].lower()
            fields.setdefault(last, []).append(match[2])
    return head, body, fields


def _changed_metadata(metadata, wheel):
    head, body, fields = _headers(metadata)
    for key, value in ((b'metadata-version', b'2.1'), (b'name', b'metadrive-simulator'),
                       (b'version', b'0.4.3')):
        _require(fields.get(key) == [value], 'BAD_DISTRIBUTION_METADATA')
    targets = []
    for requirement in fields.get(b'requires-dist', []):
        match = re.match(rb'[A-Za-z0-9][A-Za-z0-9._-]*', requirement)
        _require(match is not None, 'BAD_REQUIREMENT')
        name = re.sub(rb'[-_.]+', b'-', match[0].lower())
        _require(name not in (b'opencv-python-headless', b'opencv-contrib-python',
                              b'opencv-contrib-python-headless'), 'PREEXISTING_CV2_VARIANT')
        if name == b'opencv-python':
            targets.append(requirement)
    _require(targets == [b'opencv-python'], 'BAD_OPENCV_REQUIREMENT')
    old = b'Requires-Dist: opencv-python'
    lines = head.split(b'\n')
    _require(lines.count(old) == 1, 'BAD_OPENCV_REQUIREMENT')
    new_metadata = b'\n'.join(b'Requires-Dist: opencv-python-headless==5.0.0.93'
                               if line == old else line for line in lines) + b'\n\n' + body
    wheel_head, wheel_body, wf = _headers(wheel)
    _require(set(wf) == {b'wheel-version', b'generator', b'root-is-purelib', b'tag'}
             and wf[b'wheel-version'] == [b'1.0']
             and wf[b'root-is-purelib'] == [b'true'] and wf[b'tag'] == [b'py3-none-any']
             and len(wf[b'generator']) == 1 and wf[b'generator'][0]
             and b'\n' not in wf[b'generator'][0] and not wheel_body, 'BAD_WHEEL_METADATA')
    wheel_lines = wheel_head.split(b'\n')
    generator_lines = [line for line in wheel_lines if line.startswith(b'Generator: ')]
    _require(len(generator_lines) == 1, 'BAD_WHEEL_METADATA')
    new_wheel = b'\n'.join(b'Generator: engine-clock-wheel-derivative (metadata-v1)'
                            if line == generator_lines[0] else line for line in wheel_lines)
    new_wheel += b'\nBuild: 1headless\n\n'
    _require(max(len(new_metadata), len(new_wheel)) <= MAX_METADATA_BYTES, 'METADATA_LIMIT')
    return new_metadata, new_wheel


class _Output(io.BytesIO):
    def write(self, data):
        _require(self.tell() + len(data) <= MAX_OUTPUT_BYTES, 'OUTPUT_LIMIT')
        return super().write(data)


class _Transform:
    def __init__(self, source, deadline, receipt):
        self.source, self.deadline, self.receipt = source, deadline, receipt

    def check(self):
        _require(perf_counter() < self.deadline, 'DEADLINE')

    def stage(self, value):
        self.check()
        self.receipt['failure_stage'] = value

    def precheck(self):
        """Bound central-directory work before ZipFile allocates ZipInfo objects."""
        self.stage('validate_zip_header')
        source = self.source
        _require(len(source) >= 22 and source[-22:-18] == b'PK\x05\x06', 'BAD_EOCD')
        _, disk, cd_disk, on_disk, count, cd_size, cd_offset, comment = struct.unpack('<4s4H2LH', source[-22:])
        # Reserve one output entry for the mandatory derivation marker.
        _require(count + 1 <= MAX_MEMBERS, 'MEMBER_LIMIT')
        _require(disk == cd_disk == comment == 0 and on_disk == count
                 and count < 65535 and cd_offset + cd_size == len(source) - 22
                 and cd_offset <= len(source) - 22, 'BAD_EOCD')
        offset, observed, expanded = cd_offset, 0, 0
        while offset < len(source) - 22:
            self.check()
            observed += 1
            _require(observed <= count and offset + 46 <= len(source) - 22
                     and source[offset:offset+4] == b'PK\x01\x02', 'BAD_CENTRAL_DIRECTORY')
            flags, compression = struct.unpack_from('<2H', source, offset+8)
            compressed, size = struct.unpack_from('<2L', source, offset+20)
            nlen, xlen, clen, disk_number = struct.unpack_from('<4H', source, offset+28)
            _require(0 < nlen <= MAX_PATH_BYTES and xlen == clen == disk_number == 0
                     and flags in (0, 0x800) and compression in (ZIP_STORED, ZIP_DEFLATED),
                     'UNSUPPORTED_ZIP')
            expanded += size
            _require(size <= MAX_MEMBER_BYTES and expanded <= MAX_EXPANDED_BYTES,
                     'EXPANDED_OR_MEMBER_LIMIT')
            _require(compressed <= len(source), 'BAD_CENTRAL_DIRECTORY')
            offset += 46 + nlen
            _require(offset <= len(source) - 22, 'BAD_CENTRAL_DIRECTORY')
        _require(observed == count and offset == len(source) - 22, 'BAD_CENTRAL_DIRECTORY')
        self.directory = count, cd_offset

    def inspect(self, archive):
        self.stage('validate_zip')
        source = self.source
        count, cd_offset = self.directory
        infos = archive.infolist()
        _require(len(infos) == count and archive.start_dir == cd_offset
                 and not archive.comment, 'BAD_EOCD')
        entries, paths, expanded = {}, {}, 0
        for info in infos:
            self.check()
            _require(info.filename == info.orig_filename, 'BAD_PATH')
            directory = info.is_dir()
            path = _name(info.filename, directory)
            _require(path not in paths, 'DUPLICATE_PATH')
            kind = stat.S_IFMT(info.external_attr >> 16)
            _require(kind in ((0, stat.S_IFDIR) if directory else (0, stat.S_IFREG))
                     and (directory or not info.external_attr & 0x10), 'SPECIAL_MEMBER')
            _require(not directory or info.file_size == 0, 'BAD_DIRECTORY')
            _require(info.flag_bits in (0, 0x800) and info.compress_type in (ZIP_STORED, ZIP_DEFLATED)
                     and not info.extra and not info.comment and info.volume == 0, 'UNSUPPORTED_ZIP')
            _require(info.file_size <= MAX_MEMBER_BYTES, 'MEMBER_BYTE_LIMIT')
            expanded += info.file_size
            _require(expanded <= MAX_EXPANDED_BYTES, 'EXPANDED_LIMIT')
            _require(not (info.file_size == 0 and info.CRC != 0), 'BAD_CRC')
            for component in path.split('/'):
                _require(not component.endswith('.dist-info') or component == DIST[:-1], 'FOREIGN_METADATA')
            _require(info.filename not in (PROOF, DIST+'RECORD.jws', DIST+'RECORD.p7s'), 'SIGNED_OR_DERIVED_SOURCE')
            paths[path] = 'directory' if directory else 'file'
            entries[info.filename] = info
        _require(MUTABLE.issubset(entries) and all(not entries[p].is_dir() for p in MUTABLE), 'MISSING_METADATA')
        _require(all(entries[p].file_size <= MAX_METADATA_BYTES for p in MUTABLE), 'METADATA_LIMIT')
        for path in paths:
            self.check()
            components = path.split('/')
            for end in range(1, len(components)):
                _require(paths.get('/'.join(components[:end])) != 'file', 'FILE_ANCESTOR')
        offset = 0
        for info in sorted(infos, key=lambda value: value.header_offset):
            self.check()
            _require(info.header_offset == offset and offset + 30 <= cd_offset, 'HIDDEN_ZIP_DATA')
            signature, _, flags, compression, _, _, crc, csize, usize, nlen, xlen = struct.unpack_from('<4s5H3L2H', source, offset)
            _require(signature == b'PK\x03\x04' and flags == info.flag_bits
                     and compression == info.compress_type and crc == info.CRC
                     and csize == info.compress_size and usize == info.file_size and xlen == 0,
                     'LOCAL_CENTRAL_MISMATCH')
            name = source[offset+30:offset+30+nlen]
            _require(name == info.filename.encode('utf-8' if flags & 0x800 else 'cp437'), 'LOCAL_CENTRAL_MISMATCH')
            offset += 30 + nlen + csize
            _require(offset <= cd_offset, 'BAD_ZIP_LAYOUT')
        _require(offset == cd_offset, 'HIDDEN_ZIP_DATA')
        return entries

    def read(self, archive, info, *, collect=False, writer=None):
        self.check()
        hasher, count, chunks = hashlib.sha256(), 0, []
        remaining = info.file_size
        with archive.open(info) as stream:
            while remaining:
                self.check()
                n = min(READ_CHUNK, remaining, MAX_READ_BYTES - self.receipt['uncompressed_bytes_read'])
                _require(n > 0, 'READ_LIMIT')
                chunk = stream.read(n)
                self.receipt['uncompressed_bytes_read'] += len(chunk)
                _require(chunk and len(chunk) <= n, 'BAD_MEMBER_SIZE')
                remaining -= len(chunk); count += len(chunk); hasher.update(chunk)
                if collect: chunks.append(chunk)
                if writer is not None: writer.write(chunk)
            _require(not stream.read(1), 'BAD_MEMBER_SIZE')
        return hasher.hexdigest(), count, b''.join(chunks) if collect else None

    def records(self, raw, entries):
        self.check()
        _require(len(raw) <= MAX_METADATA_BYTES and b'\0' not in raw, 'BAD_RECORD')
        rows = csv.reader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True)
        records = {}
        for row in rows:
            self.check()
            _require(len(row) == 3, 'BAD_RECORD')
            name, digest, size = row
            _name(name)
            _require(name not in records and name in entries and not entries[name].is_dir(), 'BAD_RECORD')
            if name == RECORD:
                _require(digest == size == '', 'BAD_RECORD_SELF')
                records[name] = None
            else:
                _require(re.fullmatch(r'sha256=[A-Za-z0-9_-]{43}', digest) is not None
                         and re.fullmatch(r'0|[1-9][0-9]*', size) is not None, 'BAD_RECORD')
                decoded = base64.urlsafe_b64decode(digest[7:] + '=')
                _require(len(decoded) == 32 and base64.urlsafe_b64encode(decoded).decode().rstrip('=') == digest[7:]
                         and size == str(entries[name].file_size), 'BAD_RECORD')
                records[name] = decoded.hex()
        _require(set(records) == {name for name, info in entries.items() if not info.is_dir()}, 'BAD_RECORD_CLOSURE')
        return records

    def run(self, archive, metadata_pin, policy_hash):
        entries = self.inspect(archive)
        self.stage('read_record')
        _, _, record_data = self.read(archive, entries[RECORD], collect=True)
        records = self.records(record_data, entries)
        cached, hashes = {RECORD: record_data}, {}
        self.stage('validate_members')
        for name, info in entries.items():
            self.check()
            if name == RECORD:
                value, count = _sha(record_data), len(record_data)
            else:
                value, count, data = self.read(archive, info, collect=name in MUTABLE)
                if name in MUTABLE: cached[name] = data
                if not info.is_dir(): _require(value == records[name], 'RECORD_CONTENT_MISMATCH')
            hashes[name] = value
            self.receipt['members_validated'] += 1
        self.stage('validate_metadata')
        self.receipt['source_metadata_sha256'] = _sha(cached[META])
        _require(self.receipt['source_metadata_sha256'] == metadata_pin, 'METADATA_PIN_MISMATCH')
        new_metadata, new_wheel = _changed_metadata(cached[META], cached[WHEEL])
        preserved = hashlib.sha256(); preserved_count = preserved_bytes = 0
        for name in sorted(set(entries) - MUTABLE):
            self.check()
            info = entries[name]
            preserved.update(_canonical(dict(path=name, kind='directory' if info.is_dir() else 'file',
                                            nbytes=info.file_size, sha256=hashes[name],
                                            create_system=info.create_system, external_attr=info.external_attr)) + b'\n')
            preserved_count += 1; preserved_bytes += info.file_size
        proof = dict(schema='engine-clock-wheel-derivation-v1', policy_sha256=policy_hash,
                     build=BUILD, official_distribution=False, source_origin_authenticated=False,
                     implementation_authenticated=False, source_wheel_sha256=self.receipt['source_wheel_sha256'],
                     source_metadata_sha256=self.receipt['source_metadata_sha256'],
                     source_wheel_metadata_sha256=_sha(cached[WHEEL]),
                     preserved_members_sha256=preserved.hexdigest(), preserved_members=preserved_count,
                     preserved_bytes=preserved_bytes)
        replacement = {META: new_metadata, WHEEL: new_wheel, PROOF: _canonical(proof)+b'\n'}
        self.stage('write_output')
        buffer, output_records = _Output(), []
        with ZipFile(buffer, 'w', compression=ZIP_STORED) as output:
            for name in sorted((set(entries) | {PROOF}) - {RECORD}):
                self.check()
                old = entries.get(name)
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = old.create_system if old else 3
                info.external_attr = old.external_attr if old else (stat.S_IFREG|0o644) << 16
                info.compress_type = ZIP_STORED
                if name in replacement or old.is_dir():
                    data = replacement.get(name, b'')
                    output.writestr(info, data)
                    value, count = _sha(data), len(data)
                else:
                    with output.open(info, 'w') as writer:
                        value, count, _ = self.read(archive, old, writer=writer)
                    _require(value == hashes[name] and count == old.file_size, 'PAYLOAD_CHANGED')
                # ZipFile substitutes a default mode for external_attr == 0.
                # Attributes live in the central record, so restore afterward.
                if old is not None:
                    info.external_attr = old.external_attr
                if not info.is_dir():
                    output_records.append([name, 'sha256='+base64.urlsafe_b64encode(bytes.fromhex(value)).decode().rstrip('='), str(count)])
            output_records.append([RECORD, '', ''])
            rows = io.StringIO(newline='')
            csv.writer(rows, lineterminator='\n').writerows(sorted(output_records))
            data = rows.getvalue().encode('utf-8')
            _require(len(data) <= MAX_METADATA_BYTES, 'METADATA_LIMIT')
            info = ZipInfo(RECORD, (1980, 1, 1, 0, 0, 0))
            info.create_system, info.external_attr = entries[RECORD].create_system, entries[RECORD].external_attr
            output.writestr(info, data)
            info.external_attr = entries[RECORD].external_attr
        self.check()
        result = buffer.getvalue()
        _require(len(result) <= MAX_OUTPUT_BYTES, 'OUTPUT_LIMIT')
        self.receipt.update(preserved_members_sha256=preserved.hexdigest(), preserved_members=preserved_count,
                            preserved_bytes=preserved_bytes)
        return result


def derive_wheel(source: bytes, *, expected_source_sha256: str,
                 expected_metadata_sha256: str, deadline: float) -> tuple[bytes | None, dict]:
    """Derive bytes from caller-pinned input; never authenticate origin/admission."""
    started = perf_counter()
    receipt = dict(schema='engine-clock-wheel-derivative-result-v1', status='FAILED_OR_INCOMPLETE',
                   complete=False, native_admission=False, execution_authorized=False,
                   image_preparation_ready=False, official_distribution=False,
                   source_origin_authenticated=False, implementation_authenticated=False,
                   policy_sha256=None, source_wheel_sha256=None, source_metadata_sha256=None,
                   derived_wheel_sha256=None, preserved_members_sha256=None, preserved_members=0,
                   preserved_bytes=0, expected_upstream_filename='metadrive_simulator-0.4.3-py3-none-any.whl',
                   derived_filename=FILENAME, input_bytes=0, output_bytes=0,
                   uncompressed_bytes_read=0, members_validated=0, elapsed_s=0.,
                   failure_stage='arguments', error_code=None)
    output, effective = None, None
    try:
        _require(type(source) is bytes, 'BAD_INPUT_TYPE')
        receipt['input_bytes'] = len(source)
        _require(len(source) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT')
        for pin in (expected_source_sha256, expected_metadata_sha256):
            _require(type(pin) is str and re.fullmatch(r'[0-9a-f]{64}', pin) is not None, 'BAD_PIN')
        _require(type(deadline) in (int, float) and math.isfinite(deadline), 'BAD_DEADLINE')
        effective = min(deadline, started + MAX_SECONDS)
        transform = _Transform(source, effective, receipt)
        transform.stage('hash_source')
        receipt['policy_sha256'] = _sha(_canonical(POLICY))
        receipt['source_wheel_sha256'] = _sha(source)
        _require(receipt['source_wheel_sha256'] == expected_source_sha256, 'SOURCE_PIN_MISMATCH')
        transform.precheck()
        with ZipFile(io.BytesIO(source), 'r') as archive:
            output = transform.run(archive, expected_metadata_sha256, receipt['policy_sha256'])
        transform.stage('complete')
        receipt.update(derived_wheel_sha256=_sha(output), output_bytes=len(output),
                       status='METADATA_DERIVATIVE_CREATED', complete=True, failure_stage=None)
    except _Rejected as exc:
        receipt['error_code'] = exc.code
    except Exception:
        receipt['error_code'] = 'ARCHIVE_OR_OPERATION_FAILED'
    finished = perf_counter()
    if receipt['complete'] and finished >= effective:
        receipt.update(complete=False, error_code='DEADLINE', failure_stage='completion')
    if not receipt['complete']:
        output = None
        receipt.update(status='FAILED_OR_INCOMPLETE', derived_wheel_sha256=None,
                       output_bytes=0, preserved_members_sha256=None, preserved_members=0, preserved_bytes=0)
    receipt['elapsed_s'] = finished - started
    return output, receipt
