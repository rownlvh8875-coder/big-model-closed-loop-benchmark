"""Calibrate the private copy/read path with four independently written sample colors."""
import ctypes as ct
import struct

from scripts.panda_sdk3_runtime import need
from scripts.sdk3_wide_msaa import MS_TEXTURE, RENDERBUFFER, RGBA16F, SampleGL

WRITER = b"""#version 430 core
layout(local_size_x=4) in;
layout(rgba16f,binding=6) writeonly uniform image2DMS target;
void main() {
    int i=int(gl_LocalInvocationID.x);
    imageStore(target,ivec2(0),i,vec4(0.125*float(i+1),0.75-0.125*float(i),0.25*float(i%2),1.0));
}
"""


def known_samples():
    gl=SampleGL(None)
    u,i=ct.c_uint,ct.c_int
    for name,args in (
        ('glCreateRenderbuffers',(i,ct.POINTER(u))),
        ('glDeleteRenderbuffers',(i,ct.POINTER(u))),
        ('glNamedRenderbufferStorageMultisample',(u,i,u,i,i)),
        ('glBindImageTexture',(u,u,i,ct.c_ubyte,i,u,u)),
    ):
        method=getattr(gl.lib,name)
        method.restype,method.argtypes=None,args
        setattr(gl,name,method)
    index=6
    old=gl.value(0x8B8D)
    no_image=gl.iv(gl.glGetIntegeri_v,0x8F3A,index)==0
    need(no_image,'unused canary image binding')
    tex,rb=ct.c_uint(),ct.c_uint()
    program=0
    try:
        gl.glCreateTextures(MS_TEXTURE,1,ct.byref(tex))
        gl.glTextureStorage2DMultisample(tex,4,RGBA16F,1,1,1)
        gl.glCreateRenderbuffers(1,ct.byref(rb))
        gl.glNamedRenderbufferStorageMultisample(rb,4,RGBA16F,1,1)
        program=gl.program(WRITER)
        gl.glUseProgram(program)
        gl.glBindImageTexture(index,tex,0,0,0,0x88B9,RGBA16F)
        gl.glDispatchCompute(1,1,1)
        gl.glMemoryBarrier(0x0100)
        gl.error_free('known distinct sample writes')
        gl.glCopyImageSubData(tex,MS_TEXTURE,0,0,0,0,rb,RENDERBUFFER,0,0,0,0,1,1,1)
        gl.error_free('known samples copied to private HDR renderbuffer')
        record={}
        gl.sample_words(rb.value,0,0,record)
        actual=struct.unpack('<16f',struct.pack('<16I',*record['sample_words']))
        expected=tuple(j for i in range(4) for j in (0.125*(i+1),0.75-0.125*i,0.25*(i%2),1.))
        need(actual==expected,'exact independent canary color for each of four indices')
        return dict(zip(('expected','actual'),(expected,actual)),private_source='RGBA16F renderbuffer')
    finally:
        gl.glBindImageTexture(index,0,0,0,0,0x88B9,RGBA16F)
        gl.glUseProgram(old)
        if program:
            gl.glDeleteProgram(program)
        if rb.value:
            gl.glDeleteRenderbuffers(1,ct.byref(rb))
        if tex.value:
            gl.glDeleteTextures(1,ct.byref(tex))
        gl.error_free('canary private resources released')
