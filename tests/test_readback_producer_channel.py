import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import unittest

from tests.test_readback_call_delivery import compile_delivery
from tests.test_readback_process_mapping import symbol_ranges
try:
    from scripts import readback_producer_channel as channel
except ImportError:
    channel = None


NAMES = {'rd_probe_store', 'rd_probe_read', 'rd_fixture_call'}


class ProducerChannelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='producer-cpu-')
        cls.exe = Path(cls.temp.name) / 'fixture'
        compile_delivery(cls.exe)
        cls.sha = hashlib.sha256(cls.exe.read_bytes()).hexdigest()
        cls.profile = symbol_ranges(cls.exe, NAMES)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.assertIsNotNone(channel, 'kernel sender and spool collector required')
        self.nonce = os.urandom(32)

    def run_probe(self, probe_mode, **overrides):
        args = dict(exe=self.exe, expected_sha=self.sha, mode=probe_mode,
                    codeprofile=self.profile, nonce=self.nonce, timeout=5)
        args.update(overrides)
        return channel.run_cpu_probe(**args)

    def pair(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        a.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        a.settimeout(1)
        return a, b

    def receive(self, sock, **overrides):
        args = dict(expected_pid=os.getpid(), uid=os.getuid(), gid=os.getgid(), nonce=self.nonce)
        args.update(overrides)
        return channel.recv_record(sock, **args)

    def packet(self, **overrides):
        body = dict(schema='readback-cpu-producer-ready-v1', nonce=self.nonce.hex(), pid=os.getpid(),
                    code={n: 1 for n in NAMES}, stream_nbytes=96, status={})
        body.update(overrides)
        return json.dumps(body).encode()

    def test_actual_child_complete_stream_code_and_exit_are_bound(self):
        for mode in ('basic', 'aliases', 'preserve', 'off'):
            with self.subTest(mode=mode):
                result = self.run_probe(mode)
                self.assertTrue(result['kernel_sender_verified'])
                self.assertTrue(result['mapping']['process_code_verified'])
                self.assertTrue(result['decoded']['cpu_window_closed'])
                self.assertEqual(result['receipt']['nonce'], self.nonce.hex())
                self.assertEqual(result['receipt']['stream_sha256'], hashlib.sha256(result['stream']).hexdigest())
                self.assertFalse(result['native_admitted'])
                self.assertFalse(result['driver_state_proven'])

    def test_actual_child_bad_nonce_pid_map_status_sink_exit_and_late_write_reject(self):
        for mode in ('channel_nonce', 'channel_pid', 'channel_map', 'channel_status', 'channel_exit',
                     'channel_extra', 'channel_empty', 'channel_tamper', 'footerfail', 'invalidate', 'offinvalid'):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.run_probe(mode)

    def test_receive_requires_kernel_credentials_and_exact_body_identity(self):
        for change in ({'nonce': '1' * 64}, {'pid': os.getpid() + 1}, {'schema': 'wrong'}):
            a, b = self.pair()
            b.send(self.packet(**change))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.receive(a)
        a, b = self.pair()
        a.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 0)
        b.send(self.packet())
        with self.assertRaises(ValueError):
            self.receive(a)

    def test_real_foreign_sender_cannot_claim_owned_child_pid(self):
        a, b = self.pair()
        script = 'import os,socket; s=socket.socket(fileno=int(os.environ["SOCK"])); s.send(bytes.fromhex(os.environ["BODY"]))'
        child = subprocess.run([os.sys.executable, '-I', '-S', '-c', script], pass_fds=(b.fileno(),),
                               env=dict(SOCK=str(b.fileno()), BODY=self.packet().hex()), timeout=5)
        self.assertEqual(child.returncode, 0)
        with self.assertRaises(ValueError):
            self.receive(a)

    def test_packet_truncation_duplicates_and_received_rights_reject_without_fd_leak(self):
        a, b = self.pair()
        b.send(b'x' * (16 * 1024 + 1))
        with self.assertRaises(ValueError):
            self.receive(a)
        a, b = self.pair()
        b.send(b'{"pid":1,"pid":2}')
        with self.assertRaises(ValueError):
            self.receive(a)
        a, b = self.pair()
        with open('/dev/null', 'rb') as fd:
            before = len(os.listdir('/proc/self/fd'))
            b.sendmsg([self.packet()], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack('i', fd.fileno()))])
            with self.assertRaises(ValueError):
                self.receive(a)
            self.assertEqual(len(os.listdir('/proc/self/fd')), before)

    def test_executable_nonce_mode_and_profile_inputs_reject_before_spawn(self):
        for change in ({'expected_sha': '0' * 64}, {'nonce': b'\0' * 32}, {'nonce': b'wrong'},
                       {'mode': 'unknown'}, {'codeprofile': {}}, {'timeout': 0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_probe('basic', **change)


if __name__ == '__main__':
    unittest.main()
