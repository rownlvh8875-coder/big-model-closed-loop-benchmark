"""Scoped original-draw observation; all GPU measurements are interventions."""
from contextlib import contextmanager
from pathlib import Path
import ctypes,hashlib,math

LIMITS=dict(max_draws=512,max_queries=100000,max_pixel_readbacks=2048,max_samples=16,max_programs=8,max_shader_files=16,max_shader_file_bytes=262144,max_shader_bytes=4194304,max_trace_bytes=33554432,max_terrain_row_texels=64,max_terrain_rows=2,max_terrain_row_bytes=1024,max_terrain_total_bytes=2048,max_depth_clear_pixels=1)

def need(value,message):
    if not value:raise ValueError(message)

def pixel_gl(width,height,x,y):
    need(all(type(v) is int for v in (width,height,x,y)) and width>0 and height>0 and 0<=x<width and 0<=y<height,'valid top-left source pixel');return x,height-1-y

class Stats(ctypes.Structure):
    _fields_=[(k,ctypes.c_uint32) for k in ('version','error','active','restored')]+[(k,ctypes.c_uint64) for k in ('lookups','forwards','draws','queries','readbacks','blits')]

class Trace:
    def __init__(self,library,folder,expected_sha):
        library=Path(library);need(isinstance(expected_sha,str) and len(expected_sha)==64 and hashlib.sha256(library.read_bytes()).hexdigest()==expected_sha,'exact staged trace library')
        self.lib=ctypes.CDLL(str(library),use_errno=True);self.closed=False;self.lib.dt_configure.argtypes=[ctypes.c_char_p,ctypes.c_uint];self.lib.dt_begin.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int];self.lib.dt_get_stats.argtypes=[ctypes.POINTER(Stats)];self.lib.dt_enable_depth_probe.argtypes=[ctypes.c_int]
        for name in ('dt_configure','dt_begin','dt_end','dt_close','dt_get_stats','dt_enable_depth_probe'):getattr(self.lib,name).restype=ctypes.c_int
        need(self.lib.dt_configure(str(Path(folder)/'draw-trace.jsonl').encode(),512)==0,'trace configure')
    def enable_depth_probe(self,enabled):need(type(enabled) is bool and not self.closed and self.lib.dt_enable_depth_probe(int(enabled))==0,'explicit scoped depth-probe policy')
    def begin(self,phase,x,y):need(not self.closed and self.lib.dt_begin(phase,x,y)==0,'trace begin')
    def end(self):need(self.lib.dt_end()==0,'trace end reports observation failure')
    def stats(self):
        value=Stats();need(self.lib.dt_get_stats(ctypes.byref(value))==0,'trace stats');return {k:int(getattr(value,k)) for k,_ in value._fields_}
    def close(self):
        if not self.closed:self.lib.dt_close();self.closed=True
        return self.stats()

@contextmanager
def scoped_callbacks(regions,journal,tracer,pixel,*,make_callback,receipt,enabled=True,borrowed=lambda:True,target_step=7,expected_returns=None,scene_metadata=None):
    receipt.update(status='OFF' if not enabled else 'INSTALLED',target_region_entries=0,target_region_returns=0,errors=[],callbacks_restored=not enabled,trace_complete=False,scene_observations=[])
    if not enabled:yield receipt;return
    need(regions and len(regions)<=2 and len({phase for phase,_ in regions})==len(regions) and all(region.getDrawCallback() is None for _,region in regions),'unique unoccupied target display regions')
    installed=[];expected_returns=len(regions) if expected_returns is None else expected_returns
    def error(where,exc):receipt['errors'].append(where+': '+type(exc).__name__+': '+str(exc)[:128])
    try:
        for phase,region in regions:
            def callback(data,phase=phase):
                if journal.step!=target_step or journal.camera!='road':data.upcall();return
                receipt['target_region_entries']+=1;begun=False;returned=False
                try:
                    try:
                        need(borrowed(),'target camera still borrowed into origin')
                        if scene_metadata is not None:
                            need(len(receipt['scene_observations'])<8,'bounded draw scene snapshots');scene=dict(scene_metadata(phase,data));scene.update(phase=phase,cpu_capture_label_proves_gpu_pose=False);receipt['scene_observations'].append(scene)
                        tracer.begin(phase,*pixel);begun=True
                    except BaseException as exc:error('begin',exc)
                    data.upcall();returned=True
                finally:
                    if begun:
                        try:tracer.end()
                        except BaseException as exc:error('end',exc)
                    if returned:receipt['target_region_returns']+=1
            cb=make_callback(callback);region.setDrawCallback(cb);installed.append((region,cb))
        yield receipt
    finally:
        for region,cb in reversed(installed):
            if region.getDrawCallback()==cb:region.clearDrawCallback()
            else:receipt['errors'].append('callback ownership changed')
        receipt['callbacks_restored']=all(region.getDrawCallback() is None for _,region in regions);receipt['trace_complete']=receipt['callbacks_restored'] and not receipt['errors'] and receipt['target_region_returns']==expected_returns;receipt['status']='TRACE_RECORDED' if receipt['trace_complete'] else 'TRACE_PARTIAL'

def unproject_depth(mvp,viewport,pixel,depth,*,depth_range=(0.,1.),sample=(.5,.5)):
    import numpy as np
    matrix=np.asarray(mvp,dtype=float);view=np.asarray(viewport,dtype=float);point=np.asarray(pixel,dtype=float);interval=np.asarray(depth_range,dtype=float);sample=np.asarray(sample,dtype=float)
    need(matrix.shape==(16,) and np.isfinite(matrix).all() and view.shape==(4,) and np.isfinite(view).all() and all(v>0 for v in view[2:]) and point.shape==sample.shape==interval.shape==(2,) and np.isfinite(point).all() and np.isfinite(sample).all() and np.isfinite(interval).all() and all(0<=v<=1 for v in sample) and interval[0]!=interval[1] and type(depth) in (int,float) and math.isfinite(depth) and 0<=depth<=1,'finite depth-derived coordinate model')
    need(all(view[i]<=point[i]<view[i]+view[i+2] for i in (0,1)),'pixel inside captured GPU viewport')
    ndc=[2*(point[0]+sample[0]-view[0])/view[2]-1,2*(point[1]+sample[1]-view[1])/view[3]-1,(2*depth-interval[0]-interval[1])/(interval[1]-interval[0])]
    try:local=np.linalg.solve(matrix.reshape((4,4),order='F'),np.array([*ndc,1.]))
    except np.linalg.LinAlgError as exc:raise ValueError('invertible captured GPU MVP') from exc
    need(np.isfinite(local).all() and abs(local[3])>1e-15,'finite unprojected homogeneous point');return dict(local_point=(local[:3]/local[3]).tolist(),ndc=ndc,sample=sample.tolist(),depth=depth,actual_coordinates_proven=False)

def verify_depth_canary_pixels(raw,component_width,component_type,front,back,pixel=(3,3)):
    import numpy as np
    dtype=np.dtype('float32') if component_type==2 and component_width==4 else np.dtype('float16') if component_type==7 and component_width==2 else np.dtype('uint8') if component_type==0 and component_width==1 else None
    need(dtype is not None and type(raw) is bytes and len(raw)==256*component_width<=8192 and len(front)==len(back)==3 and front!=back,'bounded distinct challenged depth pixels')
    x,y=pixel;need(type(x) is int and type(y) is int and 0<=x<8 and 0<=y<8,'8x8GL target');pixels=np.frombuffer(raw,dtype=dtype).reshape(8,8,4);scale=255 if component_width==1 else 1;expected=np.broadcast_to(np.asarray([*front,1.])*scale,(8,8,4)).copy();expected[y,x]=np.asarray([*back,1.])*scale;need(np.array_equal(pixels,expected),'exact one target changed and63 foreground pixels preserved')
    return dict(status='ONE_PIXEL_DEPTH_PROBE_VERIFIED',verified_unchanged_pixels=63,mutated_pixel_gl=[x,y],raw_origin='GL_bottom_left',nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
