"""Literal CPU coordinates and resident buffers, without importing Panda."""
from types import SimpleNamespace
import hashlib,math,struct,unittest
import numpy as np
from scripts import sdk3_terrain_state as s

CORE=SimpleNamespace(Texture=SimpleNamespace(CMOff=1),SamplerState=SimpleNamespace(WMClamp=0,WMRepeat=1,WMMirror=2))
class Buffer(bytearray):
    def getData(self):raise AssertionError('whole-image copy forbidden')

def texture(data,**changes):
    values=dict(XSize=3,YSize=2,ZSize=1,NumComponents=1,ComponentWidth=4,ComponentType=2,TextureType=1,ExpectedRamImageSize=24,RamImageCompression=1)
    values.update(changes)
    return SimpleNamespace(hasRamImage=lambda:True,getRamImage=lambda:Buffer(data),getDefaultSampler=lambda:SimpleNamespace(getWrapU=lambda:1,getWrapV=lambda:0),**{'get'+k:lambda v=v:v for k,v in values.items()})

class TerrainMath(unittest.TestCase):
    def hits(self):return {'center':[dict(triangle_index=606,position=[14.,26.,38.])],'left':[]}
    def test_row_vector_scaled_translated_projection(self):
        m=[[2.,0.,0.,0.],[0.,3.,0.,0.],[0.,0.,4.,0.],[10.,20.,30.,1.]]
        x=s.candidate_samples(self.hits(),m,4.)[0]
        self.assertEqual(x['world_point'],[14.,26.,38.]);np.testing.assert_allclose(x['local_point'],[2.,2.,2.],rtol=0,atol=1e-14)
        np.testing.assert_allclose(x['attribute_uv'],[8.5,8.5],rtol=0,atol=1e-14);np.testing.assert_allclose(x['yellow_uv'],[256.,256.],rtol=0,atol=1e-14)
        self.assertEqual(x['triangle_index'],606);self.assertEqual(x['ray'],'center')
    def test_ratio_one_uses_unscaled_uv(self):
        x=s.candidate_samples(self.hits(),np.eye(4),1.)[0];self.assertEqual(x['attribute_uv'],[14.,26.]);self.assertEqual(x['heightfield_uv'],[14.,26.])
    def test_nonfinite_or_singular_matrix_reject(self):
        for m in [np.zeros((4,4)),np.eye(3),np.eye(4)*float('nan')]:
            with self.subTest(m=str(m)),self.assertRaises(ValueError):s.candidate_samples(self.hits(),m,4.)
    def test_nonaffine_or_invalid_ratio_reject(self):
        m=np.eye(4);m[0,3]=.5
        with self.assertRaises(ValueError):s.candidate_samples(self.hits(),m,4.)
        for ratio in [0.,-1.,float('inf'),True]:
            with self.subTest(ratio=ratio),self.assertRaises(ValueError):s.candidate_samples(self.hits(),np.eye(4),ratio)
    def test_nearest_only_and_five_candidate_limit(self):
        h={str(i):[dict(triangle_index=i,position=[0.,0.,0.]),dict(triangle_index=999,position=[1.,1.,1.])] for i in range(5)}
        self.assertEqual([x['triangle_index'] for x in s.candidate_samples(h,np.eye(4),4.)],list(range(5)))
        h['sixth']=h['0']
        with self.assertRaises(ValueError):s.candidate_samples(h,np.eye(4),4.)
    def test_invalid_point_rejects(self):
        h=self.hits();h['center'][0]['position']=[1.,float('nan'),3.]
        with self.assertRaises(ValueError):s.candidate_samples(h,np.eye(4),4.)
    def test_literal_half_texel_repeat(self):
        self.assertEqual(s.footprint([4,3],[0.,0.],'repeat','repeat'),[[3,2],[0,2],[3,0],[0,0]])
    def test_literal_clamp_at_edges(self):
        self.assertEqual(s.footprint([4,3],[1.,1.],'clamp','clamp'),[[3,2]]*4)
    def test_mirror_both_negative_and_positive_edges(self):
        self.assertEqual(s.footprint([4,3],[0.,1.],'mirror','mirror'),[[0,2]]*4)
    def test_middle_texel_uses_x_fastest_four_corners(self):
        self.assertEqual(s.footprint([4,4],[.5,.5],'repeat','clamp'),[[1,1],[2,1],[1,2],[2,2]])
    def test_invalid_footprint_inputs_reject(self):
        for shape,uv,u in [([0,4],[0.,0.],'repeat'),([True,4],[0.,0.],'repeat'),([4,4],[float('nan'),0.],'repeat'),([4,4],[0.,0.],'border')]:
            with self.subTest(shape=shape,uv=uv,u=u),self.assertRaises(ValueError):s.footprint(shape,uv,u,'repeat')
    def test_raw_window_reads_only_four_exact_offsets(self):
        raw=b''.join(struct.pack('<f',float(i)) for i in range(6));t=texture(raw)
        x=s.resident_window(t,[.5,.5],CORE);self.assertEqual(x['status'],'CAPTURED');self.assertEqual(x['wrap_modes'],['repeat','clamp'])
        self.assertEqual([r['xy'] for r in x['texels']],[[1,0],[2,0],[1,1],[2,1]])
        self.assertEqual([r['offset'] for r in x['texels']],[4,8,16,20])
        self.assertEqual([struct.unpack('<f',bytes.fromhex(r['raw_hex']))[0] for r in x['texels']],[1.,2.,4.,5.])
        self.assertEqual(x['sample_sha256'],hashlib.sha256(b''.join(bytes.fromhex(r['raw_hex']) for r in x['texels'])).hexdigest())
    def test_no_ram_does_not_call_ram_getters(self):
        x=s.resident_window(SimpleNamespace(hasRamImage=lambda:False),[.5,.5],CORE);self.assertEqual(x,dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=False))
    def test_unsupported_buffer_is_explicit(self):
        t=texture(bytes(24));t.getRamImage=lambda:SimpleNamespace()
        self.assertEqual(s.resident_window(t,[.5,.5],CORE)['status'],'UNAVAILABLE_BUFFER')
    def test_oversized_resident_extent_is_not_touched(self):
        t=texture(bytes(24),ExpectedRamImageSize=2**30+1);t.getRamImage=lambda:(_ for _ in ()).throw(AssertionError('must not access oversized RAM'))
        self.assertEqual(s.resident_window(t,[.5,.5],CORE)['status'],'UNAVAILABLE_EXTENT')
    def test_inconsistent_extent_cannot_produce_captured_bytes(self):
        t=texture(bytes(23));self.assertEqual(s.resident_window(t,[.5,.5],CORE)['status'],'UNAVAILABLE_EXTENT')
    def test_compressed_ram_is_not_sampled_as_texels(self):
        self.assertEqual(s.resident_window(texture(bytes(24),RamImageCompression=3),[.5,.5],CORE)['status'],'UNAVAILABLE_FORMAT')
    def test_default_unsupported_wrap_is_not_silently_repeated(self):
        t=texture(bytes(24));t.getDefaultSampler=lambda:SimpleNamespace(getWrapU=lambda:4,getWrapV=lambda:0)
        self.assertEqual(s.resident_window(t,[.5,.5],CORE)['status'],'UNAVAILABLE_WRAP')
    def test_uninterpreted_multicomponent_window_keeps_full_texel(self):
        t=texture(bytes(range(24)),NumComponents=4,ComponentWidth=1,ComponentType=0)
        x=s.resident_window(t,[.5,.5],CORE);self.assertEqual(x['texels'][0]['raw_hex'],'04050607');self.assertEqual(x['texels'][0]['nbytes'],4)

if __name__=='__main__':unittest.main()
