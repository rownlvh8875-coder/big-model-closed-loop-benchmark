"""Measured Docker28 version metadata as tiny synthetic DATA only."""
import copy,json,tempfile,time,unittest
from pathlib import Path
from tests.test_engine_clock_image_archive import make_save,rawjson,sha,TAG
from scripts import panda_sdk_routes_archive as previous
try:from scripts import panda_sdk_image_archive as a
except ImportError:a=None
class Docker28VersionMetadataTests(unittest.TestCase):
 def fixture(self,root,change=None):
  _,_,config=make_save(root);container=dict(Cmd=['/bin/sh','-c','#(nop) COPY CPU only']);created='2026-11-15T07:46:46Z';patch=dict(created=created,container_config=container,docker_version='28.0.4')
  nodes=[dict(id='1'*64,created='1970-01-01T00:00:00Z',container_config=copy.deepcopy(previous.EMPTY_COMPAT_CONTAINER),os='linux'),dict(id='2'*64,parent='1'*64,created=created,container_config=container,os='linux',architecture='amd64',config={**previous.EMPTY_COMPAT_CONTAINER,**config['config']},docker_version='28.0.4')]
  if change:change(nodes,patch)
  extras=[('blobs/sha256/'+sha(rawjson(x)),rawjson(x)) for x in nodes];return make_save(root,layout='oci',config_patch=patch,extra=extras)[0]
 def test_measured_head_version_field_matches_actual_config(self):
  self.assertIsNotNone(a,'versioned Docker28 metadata parser missing')
  with tempfile.TemporaryDirectory() as t:
   r=a.inspect_save_archive(self.fixture(Path(t)),expected_tag=TAG,deadline=time.perf_counter()+5);self.assertEqual(r['compatibility_metadata_files'],2);self.assertFalse(r['native_admission'])
 def test_mismatched_missing_foreign_version_or_other_extra_reject(self):
  self.assertIsNotNone(a)
  changes=[lambda n,p:n[-1].update(docker_version='29.0.0'),lambda n,p:n[-1].pop('docker_version'),lambda n,p:n[0].update(docker_version='28.0.4'),lambda n,p:n[-1].update(unexpected='value'),lambda n,p:(n[-1].update(docker_version=True),p.update(docker_version=True))]
  with tempfile.TemporaryDirectory() as t:
   for change in changes:
    f=self.fixture(Path(t),change)
    with self.subTest(change=change),self.assertRaises(ValueError):a.inspect_save_archive(f,expected_tag=TAG,deadline=time.perf_counter()+5)
if __name__=='__main__':unittest.main()
