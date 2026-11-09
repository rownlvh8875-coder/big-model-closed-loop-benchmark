import unittest
from bigbench.model_inventory import model_records, checked_model_path


class ModelInventoryTests(unittest.TestCase):
    def test_only_onnx_models_and_no_directory_entries(self):
        data=[{'type':'directory','path':'abc.onnx'},
              {'type':'file','path':'a/big_model.onnx','size':412,
               'lfs':{'oid':'a'*64}},
              {'type':'file','path':'a/dont-download.pkl','size':12}]
        result=model_records(data)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['sha256'],'a'*64)
        self.assertEqual(result[0]['size_bytes'],412)

    def test_reject_path_escape(self):
        for bad in ('../secret.onnx','/tmp/model.onnx','a/../../bad.onnx','file.pkl'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                checked_model_path(bad)

if __name__=='__main__':unittest.main()
