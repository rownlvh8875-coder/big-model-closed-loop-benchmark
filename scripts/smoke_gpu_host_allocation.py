"""Hosted Linux software API smoke only; never Windows/RTX/MSAA pixel qualification."""
from pathlib import Path
import argparse,json,sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def run():
 import platform
 if platform.system()!='Linux':raise ValueError('separate Linux software API smoke only')
 from contextlib import ExitStack
 import panda3d.core as core
 from direct.showbase.ShowBase import ShowBase
 from bigbench.laptop_gpu import _allocate_msaa_output
 if core.PandaSystem.getVersionString()!='1.10.13':raise ValueError('stock Panda1.10.13 required')
 core.loadPrcFileData('host-allocation-smoke','window-type none\naudio-library-name null\nsync-video false\nthreading-model\n')
 base=None;result=None;engine=None
 try:
  base=ShowBase(windowType='none');base.makeDefaultPipe();engine=base.graphicsEngine;initial_count=engine.getNumWindows()
  with ExitStack() as owners:
   output,allocation=_allocate_msaa_output(base,core,4,owners);base.win=output;engine.renderFrame();engine.syncFrame();gsg=output.getGsg();renderer=gsg.getDriverRenderer()
   if 'llvmpipe' not in renderer.lower():raise ValueError('explicit llvmpipe software renderer required')
   samples=output.getFbProperties().getMultisamples()
   if samples<4 or output.getXSize()!=8 or output.getYSize()!=8:raise ValueError('requested stock-Panda software output not allocated')
   result=dict(protocol='stock-panda-host-allocation-api-smoke-v2',framebuffer_allocation=allocation,software_api_smoke_passed=True,renderer=renderer,vendor=gsg.getDriverVendor(),version=gsg.getDriverVersion(),requested_samples=4,framework_reported_samples=samples,source_entry=str(Path(__file__).resolve()),real_render_calls=1,official_model_processes=0,inferences=0,windows_wgl_qualified=False,hardware_gpu_qualified=False,model_camera_qualified=False,physical_optics_validated=False,carla_validated=False,scope='actual Linux stock-Panda allocation and ownership API only; sample property is not GL pixel/MSAA certification')
  remaining=engine.getNumWindows()
  if remaining!=initial_count:raise RuntimeError('owned outputs remain before ShowBase destroy fallback')
  result.update(ownership_checked_before_base_destroy=True,initial_window_count=initial_count,window_count_after_owned_cleanup=remaining)
 finally:
  if base is not None:base.destroy()
 if result is None or engine is None or engine.getNumWindows()!=0:raise RuntimeError('owned software outputs were not removed')
 result['owned_outputs_removed']=True;return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if not a.run:p.error('--run required for the actual software context')
 try:result=run()
 except Exception as e:result=dict(status='ERROR',software_api_smoke_passed=False,error=type(e).__name__+': '+str(e),hardware_gpu_qualified=False,official_model_processes=0,inferences=0)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');return 0 if result.get('software_api_smoke_passed') else 2
if __name__=='__main__':raise SystemExit(main())
