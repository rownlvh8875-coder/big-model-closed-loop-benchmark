"""Imported-ORT rejection fixture must isolate its approved OpenCV assumption."""
import importlib,unittest
from unittest.mock import patch
class VersionIsolationRegression(unittest.TestCase):
 def test_imported_ort_fixture_survives_new_installed_opencv_release(self):
  import cv2
  old=importlib.import_module('test_engine_clock_native');case=old.AuthorizationTests('test_native_boundary_rejects_imported_ort_even_with_allowed_distribution_metadata');result=unittest.TestResult()
  with patch.object(cv2,'__version__','5.1.0'):case.run(result)
  self.assertTrue(result.wasSuccessful(),str(result.failures)+str(result.errors))
if __name__=='__main__':unittest.main()
