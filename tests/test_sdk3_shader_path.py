"""Literal CPU contracts; no Panda imports or renderer required."""
from pathlib import Path
import hashlib,tempfile,unittest
import numpy as np
from scripts import sdk3_shader_path as s

class ShaderPathTests(unittest.TestCase):
    def test_shader_loader_preserves_define_order_aliases_and_version(self):
        raw='// intro\n#version 120\nvarying vec2 uv;\n'
        expected='#version 120\n#define MAX_LIGHTS 2\n#define USE_NORMAL_MAP \n#define p3d_TextureBaseColor p3d_TextureModulate\n#define p3d_TextureMetalRoughness p3d_TextureSelector\n#define p3d_TextureNormal p3d_TextureNormal\n#define p3d_TextureEmission p3d_TextureEmission\n#line 1\n// intro\nvarying vec2 uv;\n'
        defines={'MAX_LIGHTS':2,'USE_NORMAL_MAP':''}
        self.assertEqual(s.variant(raw,defines,'fragment'),expected);self.assertEqual(defines,{'MAX_LIGHTS':2,'USE_NORMAL_MAP':''})
    def test_use330_converts_stage_qualifiers_and_missing_version_rejects(self):
        raw='#version 120\nvarying vec2 uv;\nattribute vec3 v;'
        self.assertIn('#version 330',s.variant(raw,{'USE_330':''},'vertex'));self.assertIn('out vec2 uv;',s.variant(raw,{'USE_330':''},'vertex'));self.assertIn('in vec3 v;',s.variant(raw,{'USE_330':''},'vertex'));self.assertIn('in vec2 uv;',s.variant(raw,{'USE_330':''},'fragment'))
        with self.assertRaises(ValueError):s.variant('no version',{},'fragment')
    def test_pipeline_default_disables_normal_map_and_enables_emission(self):
        config=dict(max_lights=8,use_normal_maps=False,use_emission_maps=True,enable_fog=False,use_occlusion_maps=False,use_330=False,enable_hardware_skinning=True,exposure=1.)
        self.assertEqual(s.pipeline_defines(config),{'MAX_LIGHTS':8,'USE_EMISSION_MAP':'','ENABLE_SKINNING':''})
        config['use_normal_maps']=True;self.assertIn('USE_NORMAL_MAP',s.pipeline_defines(config))
        config['use_330']='false'
        with self.assertRaises(ValueError):s.pipeline_defines(config)
    def test_tonemap_literal_vectors_clamp_before_curve_without_quantization(self):
        np.testing.assert_allclose(s.tonemap([.004,1.004,-2]),[0.,6.7/7.96,0.],rtol=1e-14,atol=0)
        np.testing.assert_allclose(s.tonemap([[.002,.502,-1]],2),[[0.,6.7/7.96,0.]],rtol=1e-14,atol=0)
    def test_tonemap_invalid_numbers_and_shape_reject(self):
        for rgb,exposure in [([np.nan,0,1],1),([0,1],1),([0,1,2],-1),([0,1,2],np.inf)]:
            with self.subTest(rgb=rgb),self.assertRaises(ValueError):s.tonemap(rgb,exposure)
    def test_text_store_utf8_sha_limits_and_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            store=s.TextStore(d,max_file=4,max_total=6);row=store.save('가','scene');p=Path(d)/row['file'];self.assertEqual(p.read_bytes(),'가'.encode());self.assertEqual(row['nbytes'],3);self.assertEqual(row['sha256'],hashlib.sha256('가'.encode()).hexdigest());store.save('abc','tone')
            with self.assertRaises(ValueError):store.save('x','over')
            with self.assertRaises(ValueError):s.TextStore(d,max_file=2).save('가','large')
            with self.assertRaises(ValueError):s.TextStore(d).save('x','../escape')
            self.assertEqual(len(list(Path(d).iterdir())),2)
if __name__=='__main__':unittest.main()
