import base64,copy,hashlib,importlib,json,unittest
from pathlib import Path
from tests.fixtures import panda_real_glx_cpu as core
class ObjectsTests(unittest.TestCase):
 def setUp(self):
  self.frames=importlib.import_module('scripts.panda_real_glx_frames');self.objects=importlib.import_module('scripts.panda_real_glx_objects');self.profile=importlib.import_module('scripts.panda_real_glx_profile')
 def frame(self,nonce,index,rgb=None):
  rgb=rgb or self.frames.challenge(nonce,index);raw=bytes(rgb)*64;return dict(index=index,nonce=nonce,width=8,height=8,channels=3,render_calls=2,ram_reads=1,nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())
 def test_two_fresh_challenges_have_large_channel_separation(self):
  n='a'*32;a=self.frames.challenge(n,0);b=self.frames.challenge(n,1);self.assertTrue(all(32<=v<=95 for v in a));self.assertEqual([v-u for u,v in zip(a,b)],[128]*3)
  self.assertNotEqual(a,self.frames.challenge('b'*32,0));self.frames.validate_frame(self.frame(n,0),n,0);self.frames.validate_frame(self.frame(n,1),n,1)
 def test_stale_wrong_shape_hash_budget_or_challenge_rejects(self):
  n='a'*32;good=self.frame(n,1)
  for field,value in [('nonce','b'*32),('index',0),('width',9),('nbytes',191),('sha256','0'*64),('render_calls',3),('ram_reads',2),('channels',4)]:
   bad=copy.deepcopy(good);bad[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):self.frames.validate_frame(bad,n,1)
  with self.assertRaises(ValueError):self.frames.validate_frame(self.frame(n,1,self.frames.challenge(n,0)),n,1)
 def test_one_quantization_step_allowed_but_larger_pixel_error_rejects(self):
  n='a'*32;rgb=self.frames.challenge(n,0);self.frames.validate_frame(self.frame(n,0,[v+1 for v in rgb]),n,0)
  with self.assertRaises(ValueError):self.frames.validate_frame(self.frame(n,0,[v+2 for v in rgb]),n,0)
 def test_real_object_api_requests_exact_pipe_two_render_calls_and_cleanup(self):
  r=self.objects.Renderer(core);setup=r.setup();self.assertEqual(core.GraphicsPipeSelection.module,'pandagl');self.assertEqual(setup['windows'],1);self.assertEqual(setup['driver']['renderer'],'softpipe');self.assertGreater(setup['objects']['texture']['pointer'],0)
  a=r.render([32,40,50]);self.assertEqual(a,bytes([32,40,50])*64);self.assertEqual(core.GraphicsEngine.last.renders,2);self.assertEqual(core.GraphicsEngine.last.syncs,2)
  b=r.render([160,168,178]);self.assertNotEqual(a,b);self.assertEqual(core.GraphicsEngine.last.renders,4)
  with self.assertRaises(ValueError):r.render([1,2,3])
  closed=r.close();self.assertEqual(closed,dict(windows_after=0,texture_ram_after=False,render_calls=4,ram_reads=2,cpp_deallocation_verified=False));self.assertEqual(core.GraphicsEngine.last.get_num_windows(),0)
 def test_wrong_driver_and_setup_failure_clean_owned_engine(self):
  from unittest.mock import patch
  r=self.objects.Renderer(core)
  with patch.object(core.GSG,'get_driver_renderer',return_value='llvmpipe'),self.assertRaises(ValueError):r.setup()
  self.assertEqual(r.close()['windows_after'],0)
 def test_fixed_profile_binds_sdk_tail_and_libgl_entry_without_loading(self):
  p=self.profile.make_profile();self.assertEqual(p['read_binding']['slot_vaddr'],830720);self.assertEqual(p['read_binding']['tail_vaddr'],248832);self.assertEqual(p['gl_profile']['functions']['glReadPixels']['vaddr'],363200);self.assertFalse(p['native_admitted']);self.assertEqual(p['sdk_sha256'],'8d302ae2a610b56db4f7feca08fd736004cf6d3d9650fdb9834f19389a0b7342')
if __name__=='__main__':unittest.main()
