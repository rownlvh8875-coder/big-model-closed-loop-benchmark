"""Cache getters must remain read-only; mip observations copy only four texels."""
from types import SimpleNamespace
import mmap,struct,unittest
try:from scripts import sdk3_prepared_texture as h
except ImportError:h=None
from tests.test_sdk3_terrain_attribute import NoWholeCopyMap
from tests.test_sdk3_terrain_state import CORE
EXTENT=11264*11264*4
class MipTexture:
    this=701
    def __init__(self,image=None,resident=True):self.image=image;self.resident=resident;self.fetches=0
    def __getattr__(self,name):raise AssertionError('unapproved texture API '+name)
    def hasRamMipmapImage(self,n):return self.resident
    def getRamMipmapImage(self,n):self.fetches+=1;return self.image
    def getExpectedMipmapXSize(self,n):return max(1,22528>>n)
    def getExpectedMipmapYSize(self,n):return max(1,22528>>n)
    def getExpectedRamMipmapImageSize(self,n):return self.getExpectedMipmapXSize(n)*self.getExpectedMipmapYSize(n)*4
    def getRamMipmapImageSize(self,n):return self.getExpectedRamMipmapImageSize(n) if self.resident else 0
    def getNumRamMipmapImages(self):return 2
    def getNumViews(self):return 1
    def getZSize(self):return 1
    def getTextureType(self):return 1
    def getNumComponents(self):return 1
    def getComponentWidth(self):return 4
    def getComponentType(self):return 2
    def getFormat(self):return 3
    def getRamImageCompression(self):return 1
    def getDefaultSampler(self):return SimpleNamespace(getWrapU=lambda:1,getWrapV=lambda:1)
class PreparedHelper(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'prepared texture observation helper is missing')
    def test_minimum_cap_bias_is_cpu_halving_inference(self):
        self.assertEqual(h.minimum_bias([22528,22528],16384),1);self.assertEqual(h.minimum_bias([22528,22528],11264),1);self.assertEqual(h.minimum_bias([22528,22528],8192),2);self.assertEqual(h.minimum_bias([2048,2048],16384),0)
        for cap in (-1,0):self.assertIsNone(h.minimum_bias([22528,22528],cap))
    def test_sparse_mip1_reads_literal_corners_without_whole_copy(self):
        with NoWholeCopyMap(-1,EXTENT,access=mmap.ACCESS_WRITE) as image:
            # UV=.5,.5 yields literal corners (5631,5631)..(5632,5632).
            points=[(5631,5631),(5632,5631),(5631,5632),(5632,5632)]
            for xy,value in zip(points,(.25,.5,.75,1.)):struct.pack_into('=f',image,(xy[1]*11264+xy[0])*4,value)
            view=memoryview(image).toreadonly()
            try:
                t=MipTexture(view);w=h.mip1_window(t,[.5,.5],CORE);self.assertEqual(w['status'],'CAPTURED');self.assertEqual(w['size_xy'],[11264,11264]);self.assertEqual(w['expected_nbytes'],EXTENT);self.assertEqual([r['raw_hex'] for r in w['texels']],['0000803e','0000003f','0000403f','0000803f']);self.assertEqual(t.fetches,1);self.assertEqual(sum(r['nbytes'] for r in w['texels']),16)
            finally:view.release()
    def test_absent_mip_never_fetches_or_generates(self):
        t=MipTexture(resident=False);self.assertEqual(h.mip1_window(t,[.5,.5],CORE),dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=False));self.assertEqual(t.fetches,0)
    def test_multiview_is_unavailable_without_fetch(self):
        t=MipTexture();t.getNumViews=lambda:2;self.assertEqual(h.mip1_window(t,[.5,.5],CORE),dict(status='UNAVAILABLE_LAYOUT'));self.assertEqual(t.fetches,0)
    def test_metadata_bounded_to_four_levels_and_has_no_fetch(self):
        t=MipTexture();x=h.mip_metadata(t);self.assertEqual([r['level'] for r in x['levels']],[0,1,2,3]);self.assertEqual(x['levels'][1]['expected_nbytes'],EXTENT);self.assertEqual(t.fetches,0)
    def test_queue_nonresident_and_retained_bytes_are_not_reinterpreted(self):
        pgo=object();seen=[]
        def value(v):
            def call(p):self.assertIs(p,pgo);seen.append(v);return v
            return call
        t=SimpleNamespace(isPrepared=value(True),getDataSizeBytes=value(507510784),getActive=value(False),getResident=value(False),wasImageModified=value(True))
        x=h.texture_cache(t,pgo);self.assertEqual(x,dict(queued_or_prepared=True,reported_graphics_bytes=507510784,active_recent_frame=False,resident_reported=False,image_modified_or_unprepared=True));self.assertEqual(len(seen),5)
if __name__=='__main__':unittest.main()
