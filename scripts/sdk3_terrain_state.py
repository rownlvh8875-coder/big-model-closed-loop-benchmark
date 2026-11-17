"""CPU candidate projections and four raw texels from existing resident RAM."""
import hashlib
import math
import sys
import numpy as np

MAX_RESIDENT_BYTES=1073741824

def _need(condition,message):
    if not condition:raise ValueError(message)

def candidate_samples(hits,local_to_world,elevation_ratio):
    matrix=np.asarray(local_to_world,dtype=float)
    _need(matrix.shape==(4,4) and np.isfinite(matrix).all() and np.allclose(matrix[:,3],[0.,0.,0.,1.],rtol=0,atol=1e-12),'finite affine row-vector terrain matrix')
    _need(type(elevation_ratio) in (int,float) and np.isfinite(elevation_ratio) and 0<elevation_ratio<=65536,'finite positive terrain ratio')
    _need(isinstance(hits,dict) and len(hits)<=5,'at most five existing CPU rays')
    try:inverse=np.linalg.inv(matrix)
    except np.linalg.LinAlgError as error:raise ValueError('invertible terrain matrix') from error
    result=[]
    for name,rows in hits.items():
        _need(isinstance(name,str) and len(name)<=64 and isinstance(rows,list),'bounded named CPU ray hits')
        if not rows:continue
        hit=rows[0];point=np.asarray(hit['position'],dtype=float)
        _need(point.shape==(3,) and np.isfinite(point).all() and type(hit['triangle_index']) is int and hit['triangle_index']>=0,'finite existing candidate hit')
        local=(np.array([*point,1.])@inverse)[:3];uv=local[:2]
        _need(np.isfinite(local).all(),'finite local candidate point')
        attribute=uv if abs(elevation_ratio-1)<.001 else uv*elevation_ratio+.5
        result.append(dict(ray=name,triangle_index=hit['triangle_index'],world_point=point.tolist(),local_point=local.tolist(),heightfield_uv=uv.tolist(),attribute_uv=attribute.tolist(),yellow_uv=(uv*128).tolist()))
    return result

def footprint(size_xy,uv,wrap_u,wrap_v):
    _need(isinstance(size_xy,(list,tuple)) and len(size_xy)==2 and all(type(v) is int and 0<v<=2**24 for v in size_xy),'bounded two-dimensional texture size')
    point=np.asarray(uv,dtype=float);_need(point.shape==(2,) and np.isfinite(point).all() and np.max(np.abs(point))<=2**20,'finite bounded texture coordinate')
    _need(wrap_u in ('repeat','clamp','mirror') and wrap_v in ('repeat','clamp','mirror'),'supported CPU default wrap policy')
    def wrap(index,size,mode):
        if mode=='repeat':return index%size
        if mode=='clamp':return min(size-1,max(0,index))
        index%=2*size;return index if index<size else 2*size-1-index
    x,y=[math.floor(float(value)*size-.5) for value,size in zip(point,size_xy)]
    return [[wrap(i,size_xy[0],wrap_u),wrap(j,size_xy[1],wrap_v)] for i,j in ((x,y),(x+1,y),(x,y+1),(x+1,y+1))]

def resident_window(texture,uv,core):
    if not texture.hasRamImage():return dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=False)
    result=dict(resident_before=True,expected_nbytes=int(texture.getExpectedRamImageSize()),compression=int(texture.getRamImageCompression()))
    expected=result['expected_nbytes']
    if not 0<expected<=MAX_RESIDENT_BYTES:return dict(result,status='UNAVAILABLE_EXTENT')
    width,height=int(texture.getXSize()),int(texture.getYSize());components=int(texture.getNumComponents());component_width=int(texture.getComponentWidth())
    if texture.getZSize()!=1 or texture.getTextureType()!=1 or not 1<=components<=4 or component_width not in (1,2,4) or result['compression']!=int(core.Texture.CMOff):return dict(result,status='UNAVAILABLE_FORMAT')
    if width<=0 or height<=0 or expected!=width*height*components*component_width:return dict(result,status='UNAVAILABLE_EXTENT')
    sampler=texture.getDefaultSampler();codes=[int(sampler.getWrapU()),int(sampler.getWrapV())]
    policy={int(core.SamplerState.WMRepeat):'repeat',int(core.SamplerState.WMClamp):'clamp',int(core.SamplerState.WMMirror):'mirror'}
    if any(code not in policy for code in codes):return dict(result,status='UNAVAILABLE_WRAP')
    modes=[policy[code] for code in codes];points=footprint([width,height],uv,*modes)
    image=texture.getRamImage()
    try:view=memoryview(image).cast('B')
    except (TypeError,ValueError):return dict(result,status='UNAVAILABLE_BUFFER')
    try:
        if len(view)!=expected:return dict(result,status='UNAVAILABLE_EXTENT')
        stride=components*component_width;rows=[];samples=[]
        for x,y in points:
            offset=(y*width+x)*stride;raw=bytes(view[offset:offset+stride]);_need(len(raw)==stride,'bounded existing resident texel')
            rows.append(dict(xy=[x,y],offset=offset,nbytes=stride,raw_hex=raw.hex()));samples.append(raw)
        return dict(result,status='CAPTURED',size_xy=[width,height],num_components=components,component_width=component_width,component_type=int(texture.getComponentType()),byte_order=sys.byteorder,uv=[float(v) for v in uv],wrap_codes=codes,wrap_modes=modes,texels=rows,sample_sha256=hashlib.sha256(b''.join(samples)).hexdigest())
    finally:view.release()

INPUT_NAMES=('PSSMShadowAtlas','pssm_mvps','pssm_nearfar','border_bias','use_pssm','fog','split_count','light_direction','attribute_tex','yellow_tex','road_tex','white_tex','road_normal','road_rough','grass_tex','grass_normal','grass_rough','rock_tex','rock_normal','rock_rough','crosswalk_tex','height_scale','elevation_texture_ratio','grass_tex_ratio')
LIMITS=dict(max_states=4,max_shader_objects=4,max_sources=2,max_file_bytes=262144,max_total_bytes=2097152,max_resident_bytes=MAX_RESIDENT_BYTES,max_points=5,max_cpu_seconds=20)
