"""Owned symlink fixtures only; never execute the pager or scan a host root."""
import tempfile,unittest
from pathlib import Path
from scripts import engine_clock_image_installer_v2 as i
class PagerAliasTests(unittest.TestCase):
 def root(self,tmp,target='/bin/more'):
  root=Path(tmp);(root/'usr/bin').mkdir(parents=True);(root/'usr/bin/more').write_bytes(b'owned nonexecutable test data');(root/'bin').symlink_to('usr/bin');(root/'etc/alternatives').mkdir(parents=True);(root/'etc/alternatives/pager').symlink_to(target);(root/'sealed').mkdir();return root
 def test_only_known_usrmerge_alias_is_canonicalized_and_original_link_kept(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=self.root(tmp);r=i.normalize_pager(root,root/'sealed/original-pager-link')
   self.assertEqual('/usr/bin/more',(root/'etc/alternatives/pager').readlink().as_posix());self.assertEqual('/bin/more',(root/'sealed/original-pager-link').readlink().as_posix());self.assertTrue(r['changed']);self.assertTrue(r['same_regular_target_observed'])
 def test_existing_canonical_link_is_not_moved(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=self.root(tmp,'/usr/bin/more');r=i.normalize_pager(root,root/'sealed/original-pager-link');self.assertFalse(r['changed']);self.assertFalse((root/'sealed/original-pager-link').is_symlink())
 def test_wrong_bin_alias_or_pager_target_rejects_without_modification(self):
  for change in ('bin','pager'):
   with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
    root=self.root(tmp)
    if change=='bin':(root/'bin').unlink();(root/'bin').symlink_to('/outside')
    else:(root/'etc/alternatives/pager').unlink();(root/'etc/alternatives/pager').symlink_to('/outside')
    with self.assertRaisesRegex(ValueError,'^IMAGE_INSTALL_REJECTED$'):i.normalize_pager(root,root/'sealed/original-pager-link')
    self.assertFalse((root/'sealed/original-pager-link').is_symlink())
if __name__=='__main__':unittest.main()
