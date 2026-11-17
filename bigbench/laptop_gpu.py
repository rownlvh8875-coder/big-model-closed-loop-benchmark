"""Windows stock-Panda framebuffer probe; no model or physical optics claims."""
import platform
from bigbench.validation_resources import SOFTWARE,actual_hardware_msaa,collect_resources
TARGET='NVIDIA GeForce RTX 3050 Ti Laptop GPU'
COLORS=[[255,0,255,255],[0,255,0,255]]

def verify_gpu_readbacks(data):
 if data.get('protocol')!='windows-panda-gpu-readbacks-v1':raise ValueError('GPU readback protocol')
 snaps=data.get('observations');images=data.get('images');colors=data.get('challenges');requested=data.get('requested_samples')
 if not isinstance(snaps,list) or len(snaps)!=2 or not isinstance(images,list) or len(images)!=2 or colors!=COLORS or data.get('render_calls')!=2 or data.get('cleanup_complete') is not True:raise ValueError('two complete rendered challenges and cleanup required')
 if type(requested) is not int or not 2<=requested<=64:raise ValueError('requested sample count')
 names=data.get('device_names');target=data.get('target_gpu')
 if not isinstance(names,list) or not all(isinstance(n,str) for n in names) or target!=TARGET:raise ValueError('target device inventory required')
 bound=any(target.lower() in n.lower() for n in names);hardware=True;samples=[]
 for snap,color,image in zip(snaps,colors,images):
  if not isinstance(snap,dict) or type(snap.get('context')) is not int or snap['context']<=0 or type(snap.get('draw_fbo')) is not int or snap['draw_fbo']<0 or snap.get('viewport')!=[0,0,8,8] or snap.get('gl_error_before')!=0 or snap.get('gl_error_after')!=0:raise ValueError('current measured framebuffer and clean GL state required')
  if not isinstance(image,str) or image!=bytes(color*64).hex():raise ValueError('actual RAM image must match every challenged RGBA pixel')
  for key in ('samples','sample_buffers','max_samples'):
   if type(snap.get(key)) is not int or not 0<=snap[key]<=64:raise ValueError('actual GL integer measurement required')
  for key in ('renderer','vendor','version'):
   if not isinstance(snap.get(key),str) or not snap[key].strip():raise ValueError('actual GL strings required')
  renderer=snap['renderer'].lower();bound=bound and target.lower() in renderer and 'nvidia' in snap['vendor'].lower();hardware=hardware and not any(s in renderer for s in SOFTWARE)
  hardware=hardware and snap['sample_buffers']>=1 and snap['max_samples']>=requested;samples.append(snap['samples'])
 for key in ('renderer','vendor','version','context','draw_fbo'):
  if snaps[0][key]!=snaps[1][key]:raise ValueError('challenge framebuffer identity changed')
 measured=actual_hardware_msaa(dict(context_current=True,device_bound=True,renderer=snaps[0]['renderer'],vendor=snaps[0]['vendor'],actual_samples=samples,requested_samples=requested))
 return dict(protocol='windows-panda-hardware-msaa-validation-v1',passed=bool(bound and hardware and measured['passed']),device_bound=bound,hardware_renderer=hardware,actual_samples=samples,requested_samples=requested,physical_optics_validated=False,carla_validated=False,model_loaded=False,scope='Windows stock Panda 1.10.13, measured 8x8 framebuffer only; does not qualify Linux SDK3 or the model camera pipeline')

def _gl_reader():
 import ctypes
 gl=ctypes.WinDLL('opengl32');gl.wglGetCurrentContext.restype=ctypes.c_void_p;gl.glGetString.argtypes=[ctypes.c_uint];gl.glGetString.restype=ctypes.c_char_p;gl.glGetIntegerv.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_int)];gl.glGetError.restype=ctypes.c_uint
 def integer(key,count=1):
  values=(ctypes.c_int*count)();gl.glGetIntegerv(key,values);return list(values) if count>1 else values[0]
 def read():
  before=gl.glGetError();r=dict(context=int(gl.wglGetCurrentContext() or 0),renderer=(gl.glGetString(0x1F01) or b'').decode('ascii','replace'),vendor=(gl.glGetString(0x1F00) or b'').decode('ascii','replace'),version=(gl.glGetString(0x1F02) or b'').decode('ascii','replace'),draw_fbo=integer(0x8CA6),samples=integer(0x80A9),sample_buffers=integer(0x80A8),max_samples=integer(0x8D57),viewport=integer(0x0BA2,4),gl_error_before=before);r['gl_error_after']=gl.glGetError();return r
 return read

def run_gpu_probe(*,requested_samples=4):
 observation=collect_resources();names=[x['name'] for x in observation['gpu_devices'] if x.get('name')]
 blocked=[]
 if platform.system()!='Windows':blocked.append('WINDOWS_NATIVE_CONTEXT_REQUIRED')
 if not any(TARGET.lower() in n.lower() for n in names):blocked.append('RTX3050TI_DEVICE_NOT_OBSERVED')
 if blocked:return dict(protocol='windows-panda-gpu-attempt-v1',status='BLOCKED',missing=blocked,passed=False,resource_observation=observation,model_loaded=False)
 if type(requested_samples) is not int or not 2<=requested_samples<=64:raise ValueError('samples2..64 required')
 from panda3d.core import PandaSystem,loadPrcFileData,FrameBufferProperties,WindowProperties,GraphicsPipe,Texture,GraphicsOutput,CardMaker,Shader,CallbackObject
 if PandaSystem.getVersionString()!='1.10.13':raise ValueError('Windows stock Panda 1.10.13 required; Linux SDK3 cannot qualify this context')
 loadPrcFileData('laptop-gpu-probe','window-type none\naudio-library-name null\nsync-video false\nthreading-model\nframebuffer-srgb false\n')
 from direct.showbase.ShowBase import ShowBase
 base=None;region=None;original=None;result=None;cleanup=False;snaps=[];images=[];armed=False;read=_gl_reader()
 try:
  base=ShowBase(windowType='none');base.makeDefaultPipe();fb=FrameBufferProperties();fb.setRgbColor(True);fb.setRgbaBits(8,8,8,8);fb.setDepthBits(24);fb.setMultisamples(requested_samples);wp=WindowProperties.size(8,8)
  win=base.graphicsEngine.makeOutput(base.pipe,'laptop-msaa-canary',0,fb,wp,GraphicsPipe.BFRefuseWindow)
  if win is None:raise RuntimeError('unable to allocate requested stock-Panda framebuffer')
  base.win=win;base.makeCamera2d(win);texture=Texture('actual-ram-readback');texture.setFormat(Texture.FRgba8);win.addRenderTexture(texture,GraphicsOutput.RTMCopyRam,GraphicsOutput.RTPColor)
  maker=CardMaker('challenge');maker.setFrameFullscreenQuad();card=base.render2d.attachNewNode(maker.generate());card.setDepthTest(False);card.setDepthWrite(False)
  card.setShader(Shader.make(Shader.SLGLSL,'#version 330\nuniform mat4 p3d_ModelViewProjectionMatrix; in vec4 p3d_Vertex; void main(){gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;}','#version 330\nuniform vec4 challenge; out vec4 frag; void main(){frag=challenge;}'))
  region=base.cam2d.node().getDisplayRegion(0);original=region.getDrawCallback()
  def callback(data):
   data.upcall()
   if armed:snaps.append(read())
  owned_callback=CallbackObject.make(callback);region.setDrawCallback(owned_callback)
  for color in COLORS:
   card.setShaderInput('challenge',tuple(x/255 for x in color));armed=True;base.graphicsEngine.renderFrame();base.graphicsEngine.syncFrame();armed=False
   if not texture.hasRamImage():raise RuntimeError('missing actual GPU RAM readback')
   images.append(bytes(texture.getRamImageAs('RGBA')).hex())
  result=dict(protocol='windows-panda-gpu-readbacks-v1',device_names=names,target_gpu=TARGET,requested_samples=requested_samples,observations=snaps,images=images,challenges=COLORS,render_calls=2,cleanup_complete=False)
 finally:
  if region is not None:
   if original is None:region.clearDrawCallback()
   else:region.setDrawCallback(original)
  if base is not None:base.destroy()
  cleanup=True
 if result is None:raise RuntimeError('GPU probe produced no result')
 result['cleanup_complete']=cleanup;return dict(protocol='windows-panda-gpu-attempt-v1',status='MEASURED',readbacks=result,validation=verify_gpu_readbacks(result))
