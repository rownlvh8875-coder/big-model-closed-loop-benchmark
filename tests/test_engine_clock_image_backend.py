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


 def test_exhausted_normal_deadline_still_stops_and_establishes_final_state(self):
  calls=[]
  def capture(argv,out,**kw):
   calls.append(argv)
   raw=b'{"Status":"exited","Running":false,"ExitCode":137}' if 'inspect' in argv else b''
   return {'status':'EXITED','returncode':0,'streams_complete':True,'_stdout':raw,'_stderr':b''}
  with tempfile.TemporaryDirectory() as tmp,patch.object(b.process,'capture',side_effect=capture):
   e=b.Docker(Path(tmp),deadline=b.time.perf_counter()+30);e.deadline=b.time.perf_counter()-1
   result=e.terminate('a'*64)
   self.assertTrue(result['stopped_state_established']);self.assertTrue(any('stop' in c for c in calls));self.assertTrue(any('inspect' in c for c in calls))
 def test_changed_actual_venv_executable_never_reaches_start(self):
  from scripts import engine_clock_image_preparation as p
  from test_engine_clock_image_archive import launch_fixture
  cid='b'*64;image='sha256:'+'4'*64;calls=[]
  with tempfile.TemporaryDirectory() as tmp:
   e=b.Docker(Path(tmp),deadline=b.time.perf_counter()+30,source_root=Path(__file__).resolve().parent.parent);e.host={}
   def call(args,**kw):
    calls.append(args)
    if args[0]=='create':return {'_stdout':cid.encode(),'_stderr':b''}
    self.fail('start reached before executable authentication')
   def normalize(raw,expected,nonce):
    result=launch_fixture(image,nonce);result['labels']['stage7.source']='1'*40;return result
   def copied(cid,remote,*args,**kw):
    if remote=='/opt/venv/bin/python':raise ValueError('IMAGE_EXECUTABLE_REJECTED')
    return {'status':'CLOSED_COPIED_TREE_MATCH'}
   with patch.object(e,'call',side_effect=call),patch.object(e,'json',return_value=[{}]),patch.object(p,'normalize_launch',side_effect=normalize),patch.object(e,'copied_tree',side_effect=copied):
    with self.assertRaisesRegex(ValueError,'^IMAGE_EXECUTABLE_REJECTED$'):
     e.collect({'config_digest':image},{'request_id':'owned','reviewed_source_sha':'1'*40},expected_manifest=b'{}',precheck=True)
   self.assertFalse(any(c[0]=='start' for c in calls))

if __name__=='__main__':unittest.main()
