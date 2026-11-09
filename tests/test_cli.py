import json
import tempfile
from pathlib import Path
import unittest
from bigbench.cli import main


class CLITests(unittest.TestCase):
    def test_mock_matrix_has_explicit_non_model_label(self):
        with tempfile.TemporaryDirectory() as directory:
            result=main(['smoke-compare','--out',directory])
            self.assertEqual(result,0)
            report=json.loads((Path(directory)/'comparison.json').read_text())
            self.assertTrue(report['not_big_model_performance'])
            self.assertEqual(len(report['results']),8)
            self.assertTrue(all(row['mock_policy'] in ('conservative','responsive') for row in report['results']))

if __name__=='__main__':unittest.main()
