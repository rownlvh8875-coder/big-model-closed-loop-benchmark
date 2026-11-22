"""Scoped per-draw snapshots of the original wide scene color and depth samples."""

from contextlib import contextmanager
import ctypes as ct
from hashlib import sha256
import os
from pathlib import Path
from time import perf_counter_ns

from scripts.panda_sdk3_runtime import need
from scripts.sdk3_wide_framebuffer import POINT, SIZE
from scripts.sdk3_wide_msaa import SampleGL, MS_TEXTURE, RENDERBUFFER, RGBA16F, SSBO, SSBO_INDEX, capture_samples

LIMIT=128
DEPTH_FORMATS={0x81A5,0x81A6,0x81A7,0x8CAC,0x88F0,0x8CAD}
DRAW_READ_SHADER=b"""#version 430 core
layout(local_size_x=4) in;
layout(binding=0) uniform sampler2DMS color_source;
layout(binding=1) uniform sampler2DMS depth_source;
layout(std430,binding=7) buffer Readout { vec4 colors[4]; vec4 depths[4]; };
void main() {
    int i=int(gl_LocalInvocationID.x);
    colors[i]=texelFetch(color_source,ivec2(0),i);
    depths[i]=texelFetch(depth_source,ivec2(0),i);
}
"""
TAP=ct.CFUNCTYPE(None,ct.c_uint,ct.c_int,ct.c_char_p,ct.c_uint,ct.c_int,ct.c_int)


class DrawReadout(SampleGL):
    def __init__(self,sensor):
        super().__init__(sensor)
        u,i,p=ct.c_uint,ct.c_int,ct.c_void_p
        for name,rest,args in (
            ('glGetAttachedShaders',None,(u,i,ct.POINTER(i),ct.POINTER(u))),
            ('glGetShaderSource',None,(u,i,ct.POINTER(i),p)),
            ('glGetFloatv',None,(u,ct.POINTER(ct.c_float))),
        ):
            method=getattr(self.lib,name)
            method.restype,method.argtypes=rest,args
            setattr(self,name,method)
        self.textures=(u*2)()
        self.buffer=u()
        self.compute=0
        self.attachments=None
        self.programs={}
        self.depth={}
        self.scene={}

    def open(self):
        color=self.source(self.scene)
        depth=self.attachment(0x8D00,0x8CD1)
        kind=self.attachment(0x8D00,0x8CD0)
        need(kind==RENDERBUFFER and depth>0,'original multisample depth renderbuffer')
        rb=lambda enum:self.iv(self.glGetNamedRenderbufferParameteriv,depth,enum)
        fmt=rb(0x8D44)
        extent=[rb(0x8D42),rb(0x8D43)]
        samples=rb(0x8CAB)
        self.depth=dict(object=depth,type=kind,format=fmt,extent=extent,samples=samples)
        need(fmt in DEPTH_FORMATS and extent==list(SIZE) and samples==4,
             f'same-size four-sample depth attachment: {fmt:#x} {extent} {samples}')
        self.attachments=(color,depth)
        self.glCreateTextures(MS_TEXTURE,2,self.textures)
        for texture,internal in zip(self.textures,(RGBA16F,fmt),strict=True):
            self.glTextureStorage2DMultisample(texture,4,internal,1,1,1)
        self.glCreateBuffers(1,ct.byref(self.buffer))
        self.glNamedBufferData(self.buffer,128,None,0x88E0)
        self.compute=self.program(DRAW_READ_SHADER)
        self.error_free('private color/depth sampler allocation')

    def describe_program(self,program):
        if program in self.programs:
            return
        count=self.iv(self.glGetProgramiv,program,0x8B85) if program else 0
        need(0<=count<=8,'bounded shader count for original draw program')
        attached=(ct.c_uint*count)()
        actual=ct.c_int()
        record=[]
        if count:
            self.glGetAttachedShaders(program,count,ct.byref(actual),attached)
        for shader in attached[:actual.value]:
            extent=self.iv(self.glGetShaderiv,shader,0x8B88)
            kind=self.iv(self.glGetShaderiv,shader,0x8B4F)
            need(0<=extent<=262144,'bounded native shader source')
            if extent:
                source=ct.create_string_buffer(extent)
                length=ct.c_int()
                self.glGetShaderSource(shader,extent,ct.byref(length),source)
                exact=source.raw[:length.value]
                record.append(dict(kind=kind,sha256=sha256(exact).hexdigest(),
                                   source=exact.decode(errors='replace')))
        self.programs[program]=record

    def draw_state(self):
        enable={name:bool(self.glIsEnabled(value)) for name,value in (
            ('sample_mask',0x8E51),('sample_coverage',0x80A0),('alpha_to_coverage',0x809E),
            ('sample_shading',0x8C36),('depth_test',0x0B71),('blend',0x0BE2),('stencil',0x0B90),
            ('scissor',0x0C11))}
        cov=ct.c_float()
        self.glGetFloatv(0x80AA,ct.byref(cov))
        return dict(**enable,sample_mask_bits=self.iv(self.glGetIntegeri_v,0x8E52,0)&0xffffffff,
                    sample_coverage_value=cov.value,sample_coverage_invert=self.value(0x80AB),
                    depth_function=self.value(0x0B74),depth_write=self.value(0x0B72),
                    color_write=self.values(0x0C23,4),scissor_box=self.values(0x0C10,4),
                    vao=self.value(0x85B5),program=self.value(0x8B8D))

    def read(self):
        before=self.state()
        need(before['draw']==self.scene['source_scene_draw_fbo'] and before['viewport']==[0,0,*SIZE],
             'read scoped to original wide scene framebuffer')
        active,program,generic=(self.value(v) for v in (0x84E0,0x8B8D,0x90D3))
        indexed=self.iv(self.glGetIntegeri_v,0x90D3,SSBO_INDEX)
        need(indexed==0,'unoccupied private SSBO index')
        units=[]
        for unit in range(2):
            self.glActiveTexture(0x84C0+unit)
            units.append((self.value(0x9104),self.iv(self.glGetIntegeri_v,0x8919,unit)))
        self.glActiveTexture(active)
        words=(ct.c_uint32*32)()
        try:
            self.glUseProgram(self.compute)
            x,y=POINT[0],SIZE[1]-1-POINT[1]
            for unit,(source,texture) in enumerate(zip(self.attachments,self.textures,strict=True)):
                self.glCopyImageSubData(source,RENDERBUFFER,0,x,y,0,texture,MS_TEXTURE,0,0,0,0,1,1,1)
                self.glActiveTexture(0x84C0+unit)
                self.glBindTexture(MS_TEXTURE,texture)
                self.glBindSampler(unit,0)
            self.error_free('copy original per-sample color and depth without resolve')
            self.glBindBufferBase(SSBO,SSBO_INDEX,self.buffer)
            self.glDispatchCompute(1,1,1)
            self.glMemoryBarrier(0x0200)
            self.glGetNamedBufferSubData(self.buffer,0,128,words)
            self.error_free('read true color and depth sample words')
        finally:
            self.glBindBufferBase(SSBO,SSBO_INDEX,indexed)
            self.glBindBuffer(SSBO,generic)
            for unit,(texture,sampler) in enumerate(units):
                self.glActiveTexture(0x84C0+unit)
                self.glBindTexture(MS_TEXTURE,texture)
                self.glBindSampler(unit,sampler)
            self.glActiveTexture(active)
            self.glUseProgram(program)
        need(self.state()==before and self.value(0x8B8D)==program,'original draw GL state restored')
        self.error_free('restore succeeded')
        return dict(color_words=list(words[:16]),depth_words=list(words[16::4]))

    def close(self):
        if self.compute:
            self.glDeleteProgram(self.compute)
        if self.buffer.value:
            self.glDeleteBuffers(1,ct.byref(self.buffer))
        if self.textures[0]:
            self.glDeleteTextures(2,self.textures)
        self.error_free('private draw readers removed')


@contextmanager
def trace_draws(provider,timing,events):
    shim_path=Path('/observer.so')
    need(os.environ.get('LD_PRELOAD')==str(shim_path),'exact camera-only observer preload')
    shim=ct.CDLL(str(shim_path))
    shim.wide_draw_begin.argtypes=[TAP]
    shim.wide_draw_end.argtypes=[ct.POINTER(ct.c_uint),ct.POINTER(ct.c_uint),ct.c_void_p]
    sensor=provider.env.engine.sensors['bigbench_wide']
    scenes=[r for b in sensor.manager.buffers for r in b.getDisplayRegions()
            if r.isActive() and r.getCamera()==sensor.cam]
    need(len(scenes)==1,'one original wide scene DisplayRegion for draw order')
    scene,=scenes
    trace=dict(records=[],errors=[],shader_programs={},begin_ns=None)
    trace['observer_sha256']=sha256(shim_path.read_bytes()).hexdigest()
    gl=DrawReadout(sensor)

    @TAP
    def tap(index,edge,name,mode,count,instances):
        if trace['errors']:
            return
        try:
            need(index<=LIMIT,'bounded original draw count')
            if index==1 and edge==0:
                gl.open()
                trace.update(scene=gl.scene,depth=gl.depth)
            row=dict(draw=index,edge=edge,entry=name.decode(),mode=mode,count=count,instances=instances)
            if edge==0:
                row['draw_state']=gl.draw_state()
                gl.describe_program(row['draw_state']['program'])
            row.update(gl.read())
            trace['records'].append(row)
        except BaseException as exc:
            trace['errors'].append(f'draw {index} edge {edge}: {type(exc).__name__}: {exc}')

    def observe(upcall):
        trace['begin_ns']=perf_counter_ns()
        counter,missing=ct.c_uint(),ct.c_uint()
        last=ct.create_string_buffer(64)
        need(shim.wide_draw_begin(tap)==0,'scoped draw tap enabled once')
        try:
            upcall()
        finally:
            trace['shim_end']=shim.wide_draw_end(ct.byref(counter),ct.byref(missing),last)
            trace.update(draws=counter.value,unrecognized_lookup_count=missing.value,
                         last_unrecognized_lookup=last.value.decode(),end_ns=perf_counter_ns(),
                         shader_programs=gl.programs)
            try:
                gl.close()
            except ValueError as exc:
                trace['errors'].append(str(exc))

    with capture_samples(provider,timing,events,draw_hook=observe):
        yield
    if len(events)==1:
        events[0]['draw_trace']=trace
