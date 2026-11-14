"""Explicit resource/cgroup fixtures; no actual cgroup scan, Docker or engine."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
try:
    from scripts import engine_clock_sealed_native_v5 as n
    from scripts import engine_clock_sealed_native_container_v5 as c
    from scripts import engine_clock_sealed_native_run_v5 as r
except ImportError:n=c=r=None

class NativeMemoryTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(n,'explicit native memory experiment absent')
    def files(self,root):
        for name,value in {'memory.max':'4294967296\n','memory.current':'2684354560\n','memory.peak':'3221225472\n','memory.events':'low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n'}.items():(root/name).write_text(value)
    def test_four_gib_snapshot_and_oom_delta(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.files(root);before=c.memory_snapshot(root)
            self.assertEqual(4294967296,before['max_bytes']);self.assertEqual(3221225472,before['peak_bytes'])
            c.require_no_oom(before,before)
            (root/'memory.events').write_text('oom 1\noom_kill 1\n')
            after=c.memory_snapshot(root)
            with self.assertRaises(ValueError):c.require_no_oom(before,after)
    def test_unbounded_wrong_cap_malformed_and_unsafe_memory_files_reject(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.files(root)
            for value in ('max\n','2147483648\n','-1\n','not-a-number\n'):
                (root/'memory.max').write_text(value)
                with self.assertRaises(ValueError):c.memory_snapshot(root)
            self.files(root);(root/'memory.events').write_bytes(b'x'*8193)
            with self.assertRaises(ValueError):c.memory_snapshot(root)
            self.files(root);(root/'memory.max').unlink();(root/'memory.max').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):c.memory_snapshot(root)
            import os
            (root/'memory.max').unlink();os.mkfifo(root/'memory.max')
            with self.assertRaises(ValueError):c.memory_snapshot(root)
    def test_host_minimum_and_state_projection(self):
        self.assertEqual(16777216000,r.host_memory_profile(b'MemTotal: 16384000 kB\nMemFree: 1 kB\n')['total_bytes'])
        with self.assertRaises(ValueError):r.host_memory_profile(b'MemTotal: 4194304 kB\n')
        value=r.state_projection(dict(Running=False,Status='exited',ExitCode=137,OOMKilled=True,Error='SECRET_SENTINEL',Config={'Env':['TOKEN=SECRET_SENTINEL']}))
        self.assertEqual(dict(Running=False,Status='exited',ExitCode=137,OOMKilled=True),value)
        self.assertNotIn('SECRET_SENTINEL',json.dumps(value))
    def test_exact_new_docker_memory_and_identity_resource_binding(self):
        from test_engine_clock_sealed_native_v2 import LaunchDiagnosticTests
        raw,routes,ex=LaunchDiagnosticTests('runTest').fixture();raw['Config']['Cmd']=n.CONTAINER_COMMAND;raw['Config']['Labels']['stage7.request']=n.ID
        raw['HostConfig']['CgroupnsMode']='private'
        with self.assertRaises(ValueError):n.validate_launch(raw,routes,ex)
        raw['HostConfig']['Memory']=4294967296
        raw['HostConfig']['CgroupnsMode']='private'
        self.assertTrue(n.validate_launch(raw,routes,ex)['validated'])
        self.assertEqual({'memory_bytes':4294967296,'nano_cpus':2000000000,'pids_limit':128,'cgroup_namespace':'private'},n.environment_identity()['container_resources'])

if __name__=='__main__':unittest.main()
