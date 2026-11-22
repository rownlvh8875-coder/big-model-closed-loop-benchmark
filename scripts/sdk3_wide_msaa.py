"""Observe the exact four HDR samples before Panda3D resolves the scene."""

from contextlib import contextmanager
import ctypes as ct
from time import perf_counter_ns

from scripts.panda_sdk3_runtime import need
from scripts.sdk3_wide_framebuffer import (
    GL_COLOR_ATTACHMENT0, GL_DRAW_FRAMEBUFFER, GL_FRAMEBUFFER_COMPLETE, GL_PIXEL_PACK_BUFFER, PACK, POINT, SIZE,
)
from scripts.sdk3_wide_hdr import HDRGL, capture_hdr

MS_TEXTURE = 0x9100
RGBA16F = 0x881A
RENDERBUFFER = 0x8D41
SSBO = 0x90D2
SSBO_INDEX = 7
SAMPLE_SHADER = b"""#version 430 core
layout(local_size_x = 4) in;
layout(binding = 0) uniform sampler2DMS color_samples;
layout(std430, binding = 7) buffer Readout { vec4 values[4]; };
void main() {
    int sample_index = int(gl_LocalInvocationID.x);
    values[sample_index] = texelFetch(color_samples, ivec2(0), sample_index);
}
"""


class SampleGL(HDRGL):
    def __init__(self,sensor):
        super().__init__(sensor)
        u,i,p=ct.c_uint,ct.c_int,ct.c_void_p
        calls=(
            ('glGetNamedRenderbufferParameteriv',None,(u,u,ct.POINTER(i))),
            ('glGetMultisamplefv',None,(u,u,ct.POINTER(ct.c_float))),
            ('glCreateTextures',None,(u,i,ct.POINTER(u))),
            ('glDeleteTextures',None,(i,ct.POINTER(u))),
            ('glTextureStorage2DMultisample',None,(u,i,u,i,i,ct.c_ubyte)),
            ('glCopyImageSubData',None,(u,u,i,i,i,i,u,u,i,i,i,i,i,i,i)),
            ('glBindTexture',None,(u,u)),
            ('glBindSampler',None,(u,u)),
            ('glCreateShader',u,(u,)),
            ('glShaderSource',None,(u,i,ct.POINTER(ct.c_char_p),ct.POINTER(i))),
            ('glCompileShader',None,(u,)),
            ('glGetShaderiv',None,(u,u,ct.POINTER(i))),
            ('glGetShaderInfoLog',None,(u,i,ct.POINTER(i),p)),
            ('glDeleteShader',None,(u,)),
            ('glCreateProgram',u,()),
            ('glAttachShader',None,(u,u)),
            ('glLinkProgram',None,(u,)),
            ('glGetProgramiv',None,(u,u,ct.POINTER(i))),
            ('glGetProgramInfoLog',None,(u,i,ct.POINTER(i),p)),
            ('glDeleteProgram',None,(u,)),
            ('glUseProgram',None,(u,)),
            ('glCreateBuffers',None,(i,ct.POINTER(u))),
            ('glNamedBufferData',None,(u,ct.c_ssize_t,p,u)),
            ('glGetNamedBufferSubData',None,(u,ct.c_ssize_t,ct.c_ssize_t,p)),
            ('glBindBufferBase',None,(u,u,u)),
            ('glDeleteBuffers',None,(i,ct.POINTER(u))),
            ('glDispatchCompute',None,(u,u,u)),
            ('glMemoryBarrier',None,(u,)),
            ('glCreateFramebuffers',None,(i,ct.POINTER(u))),
            ('glDeleteFramebuffers',None,(i,ct.POINTER(u))),
            ('glNamedFramebufferTexture',None,(u,u,u,i)),
            ('glNamedFramebufferReadBuffer',None,(u,u)),
            ('glNamedFramebufferDrawBuffer',None,(u,u)),
            ('glCheckNamedFramebufferStatus',u,(u,u)),
            ('glTextureStorage2D',None,(u,i,u,i,i)),
            ('glBlitNamedFramebuffer',None,(u,u,i,i,i,i,i,i,i,i,u,u)),
            ('glIsEnabled',ct.c_ubyte,(u,)),
        )
        for name,result,args in calls:
            fn=getattr(self.lib,name)
            fn.restype,fn.argtypes=result,args
            setattr(self,name,fn)

    def error_free(self,message):
        error=self.glGetError()
        need(error==0,f'{message}: GL {error:#x}')

    def program(self,source=SAMPLE_SHADER):
        shader=self.glCreateShader(0x91B9)
        program=self.glCreateProgram()
        need(shader and program,'private compute shader and program allocated')
        try:
            string=ct.c_char_p(source)
            self.glShaderSource(shader,1,ct.byref(string),None)
            self.glCompileShader(shader)
            self.require_status(shader,self.glGetShaderiv,self.glGetShaderInfoLog,0x8B81)
            self.glAttachShader(program,shader)
            self.glLinkProgram(program)
            self.require_status(program,self.glGetProgramiv,self.glGetProgramInfoLog,0x8B82)
            return program
        except Exception:
            self.glDeleteProgram(program)
            raise
        finally:
            self.glDeleteShader(shader)

    def require_status(self,handle,get,log,param):
        if not self.iv(get,handle,param):
            message=ct.create_string_buffer(4096)
            log(handle,len(message),None,message)
            raise ValueError(message.value.decode(errors='replace'))

    def source(self,record):
        need(bool(self.glXGetCurrentContext()),'live original wide scene GL context')
        self.error_free('known error-free original scene draw')
        state=self.state()
        plane=state['draw_buffer']
        need(state['viewport']==[0,0,*SIZE] and state['draw']>0 and plane==GL_COLOR_ATTACHMENT0,
             'original wide scene viewport and color attachment')
        need(self.glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,
             'complete original scene framebuffer')
        kind=self.attachment(plane,0x8CD0)
        handle=self.attachment(plane,0x8CD1)
        gl_samples=self.value(0x80A9)
        need(handle>0 and kind==RENDERBUFFER and gl_samples==4,
             f'actual four-sample scene color renderbuffer: kind={kind:#x} samples={gl_samples}')
        rb=lambda key:self.iv(self.glGetNamedRenderbufferParameteriv,handle,key)
        extent=[rb(0x8D42),rb(0x8D43)]
        fmt,samples=rb(0x8D44),rb(0x8CAB)
        need(extent==list(SIZE) and fmt==RGBA16F and samples==4,
             f'matching RGBA16F four-sample color renderbuffer: {extent} {fmt:#x} {samples}')
        positions=[]
        for index in range(4):
            point=(ct.c_float*2)()
            self.glGetMultisamplefv(0x8E50,index,point)
            positions.append(list(point))
        self.error_free('actual multisample framebuffer queries')
        record.update(source_attachment=handle,source_attachment_type=kind,internal_format=fmt,
                      source_extent=extent,source_samples=samples,sample_positions=positions,
                      source_scene_draw_fbo=state['draw'])
        return handle

    def private_resolve(self,texture,record):
        prior=self.state()
        scissor=self.values(0x0C10,4)
        if self.glIsEnabled(0x0C11):
            x,y,w,h=scissor
            need(x<=0<x+w and y<=0<y+h,'private resolve pixel inside original scissor')
        pair=(ct.c_uint*2)()
        output=ct.c_uint()
        words=(ct.c_uint32*4)()
        try:
            self.glCreateTextures(0x0DE1,1,ct.byref(output))
            self.glTextureStorage2D(output,1,RGBA16F,1,1)
            self.glCreateFramebuffers(2,pair)
            src,dst=pair
            self.glNamedFramebufferTexture(src,GL_COLOR_ATTACHMENT0,texture,0)
            self.glNamedFramebufferTexture(dst,GL_COLOR_ATTACHMENT0,output,0)
            self.glNamedFramebufferReadBuffer(src,GL_COLOR_ATTACHMENT0)
            self.glNamedFramebufferDrawBuffer(dst,GL_COLOR_ATTACHMENT0)
            need(all(self.glCheckNamedFramebufferStatus(fb,0x8D40)==GL_FRAMEBUFFER_COMPLETE for fb in pair),
                 'complete private 1x1 reference resolve framebuffers')
            self.glBlitNamedFramebuffer(src,dst,0,0,1,1,0,0,1,1,0x4000,0x2600)
            self.glBindBuffer(GL_PIXEL_PACK_BUFFER,0)
            for idx,key in enumerate(PACK):
                self.glPixelStorei(key,int(idx==0))
            self.glGetTextureSubImage(output,0,0,0,0,1,1,1,0x1908,0x1406,ct.sizeof(words),words)
            self.error_free('private same-format four-to-one GPU reference resolve')
            record.update(private_resolve_words=list(words),private_blit_calls=1)
        finally:
            for name,value in zip(PACK,prior['pack'],strict=True):
                self.glPixelStorei(name,value)
            self.glBindBuffer(GL_PIXEL_PACK_BUFFER,prior['pack_buffer'])
            if pair[0]:
                self.glDeleteFramebuffers(2,pair)
            if output.value:
                self.glDeleteTextures(1,ct.byref(output))
        need(self.state()==prior,'private resolve saved and restored its original GL state')
        self.error_free('private resolve released its own resources')

    def sample_words(self,source,x,y,record):
        prior=self.state()
        active=self.value(0x84E0)
        program=self.value(0x8B8D)
        generic=self.value(0x90D3)
        indexed=self.iv(self.glGetIntegeri_v,0x90D3,SSBO_INDEX)
        sampler=self.iv(self.glGetIntegeri_v,0x8919,0)
        need(indexed==0,'unused private SSBO binding index')
        texture,buffer=ct.c_uint(),ct.c_uint()
        compute=0
        self.glActiveTexture(0x84C0)
        ms_binding=self.value(0x9104)
        words=(ct.c_uint32*16)()
        try:
            self.glCreateTextures(MS_TEXTURE,1,ct.byref(texture))
            self.glTextureStorage2DMultisample(texture,4,RGBA16F,1,1,1)
            self.glCopyImageSubData(source,RENDERBUFFER,0,x,y,0,texture,MS_TEXTURE,0,0,0,0,1,1,1)
            self.error_free('sample-preserving 1x1 copy from original renderbuffer')
            record['sample_copy_calls']=1
            self.private_resolve(texture,record)
            compute=self.program()
            self.glCreateBuffers(1,ct.byref(buffer))
            self.glNamedBufferData(buffer,ct.sizeof(words),None,0x88E0)
            self.glUseProgram(compute)
            self.glBindTexture(MS_TEXTURE,texture)
            self.glBindSampler(0,0)
            self.glBindBufferBase(SSBO,SSBO_INDEX,buffer)
            self.glDispatchCompute(1,1,1)
            self.glMemoryBarrier(0x0200)
            self.glGetNamedBufferSubData(buffer,0,ct.sizeof(words),words)
            self.error_free('actual indexed RGBA32F sample readout')
            record.update(extra_compute_calls=1,sample_words=list(words))
        finally:
            self.glBindBufferBase(SSBO,SSBO_INDEX,0)
            self.glBindBuffer(SSBO,generic)
            self.glBindSampler(0,sampler)
            self.glBindTexture(MS_TEXTURE,ms_binding)
            self.glActiveTexture(active)
            self.glUseProgram(program)
            if buffer.value:
                self.glDeleteBuffers(1,ct.byref(buffer))
            if compute:
                self.glDeleteProgram(compute)
            if texture.value:
                self.glDeleteTextures(1,ct.byref(texture))
            self.glActiveTexture(0x84C0)
            texture_restored=self.value(0x9104)==ms_binding
            self.glActiveTexture(active)
            record['state_restored']=(self.state()==prior and texture_restored
                and self.value(0x8B8D)==program and self.value(0x90D3)==generic
                and self.iv(self.glGetIntegeri_v,0x90D3,SSBO_INDEX)==indexed
                and self.iv(self.glGetIntegeri_v,0x8919,0)==sampler and self.value(0x84E0)==active)
            record['restore_gl_error']=self.glGetError()
        need(record['state_restored'] and record['restore_gl_error']==0,'restore original scene GL state')


@contextmanager
def capture_samples(provider,timing,events):
    from panda3d.core import CallbackObject

    sensor=provider.env.engine.sensors['bigbench_wide']
    scenes=[r for b in sensor.manager.buffers for r in b.getDisplayRegions()
            if r.isActive() and r.getCamera()==sensor.cam]
    need(len(scenes)==1,'unique original wide scene DisplayRegion')
    scene,=scenes
    need(scene.getDrawCallback() is None,'unoccupied original scene callback')
    gl=SampleGL(sensor)
    records=[]

    def draw(data):
        if timing.active!='wide':
            data.upcall()
            return
        row=dict(callback_enter_ns=perf_counter_ns(),sample_copy_calls=0,extra_compute_calls=0)
        records.append(row)
        data.upcall()
        row['after_original_draw_ns']=perf_counter_ns()
        try:
            setup=data.getSceneSetup()
            need(len(records)==1 and setup is not None and setup.getDisplayRegion()==scene,
                 'one actual original wide scene draw at the target')
            handle=gl.source(row)
            row['sample_pixel_gl']=[POINT[0],SIZE[1]-1-POINT[1]]
            gl.sample_words(handle,*row['sample_pixel_gl'],row)
        except (AttributeError,ValueError,TypeError,RuntimeError) as exc:
            row['failure']=f'{type(exc).__name__}: {exc}'
        finally:
            row['callback_exit_ns']=perf_counter_ns()

    callback=CallbackObject.make(draw)
    scene.setDrawCallback(callback)
    try:
        with capture_hdr(provider,timing,events):
            yield
    finally:
        need(scene.getDrawCallback()==callback,'owned HDR scene callback')
        scene.clearDrawCallback()
        need(scene.getDrawCallback() is None,'restore original HDR scene callback')
        if len(events)==1:
            events[0]['pre_resolve']=records
            events[0]['scene_callback_restored']=True
