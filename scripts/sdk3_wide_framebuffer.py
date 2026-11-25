"""Observe the original wide post-process framebuffer during its draw callback."""

from contextlib import contextmanager
import ctypes as ct
from time import perf_counter_ns

from scripts.panda_sdk3_runtime import need

SIZE = (964, 604)
POINT = (329, 306)
PATCH_RADIUS = 1
GL_READ_FRAMEBUFFER = 0x8CA8
GL_DRAW_FRAMEBUFFER = 0x8CA9
GL_COLOR_ATTACHMENT0 = 0x8CE0
GL_PIXEL_PACK_BUFFER = 0x88EB
GL_FRAMEBUFFER_COMPLETE = 0x8CD5
# alignment, row length, skip rows/pixels, swap bytes, lsb first, image height/skip
PACK = (0x0D05, 0x0D02, 0x0D03, 0x0D04, 0x0D00, 0x0D01, 0x806C, 0x806B)


class GL:
    def __init__(self):
        self.lib = ct.CDLL('libGL.so.1')
        u, i, p = ct.c_uint, ct.c_int, ct.c_void_p
        api = (
            ('glXGetCurrentContext', p, ()), ('glGetError', u, ()),
            ('glGetIntegerv', None, (u, ct.POINTER(i))),
            ('glBindFramebuffer', None, (u, u)), ('glBindBuffer', None, (u, u)),
            ('glReadBuffer', None, (u,)), ('glPixelStorei', None, (u, i)),
            ('glCheckFramebufferStatus', u, (u,)),
            ('glGetFramebufferAttachmentParameteriv', None, (u, u, u, ct.POINTER(i))),
            ('glReadPixels', None, (i,i,i,i,u,u,p)),
        )
        for name, result, arguments in api:
            fn = getattr(self.lib,name)
            fn.restype, fn.argtypes = result,arguments
            setattr(self,name,fn)

    def values(self, name, count=1):
        dst=(ct.c_int*count)()
        self.glGetIntegerv(name,dst)
        return list(dst)

    def value(self,name):
        return self.values(name)[0]

    def attachment(self, plane, name):
        number=ct.c_int()
        self.glGetFramebufferAttachmentParameteriv(GL_DRAW_FRAMEBUFFER,plane,name,ct.byref(number))
        return number.value

    def state(self):
        return dict(draw=self.value(0x8CA6),read=self.value(0x8CAA),
                    read_buffer=self.value(0x0C02),draw_buffer=self.value(0x8825),
                    pack_buffer=self.value(0x88ED),pack=[self.value(name) for name in PACK],
                    viewport=self.values(0x0BA2,4))

    def read_patch(self, receipt):
        context=self.glXGetCurrentContext()
        need(bool(context),'active GLX context at wide post-process return')
        before_error=self.glGetError()
        need(before_error==0,f'GL error before observation {before_error:#x}')
        prior=self.state()
        width,height=SIZE
        samples=self.value(0x80A9)
        plane=prior['draw_buffer']
        receipt.update(gl_context=int(context), gl_before=prior, samples=samples, gl_error_before=before_error,
                       attachment=dict(type=self.attachment(plane,0x8CD0),
                                       object=self.attachment(plane,0x8CD1),
                                       encoding=self.attachment(plane,0x8210),
                                       component_type=self.attachment(plane,0x8211),
                                       rgb_bits=[self.attachment(plane,n) for n in (0x8212,0x8213,0x8214)]))
        need(prior['viewport']==[0,0,width,height] and prior['draw']>0 and plane==GL_COLOR_ATTACHMENT0,
             'actual complete 964x604 post-process color attachment')
        need(self.glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE and samples==0,
             'single-sample complete final post-process FBO')
        need(self.glGetError()==0,'valid attachment/state queries')
        x,y=POINT
        rad=PATCH_RADIUS
        edge=rad*2+1
        bottom=height-1-y
        saved_source_read=None
        raw=(ct.c_ubyte*(edge*edge*4))()
        try:
            self.glBindFramebuffer(GL_READ_FRAMEBUFFER,prior['draw'])
            saved_source_read=self.value(0x0C02)
            if saved_source_read!=plane:
                self.glReadBuffer(plane)
            self.glBindBuffer(GL_PIXEL_PACK_BUFFER,0)
            for idx,key in enumerate(PACK):
                self.glPixelStorei(key,int(idx==0))
            receipt['gl_patch_bottom_left']=[x-rad,bottom-rad,edge,edge]
            self.glReadPixels(x-rad,bottom-rad,edge,edge,0x1908,0x1401,raw)
            receipt['extra_gl_read_calls']=1
            receipt['gl_error_after_read']=self.glGetError()
        finally:
            for name,value in zip(PACK,prior['pack'],strict=True):
                self.glPixelStorei(name,value)
            self.glBindBuffer(GL_PIXEL_PACK_BUFFER,prior['pack_buffer'])
            if saved_source_read is not None and saved_source_read!=plane:
                self.glReadBuffer(saved_source_read)
            self.glBindFramebuffer(GL_READ_FRAMEBUFFER,prior['read'])
            receipt['gl_after']=self.state()
            receipt['gl_error_after_restore']=self.glGetError()
            receipt['state_restored']=receipt['gl_after']==prior
        need(receipt['state_restored'] and not receipt['gl_error_after_read'] and not receipt['gl_error_after_restore'],
             'successful read and restored GL state')
        receipt['rgba_bottom_up']=list(raw)


@contextmanager
def post_capture(provider, timing, events, observer=GL):
    """Retain callback ownership and one original upcall on every invocation."""
    from panda3d.core import CallbackObject

    engine=provider.env.engine
    sensor=engine.sensors['bigbench_wide']
    region=sensor.manager.region
    output=sensor.buffer
    need(region.isActive() and region.getDrawCallback() is None and region.getWindow()==output,
         'original active unoccupied wide post-process region')
    need(region.getCamera()!=sensor.cam and [output.getXSize(),output.getYSize()]==list(SIZE),
         'original final filter output and actual dimensions')
    gl=observer()

    def observe(data):
        if timing.active!='wide':
            data.upcall()
            return
        record=dict(callback_enter_ns=perf_counter_ns(),original_draw_returns=0,extra_gl_read_calls=0)
        events.append(record)
        data.upcall()
        record['original_draw_returns']+=1
        record['after_original_draw_ns']=perf_counter_ns()
        try:
            need(len(events)==1,'one wide post-process after-draw observation')
            setup=data.getSceneSetup()
            need(setup is not None and setup.getDisplayRegion()==region,
                 'original final wide region in the draw scene')
            need([setup.getViewportWidth(),setup.getViewportHeight()]==list(SIZE),
                 'original full wide post-process viewport')
            record['region_proven']=True
            gl.read_patch(record)
        except (ValueError, RuntimeError, AttributeError, TypeError) as exc:
            record['failure']=f'{type(exc).__name__}: {exc}'
        finally:
            record['callback_exit_ns']=perf_counter_ns()

    callback=CallbackObject.make(observe)
    region.setDrawCallback(callback)
    try:
        yield
    finally:
        need(region.getDrawCallback()==callback,'owned final wide draw callback')
        region.clearDrawCallback()
        need(region.getDrawCallback() is None,'original wide region restored')


def patch_rgb(images):
    x,y=POINT
    r=PATCH_RADIUS
    return images['wide'][y-r:y+r+1,x-r:x+r+1,:].tolist()


def framebuffer_rgb(record):
    raw=record['rgba_bottom_up']
    edge=PATCH_RADIUS*2+1
    need(len(raw)==edge*edge*4,'exact bounded GL RGBA patch')
    return [[raw[(row*edge+col)*4:(row*edge+col)*4+3] for col in range(edge)]
            for row in range(edge-1,-1,-1)]
