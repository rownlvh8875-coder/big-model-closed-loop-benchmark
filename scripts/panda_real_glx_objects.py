"""One owned Panda engine/output/texture; actual core imported by qualified child."""
from scripts.panda_real_glx_frames import need
PRC='''load-display pandagl
aux-display
window-type offscreen
win-size 8 8
framebuffer-srgb false
framebuffer-multisample false
multisamples 0
sync-video false
threading-model
audio-library-name null
notify-level warning
'''
def identity(value):
 pointer=int(value.this);need(0<pointer<2**64,'actual Panda object pointer');name=value.get_type().get_name() if hasattr(value,'get_type') else type(value).__name__;need(type(name) is str and 0<len(name)<=128,'Panda type name');return dict(pointer=pointer,type=name)
class Renderer:
 def __init__(self,core):self.core=core;self.engine=None;self.output=None;self.texture=None;self.scene=None;self.camera_node=None;self.render_calls=0;self.ram_reads=0;self.closed=False;self.ready=False
 def setup(self):
  need(not self.ready and self.engine is None and not self.closed,'one owned renderer');c=self.core;c.load_prc_file_data('real-glx-canary',PRC);self.engine=c.GraphicsEngine();pipe=c.GraphicsPipeSelection.get_global_ptr().make_module_pipe('pandagl');need(pipe is not None,'exact pandagl pipe');fb=c.FrameBufferProperties();fb.set_rgb_color(True);fb.set_rgba_bits(8,8,8,8);fb.set_depth_bits(0);fb.set_stencil_bits(0);fb.set_multisamples(0);fb.set_srgb_color(False)
  self.output=self.engine.make_output(pipe,'real-glx-canary',0,fb,c.WindowProperties.size(8,8),c.GraphicsPipe.BF_refuse_window);need(self.output is not None,'Panda output allocation');self.engine.open_windows();need(self.output.is_valid() and self.output.get_x_size()==self.output.get_y_size()==8,'valid8x8output');gsg=self.output.get_gsg();need(gsg is not None and gsg.is_valid(),'valid actual GSG')
  driver=dict(vendor=gsg.get_driver_vendor(),renderer=gsg.get_driver_renderer(),version=gsg.get_driver_version());need(all(type(v) is str and 0<len(v)<=512 for v in driver.values()) and driver['renderer'].strip().lower()=='softpipe','fixed softpipe driver')
  self.texture=c.Texture('real-glx-texture');self.output.add_render_texture(self.texture,c.GraphicsOutput.RTM_copy_ram,c.GraphicsOutput.RTP_color);self.output.set_clear_color_active(True);self.output.set_clear_depth_active(False);self.scene=c.NodePath('real-glx-empty-scene');camera=c.Camera('real-glx-camera');camera.set_scene(self.scene);lens=c.OrthographicLens();lens.set_film_size(2,2);lens.set_near_far(.1,10);camera.set_lens(lens);self.camera_node=self.scene.attach_new_node(camera);self.region=self.output.make_display_region();self.region.set_camera(self.camera_node);self.region.set_clear_color_active(True)
  objects={n:identity(v) for n,v in dict(pipe=pipe,output=self.output,gsg=gsg,texture=self.texture,camera=camera).items()};need(len({v['pointer'] for v in objects.values()})==5,'distinct actual Panda objects');windows=self.engine.get_num_windows();need(type(windows) is int and 1<=windows<=2,'owned engine output count');self.ready=True;self.setup_report=dict(objects=objects,driver=driver,windows=windows,width=8,height=8,physical_gpu_qualified=False,cpp_object_abi_complete=False);return self.setup_report
 def render(self,rgb):
  need(self.ready and not self.closed and self.ram_reads<2 and type(rgb) is list and len(rgb)==3 and all(type(v) is int and 0<=v<=255 for v in rgb),'two bounded RGB reads');color=tuple(v/255 for v in rgb)+(1.,);self.output.set_clear_color(color);self.region.set_clear_color(color)
  for _ in range(2):self.engine.render_frame();self.render_calls+=1;self.engine.sync_frame()
  need(self.texture.has_ram_image() and self.texture.get_x_size()==self.texture.get_y_size()==8,'actual8x8TextureRAM');raw=bytes(self.texture.get_ram_image_as('RGB'));self.ram_reads+=1;need(len(raw)==192,'RGB byte extent');return raw
 def close(self):
  need(not self.closed,'one cleanup');self.closed=True
  try:
   if self.output is not None:self.output.clear_render_textures()
   if self.engine is not None:self.engine.remove_all_windows()
  finally:
   if self.texture is not None:self.texture.clear_ram_image()
   if self.camera_node is not None:self.camera_node.remove_node()
   if self.scene is not None:self.scene.remove_node()
  count=self.engine.get_num_windows() if self.engine is not None else 0;ram=self.texture.has_ram_image() if self.texture is not None else False;need(count==0 and ram is False,'owned output/RAM cleanup');return dict(windows_after=count,texture_ram_after=ram,render_calls=self.render_calls,ram_reads=self.ram_reads,cpp_deallocation_verified=False)
