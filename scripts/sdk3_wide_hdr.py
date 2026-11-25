"""Read the existing resolved HDR texture bound to the original wide shader."""

import ctypes as ct
from hashlib import sha256

from scripts.panda_sdk3_runtime import need
from scripts.sdk3_wide_framebuffer import GL, GL_PIXEL_PACK_BUFFER, PACK, PATCH_RADIUS, POINT, SIZE, post_capture

FLT_RGBA = (0x1908, 0x1406)
RGBA_F = {0x881A: 'RGBA16F', 0x8814: 'RGBA32F'}


class HDRGL(GL):
    def __init__(self, sensor):
        super().__init__()
        self.sensor = sensor
        u, i, p = ct.c_uint, ct.c_int, ct.c_void_p
        extra = (
            ('glGetUniformLocation', i, (u, ct.c_char_p)),
            ('glGetUniformiv', None, (u,i,ct.POINTER(i))),
            ('glGetUniformfv', None, (u,i,ct.POINTER(ct.c_float))),
            ('glGetIntegeri_v', None, (u,u,ct.POINTER(i))),
            ('glActiveTexture', None, (u,)),
            ('glGetTextureLevelParameteriv', None, (u,i,u,ct.POINTER(i))),
            ('glGetTextureParameteriv', None, (u,u,ct.POINTER(i))),
            ('glGetSamplerParameteriv', None, (u,u,ct.POINTER(i))),
            ('glGetTextureSubImage', None, (u,i,i,i,i,i,i,i,u,u,i,p)),
        )
        for name,result,args in extra:
            fn=getattr(self.lib,name)
            fn.restype,fn.argtypes=result,args
            setattr(self,name,fn)

    @staticmethod
    def iv(query,*args):
        value=ct.c_int()
        query(*args,ct.byref(value))
        return value.value

    def read_patch(self,receipt):
        self.read_hdr(receipt.setdefault('hdr',{}))
        super().read_patch(receipt)

    def read_hdr(self,record):
        from panda3d.core import Shader

        sensor=self.sensor
        gsg=sensor.buffer.getGsg()
        prepared=gsg.getPreparedObjects()
        texture=sensor.scene_tex
        bound_input=sensor.tonemap_quad.getShaderInput('tex').getTexture()
        need(bound_input==texture and texture.isPrepared(prepared),'already prepared original Panda HDR input')
        # The prepared-object path returns the existing context. The actual active
        # GL sampler binding below must agree with its native texture name.
        texture_context=texture.prepareNow(0,prepared,gsg)
        need(texture_context is not None,'existing Panda HDR texture context')
        expected_id=int(texture_context.getNativeId())
        program=self.value(0x8B8D)
        location=self.glGetUniformLocation(program,b'tex') if program else -1
        exp_location=self.glGetUniformLocation(program,b'exposure') if program else -1
        record.update(program=program,tex_location=location,exposure_location=exp_location,
                      expected_texture=expected_id)
        need(program>0 and location>=0 and exp_location>=0,'actual active wide tonemap program and uniforms')
        unit=self.iv(self.glGetUniformiv,program,location)
        exposure=ct.c_float()
        self.glGetUniformfv(program,exp_location,ct.byref(exposure))
        active_before=self.value(0x84E0)
        need(0<=unit<self.value(0x8B4D),'valid live HDR sampler unit')
        try:
            self.glActiveTexture(0x84C0+unit)
            native_id=self.value(0x8069)
        finally:
            self.glActiveTexture(active_before)
        sampler=self.iv(self.glGetIntegeri_v,0x8919,unit)
        need(native_id==expected_id and native_id>0,'on-draw GL sampler reads the original scene texture')
        level=lambda key:self.iv(self.glGetTextureLevelParameteriv,native_id,0,key)
        extents=[level(0x1000),level(0x1001)]
        fmt=level(0x1003)
        parameters=self.glGetSamplerParameteriv if sampler else self.glGetTextureParameteriv
        filtering={name:self.iv(parameters,sampler or native_id,key)
                   for name,key in (('min',0x2801),('mag',0x2800),('wrap_s',0x2802),('wrap_t',0x2803))}
        shader=sensor.tonemap_quad.getShader()
        scene_regions=[b for b in sensor.manager.buffers
                       if any(r.isActive() and r.getCamera()==sensor.cam for r in b.getDisplayRegions())]
        need(len(scene_regions)==1,'unique original wide HDR scene output')
        record.update(bound_texture=native_id,texture_size=extents,internal_format=fmt,unit=unit,
                      sampler=sampler,filter=filtering,exposure=exposure.value,
                      scene_actual_samples=scene_regions[0].getFbProperties().getMultisamples(),
                      fragment_sha256=sha256(shader.getText(Shader.STFragment).encode()).hexdigest(),
                      vertex_sha256=sha256(shader.getText(Shader.STVertex).encode()).hexdigest())
        need(extents==list(SIZE) and fmt in RGBA_F,
             f'full-size resolved 2D RGBA floating-point HDR texture: {extents} {fmt:#x}')
        need(self.glGetError()==0,'no prior GL error at resolved texture read')
        before=self.state()
        x,y=POINT
        rad=PATCH_RADIUS
        edge=2*rad+1
        start=(x-rad,SIZE[1]-1-y-rad)
        words=(ct.c_uint32*(edge*edge*4))()
        try:
            self.glBindBuffer(GL_PIXEL_PACK_BUFFER,0)
            for idx,parameter in enumerate(PACK):
                self.glPixelStorei(parameter,int(idx==0))
            self.glGetTextureSubImage(native_id,0,*start,0,edge,edge,1,*FLT_RGBA,ct.sizeof(words),words)
            record.update(extra_gl_read_calls=1,gl_error_after_read=self.glGetError())
        finally:
            for key,value in zip(PACK,before['pack'],strict=True):
                self.glPixelStorei(key,value)
            self.glBindBuffer(GL_PIXEL_PACK_BUFFER,before['pack_buffer'])
            record.update(gl_error_after_restore=self.glGetError(),
                          restored=(before==self.state() and active_before==self.value(0x84E0)
                                    and program==self.value(0x8B8D)))
        need(record['restored'] and not record['gl_error_after_read'] and not record['gl_error_after_restore'],
             'one bounded live HDR texture read with restored state')
        record.update(patch_bottom_left=[*start,edge,edge],rgba32f_words_bottom_up=list(words))


def capture_hdr(provider,timing,events):
    sensor=provider.env.engine.sensors['bigbench_wide']
    return post_capture(provider,timing,events,observer=lambda:HDRGL(sensor))
