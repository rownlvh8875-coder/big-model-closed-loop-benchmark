"""Sparse large-buffer reads with real pages and bounded physical memory."""
from types import SimpleNamespace
import copy,mmap,resource,struct,sys,unittest
from scripts import sdk3_terrain_attribute as sparse,sdk3_terrain_state as old
from tests.test_sdk3_terrain_state import CORE

SIZE_XY=[22528,22528]
EXTENT=2030043136
class NoWholeCopyMap(mmap.mmap):
    def __bytes__(self):raise AssertionError('whole mmap copy forbidden')
    def getData(self):raise AssertionError('whole RAM copy forbidden')

def large_texture(readonly,*,extent=EXTENT):
    calls=[];t=SimpleNamespace(hasRamImage=lambda:True,getExpectedRamImageSize=lambda:extent,getRamImageCompression=lambda:1,getXSize=lambda:22528,getYSize=lambda:22528,getZSize=lambda:1,getTextureType=lambda:1,getNumComponents=lambda:1,getComponentWidth=lambda:4,getComponentType=lambda:2,getDefaultSampler=lambda:SimpleNamespace(getWrapU=lambda:1,getWrapV=lambda:1),getRamImage=lambda:(calls.append('getRamImage') or readonly),getRamImageAs=lambda *a:(_ for _ in ()).throw(AssertionError('whole conversion forbidden')))
    return t,calls

class SparseAttribute(unittest.TestCase):
    def test_real_2030043136_byte_readonly_map_reads_far_end_without_full_copy(self):
        self.assertGreater(sys.maxsize,2**31);self.assertTrue(sys.platform.startswith('linux'))
        xy=[[22527,22527],[0,22527],[22527,0],[0,0]];values=[.125,.25,.5,1.]
        with NoWholeCopyMap(-1,EXTENT,access=mmap.ACCESS_WRITE) as mapping:
            for point,value in zip(xy,values):struct.pack_into('=f',mapping,(point[1]*22528+point[0])*4,value)
            view=memoryview(mapping).toreadonly()
            try:
                texture,calls=large_texture(view);before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                original=old.resident_window(texture,[1.,1.],CORE);self.assertEqual(original['status'],'UNAVAILABLE_EXTENT');self.assertEqual(calls,[])
                result=sparse.resident_window(texture,[1.,1.],CORE);after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                self.assertEqual(result['status'],'CAPTURED');self.assertEqual(result['expected_nbytes'],EXTENT);self.assertEqual([r['xy'] for r in result['texels']],xy)
                self.assertGreater(result['texels'][0]['offset'],2**30);self.assertEqual([struct.unpack('=f',bytes.fromhex(r['raw_hex']))[0] for r in result['texels']],values)
                self.assertEqual(sum(r['nbytes'] for r in result['texels']),16);self.assertEqual(calls,['getRamImage']);self.assertLess(after-before,32*1024)
                self.assertEqual(old.MAX_RESIDENT_BYTES,2**30)
            finally:view.release()
    def test_over_2gib_logical_extent_is_rejected_without_buffer_access(self):
        texture,calls=large_texture(None,extent=2**31+1);result=sparse.resident_window(texture,[1.,1.],CORE);self.assertEqual(result['status'],'UNAVAILABLE_EXTENT');self.assertEqual(calls,[])
    def test_nonresident_does_not_require_any_ram_api(self):
        self.assertEqual(sparse.resident_window(SimpleNamespace(hasRamImage=lambda:False),[0.,0.],CORE),dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=False))
    def test_budget_counts_actual_raw_texel_bytes_not_logical_extent(self):
        window=dict(status='CAPTURED',expected_nbytes=EXTENT,texels=[dict(nbytes=16)]*4);x=dict(textures=[dict(windows=[dict(window=copy.deepcopy(window)) for _ in range(5)]) for _ in range(3)])
        self.assertEqual(sparse.sample_bytes(x),960)
        self.assertEqual(sparse.sample_bytes(dict(textures=[dict(windows=[dict(window=dict(status='UNAVAILABLE_EXTENT'))])])),0)
    def test_window_over_64_bytes_or_excess_windows_reject(self):
        for window in [dict(status='CAPTURED',texels=[dict(nbytes=17)]*4),dict(status='CAPTURED',texels=[dict(nbytes=16)]*5),dict(status='CAPTURED',texels=[dict(nbytes=True)]*4)]:
            with self.subTest(window=window),self.assertRaises(ValueError):sparse.sample_bytes(dict(textures=[dict(windows=[dict(window=window)])]))
        with self.assertRaises(ValueError):sparse.sample_bytes(dict(textures=[dict(windows=[dict(window=dict(status='UNAVAILABLE_EXTENT'))]*6)]))
    def test_old_function_globals_and_limits_are_not_changed(self):
        before=old.resident_window.__globals__['MAX_RESIDENT_BYTES'];proxy=sparse.proxy();self.assertEqual(before,2**30);self.assertEqual(proxy.MAX_RESIDENT_BYTES,2**31);self.assertEqual(proxy.LIMITS['max_resident_bytes'],2**31);self.assertIs(proxy.candidate_samples,old.candidate_samples);self.assertEqual(old.LIMITS['max_resident_bytes'],2**30)

if __name__=='__main__':unittest.main()
