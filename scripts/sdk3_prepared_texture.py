"""Bounded read-only cache metadata and already-resident attribute mip1 windows."""
from scripts import sdk3_terrain_attribute as sparse
POLICY=dict(max_outputs=6,max_gsgs=6,max_textures=3,max_views=8,max_mip_levels=4,max_points=5,max_logical_buffer_bytes=2147483648,max_window_bytes=16,max_total_sample_bytes=80,max_cpu_seconds=20,max_rss_delta_kib=32768)
REFERENCE_SHA256='c4e30a70fcc8200f4b6134c1b3c23681b4d17d7609f6d9bd41c8af73398a0f1b'
FALSE_FLAGS=('hardware_texture_dimensions_proven','actual_upload_bias_proven','active_is_target_pixel_proof','gpu_program_execution_proven','gpu_pixel_owner_proven','unique_cause_proven','repair_proven','stage7_complete')

def minimum_bias(size_xy,cap):
    sparse.previous._need(isinstance(size_xy,list) and len(size_xy)==2 and all(type(v) is int and 0<v<=2**24 for v in size_xy) and type(cap) is int,'bounded texture extent/cached dimension cap')
    if cap<=0:return None
    n=0
    while any(max(1,v>>n)>cap for v in size_xy):n+=1
    return n

def texture_cache(texture,pgo):
    return dict(queued_or_prepared=bool(texture.isPrepared(pgo)),reported_graphics_bytes=int(texture.getDataSizeBytes(pgo)),active_recent_frame=bool(texture.getActive(pgo)),resident_reported=bool(texture.getResident(pgo)),image_modified_or_unprepared=bool(texture.wasImageModified(pgo)))

def mip_metadata(texture):
    return dict(num_views=int(texture.getNumViews()),num_ram_mipmap_images=int(texture.getNumRamMipmapImages()),levels=[dict(level=n,size_xy=[int(texture.getExpectedMipmapXSize(n)),int(texture.getExpectedMipmapYSize(n))],expected_nbytes=int(texture.getExpectedRamMipmapImageSize(n)),resident=bool(texture.hasRamMipmapImage(n)),cached_nbytes=int(texture.getRamMipmapImageSize(n))) for n in range(4)])

class _Mip1:
    def __init__(self,texture):self.texture=texture
    def __getattr__(self,name):return getattr(self.texture,name)
    def hasRamImage(self):return self.texture.hasRamMipmapImage(1)
    def getXSize(self):return self.texture.getExpectedMipmapXSize(1)
    def getYSize(self):return self.texture.getExpectedMipmapYSize(1)
    def getExpectedRamImageSize(self):return self.texture.getExpectedRamMipmapImageSize(1)
    def getRamImage(self):return self.texture.getRamMipmapImage(1)

def mip1_window(texture,uv,core):
    if not texture.hasRamMipmapImage(1):return dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=False)
    if (texture.getNumViews(),texture.getZSize(),texture.getTextureType(),texture.getNumComponents(),texture.getComponentWidth(),texture.getComponentType(),texture.getFormat())!=(1,1,1,1,4,2,3):return dict(status='UNAVAILABLE_LAYOUT')
    return sparse.resident_window(_Mip1(texture),uv,core)
