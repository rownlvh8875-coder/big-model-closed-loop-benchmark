"""Bounded return-buffer CPU wire reader. No renderer loading or native authority.

The bytes describe after-call memory, not successful/fresh GPU writes. Every label
and borrowed extent originates with an as-yet unqualified caller/ABI adapter.
"""
from dataclasses import dataclass
import struct

HEADER=struct.Struct('<8sIIQ32sIIIIQiiiiIIIIIIIIQQQQ')
FOOTER=struct.Struct('<8sII32sQQQQQII')
MAX_WIRE=64*1024*1024
MAX_SPAN=8*1024*1024

def _need(ok,message):
    if not ok:raise ValueError(message)

def _integer(value,lo,hi):
    return type(value) is int and lo<=value<=hi

def _nonce(value):
    return type(value) is bytes and len(value)==32 and any(value)

def _authority():
    return dict(native_admitted=False,gpu_write_proven=False,physical_frame_proven=False)

@dataclass(frozen=True)
class Record:
    index:int
    nonce:bytes
    host_call:int
    requested_camera:int
    producer_camera:int
    read_fbo:int
    context_tag:int
    x:int
    y:int
    width:int
    height:int
    format:int
    type:int
    alignment:int
    row_length:int
    skip_pixels:int
    skip_rows:int
    pack_buffer:int
    label_basis:int
    payload_bytes:int
    row_stride:int
    first_pixel_offset:int
    capacity:int
    payload:bytes

def _validate(record):
    _need(type(record) is Record,'record type')
    for name in ('host_call','requested_camera','producer_camera','read_fbo','format','type','alignment',
                 'row_length','skip_pixels','skip_rows','pack_buffer','label_basis'):
        _need(_integer(getattr(record,name),0,2**32-1),'unsigned metadata')
    for name in ('index','context_tag','payload_bytes','row_stride','first_pixel_offset','capacity'):
        _need(_integer(getattr(record,name),0,2**64-1),'unsigned extent')
    _need(_nonce(record.nonce) and 1<=record.index<=24 and 1<=record.host_call<=12,'record identity')
    _need(record.requested_camera==(1 if record.host_call%2 else 2),'requester sequence')
    _need(record.producer_camera<=2 and record.label_basis<=1 and
          (record.producer_camera==0)==(record.label_basis==0),'producer metadata')
    _need(record.context_tag>0 and record.pack_buffer==0,'context/PBO')
    _need(_integer(record.x,-2**31,2**31-1) and _integer(record.y,-2**31,2**31-1),'coordinates')
    _need(_integer(record.width,1,964) and _integer(record.height,1,604),'shape')
    components={0x1907:3,0x1908:4,0x80e0:3,0x80e1:4}.get(record.format)
    _need(components is not None and record.type==0x1401,'component type')
    _need(record.alignment in (1,2,4,8) and record.row_length<=4096 and
          record.skip_pixels<=4096 and record.skip_rows<=4096,'pack state')
    row=record.row_length or record.width
    _need(record.skip_pixels+record.width<=row,'overlapping rows')
    stride=(row*components+record.alignment-1)//record.alignment*record.alignment
    offset=record.skip_rows*stride+record.skip_pixels*components
    span=offset+(record.height-1)*stride+record.width*components
    _need(record.row_stride==stride and record.first_pixel_offset==offset and
          0<span<=record.capacity<=MAX_SPAN,'borrowed extent')
    _need(record.payload_bytes==record.width*record.height*components and
          type(record.payload) is bytes and len(record.payload)==record.payload_bytes,'payload extent')
    return components

def decode_stream(blob,*,expected_nonce,expected_windows,reads_per_window,enabled):
    """Accept only a complete CPU window, bound by externally supplied expectations."""
    _need(_nonce(expected_nonce),'expected nonce')
    _need(_integer(expected_windows,1,12) and _integer(reads_per_window,1,2) and type(enabled) is bool,'expected window')
    _need(type(blob) is bytes and 96<=len(blob)<=MAX_WIRE,'wire size')
    records=[];offset=0
    while blob[offset:offset+8]==b'RBRET001':
        _need(enabled and len(records)<24 and len(blob)-offset>=160,'data header extent')
        h=HEADER.unpack_from(blob,offset)
        _need(h[1:3]==(1,160),'data version')
        n=h[22]
        _need(n<=964*604*4 and offset+160+n<=len(blob)-96,'payload boundary/footer reserve')
        record=Record(*h[3:],blob[offset+160:offset+160+n]);_validate(record)
        _need(record.nonce==expected_nonce and record.index==len(records)+1,'nonce/index drift')
        _need(record.host_call==len(records)//reads_per_window+1 and record.host_call<=expected_windows,'window count/order')
        records.append(record);offset+=160+n
    _need(len(blob)-offset==96,'terminal footer missing or trailing bytes')
    f=FOOTER.unpack_from(blob,offset)
    _need(f[:4]==(b'RBEND001',1,96,expected_nonce),'terminal identity')
    expected=expected_windows*reads_per_window
    captured=expected if enabled else 0
    _need(f[4:]==(expected,captured,captured,offset,expected_windows,0,int(enabled)),'terminal counters/status')
    _need(len(records)==captured,'record count')
    return dict(records=tuple(records),footer=dict(forwards=f[4],attempts=f[5],captured=f[6],
        data_wire_bytes=f[7],closed_windows=f[8],error=f[9],enabled=bool(f[10])),
        cpu_window_closed=True,**_authority())

def normalize_rgb(record):
    """Normalize packed original component bytes to top-down RGB, without mutation."""
    n=_validate(record);w=record.width;h=record.height
    out=bytearray(w*h*3);bgr=record.format in (0x80e0,0x80e1)
    for top in range(h):
        src=(h-1-top)*w*n;row=record.payload[src:src+w*n];dst=top*w*3;end=dst+w*3
        out[dst:end:3]=row[2 if bgr else 0::n]
        out[dst+1:end:3]=row[1::n]
        out[dst+2:end:3]=row[0 if bgr else 2::n]
    return bytes(out)

def match_cpu_candidate(records,*,nonce,host_call,camera,context_tag,width,height,rgb):
    """Return byte candidates only; even a unique match has no native/frame authority."""
    _need(type(records) in (list,tuple) and len(records)<=24,'candidate bound')
    _need(_nonce(nonce) and _integer(host_call,1,12) and _integer(camera,1,2) and
          camera==(1 if host_call%2 else 2) and _integer(context_tag,1,2**64-1),'query identity')
    _need(_integer(width,1,964) and _integer(height,1,604) and type(rgb) is bytes and len(rgb)==width*height*3,'query shape')
    matches=[];unknown=[]
    for r in records:
        _validate(r)
        if (r.nonce,r.host_call,r.requested_camera,r.context_tag,r.width,r.height)!=(nonce,host_call,camera,context_tag,width,height):continue
        if normalize_rgb(r)!=rgb:continue
        if r.producer_camera==0:unknown.append(r.index)
        elif r.producer_camera==camera:matches.append(r.index)
    status=('insufficient_producer_metadata' if unknown else 'unique_cpu_byte_candidate' if len(matches)==1
            else 'ambiguous_cpu_byte_candidates' if matches else 'no_cpu_byte_candidate')
    return dict(status=status,record_indices=matches,unknown_producer_indices=unknown,**_authority())
