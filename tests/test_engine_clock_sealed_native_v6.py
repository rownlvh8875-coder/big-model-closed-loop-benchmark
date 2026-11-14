"""Closed selection integration fixtures, no native process/proc scan."""
import json
from pathlib import Path
import tempfile
import unittest
try:
    from scripts import engine_clock_sealed_native_v6 as n
    from scripts import engine_clock_sealed_native_container_v6 as c
except ImportError:n=c=None

class SelectionProtocolTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(n,'pre-gate native selection evidence missing')
    def test_rejected_mapping_is_persisted_before_gate(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'map-report.json'
            with self.assertRaises(ValueError):c.classify_map_view('1000-2000 r-xp 0 00:01 12 /host/injected.so\n',set(),set(),path)
            d=json.loads(path.read_bytes());self.assertFalse(d['accepted'])
            self.assertEqual('/host/injected.so',d['rejections'][0]['path'])
    def test_policy_and_helper_are_in_actual_source_identity(self):
        from scripts import engine_clock_native_selection as selection
        root=Path(__file__).resolve().parents[1];paths=n.source_paths(root)
        self.assertTrue({'scripts/engine_clock_native_selection.py','tests/test_engine_clock_native_selection.py',
            'scripts/engine_clock_sealed_native_container_v6.py','docs/evidence/STAGE7_ENGINE_CLOCK_SEALED_NATIVE_05_RESULT.json'}<=paths)
        self.assertEqual(selection.POLICY,n.environment_identity()['selection_policy'])

if __name__=='__main__':unittest.main()
