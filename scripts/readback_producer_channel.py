"""Collect an owned CPU probe's actual completion, code bytes and stream.

The pinned executable/profile must come from a reviewed CPU-only fixture. This
module is not a sandbox for arbitrary executables and grants no native authority.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import subprocess
import tempfile
import time

from scripts.readback_process_mapping import MAX_FILE, _profile, elf_ranges, verify_process_code
from scripts.readback_return_codec import MAX_WIRE, decode_stream

MAX_PACKET = 16 * 1024
CODE_NAMES = {'rd_probe_store', 'rd_probe_read', 'rd_fixture_call'}
MODES = {'basic', 'aliases', 'preserve', 'off', 'channel_nonce', 'channel_pid', 'channel_map',
         'channel_status', 'channel_exit', 'channel_extra', 'channel_empty', 'channel_tamper',
         'footerfail', 'invalidate', 'offinvalid'}
STATUS_INTS = {'original_commands', 'original_calls', 'resolver_calls', 'args_ok', 'errno_ok', 'regs_ok',
               'attached', 'bound', 'delivery_error', 'events', 'replayed', 'error', 'captured',
               'attempts', 'forwards', 'wire_bytes', 'finish'}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _nonce(nonce):
    _need(type(nonce) is bytes and len(nonce) == 32 and any(nonce), 'fresh nonzero 32B nonce required')


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, 'duplicate packet field')
        result[key] = value
    return result


def _bad_constant(value):
    raise ValueError('nonfinite JSON value')


def recv_record(sock, *, expected_pid, uid, gid, nonce):
    """Validate per-message SCM_CREDENTIALS; SO_PEERCRED on a precreated pair is insufficient."""
    _nonce(nonce)
    for value in (expected_pid, uid, gid):
        _need(type(value) is int and 0 <= value < 2**32, 'expected kernel identity')
    raw, ancillary, flags, _ = sock.recvmsg(MAX_PACKET, socket.CMSG_SPACE(12) + socket.CMSG_SPACE(1024))
    credentials, unexpected, received_fds = [], False, []
    # Always close received SCM_RIGHTS, including on truncated or malformed messages.
    try:
        for level, kind, data in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                received_fds.extend(struct.unpack(f'{len(data) // 4}i', data[:len(data) // 4 * 4]))
                unexpected = True
            elif level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS and len(data) == 12:
                credentials.append(struct.unpack('iII', data))
            else:
                unexpected = True
        _need(raw and not flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC), 'empty or truncated packet')
        _need(not unexpected and credentials == [(expected_pid, uid, gid)], 'kernel sender mismatch or unexpected ancillary data')
        try:
            body = json.loads(raw, object_pairs_hook=_unique, parse_constant=_bad_constant)
        except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            raise ValueError('invalid packet JSON') from exc
        _need(type(body) is dict and set(body) == {'schema', 'nonce', 'pid', 'code', 'stream_nbytes', 'status'}, 'exact packet fields')
        _need(body['schema'] == 'readback-cpu-producer-ready-v1' and body['nonce'] == nonce.hex() and
              type(body['pid']) is int and body['pid'] == expected_pid, 'packet identity mismatch')
        code = body['code']
        _need(type(code) is dict and set(code) == CODE_NAMES and all(type(v) is int and 0 < v < 2**64 for v in code.values()), 'packet code addresses')
        _need(type(body['stream_nbytes']) is int and 96 <= body['stream_nbytes'] <= MAX_WIRE, 'packet stream budget')
        status = body['status']
        _need(type(status) is dict and set(status) == STATUS_INTS | {'source', 'driver_state_proven', 'runtime_admission_ready'}, 'exact producer status fields')
        _need(all(type(status[k]) is int and -1 <= status[k] <= 2**64 - 1 for k in STATUS_INTS), 'producer counter types')
        _need(status['source'] == 'SYNTHETIC_TYPED_DISPATCH_ONLY' and status['driver_state_proven'] is False and
              status['runtime_admission_ready'] is False, 'CPU-only producer status required')
        return body
    finally:
        for fd in received_fds:
            os.close(fd)


def _spool_snapshot(spool):
    info = os.fstat(spool.fileno())
    _need(stat.S_ISREG(info.st_mode) and 96 <= info.st_size <= MAX_WIRE, 'bounded regular stream required')
    raw = os.pread(spool.fileno(), info.st_size, 0)
    _need(len(raw) == info.st_size, 'short stream read')
    identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    return raw, identity, hashlib.sha256(raw).hexdigest()


def run_cpu_probe(exe, expected_sha, mode, codeprofile, nonce, timeout=10):
    """Run a pinned CPU child, inspect it while held, then require clean EOF/exit.

    Returned stream/decoded records are private CPU evidence. Caller supplies a
    new os.urandom(32) nonce for each run; no cross-run replay registry is implied.
    """
    _nonce(nonce)
    _need(type(mode) is str and mode in MODES, 'reviewed CPU mode required')
    _need(type(timeout) in (int, float) and 0 < timeout <= 30, 'bounded timeout required')
    _need(type(codeprofile) is dict and set(codeprofile) == CODE_NAMES, 'reviewed exact CPU ranges required')
    _profile(codeprofile, {name: 1 for name in codeprofile})
    path = os.path.abspath(os.fspath(exe))
    _need(path == os.path.realpath(path) and type(expected_sha) is str and re.fullmatch('[0-9a-f]{64}', expected_sha), 'canonical executable SHA256 required')
    child = parent_sock = child_sock = None
    executable_fd = None
    deadline = time.monotonic() + timeout
    def remaining():
        left = deadline - time.monotonic()
        _need(left > 0, 'CPU probe timed out')
        return left
    try:
        executable_fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        executable_stat = os.fstat(executable_fd)
        _need(stat.S_ISREG(executable_stat.st_mode) and 64 <= executable_stat.st_size <= MAX_FILE, 'bounded regular executable')
        image = os.pread(executable_fd, executable_stat.st_size, 0)
        _need(hashlib.sha256(image).hexdigest() == expected_sha, 'executable SHA256 mismatch')
        elf_ranges(image)
        parent_sock, child_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        parent_sock.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        with tempfile.TemporaryFile() as spool, tempfile.TemporaryFile() as errors:
            env = dict(PATH=os.defpath, LANG='C', RD_CONTROL_FD=str(child_sock.fileno()), RD_NONCE=nonce.hex())
            # Execute the already opened inode, so a pathname swap cannot select different code.
            child = subprocess.Popen([path, mode], executable=f'/proc/self/fd/{executable_fd}',
                                     pass_fds=(child_sock.fileno(), executable_fd), env=env,
                                     stdout=spool, stderr=errors, stdin=subprocess.DEVNULL)
            child_sock.close()
            child_sock = None
            parent_sock.settimeout(remaining())
            packet = recv_record(parent_sock, expected_pid=child.pid, uid=os.getuid(), gid=os.getgid(), nonce=nonce)
            running_exe = os.stat(f'/proc/{child.pid}/exe')
            _need((running_exe.st_dev, running_exe.st_ino) == (executable_stat.st_dev, executable_stat.st_ino), 'child executable inode mismatch')
            mapped = verify_process_code(child.pid, path, expected_sha, codeprofile, packet['code'])
            raw, spool_identity, digest = _spool_snapshot(spool)
            _need(packet['stream_nbytes'] == len(raw), 'producer stream extent mismatch')
            parent_sock.settimeout(remaining())
            _need(parent_sock.send(b'A') == 1, 'completion acknowledgment failed')
            _need(child.wait(timeout=remaining()) == 0, 'producer process failed')
            parent_sock.settimeout(remaining())
            extra, anc, flags, _ = parent_sock.recvmsg(MAX_PACKET, socket.CMSG_SPACE(1024))
            # Reuse the closing discipline even for a malicious extra rights packet.
            for level, kind, data in anc:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    for fd in struct.unpack(f'{len(data) // 4}i', data[:len(data) // 4 * 4]):
                        os.close(fd)
            _need(not extra and not anc and not flags, 'extra producer packet or ancillary data')
            final_raw, final_identity, final_digest = _spool_snapshot(spool)
            _need((final_identity, final_digest) == (spool_identity, digest), 'stream changed after completion')
            status = packet['status']
            _need(all(status[k] == v for k, v in dict(args_ok=1, errno_ok=1, regs_ok=1, attached=0, bound=0,
                  delivery_error=0, finish=0, error=0, original_calls=2, replayed=5).items()), 'producer finalization failed')
            receipt = dict(schema='readback-return-producer-finalization-v1', nonce=nonce.hex(),
                           stream_sha256=digest, stream_nbytes=len(raw), finish_result=status['finish'],
                           error=status['error'], forwards=status['forwards'], attempts=status['attempts'],
                           captured=status['captured'], data_wire_bytes=status['wire_bytes'])
            decoded = decode_stream(final_raw, expected_nonce=nonce, expected_windows=1, reads_per_window=2,
                                    enabled=not mode.startswith('off'), producer_receipt=receipt)
            _need(os.fstat(errors.fileno()).st_size <= 16384, 'producer diagnostic byte budget')
            return dict(schema='readback-cpu-channel-result-v1', kernel_sender_verified=True, mapping=mapped,
                        receipt=receipt, status=status, stream=raw, decoded=decoded, exit_code=child.returncode,
                        native_admitted=False, driver_state_proven=False, panda_runtime_mapping_verified=False)
    except (OSError, subprocess.TimeoutExpired, OverflowError) as exc:
        raise ValueError('CPU producer unavailable, timed out or failed') from exc
    finally:
        if parent_sock is not None:
            parent_sock.close()
        if child_sock is not None:
            child_sock.close()
        if child is not None and child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        if executable_fd is not None:
            os.close(executable_fd)
