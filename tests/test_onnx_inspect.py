import tempfile
import unittest
from pathlib import Path
from bigbench.onnx_inspect import inspect_onnx


class ONNXInspectTests(unittest.TestCase):
    def test_reject_missing_model(self):
        with self.assertRaises(ValueError):
            inspect_onnx(Path('/no-such-model.onnx'))

    def test_reject_incorrect_extension(self):
        with tempfile.TemporaryDirectory() as dirname:
            p=Path(dirname)/'fake.pkl'
            p.write_bytes(b'fake')
            with self.assertRaises(ValueError):
                inspect_onnx(p)

if __name__ == '__main__': unittest.main()
