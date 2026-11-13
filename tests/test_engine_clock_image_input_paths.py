"""Owned metadata fixtures for genuine Ubuntu merged-/usr directory/alias interaction."""
import copy
import unittest
try:
 from scripts.engine_clock_image_input_paths import project_package_member
except ImportError:project_package_member=None

class ImageInputPathTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(project_package_member,'merged-/usr projection missing');self.aliases={'bin':'usr/bin','sbin':'usr/sbin','lib':'usr/lib','lib64':'usr/lib64'}
 def test_real_alias_directory_and_payload_share_canonical_root_without_rewriting(self):
  alias={'path':'lib','kind':'symlink','target':'usr/lib','normalized_target':'usr/lib','mode':511,'nbytes':0}
  directory={'path':'lib','kind':'directory','mode':493,'nbytes':0}
  payload={'path':'lib/x86_64-linux-gnu/libunwind.so.8.0.1','kind':'file','mode':420,'nbytes':123,'sha256':'fixture-digest'}
  original=copy.deepcopy([alias,directory,payload]);self.assertIsNone(project_package_member(alias,self.aliases));self.assertEqual({**directory,'path':'usr/lib'},project_package_member(directory,self.aliases));self.assertEqual({**payload,'path':'usr/lib/x86_64-linux-gnu/libunwind.so.8.0.1'},project_package_member(payload,self.aliases));self.assertEqual(original,[alias,directory,payload])
 def test_link_target_projection_keeps_original_descriptor(self):
  for kind in ('symlink','hardlink'):
   row={'path':'lib64/loader','kind':kind,'target':'../lib/x86_64-linux-gnu/ld.so','normalized_target':'lib/x86_64-linux-gnu/ld.so','mode':511,'nbytes':0}
   self.assertEqual({**row,'path':'usr/lib64/loader','normalized_target':'usr/lib/x86_64-linux-gnu/ld.so'},project_package_member(row,self.aliases))
 def test_alias_root_changed_target_or_file_rejects(self):
  for row in ({'path':'lib','kind':'symlink','target':'/SECRET'},{'path':'lib','kind':'file'},{'path':'lib','kind':'hardlink','target':'usr/lib'}):
   with self.assertRaisesRegex(ValueError,'^INVALID_IMAGE_INPUT_PATH$'):project_package_member(row,self.aliases)
 def test_unsafe_path_or_unregistered_alias_rejects(self):
  for name in ('../SECRET','/lib/foo','lib//foo','lib/./foo','lib/../foo','lib\\foo','lib/\x00foo','lib/\ud800'):
   with self.assertRaisesRegex(ValueError,'^INVALID_IMAGE_INPUT_PATH$'):project_package_member({'path':name,'kind':'file'},self.aliases)
  for aliases in ({'lib':'/usr/lib'},{'lib':'SECRET'},{'etc':'usr/etc'}):
   with self.assertRaisesRegex(ValueError,'^INVALID_IMAGE_INPUT_PATH$'):project_package_member({'path':'usr/file','kind':'file'},aliases)
 def test_regular_canonical_payload_metadata_is_preserved(self):
  row={'path':'usr/lib/real.so','kind':'file','mode':420,'nbytes':37,'sha256':'distinct'};result=project_package_member(row,self.aliases);self.assertEqual(row,result);self.assertIsNot(row,result)

if __name__=='__main__':unittest.main()
