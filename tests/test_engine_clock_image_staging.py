"""Owned archive inputs only; never contact publishers or execute their content."""
import hashlib,io,tarfile,tempfile,time,unittest
from pathlib import Path
try:from scripts import engine_clock_image_staging as s
except ImportError:s=None
class StagingTests(unittest.TestCase):
 def test_python_archive_matches_closed_manifest_before_any_extraction(self):
  self.assertIsNotNone(s)
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'python.tar.gz'
   with tarfile.open(p,'w:gz') as out:
    t=tarfile.TarInfo('bin/owned');t.mode=0o755;t.size=4;out.addfile(t,io.BytesIO(b'data'))
   entries=[{'path':'bin/owned','kind':'file','mode':0o755,'nbytes':4,'sha256':hashlib.sha256(b'data').hexdigest()}]
   self.assertEqual('PYTHON_ARCHIVE_MEMBERS_MATCH',s.verify_python_archive(p,entries,deadline=time.perf_counter()+10)['status'])
   entries[0]['sha256']='0'*64
   with self.assertRaisesRegex(ValueError,'^IMAGE_STAGING_REJECTED$'):s.verify_python_archive(p,entries,deadline=time.perf_counter()+10)
if __name__=='__main__':unittest.main()
