"""Exercise Xvfb status handling with real receipt validation, no native render."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_native_capture_schedule import fixture
from scripts.run_native_capture_trial import run_capture


class NativeCaptureRunnerTests(unittest.TestCase):
    def invoke(self, status, *, write=True, invalid=False, stale=False):
        with TemporaryDirectory() as tmp:
            out=Path(tmp)/'native.json'
            if stale:out.write_text('{}')
            def native(command):
                self.assertEqual(command[:2],['xvfb-run','-a'])
                self.assertIn('task_step_pair_twice',command)
                if write:
                    d=fixture(20261109,'s_curve_left_right','paired_two_ticks',0)
                    if invalid:d['registered_tasks_after'].remove('PSSM.update')
                    out.write_text(json.dumps(d))
                return SimpleNamespace(returncode=status)
            with patch('scripts.run_native_capture_trial.subprocess.run',side_effect=native):
                return run_capture(seed=20261109,scene='s_curve_left_right',
                                   arm='paired_two_ticks',out=out)

    def test_cleanup_status_five_requires_a_valid_new_native_receipt(self):
        self.assertEqual(self.invoke(5),0)

    def test_success_requires_a_valid_native_receipt(self):
        self.assertEqual(self.invoke(0),0)
        with self.assertRaises(ValueError):self.invoke(0,invalid=True)

    def test_cleanup_failure_without_receipt_cannot_pass(self):
        with self.assertRaises(FileNotFoundError):self.invoke(5,write=False)
        with self.assertRaises(ValueError):self.invoke(5,invalid=True)

    def test_real_native_failure_status_is_preserved_even_if_a_file_exists(self):
        self.assertEqual(self.invoke(2),2)
        self.assertEqual(self.invoke(7),7)

    def test_preexisting_output_is_rejected_before_launch(self):
        with self.assertRaises(ValueError):self.invoke(5,stale=True)
