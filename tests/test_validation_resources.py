"""Readiness cannot become actual scientific validation, even on a powerful laptop."""
from pathlib import Path
import copy,subprocess,sys,tempfile,unittest
try:from bigbench import validation_resources as v
except ImportError:v=None
class ResourceContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(v,'laptop readiness boundary is missing')
 def ready(self):return dict(system='Linux',machine='x86_64',wsl=False,memory_available_bytes=16*1024**3,disk_free_bytes=20*1024**3,gpu_devices=[{'name':'NVIDIA device'}],active_renderer=None,carla=dict(endpoint_configured=True,client_installed=True,dedicated_server=False),calibration=dict(manifest_exists=True,measured_provenance=False))
 def test_missing_resources_remain_blocked_and_never_pass(self):
  o=self.ready();o.update(gpu_devices=[],memory_available_bytes=None);o['carla'].update(endpoint_configured=False);o['calibration']['manifest_exists']=False;r=v.resource_readiness(o);self.assertEqual(r['full_s']['readiness'],'BLOCKED');self.assertEqual(r['hardware_gpu']['readiness'],'BLOCKED');self.assertEqual(r['carla']['readiness'],'BLOCKED');self.assertEqual(r['physical_optics']['readiness'],'BLOCKED');self.assertTrue(all(x['verification_status']=='NOT_RUN' for x in r.values()))
 def test_device_presence_is_only_readiness_not_active_gl_proof(self):
  r=v.resource_readiness(self.ready());self.assertEqual(r['hardware_gpu']['readiness'],'READY_FOR_PROBE');self.assertEqual(r['hardware_gpu']['verification_status'],'NOT_RUN')
 def test_software_or_unknown_renderer_never_passes_hardware_msaa(self):
  for name in ('softpipe','llvmpipe (LLVM 21)','SwiftShader','Microsoft Basic Render Driver',''):
   with self.subTest(name=name):self.assertFalse(v.actual_hardware_msaa(dict(renderer=name,vendor='Mesa',context_current=True,actual_samples=[4,4],requested_samples=4,device_bound=True))['passed'])
 def test_requested_msaa_is_not_promoted_over_actual_observation(self):
  base=dict(renderer='NVIDIA RTX',vendor='NVIDIA',context_current=True,actual_samples=[1,1],requested_samples=4,device_bound=True);self.assertFalse(v.actual_hardware_msaa(base)['passed']);base['actual_samples']=[4,4];self.assertTrue(v.actual_hardware_msaa(base)['passed'])
  for key,value in [('actual_samples',[]),('context_current',False),('device_bound',False),('actual_samples',[True,4])]:
   x=copy.deepcopy(base);x[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):v.actual_hardware_msaa(x)
 def test_physical_data_and_dedicated_server_are_required(self):
  o=self.ready();r=v.resource_readiness(o);self.assertEqual(r['physical_optics']['readiness'],'BLOCKED');self.assertEqual(r['carla']['readiness'],'BLOCKED');o['calibration']['measured_provenance']=True;o['carla']['dedicated_server']=True;r=v.resource_readiness(o);self.assertEqual(r['physical_optics']['readiness'],'READY_FOR_PROBE');self.assertEqual(r['carla']['readiness'],'READY_FOR_PROBE');self.assertTrue(all(x['verification_status']=='NOT_RUN' for x in r.values()))
 def test_endpoint_inputs_cannot_be_shell_commands_or_credentials(self):
  self.assertEqual(v.endpoint('localhost',2000),dict(host='localhost',port=2000))
  for host,port in [('user:pass@host',2000),('x;whoami',2000),('x',0),('x',True),('http://x',2000)]:
   with self.subTest(host=host),self.assertRaises(ValueError):v.endpoint(host,port)
 def test_windows_and_mac_do_not_claim_frozen_linux_sdk_compatibility(self):
  for system,machine in [('Windows','AMD64'),('Darwin','arm64')]:
   o=self.ready();o.update(system=system,machine=machine);r=v.resource_readiness(o);self.assertEqual(r['full_s']['readiness'],'BLOCKED');self.assertIn('LINUX_X86_64_RUNTIME_REQUIRED',r['full_s']['missing'])
 def test_container_memory_headroom_cannot_be_replaced_by_host_memory(self):
  self.assertEqual(v.effective_memory(64,32,8,3),(8,5));self.assertEqual(v.effective_memory(64,4,8,3),(8,4));self.assertEqual(v.effective_memory(64,32,None,None),(64,32))
 def test_cli_is_cold_and_missing_carla_does_not_import_simulator(self):
  path=Path(__file__).resolve().parents[1]/'scripts/validate_laptop_environment.py';r=subprocess.run([sys.executable,'-I','-S','-B',str(path),'--help'],capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__':unittest.main()
