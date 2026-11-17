"""Synthetic readback contracts only; never a hardware GPU PASS in CI."""
from pathlib import Path
import copy,subprocess,sys,unittest
try:from bigbench import laptop_gpu as g
except ImportError:g=None
class LaptopGpuContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(g,'Windows actual-context GPU probe missing')
 def fixture(self):
  name='NVIDIA GeForce RTX 3050 Ti Laptop GPU';colors=[[255,0,255,255],[0,255,0,255]];snap=dict(renderer=name+'/PCIe/SSE2',vendor='NVIDIA Corporation',version='4.6 unit',context=123,draw_fbo=7,samples=4,sample_buffers=1,max_samples=8,viewport=[0,0,8,8],gl_error_before=0,gl_error_after=0)
  return dict(protocol='windows-panda-gpu-readbacks-v1',device_names=[name],target_gpu=name,requested_samples=4,observations=[copy.deepcopy(snap),copy.deepcopy(snap)],images=[bytes(color*64).hex() for color in colors],challenges=colors,render_calls=2,cleanup_complete=True)
 def test_measured_hardware_and_every_challenged_pixel_are_required(self):
  r=g.verify_gpu_readbacks(self.fixture());self.assertTrue(r['passed']);self.assertEqual(r['actual_samples'],[4,4]);self.assertFalse(r['physical_optics_validated'])
 def test_software_or_other_adapter_cannot_borrow_nvidia_inventory(self):
  for renderer in ('llvmpipe','Intel UHD Graphics'):
   data=self.fixture()
   for snap in data['observations']:snap['renderer']=renderer
   r=g.verify_gpu_readbacks(data);self.assertFalse(r['passed'])
 def test_requested4_and_actual1_is_failed_msaa_even_when_pixels_match(self):
  data=self.fixture()
  for snap in data['observations']:snap['samples']=1
  self.assertFalse(g.verify_gpu_readbacks(data)['passed'])
 def test_bad_pixels_context_errors_or_missing_callback_do_not_pass(self):
  for kind in ('pixels','context','gl_error','missing','cleanup'):
   data=self.fixture()
   if kind=='pixels':data['images'][1]='00'*256
   elif kind=='context':data['observations'][1]['context']=0
   elif kind=='gl_error':data['observations'][1]['gl_error_after']=1282
   elif kind=='missing':data['observations'].pop()
   else:data['cleanup_complete']=False
   with self.subTest(kind=kind),self.assertRaises(ValueError):g.verify_gpu_readbacks(data)
 def test_cold_gpu_help_does_not_import_panda_or_ort(self):
  root=Path(__file__).resolve().parents[1];r=subprocess.run([sys.executable,'-I','-S','-B',str(root/'scripts/probe_laptop_gpu.py'),'--help'],capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__':unittest.main()
