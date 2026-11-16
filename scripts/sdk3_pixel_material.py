"""CPU-only UV math and bounded resident/readonly texture evidence."""
from pathlib import Path
import hashlib,os,re,stat
import numpy as np

MAX_FILE=8*1024**2
MAX_TOTAL=16*1024**2


def interpolate_uv(values,barycentric):
    uv=np.asarray(values,dtype=float);b=np.asarray(barycentric,dtype=float)
    if uv.shape!=(3,2) or b.shape!=(3,) or not np.isfinite(uv).all() or not np.isfinite(b).all() or abs(float(b.sum())-1)>1e-9 or np.min(b)<-1e-9 or np.max(b)>1+1e-9:raise ValueError('finite triangle UV and barycentric weights')
    return (b@uv).tolist()


def transform_uv(uv,matrix):
    uv=np.asarray(uv,float);matrix=np.asarray(matrix,float)
    if uv.shape!=(2,) or matrix.shape!=(4,4) or not np.isfinite(uv).all() or not np.isfinite(matrix).all():raise ValueError('finite 2D UV and texture matrix')
    # Retain all four coordinates; shader/projective division is not assumed.
    return (np.array([*uv,0.,1.])@matrix).tolist()


class BoundedStore:
    def __init__(self,folder,max_file=MAX_FILE,max_total=MAX_TOTAL):self.folder=Path(folder);self.max_file=max_file;self.max_total=max_total;self.used=0;self.sequence=0
    def fits(self,size):return type(size) is int and 0<size<=self.max_file and self.used+size<=self.max_total
    def save(self,data,kind):
        if not isinstance(data,(bytes,bytearray)) or not re.fullmatch('[a-z0-9_-]+',kind):raise ValueError('raw bytes and safe evidence kind')
        if not self.fits(len(data)):return dict(status='UNAVAILABLE_LIMIT')
        self.sequence+=1;name=f'material-{self.sequence:03d}-{kind}.bin'
        with (self.folder/name).open('xb') as f:f.write(data)
        self.used+=len(data);return dict(status='CAPTURED',file=name,nbytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    def copy_asset(self,path,roots):
        if not str(path):return dict(status='UNAVAILABLE_NO_PATH')
        try:
            path=Path(path).resolve();roots=[Path(root).resolve() for root in roots]
            if not any(path.is_relative_to(root) for root in roots):return dict(status='UNAVAILABLE_OUTSIDE_ASSET_ROOT')
            if path.suffix.lower() not in ('.png','.jpg','.jpeg','.bmp','.tga','.dds','.ktx','.txo','.rgb','.rgba','.ppm','.pgm','.pbm','.exr'):return dict(status='UNAVAILABLE_FILE_TYPE')
            size=path.stat().st_size
            if not self.fits(size):return dict(status='UNAVAILABLE_LIMIT')
            with path.open('rb') as f:
                if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):return dict(status='UNAVAILABLE_NOT_REGULAR')
                data=f.read(min(self.max_file,self.max_total-self.used)+1)
            result=self.save(data,'asset');result['source_path']=str(path);return result
        except OSError as error:return dict(status='UNAVAILABLE_READ_ERROR',error_type=type(error).__name__)


def capture_cached_ram(texture,store):
    if not texture.hasRamImage():return dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=False)
    expected=int(texture.getExpectedRamImageSize());compression=int(texture.getRamImageCompression())
    if not store.fits(expected):return dict(status='UNAVAILABLE_LIMIT',resident_before=True,expected_nbytes=expected,compression=compression)
    image=texture.getRamImage();size=len(image)
    if not store.fits(size):return dict(status='UNAVAILABLE_LIMIT',resident_before=True,expected_nbytes=expected,compression=compression)
    raw=image.getData()
    if len(raw)!=size:raise ValueError('resident RAM byte extent changed')
    result=store.save(raw,'ram');result.update(resident_before=True,expected_nbytes=expected,compression=compression);return result
