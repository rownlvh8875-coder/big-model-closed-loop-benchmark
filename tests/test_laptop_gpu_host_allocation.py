"""Fake WGL allocation/ownership only. No actual Panda/GL or hardware PASS."""
from contextlib import ExitStack
from types import ModuleType,SimpleNamespace
from unittest.mock import Mock,patch
import sys,unittest
from bigbench import laptop_gpu as g

class DrawBoundary(RuntimeError):pass
class CleanupFailure(RuntimeError):pass
class OpenFailure(RuntimeError):pass

class WglHarness:
 def __init__(self,mode='draw',samples=4):
  self.mode=mode;self.samples=samples;self.events=[];self.requests=[];self.outputs=[];self.opens=0;self.draws=0;self.original_callback=object();h=self
  class FB:
   def setRgbColor(self,v):self.rgb=v
   def setRgbaBits(self,*v):self.rgba=v
   def setDepthBits(self,v):self.depth=v
   def setMultisamples(self,v):self.samples=v
  class Output:
   def __init__(self,role):self.role=role;self.opened=False;self.active=True
   def isValid(self):return self.opened
   def getGsg(self):return None if h.mode=='null_gsg' else h.alternate_gsg if self.role=='canary' and h.mode=='alternate_target' else h.gsg
   def getType(self):return SimpleNamespace(getName=lambda:'wglGraphicsBuffer' if self.role=='host' or h.mode=='alternate_target' else 'GLGraphicsBuffer')
   def getFbProperties(self):return SimpleNamespace(getMultisamples=lambda:h.samples)
   def getXSize(self):return 8
   def getYSize(self):return 8
   def isActive(self):return self.active
   def setActive(self,value):self.active=value;h.events.append('inactive_'+self.role)
   def setClearColorActive(self,value):pass
   def setClearColor(self,value):pass
   def addRenderTexture(self,*args):pass
  class Engine:
   def makeOutput(self,*args):
    fb=args[3];h.requests.append(fb.samples);h.events.append('allocate_'+str(fb.samples));assert fb.rgba==(8,8,8,8) and fb.depth==24 and args[4]==(8,8)
    if fb.samples==0:
     if h.mode=='host_null':return None
     output=Output('host');h.host=output
    else:
     # Mirrors the real WGL FBO requirement. An unhosted MSAA call fails.
     if len(args)!=8 or args[6] is not h.gsg or args[7] is not getattr(h,'host',None):return None
     assert h.host.opened and not h.host.active,'host must be initialized and inactive before target'
     if h.mode=='target_null':return None
     output=Output('canary')
    h.outputs.append(output);return output
   def openWindows(self):
    h.opens+=1;h.events.append('open_'+str(h.opens))
    if h.mode=='open_host_fail' and h.opens==1 or h.mode=='open_target_fail' and h.opens==2:raise OpenFailure('owned output open failure')
    for output in h.outputs:output.opened=True
   def removeWindow(self,output):
    h.events.append('remove_'+output.role)
    if h.mode=='remove_canary_fail' and output.role=='canary':raise CleanupFailure('remove failure')
    h.outputs.remove(output)
   def renderFrame(self):h.draws+=1;h.events.append('draw');raise DrawBoundary('original shader draw path reached')
  class Region:
   def __init__(self):self.callback=h.original_callback
   def getDrawCallback(self):return self.callback
   def setDrawCallback(self,value):
    if value is h.original_callback:
     h.events.append('callback_restored')
     if h.mode=='restore_callback_fail':raise CleanupFailure('callback restore failure')
    else:h.events.append('callback_installed')
    self.callback=value
   def clearDrawCallback(self):self.callback=None
  class Base:
   def __init__(self,windowType):assert windowType=='none';self.pipe=object();self.graphicsEngine=Engine();self.render2d=Mock();self.cam2d=Mock();h.region=Region();self.cam2d.node.return_value.getDisplayRegion.return_value=h.region;h.base=self
   def makeDefaultPipe(self):h.events.append('default_pipe')
   def makeCamera2d(self,win):h.events.append('camera_canary')
   def destroy(self):h.events.append('base_destroyed');h.outputs.clear()
  self.gsg=SimpleNamespace(this=101,isValid=lambda:self.mode!='invalid_gsg',getDriverRenderer=lambda:'llvmpipe UNIT',getDriverVendor=lambda:'Mesa UNIT',getDriverVersion=lambda:'unit');self.alternate_gsg=SimpleNamespace(this=202,isValid=lambda:True);core=ModuleType('panda3d.core');self.core=core
  for name in ('Texture','CardMaker','Shader','GeomVertexData','GeomVertexFormat','GeomVertexWriter','GeomTriangles','Geom','GeomNode'):setattr(core,name,Mock())
  core.FrameBufferProperties=FB;core.WindowProperties=SimpleNamespace(size=lambda *args:args);core.GraphicsPipe=SimpleNamespace(BFRefuseWindow=1);core.GraphicsOutput=SimpleNamespace(RTMCopyRam=1,RTPColor=2);core.AntialiasAttrib=SimpleNamespace(MMultisample=1,MNone=0);core.CallbackObject=SimpleNamespace(make=lambda fn:fn);core.PandaSystem=SimpleNamespace(getVersionString=lambda:'1.10.13');core.loadPrcFileData=Mock();self.Base=Base
 def modules(self):
  panda=ModuleType('panda3d');panda.__path__=[];panda.core=self.core;direct=ModuleType('direct');direct.__path__=[];showbase=ModuleType('direct.showbase');showbase.__path__=[];entry=ModuleType('direct.showbase.ShowBase');entry.ShowBase=self.Base
  return {'panda3d':panda,'panda3d.core':self.core,'direct':direct,'direct.showbase':showbase,'direct.showbase.ShowBase':entry}
 def run(self):
  with patch.dict(sys.modules,self.modules()),patch.object(g.platform,'system',return_value='Windows'),patch.object(g,'collect_resources',return_value={'gpu_devices':[{'name':g.TARGET}]}),patch.object(g,'_gl_reader',return_value=lambda:{}):return g.run_gpu_probe(requested_samples=self.samples)

class HostAllocationContracts(unittest.TestCase):
 def test_missing_windows_resources_stay_blocked_under_new_attempt_revision(self):
  with patch.object(g.platform,'system',return_value='Linux'),patch.object(g,'collect_resources',return_value={'gpu_devices':[]}):r=g.run_gpu_probe()
  self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['protocol'],'windows-panda-gpu-attempt-v2');self.assertFalse(r['model_loaded'])
 def test_original_draw_requires_initialized_inactive_host_and_same_gsg(self):
  h=WglHarness()
  with self.assertRaises(DrawBoundary):h.run()
  self.assertEqual(h.requests,[0,4]);self.assertEqual(h.opens,2);self.assertEqual(h.draws,1);self.assertFalse(h.outputs)
 def test_valid_alternative_target_records_actual_type_and_unshared_gsg(self):
  self.assertNotIn('FBO',g.CONSTRUCTION)
  h=WglHarness('alternate_target');base=h.Base(windowType='none');base.makeDefaultPipe()
  try:
   with ExitStack() as owners:
    output,allocation=g._allocate_msaa_output(base,h.core,4,owners);self.assertEqual(allocation['observed_canary_type'],'wglGraphicsBuffer');self.assertEqual(allocation['observed_host_type'],'wglGraphicsBuffer');self.assertFalse(allocation['canary_shares_host_gsg']);self.assertEqual(allocation['canary_requested_samples'],4);self.assertTrue(allocation['host_inactive'])
  finally:base.destroy()
 def test_failed_host_does_not_attempt_canary(self):
  h=WglHarness('host_null')
  with self.assertRaisesRegex(RuntimeError,'host'):h.run()
  self.assertEqual(h.requests,[0]);self.assertEqual(h.draws,0);self.assertIn('base_destroyed',h.events)
 def test_null_or_invalid_host_gsg_is_cleaned_before_target_attempt(self):
  for mode in ('null_gsg','invalid_gsg'):
   h=WglHarness(mode)
   with self.subTest(mode=mode),self.assertRaisesRegex(RuntimeError,'GSG'):h.run()
   self.assertEqual(h.requests,[0]);self.assertIn('remove_host',h.events);self.assertIn('base_destroyed',h.events)
 def test_failed_target_never_retries_lower_samples(self):
  for samples in (2,4,8,64):
   h=WglHarness('target_null',samples)
   with self.subTest(samples=samples),self.assertRaisesRegex(RuntimeError,'canary'):h.run()
   self.assertEqual(h.requests,[0,samples]);self.assertIn('remove_host',h.events);self.assertEqual(h.draws,0)
 def test_open_failures_release_every_allocated_output(self):
  for mode,expected in (('open_host_fail',['remove_host']),('open_target_fail',['remove_canary','remove_host'])):
   h=WglHarness(mode)
   with self.subTest(mode=mode),self.assertRaises(OpenFailure):h.run()
   self.assertEqual([v for v in h.events if v.startswith('remove_')],expected);self.assertIn('base_destroyed',h.events)
 def test_draw_failure_restores_callback_before_canary_host_base_cleanup(self):
  h=WglHarness()
  with self.assertRaises(DrawBoundary):h.run()
  self.assertEqual(h.events[-4:],['callback_restored','remove_canary','remove_host','base_destroyed']);self.assertIs(h.region.callback,h.original_callback)
 def test_callback_restoration_failure_still_disposes_outputs_and_base(self):
  h=WglHarness('restore_callback_fail')
  with self.assertRaises(CleanupFailure):h.run()
  self.assertEqual(h.events[-4:],['callback_restored','remove_canary','remove_host','base_destroyed'])
 def test_output_disposal_failure_still_attempts_host_and_base_cleanup(self):
  h=WglHarness('remove_canary_fail')
  with self.assertRaises(CleanupFailure):h.run()
  self.assertEqual(h.events[-3:],['remove_canary','remove_host','base_destroyed'])
class NativeSmokeColdContracts(unittest.TestCase):
 def test_cold_smoke_help_does_not_import_panda_or_create_outputs(self):
  from pathlib import Path
  import subprocess
  entry=Path(__file__).resolve().parents[1]/'scripts/smoke_gpu_host_allocation.py';result=subprocess.run([sys.executable,'-I','-S','-B',str(entry),'--help'],capture_output=True,text=True,timeout=10);self.assertEqual(result.returncode,0,result.stderr)
class NativeOwnershipEvidenceContracts(unittest.TestCase):
 def smoke(self,omit):
  from scripts import smoke_gpu_host_allocation as smoke
  h=WglHarness();parent=h.Base
  class SmokeBase(parent):
   def __init__(self,windowType):
    super().__init__(windowType);self.graphicsEngine.renderFrame=lambda:None;self.graphicsEngine.syncFrame=lambda:None;self.graphicsEngine.getNumWindows=lambda:len(h.outputs)
  h.Base=SmokeBase;actual=g._allocate_msaa_output
  def allocate(base,core,samples,owners):
   class IncompleteOwner:
    def callback(self,fn,output):
     if output.role!=omit:owners.callback(fn,output)
   return actual(base,core,samples,IncompleteOwner())
  with patch.dict(sys.modules,h.modules()),patch('platform.system',return_value='Linux'),patch.object(g,'_allocate_msaa_output',side_effect=allocate):return smoke.run(),h
 def test_missing_owner_callback_is_rejected_before_working_base_fallback(self):
  for omit in ('host','canary'):
   with self.subTest(omit=omit),self.assertRaisesRegex(RuntimeError,'before ShowBase'):self.smoke(omit)
 def test_complete_owner_cleanup_is_checked_before_base_fallback(self):
  report,h=self.smoke(None);self.assertTrue(report['ownership_checked_before_base_destroy']);self.assertEqual(report['initial_window_count'],report['window_count_after_owned_cleanup']);self.assertEqual(report['window_count_after_owned_cleanup'],0);self.assertFalse(h.outputs);self.assertIn('base_destroyed',h.events)
if __name__=='__main__':unittest.main()
