"""Verify raw HDR bytes, source binding, and the matching final FBO result."""
from math import isfinite
import struct

from scripts.panda_sdk3_runtime import need
from scripts.sdk3_wide_framebuffer import SIZE
from scripts.sdk3_wide_hdr import RGBA_F
from scripts.verify_sdk3_wide_framebuffer import verify as verify_base


def decode_hdr(hdr):
    words=hdr['rgba32f_words_bottom_up']
    need(len(words)==36 and all(type(w) is int and 0<=w<2**32 for w in words),'exact observed HDR words')
    values=struct.unpack('<36f',struct.pack('<36I',*words))
    need(all(isfinite(value) for value in values),'finite resolved HDR sample values')
    return [[list(values[(row*3+col)*4:(row*3+col+1)*4])
             for col in range(3)] for row in (2,1,0)]


def verify(native, poses, trial, context, history='sequential'):
    result=verify_base(native,poses,trial,context,history)
    result['history']=history
    if trial=='control':
        return result
    hdr=result['observation']['hdr']
    need(hdr['program']>0 and hdr['tex_location']>=0 and hdr['exposure_location']>=0
         and hdr['expected_texture']==hdr['bound_texture']>0,'bound original live tonemap program and texture')
    need(hdr['texture_size']==list(SIZE) and hdr['internal_format'] in RGBA_F
         and hdr['patch_bottom_left']==[328,296,3,3] and hdr['extra_gl_read_calls']==1
         and hdr['restored'] and hdr['gl_error_after_read']==hdr['gl_error_after_restore']==0,
         'bounded valid resolved HDR observation')
    need(hdr['fragment_sha256']=='835b7ccb2d88f79d3d92b2009e142ad88453939a37a6e156808809e069c9af12'
         and hdr['vertex_sha256']=='8166ad854899374d1ba86d3e34dc075e8efa04c4293be7952c80196b75f38c73'
         and hdr['exposure']==1.0 and hdr['filter']['min']==hdr['filter']['mag']==0x2601,
         'exact original tonemap sources and live exposure and linear sampling')
    need(result['same_nine_pixels'],'measured final framebuffer matches the original RAM pixel neighborhood')
    result.update(hdr_patch=decode_hdr(hdr),extra_gl_read_calls=2)
    return result
