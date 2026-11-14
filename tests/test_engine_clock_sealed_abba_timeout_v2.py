"""Compose the owned Docker adapter with the real frozen CPU process capturer."""
from pathlib import Path
import sys
import tempfile
from time import perf_counter
import unittest
from unittest.mock import patch
try:
    from scripts import engine_clock_sealed_abba_v2 as n
    from scripts import engine_clock_sealed_abba_run_v2 as runner
except ImportError:
    from scripts import engine_clock_sealed_abba as n
    from scripts import engine_clock_sealed_abba_run as runner
from scripts import engine_clock_image_process as process


class RegisteredStartTimeoutTests(unittest.TestCase):
    def test_registered_start_timeout_reaches_real_capture_without_cap_relaxation(self):
        # Only the external Docker executable is replaced with an owned CPU
        # command. Real adapter deadlines, argument forwarding and capture run.
        original=process.capture
        def cpu_boundary(command,out,**kwargs):
            self.assertEqual(['start','--attach','a'*64],command[-3:])
            return original([sys.executable,'-I','-S','-B','-c',
                "print('CPU_START_ADAPTER_ONLY')"],out,**kwargs)
        with tempfile.TemporaryDirectory() as td,patch.object(process,'capture',side_effect=cpu_boundary):
            engine=runner.Docker(Path(td)/'engine',deadline=perf_counter()+3600)
            try:result=engine.call(['start','--attach','a'*64],timeout=n.BUDGET['container_seconds'])
            except ValueError as exc:self.fail('registered start rejected before Popen: '+str(exc))
            self.assertEqual('EXITED',result['status']);self.assertEqual(0,result['returncode'])
            self.assertEqual(b'CPU_START_ADAPTER_ONLY\n',result['_stdout'])
            self.assertTrue(result['streams_complete'])


if __name__=='__main__':unittest.main()
