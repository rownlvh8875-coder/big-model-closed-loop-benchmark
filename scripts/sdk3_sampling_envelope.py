"""Conditional CPU sampling models; these never attest GPU format or sampling."""
import hashlib
import math
import struct

FORMATS=('recorded_float32','snorm8_nearest_even','unorm8_nearest_even')
COORDINATES=('recorded_f64','f32_separate','f32_fma_model')
WEIGHT_BITS=(None,8,12)

def need(condition,message):
    if not condition:raise ValueError(message)

def vector(value,length=None):
    need(isinstance(value,(list,tuple)) and (length is None or len(value)==length) and 0<len(value)<=4 and all(type(v) in (int,float) and math.isfinite(v) for v in value),'finite numeric vector')
    return [float(v) for v in value]

def normalize(values,mode):
    values=vector(values);need(mode in FORMATS,'known scalar model')
    if mode=='recorded_float32':return values
    scale,minimum=(127,-1.) if mode=='snorm8_nearest_even' else (255,0.)
    return [round(max(minimum,min(1.,v))*scale)/scale for v in values]

def yellow(value):
    value=vector([value])[0];return .01<value<.11

def _f32(value):return struct.unpack('=f',struct.pack('=f',value))[0]

def attribute_uv(local_uv,ratio,mode):
    uv=vector(local_uv,2);need(max(map(abs,uv))<=2**20 and type(ratio) in (int,float) and math.isfinite(ratio) and 0<ratio<=65536 and mode in COORDINATES,'bounded shader coordinate model')
    if mode=='recorded_f64':return uv if abs(ratio-1)<.001 else [v*ratio+.5 for v in uv]
    uv=[_f32(v) for v in uv];ratio=_f32(ratio)
    if abs(_f32(ratio-1.))<_f32(.001):return uv
    return [_f32((_f32(v*ratio) if mode=='f32_separate' else v*ratio)+.5) for v in uv]

def _size(size):
    need(isinstance(size,list) and len(size)==2 and all(type(v) is int and 0<v<=2**24 for v in size),'bounded two dimensional extent');return size

def fractions(uv,size):
    uv=vector(uv,2);_size(size);need(max(map(abs,uv))<=2**20,'bounded sampling coordinate')
    return [v*n-.5-math.floor(v*n-.5) for v,n in zip(uv,size)]

def _fraction(value):
    value=vector(value,2);need(all(0<=v<=1 for v in value),'same-cell fractions in zero to one');return value

def bilinear(values,fraction,bits=None):
    v=vector(values,4);a,b=_fraction(fraction);need(bits is None or type(bits) is int and bits in (8,12),'known hypothetical weight precision')
    if bits is not None:a,b=[round(x*2**bits)/2**bits for x in (a,b)]
    return (1-a)*(1-b)*v[0]+a*(1-b)*v[1]+(1-a)*b*v[2]+a*b*v[3]

def threshold_roots(values,fraction):
    values=vector(values,4);a,b=_fraction(fraction);current=bilinear(values,[a,b]);slopes=[(1-b)*(values[1]-values[0])+b*(values[3]-values[2]),(1-a)*(values[2]-values[0])+a*(values[3]-values[1])];result=[]
    for axis,(old,slope) in enumerate(zip((a,b),slopes)):
        if slope==0:continue
        for threshold in (.01,.11):
            root=old+(threshold-current)/slope
            if math.isfinite(root) and 0<=root<=1:result.append(dict(axis=axis,threshold=threshold,fraction=root,delta_texels=root-old,threshold_is_yellow=False))
    return result

def conditional_envelope(values,fraction,bits):
    values=vector(values,4);a,b=_fraction(fraction);need(type(bits) is int and bits in (8,12),'known conditional fraction box')
    scaled=[max(-1.,min(1.,v))*127 for v in values];low=[math.floor(v)/127 for v in scaled];high=[math.ceil(v)/127 for v in scaled];box=[(max(0.,v-2**-bits),min(1.,v+2**-bits)) for v in (a,b)]
    lower=min(bilinear(low,[x,y]) for x in box[0] for y in box[1]);upper=max(bilinear(high,[x,y]) for x in box[0] for y in box[1])
    return dict(minimum=lower,maximum=upper,all_yellow=lower>.01 and upper<.11,code_model='adjacent_snorm8_floor_ceil',fraction_box=box,fraction_error=2**-bits,hardware_bound_proven=False)

def _footprint(uv,size,modes):
    uv=vector(uv,2);_size(size);fractions(uv,size);need(isinstance(modes,list) and len(modes)==2 and all(v in ('repeat','clamp','mirror') for v in modes),'known wrap policy')
    xy=[math.floor(v*n-.5) for v,n in zip(uv,size)]
    def wrap(i,n,mode):
        if mode=='repeat':return i%n
        if mode=='clamp':return min(n-1,max(0,i))
        i%=2*n;return i if i<n else 2*n-1-i
    return [[wrap(i,size[0],modes[0]),wrap(j,size[1],modes[1])] for i,j in ((xy[0],xy[1]),(xy[0]+1,xy[1]),(xy[0],xy[1]+1),(xy[0]+1,xy[1]+1))]

def decode_window(window):
    need(isinstance(window,dict) and window.get('status')=='CAPTURED','captured scalar CPU window');size=window.get('size_xy');_size(size)
    need(window.get('resident_before') is True and type(window.get('expected_nbytes')) is int and window['expected_nbytes']==size[0]*size[1]*4<=2**31 and window.get('compression')==1 and window.get('num_components')==1 and window.get('component_width')==4 and window.get('component_type')==2 and window.get('byte_order') in ('little','big'),'uncompressed single float32 window')
    modes=window.get('wrap_modes');points=_footprint(window.get('uv'),size,modes);need(window.get('wrap_codes')==[{'clamp':0,'repeat':1,'mirror':2}[v] for v in modes],'consistent CPU default wrap codes');rows=window.get('texels');need(isinstance(rows,list) and len(rows)==4,'four existing corners');raw=[]
    for row,xy in zip(rows,points):
        need(isinstance(row,dict) and row.get('xy')==xy and type(row.get('offset')) is int and row['offset']==(xy[1]*size[0]+xy[0])*4 and row.get('nbytes')==4 and isinstance(row.get('raw_hex'),str) and len(row['raw_hex'])==8,'exact corner offset and byte extent')
        try:value=bytes.fromhex(row['raw_hex'])
        except ValueError as error:raise ValueError('hexadecimal corner bytes') from error
        need(len(value)==4,'four raw bytes');raw.append(value)
    need(hashlib.sha256(b''.join(raw)).hexdigest()==window.get('sample_sha256'),'raw window digest');return vector([struct.unpack(('<' if window['byte_order']=='little' else '>')+'f',v)[0] for v in raw],4)

def scenario(window,uv,format_mode,weight_bits):
    need(format_mode in FORMATS and (weight_bits is None or type(weight_bits) is int and weight_bits in (8,12)),'known scenario model');vector(uv,2);need(isinstance(window,dict),'CPU window object')
    if window.get('status')!='CAPTURED':
        status=window.get('status');need(status in ('UNAVAILABLE_NOT_RESIDENT','UNAVAILABLE_LAYOUT','UNAVAILABLE_EXTENT','UNAVAILABLE_FORMAT','UNAVAILABLE_WRAP','UNAVAILABLE_BUFFER') and 'texels' not in window,'unavailable window has no invented corners');return dict(status=status)
    values=decode_window(window);points=_footprint(uv,window['size_xy'],window['wrap_modes'])
    if points!=[r['xy'] for r in window['texels']]:return dict(status='UNAVAILABLE_OUTSIDE_CAPTURED_CELL')
    fraction=fractions(uv,window['size_xy']);value=bilinear(normalize(values,format_mode),fraction,weight_bits)
    return dict(status='MODELED',uv=list(uv),fraction=fraction,value=value,yellow=yellow(value),actual_gpu_sample_proven=False)
