"""Synthetic GL state tests; these are not native GPU evidence."""
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.native_shadow_sampler_probe import (
    OpenGLQuery, classify_binding, configure_sampler, terminal_sampler_probe,
)


def binding(**updates):
    r=dict(uniform_type=0x8b5e, bound_texture=8, expected_atlas_texture=8,
           texture_internal_format=0x8cac, use_pssm=1,
           effective_compare_mode=0x884e, min_filter=0x2601, mag_filter=0x2601,
           gl_error_before=0, gl_error_after=0)
    return dict(r, **updates)


@contextmanager
def fake_observer(*args):
    yield


class ShadowSamplerProbeTests(unittest.TestCase):
    def query(self, sampler=9, fail=False):
        q=OpenGLQuery.__new__(OpenGLQuery)
        q.integer=lambda f,*args:f(*args)
        q.error=lambda:0
        q.geti=lambda enum:{0x8b8d:10,0x84e0:0x84c7,0x8069:8}[enum]
        q.getp=lambda *args:1
        def uniform(program,index,cap,length,size,typ,name):
            name.value=b'PSSMShadowAtlas';typ._obj.value=0x8b5e
        q.getu=uniform
        q.loc=lambda program,name:0 if name==b'PSSMShadowAtlas' else 1
        q.getuv=lambda program,location:3 if location==0 else 1
        q.getix=lambda *args:sampler
        q.gets=lambda sampler,enum:0 if enum==0x884c else 0x2601
        q.gett=lambda target,enum:0x884e if enum==0x884c else 0x2601
        def texture_level(*args):
            if fail:raise RuntimeError('query failed')
            return 0x8cac
        q.gettl=texture_level
        q.string=lambda enum:b'synthetic'
        active=[];q.active=active.append
        context=SimpleNamespace(getNativeId=lambda:8)
        texture=SimpleNamespace(prepare_now=lambda *args:context)
        engine=SimpleNamespace(pssm=SimpleNamespace(depth_tex=texture))
        gsg=SimpleNamespace(getPreparedObjects=lambda:None)
        return q,engine,gsg,active

    def test_sampler_object_overrides_texture_compare_and_texture_fallback_is_observed(self):
        for sampler,expected in ((9,'RAW_DEPTH_SAMPLER_CONSISTENT'),
                                 (0,'NONSHADOW_DEPTH_COMPARE_ENABLED')):
            q,engine,gsg,active=self.query(sampler)
            r=q.sample(engine,gsg)
            self.assertEqual(r['texture_compare_mode'],0x884e)
            self.assertEqual(r['classification'],expected)
            self.assertEqual(active,[0x84c3,0x84c7])

    def test_active_texture_restored_even_when_gl_query_raises(self):
        q,engine,gsg,active=self.query(fail=True)
        with self.assertRaisesRegex(RuntimeError,'query failed'):q.sample(engine,gsg)
        self.assertEqual(active,[0x84c3,0x84c7])

    def test_original_filter_is_untouched_and_linear_changes_only_two_filters(self):
        source='uniform sampler2D PSSMShadowAtlas; texture2D(PSSMShadowAtlas, step(ref_depth, depth_sample)'
        class Texture:
            values=[6,6]
            def getMinfilter(self):return self.values[0]
            def getMagfilter(self):return self.values[1]
            def setMinfilter(self,v):self.values=[v,self.values[1]]
            def setMagfilter(self,v):self.values=[self.values[0],v]
        modules={
            'metadrive.version':SimpleNamespace(VERSION='0.4.3'),
            'metadrive.third_party.simplepbr':SimpleNamespace(_load_shader_str=lambda *args:source),
            'panda3d.core':SimpleNamespace(SamplerState=SimpleNamespace(FTShadow=6,FTLinear=1)),
        }
        with patch.dict('sys.modules',modules):
            for mode,expected in (('original',[6,6]),('raw_linear',[1,1])):
                tex=Texture();engine=SimpleNamespace(pssm=SimpleNamespace(depth_tex=tex))
                r=configure_sampler(engine,mode)
                self.assertEqual(r['filters_after'],expected)
                self.assertEqual(tex.values,expected)
                self.assertFalse(r['shader_edited'])
            with self.assertRaises(RuntimeError):configure_sampler(engine,'original')

    def test_actual_depth_atlas_with_nonshadow_sampler_and_compare_is_undefined(self):
        self.assertEqual(classify_binding(binding()), 'NONSHADOW_DEPTH_COMPARE_ENABLED')
        self.assertEqual(classify_binding(binding(effective_compare_mode=0)),
                         'RAW_DEPTH_SAMPLER_CONSISTENT')

    def test_residual_program_wrong_texture_disabled_shadow_and_gl_errors_are_inconclusive(self):
        for changes in ({'bound_texture':9}, {'bound_texture':0,'expected_atlas_texture':0},
                        {'texture_internal_format':0x8058}, {'use_pssm':0},
                        {'gl_error_before':0x500}, {'gl_error_after':0x502},
                        {'uniform_type':0x8b62}, {'effective_compare_mode':123}):
            with self.subTest(changes=changes):
                self.assertEqual(classify_binding(binding(**changes)), 'INCONCLUSIVE_BINDING')

    def test_off_does_not_touch_engine_or_load_gl(self):
        with patch('scripts.native_shadow_sampler_probe.OpenGLQuery', side_effect=AssertionError):
            with terminal_sampler_probe(object(), enabled=False) as receipt:
                self.assertEqual(receipt['status'],'OFF')
                self.assertEqual(receipt['records'],[])

    def test_callbacks_are_restored_when_positive_capture_raises(self):
        class Region:
            callback=None
            def getDrawCallback(self):return self.callback
            def setDrawCallback(self,cb):self.callback=cb
            def clearDrawCallback(self):self.callback=None
        region=Region()
        with patch('scripts.native_shadow_sampler_probe.OpenGLQuery'), \
             patch('scripts.native_shadow_sampler_probe.scene_regions',return_value=[('road',None,region)]), \
             patch('scripts.native_shadow_sampler_probe.state_observer',side_effect=fake_observer), \
             patch('scripts.native_shadow_sampler_probe.make_callback',side_effect=lambda f:f):
            with self.assertRaisesRegex(RuntimeError,'capture failed'):
                with terminal_sampler_probe(object(),enabled=True):
                    self.assertIsNotNone(region.callback)
                    raise RuntimeError('capture failed')
        self.assertIsNone(region.callback)

    def test_preexisting_callback_is_never_overwritten(self):
        sentinel=object()
        region=SimpleNamespace(getDrawCallback=lambda:sentinel)
        with patch('scripts.native_shadow_sampler_probe.OpenGLQuery'), \
             patch('scripts.native_shadow_sampler_probe.scene_regions',return_value=[('road',None,region)]):
            with self.assertRaisesRegex(RuntimeError,'existing'):
                with terminal_sampler_probe(object(),enabled=True):pass


if __name__=='__main__':unittest.main()
