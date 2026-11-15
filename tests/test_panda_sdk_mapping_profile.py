"""Exact SDK bytes and synthetic request API fixtures, never load the SDK."""
import copy,json,struct,tempfile,unittest
from pathlib import Path
try:
 from scripts import panda_sdk_mapping_profile as profile
 from scripts import panda_sdk_mapping_policy as p
except ImportError:profile=p=None
class MappingProfileTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(profile,'new image-bound mapping profile required')
 def test_four_export_code_ranges_scalar_sizes_and_stats_layout(self):
  r=profile.make_profile((profile.ROOT/profile.SDK).read_bytes());self.assertEqual(set(r['functions']),{'pca_context_size','rc_context_size','psd_get_stats','psd_source_idle'});self.assertEqual(r['expected_sizes'],{'pca_context_size':2640344,'rc_context_size':2320});self.assertEqual(r['stats_size'],48);self.assertEqual(len(r['call_sequence']),5);self.assertFalse(r['native_admitted'])
 def test_foreign_sdk_and_scalar_opcode_cannot_define_profile(self):
  raw=bytearray((profile.ROOT/profile.SDK).read_bytes());raw[-1]^=1
  with self.assertRaises(ValueError):profile.make_profile(bytes(raw))
  for raw in [b'\xb8\x01\0\0\0\xc2',b'\xb8'+b'\xff'*4+b'\xc3',b'CPU']:
   with self.assertRaises(ValueError):profile.scalar_size(raw)
 def test_loader_profile_does_not_use_section_headers(self):
  raw=bytearray((profile.ROOT/profile.SDK).read_bytes());a=profile.export_ranges(bytes(raw));struct.pack_into('<Q',raw,40,0);struct.pack_into('<HHH',raw,58,0,0,0);self.assertEqual(a,profile.export_ranges(bytes(raw)))
 def test_closed_request_new_window_cannot_expand_or_replay(self):
  r=p.request_template('a'*40,[dict(event='push',run_id=101),dict(event='pull_request',run_id=102)],p.ROOT);p.validate_request(r,p.ROOT)
  for key,value in [('branch','diagnostic/engine-clock-sealed-native-20261114-02'),('permissions',dict(native_admission=True)),('sdk_sha256','0'*64),('budget',dict(mapping_windows=2))]:
   with self.assertRaises(ValueError):p.validate_request(dict(r,**{key:value}),p.ROOT)
  bad=copy.deepcopy(r);bad['source_closure'][p.PROFILE]='0'*64
  with self.assertRaises(ValueError):p.validate_request(bad,p.ROOT)
 def test_current_image_and_new_source_manifest_are_pinned(self):
  r=p.image_authority(p.ROOT);self.assertEqual(r['archive']['image_tar_sha256'],'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698');self.assertEqual(r['sdk_sha256'],profile.SDK_SHA);self.assertFalse(r['native_admitted']);self.assertEqual(len(p.expected_inventory(p.ROOT)['entries']),44232)
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);q=root/p.AUTH;q.parent.mkdir(parents=True);q.write_bytes((p.ROOT/p.AUTH).read_bytes()+b'\n')
   with self.assertRaisesRegex(ValueError,'image authority pin'):p.image_authority(root)
 def test_workflow_is_new_one_use_push_and_no_model_dispatch(self):
  s=(p.ROOT/p.WORKFLOW).read_text();self.assertIn("branches: ['"+p.BRANCH+"']",s);self.assertIn('scripts/run_panda_sdk_mapping_canary.py --run',s);self.assertNotIn('workflow_dispatch',s);self.assertNotIn('id-token: write',s);self.assertIn('persist-credentials: false',s)
if __name__=='__main__':unittest.main()
