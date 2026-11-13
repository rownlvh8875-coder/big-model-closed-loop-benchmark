"""Owned caller-root candidate/prefix fixtures; no host root scan or package import."""
import copy
import hashlib
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from scripts import engine_clock_runtime_inventory as core
try:
 from scripts import engine_clock_image_inventory as image
except ImportError:image=None

def tree(root):
 for name in ('etc','usr/lib','usr/lib64','opt/python','opt/venv'): (root/name).mkdir(parents=True,exist_ok=True)
 (root/'lib').symlink_to('usr/lib');(root/'lib64').symlink_to('usr/lib64')
 for name in ('hostname','hosts','resolv.conf'):(root/'etc'/name).write_text('owned runtime metadata')
 (root/'etc/mtab').symlink_to('/proc/mounts')

def put(root,name,data=b'abc',mode=0o640):
 p=root/name.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(mode);return p

def prefix_tree(root):
 tree(root);members={}
 for name,data in [('bin/python3.11',b'owned interpreter fixture'),('lib/libpython3.11.so.1.0',b'owned library fixture'),('lib/python3.11/os.py',b'owned stdlib fixture')]:
  p=put(root,'opt/python/'+name,data,0o755 if name.startswith('bin/') else 0o644);members[name]={'nbytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
 put(root,'opt/venv/bin/python',b'owned interpreter fixture',0o755)
 parent=root/'opt/hostedtoolcache/Python/3.11.18';parent.mkdir(parents=True);(parent/'x64').symlink_to('/opt/python')
 obs={'python_version':'3.11.18','executable':'/opt/venv/bin/python','executable_realpath':'/opt/venv/bin/python','stdlib_realpath':'/opt/python/lib/python3.11/os.py','loaded_libpython_realpaths':['/opt/python/lib/libpython3.11.so.1.0'],'isolated':True,'no_site':True,'dont_write_bytecode':True,'imported_forbidden':[]}
 return members,obs

class ImageCandidateInventoryTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(image,'isolated image inventory producer missing')
 def candidate(self,root):return image.create_inventory(root,deadline=time.perf_counter()+10)
 def test_candidate_covers_real_aliases_exclusions_modes_empty_bytes_without_admission(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tree(root);put(root,'usr/a.so');put(root,'usr/empty',b'');before=core._Collector.matched;r=self.candidate(root)
   self.assertEqual('CANDIDATE_INSTALLED_MANIFEST_COLLECTED',r['status']);self.assertTrue(r['complete']);self.assertFalse(r['native_admission']);self.assertFalse(r['installed_runtime_verified']);self.assertEqual(3,r['bytes_read']);self.assertIs(before,core._Collector.matched)
   m=r['inventory'];self.assertEqual(m,core.validate_inventory(m));self.assertIn('/usr/lib',m['roots']);self.assertIn('/usr/lib64',m['roots']);self.assertNotIn('/etc/hosts',[v['path'] for v in m['entries']]);self.assertEqual({'/lib','/lib64','/usr/a.so','/usr/empty'},{v['path'] for v in m['entries']})
   verified=image.verify_inventory(root,m,deadline=time.perf_counter()+10);self.assertEqual('INSTALLED_FILES_MATCH',verified['status']);self.assertFalse(verified['native_admission'])
 def test_changed_or_extra_payload_after_candidate_rejects_verification(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tree(root);p=put(root,'usr/file');r=self.candidate(root);p.write_bytes(b'xyz');v=image.verify_inventory(root,r['inventory'],deadline=time.perf_counter()+10);self.assertFalse(v['complete']);self.assertIsNone(v['inventory'])
 def test_escaping_symlink_or_special_file_fails_without_following_it(self):
  for kind in ('link','fifo'):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);tree(root)
    if kind=='link':(root/'usr/link').symlink_to('/SECRET_SENTINEL')
    else:os.mkfifo(root/'usr/pipe')
    r=self.candidate(root);self.assertEqual('FAILED_OR_INCOMPLETE',r['status']);self.assertFalse(r['complete']);self.assertIsNone(r['inventory']);self.assertNotIn('SECRET_SENTINEL',r['error_code'])
 def test_file_and_aggregate_limits_stop_before_excess_payload_hashing(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tree(root);put(root,'usr/a',b'abc');put(root,'usr/b',b'def')
   for key,value,max_read in [('MAX_FILE_BYTES',2,0),('MAX_INSTALLED_BYTES',5,3),('MAX_NODES',3,0),('MAX_READ_BYTES',2,2),('MAX_JSON_BYTES',10,6)]:
    with self.subTest(limit=key),patch.object(core,key,value):
     r=self.candidate(root);self.assertFalse(r['complete']);self.assertIsNone(r['inventory']);self.assertLessEqual(r['bytes_read'],max_read)
 def test_mutation_between_real_scan_passes_cannot_create_a_candidate(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tree(root);p=put(root,'usr/file');original=image._Candidate.scan
   def mutate(collector,rootfd,expected,read_payload):
    graph=original(collector,rootfd,expected,read_payload)
    if read_payload:p.write_bytes(b'xyz')
    return graph
   with patch.object(image._Candidate,'scan',mutate):r=self.candidate(root)
   self.assertFalse(r['complete']);self.assertIsNone(r['inventory']);self.assertFalse(r['native_admission'])
 def test_expired_deadline_never_returns_a_candidate(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tree(root);r=image.create_inventory(root,deadline=0);self.assertFalse(r['complete']);self.assertEqual(0,r['bytes_read'])
 def test_prefix_uses_caller_root_literal_alias_and_verified_canonical_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);members,obs=prefix_tree(root);r=image.verify_prefix(root,obs,expected_members=members);self.assertEqual('PREFIX_LAYOUT_AND_OBSERVATION_MATCH',r['status']);self.assertFalse(r['external_container_origin_authenticated']);self.assertFalse(r['native_admission'])
   for change in ({'python_version':'3.11.17'},{'loaded_libpython_realpaths':['/usr/lib/SECRET.so']},{'imported_forbidden':['onnxruntime']},{'no_site':False}):
    with self.assertRaisesRegex(ValueError,'^IMAGE_PREFIX_REJECTED$'):image.verify_prefix(root,{**obs,**change},expected_members=members)
 def test_prefix_rejects_alias_or_parent_substitution_and_changed_runtime_bytes(self):
  for mutation in ('alias','parent_mode','library'):
   with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);members,obs=prefix_tree(root)
    if mutation=='alias':p=root/'opt/hostedtoolcache/Python/3.11.18/x64';p.unlink();p.symlink_to('/SECRET')
    elif mutation=='parent_mode':(root/'opt/hostedtoolcache').chmod(0o777)
    else:(root/'opt/python/lib/libpython3.11.so.1.0').write_bytes(b'changed')
    with self.assertRaisesRegex(ValueError,'^IMAGE_PREFIX_REJECTED$'):image.verify_prefix(root,obs,expected_members=members)

if __name__=='__main__':unittest.main()
