"""Owned fake Docker metadata and command captures; never launch a container."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
try:from scripts import engine_clock_image_backend as b
except ImportError:b=None

class BackendTests(unittest.TestCase):
 def test_offline_config_environment_and_private_metadata_capture(self):
  self.assertIsNotNone(b)
  calls=[]
  def capture(argv,out,**kw):
   calls.append((argv,kw));return {'status':'EXITED','returncode':0,'streams_complete':True,'_stdout':b'[{"Id":"owned"}]','_stderr':b''}
  with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'DOCKER_HOST':'tcp://secret','DOCKER_CONFIG':'/secret','HTTPS_PROXY':'https://secret'}),patch.object(b.process,'capture',side_effect=capture):
   e=b.Docker(Path(tmp),deadline=b.time.perf_counter()+30);self.assertEqual([{'Id':'owned'}],e.json(['inspect','owned']))
   argv,kw=calls[0];self.assertIn('--host=unix:///var/run/docker.sock',argv);self.assertNotIn('DOCKER_HOST',kw['env']);self.assertNotIn('DOCKER_CONFIG',kw['env']);self.assertFalse(kw['keep_stdout']);self.assertFalse(kw['keep_stderr']);self.assertIn('--config',argv)
 def test_failed_capture_stops_before_projection_without_secret_message(self):
  self.assertIsNotNone(b)
  with tempfile.TemporaryDirectory() as tmp,patch.object(b.process,'capture',return_value={'status':'EXITED','returncode':1,'streams_complete':True,'_stdout':b'SECRET','_stderr':b'SECRET'}):
   e=b.Docker(Path(tmp),deadline=b.time.perf_counter()+30)
   with self.assertRaisesRegex(ValueError,'^IMAGE_DOCKER_REJECTED$'):e.json(['inspect','owned'])

if __name__=='__main__':unittest.main()
