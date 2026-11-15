"""Handwritten Panda-shaped CPU data fixture. Never real driver/frame authority."""
from pathlib import Path
_ids=1000
class Typed:
 def __init__(self):
  global _ids
  _ids+=1;self.this=_ids
 def get_type(self):return self
 def get_name(self):return type(self).__name__
class Texture(Typed):
 T_unsigned_byte=0;F_rgba8=1
 def __init__(self,name):super().__init__();self.name=name;self.raw=None
 def has_ram_image(self):return self.raw is not None
 def get_ram_image_as(self,fmt):
  if fmt!='RGB':raise ValueError('CPU format');
  return self.raw
 def get_x_size(self):return 8
 def get_y_size(self):return 8
 def clear_ram_image(self):self.raw=None
class FrameBufferProperties:
 def __getattr__(self,name):
  if name.startswith('set_'):return lambda *args:None
  raise AttributeError(name)
class WindowProperties:
 @staticmethod
 def size(w,h):return (w,h)
class GraphicsPipe:BF_refuse_window=4
class GraphicsOutput:RTM_copy_ram=3;RTP_color=2
class Pipe(Typed):
 def get_name(self):return 'glxGraphicsPipe'
class GraphicsPipeSelection:
 module=None
 @classmethod
 def get_global_ptr(cls):return cls()
 def make_module_pipe(self,module):GraphicsPipeSelection.module=module;return Pipe()
class GSG(Typed):
 def is_valid(self):return True
 def get_driver_vendor(self):return 'CPU fixture Mesa-shaped'
 def get_driver_renderer(self):return 'softpipe'
 def get_driver_version(self):return 'CPU fixture 3.3'
class Region:
 def set_camera(self,cam):self.cam=cam
 def set_clear_color_active(self,value):self.color_active=value
 def set_clear_color(self,value):self.color=value
class Output(Typed):
 def __init__(self):super().__init__();self.gsg=GSG();self.textures=[];self.color=(0,0,0,1);self.valid=True
 def is_valid(self):return self.valid
 def get_x_size(self):return 8
 def get_y_size(self):return 8
 def get_gsg(self):return self.gsg
 def set_clear_color_active(self,value):self.clear_active=value
 def set_clear_color(self,value):self.color=value
 def set_clear_depth_active(self,value):self.clear_depth=value
 def add_render_texture(self,tex,mode,plane):self.textures.append(tex);self.mode=mode;self.plane=plane
 def clear_render_textures(self):self.textures=[]
 def make_display_region(self):return Region()
class GraphicsEngine:
 last=None
 def __init__(self):self.outputs=[];self.renders=0;self.syncs=0;GraphicsEngine.last=self
 def make_output(self,pipe,name,sort,fb,props,flags):
  if flags!=4 or props!=(8,8):raise ValueError('CPU requested output contract')
  out=Output();self.outputs.append(out);return out
 def open_windows(self):pass
 def get_num_windows(self):return len(self.outputs)
 def render_frame(self):
  self.renders+=1
  for out in self.outputs:
   for texture in out.textures:texture.raw=bytes(round(x*255) for x in out.color[:3])*64
 def sync_frame(self):self.syncs+=1
 def remove_all_windows(self):self.outputs=[]
class NodePath(Typed):
 def __init__(self,name):super().__init__();self.name=name;self.removed=False
 def attach_new_node(self,node):return NodePath(node)
 def remove_node(self):self.removed=True
class Camera(Typed):
 def __init__(self,name):super().__init__()
 def set_scene(self,node):self.scene=node
 def set_lens(self,lens):self.lens=lens
class OrthographicLens:
 def set_film_size(self,w,h):pass
 def set_near_far(self,a,b):pass
def load_prc_file_data(name,text):return None
