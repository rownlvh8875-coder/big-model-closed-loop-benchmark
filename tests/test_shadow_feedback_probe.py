"""CPU state contracts and synthetic bindings, never native GPU evidence."""
from contextlib import contextmanager
import importlib
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import patch


def feedback(test):
    test.assertIsNotNone(importlib.util.find_spec('scripts.native_shadow_feedback_probe'),
                         'feedback guard and terminal observer are not implemented')
    return importlib.import_module('scripts.native_shadow_feedback_probe')


def binding(camera='shadow0', guard=False, linear=False):
    shadow = camera.startswith('shadow')
    placeholder = shadow and guard
    return dict(camera=camera, program=10, uniform_type=0x8b5e, unit=3,
        bound_texture=9 if placeholder else 8, expected_atlas_texture=8,
        expected_placeholder_texture=9 if guard else 0,
        texture_internal_format=0x8058 if placeholder else 0x8cac,
        use_pssm=0 if placeholder else 1, sampler=1,
        texture_compare_mode=0 if placeholder or linear else 0x884e,
        effective_compare_mode=0 if placeholder or linear else 0x884e,
        min_filter=0x2601, mag_filter=0x2601,
        gl_error_before=0, gl_error_after=0, draw_framebuffer=1 if shadow else 2,
        framebuffer_samples=0 if shadow else 4, framebuffer_sample_buffers=0 if shadow else 1,
        attachments=dict(depth=dict(object_type=0x1702 if shadow else 0x8d41,
            object_name=8, texture_level=0 if shadow else None),
            color0=dict(object_type=0 if shadow else 0x1702,
                object_name=0 if shadow else 11, texture_level=None if shadow else 0)),
        comparison_state_source='sampler_object', query_duration_s=.001,
        driver=dict(vendor='synthetic', renderer='synthetic', version='synthetic'))


@contextmanager
def fake_observer(*args):
    yield


class FeedbackBindingsTests(unittest.TestCase):
    def test_actual_framebuffer_sample_counts_are_queried_and_query_errors_rejected(self):
        f = feedback(self)
        for error in (0, 0x502):
            q = f.FeedbackOpenGLQuery.__new__(f.FeedbackOpenGLQuery)
            q.integer = lambda fn, *args: fn(*args)
            q.geti = lambda enum: {0x8ca6: 22, 0x80a9: 4, 0x80a8: 1}[enum]
            q.get_attachment = lambda target, point, parameter: {
                0x8d00: {0x8cd0: 0x8d41, 0x8cd1: 8},
                0x8ce0: {0x8cd0: 0x1702, 0x8cd1: 11, 0x8cd2: 0},
            }[point][parameter]
            q.error = lambda: error
            row = binding('road')
            # The source row does not supply these new actual-GL observations.
            del row['framebuffer_samples']; del row['framebuffer_sample_buffers']
            with patch('scripts.native_shadow_sampler_probe.OpenGLQuery.sample', return_value=row):
                observed = q.sample(SimpleNamespace(), None, 'road')
            self.assertEqual(observed.get('framebuffer_samples'), 4)
            self.assertEqual(observed.get('framebuffer_sample_buffers'), 1)
            self.assertEqual(observed['gl_error_after'], error)
            if error:
                with self.assertRaises(ValueError):
                    f.validate_feedback_binding(observed, guarded=False, linear=False)
            else:
                f.validate_feedback_binding(observed, guarded=False, linear=False)

    def test_framebuffer_sample_counts_must_be_nonnegative_integers_and_consistent(self):
        f = feedback(self)
        for samples, buffers in ((0, 0), (1, 1), (4, 1)):
            row = binding('road')
            row.update(framebuffer_samples=samples, framebuffer_sample_buffers=buffers,
                       classification='RGB_ATLAS_COMPARE_ENABLED')
            f.validate_feedback_binding(row, guarded=False, linear=False)
        for samples, buffers in ((None, 1), (4, None), (-1, 1), (4, -1),
                                 (True, 1), (4, False), (4.0, 1), (4, 1.0),
                                 (float('nan'), 1), (4, float('inf')), (0, 1), (4, 0), (4, 2)):
            row = binding('road')
            row.update(framebuffer_samples=samples, framebuffer_sample_buffers=buffers,
                       classification='RGB_ATLAS_COMPARE_ENABLED')
            with self.subTest(samples=samples, buffers=buffers):
                with self.assertRaises(ValueError):
                    f.validate_feedback_binding(row, guarded=False, linear=False)

    def test_attachment_queries_do_not_conflate_renderbuffer_names_or_lose_gl_errors(self):
        f = feedback(self)
        q = f.FeedbackOpenGLQuery.__new__(f.FeedbackOpenGLQuery)
        q.integer = lambda fn, *args: fn(*args)
        calls = []
        def attachment(target, point, parameter):
            calls.append((point, parameter))
            return {0x8cd0: 0x8d41, 0x8cd1: 8}[parameter]
        q.get_attachment = attachment
        self.assertEqual(q.attachment(0x8d00), dict(object_type=0x8d41, object_name=8, texture_level=None))
        self.assertNotIn((0x8d00, 0x8cd2), calls)
        q.geti = lambda enum: 1
        q.error = lambda: 0
        engine = SimpleNamespace()
        row = binding(); row['gl_error_after'] = 0x502
        with patch('scripts.native_shadow_sampler_probe.OpenGLQuery.sample', return_value=row):
            observed = q.sample(engine, None, 'shadow0')
        self.assertEqual(observed['gl_error_after'], 0x502)
        self.assertEqual(observed['classification'], 'INCONCLUSIVE_BINDING')

    def test_texture_namespace_and_mip_level_define_shadow_alias(self):
        f = feedback(self)
        row = binding()
        self.assertEqual(f.classify_feedback_binding(row), 'SHADOW_ATLAS_READ_WRITE_BINDING_HAZARD')
        for key, value in (('object_type', 0x8d41), ('object_name', 99), ('texture_level', 1)):
            row = binding(); row['attachments']['depth'][key] = value
            self.assertEqual(f.classify_feedback_binding(row), 'INCONCLUSIVE_BINDING')

    def test_guard_and_rgb_binding_contract_rejects_leaks_and_wrong_sampler(self):
        f = feedback(self)
        for guard in (False, True):
            for linear in (False, True):
                for camera in ('shadow0', 'shadow1', 'road', 'wide'):
                    row = binding(camera, guard, linear)
                    row['classification'] = f.classify_feedback_binding(row)
                    f.validate_feedback_binding(row, guarded=guard, linear=linear)
                    for key, value in (('use_pssm', 1-row['use_pssm']),
                                       ('bound_texture', 99), ('uniform_type', 0x8b62),
                                       ('gl_error_after', 0x502), ('min_filter', 0x2600)):
                        bad = dict(row, **{key: value})
                        with self.assertRaises(ValueError):
                            f.validate_feedback_binding(bad, guarded=guard, linear=linear)

    def test_off_installs_nothing_and_existing_callback_is_preserved(self):
        f = feedback(self)
        with patch.object(f, 'FeedbackOpenGLQuery', side_effect=AssertionError):
            with f.terminal_feedback_probe(object(), enabled=False) as receipt:
                self.assertEqual(receipt['records'], [])
                self.assertEqual(receipt['status'], 'OFF')
        sentinel = object()
        region = SimpleNamespace(getDrawCallback=lambda: sentinel)
        with patch.object(f, 'FeedbackOpenGLQuery'), \
             patch.object(f, 'feedback_regions', return_value=[('road', None, region)]):
            with self.assertRaisesRegex(RuntimeError, 'existing'):
                with f.terminal_feedback_probe(object(), enabled=True):
                    self.fail('unexpected observer setup')

    def test_observer_callbacks_removed_on_capture_and_partial_setup_failures(self):
        f = feedback(self)
        class Region:
            callback = None
            fail = False
            def getDrawCallback(self): return self.callback
            def setDrawCallback(self, cb):
                self.callback = cb
                if self.fail: raise RuntimeError('install failed')
            def clearDrawCallback(self): self.callback = None
        for partial in (False, True):
            first, second = Region(), Region(); second.fail = partial
            with patch.object(f, 'FeedbackOpenGLQuery'), \
                 patch.object(f, 'feedback_regions', return_value=[('road', None, first), ('shadow0', None, second)]), \
                 patch.object(f, 'feedback_state_observer', side_effect=fake_observer), \
                 patch.object(f, 'make_callback', side_effect=lambda fn: fn):
                with self.assertRaises(RuntimeError):
                    with f.terminal_feedback_probe(object(), enabled=True):
                        raise RuntimeError('capture failed')
            self.assertIsNone(first.callback)
            self.assertIsNone(second.callback)


@unittest.skipUnless(importlib.util.find_spec('panda3d'), 'Panda CPU state-contract runs in native CI')
class PandaGuardTests(unittest.TestCase):
    def engine(self):
        from panda3d.core import Camera, NodePath, Texture, SamplerState
        cameras = [NodePath(Camera('shadow'+str(i))) for i in range(2)]
        tex = Texture('depth'); tex.setMinfilter(SamplerState.FTShadow); tex.setMagfilter(SamplerState.FTShadow)
        rig = SimpleNamespace(get_camera=lambda i: cameras[i])
        return SimpleNamespace(pssm=SimpleNamespace(camera_rig=rig, num_splits=2, depth_tex=tex)), cameras

    def test_guard_has_only_two_high_priority_inputs_and_inherits_shader(self):
        f = feedback(self)
        from panda3d.core import RenderState, ShaderAttrib, ShaderInput, Texture
        engine, cameras = self.engine()
        result = f.setup_shadow_guard(engine, enabled=True)
        self.assertTrue(result['enabled'])
        for camera in cameras:
            state = camera.node().getInitialState()
            attrib = state.getAttrib(ShaderAttrib)
            self.assertEqual(state, RenderState.make(attrib))
            self.assertEqual(attrib.clearShaderInput('use_pssm').clearShaderInput('PSSMShadowAtlas'), ShaderAttrib.make())
            self.assertIsNone(attrib.getShader())
            self.assertFalse(attrib.hasShader())
            self.assertEqual(attrib.getShaderInput('use_pssm').getPriority(), 1000000)
            self.assertEqual(attrib.getShaderInput('PSSMShadowAtlas').getPriority(), 1000000)
            inherited = ShaderAttrib.make().setShaderInput(ShaderInput('use_pssm', True))
            composed = RenderState.make(inherited).compose(state).getAttrib(ShaderAttrib)
            self.assertEqual(composed.getShaderInput('use_pssm').getVector()[0], 0.)
            placeholder = attrib.getShaderInput('PSSMShadowAtlas').getTexture()
            self.assertEqual((placeholder.getXSize(), placeholder.getYSize()), (1, 1))
            self.assertEqual(placeholder.getFormat(), Texture.FRgba8)
            self.assertEqual(bytes(placeholder.getRamImage()), b'\xff'*4)
            self.assertEqual((int(placeholder.getMinfilter()), int(placeholder.getMagfilter())), (1, 1))

    def test_preexisting_second_state_fails_before_mutating_first(self):
        f = feedback(self)
        from panda3d.core import RenderState, ColorAttrib
        engine, cameras = self.engine()
        state = RenderState.make(ColorAttrib.makeOff())
        cameras[1].node().setInitialState(state)
        with self.assertRaisesRegex(RuntimeError, 'empty'):
            f.setup_shadow_guard(engine, enabled=True)
        self.assertTrue(cameras[0].node().getInitialState().isEmpty())
        self.assertEqual(cameras[1].node().getInitialState(), state)

    def test_configure_rejects_unknown_state_before_even_sampler_setters(self):
        feedback(self)
        from panda3d.core import RenderState, ColorAttrib
        from scripts.native_shadow_sampler_probe import configure_sampler
        engine, cameras = self.engine()
        cameras[1].node().setInitialState(RenderState.make(ColorAttrib.makeOff()))
        setters=[]
        engine.pssm.depth_tex=SimpleNamespace(getMinfilter=lambda:6,getMagfilter=lambda:6,
            setMinfilter=lambda value:setters.append(value),setMagfilter=lambda value:setters.append(value))
        with self.assertRaisesRegex(RuntimeError,'empty'):
            configure_sampler(engine,'feedback_both')
        self.assertEqual(setters,[])

    def test_setup_failure_rolls_back_camera_and_sampler_and_marker(self):
        f = feedback(self)
        from scripts.native_shadow_sampler_probe import configure_sampler
        engine, cameras = self.engine()
        original = f.apply_guard_state
        calls = []
        def fail_second(camera, state):
            calls.append(camera)
            if len(calls) == 2: raise RuntimeError('setter failed')
            return original(camera, state)
        with patch.object(f, 'apply_guard_state', side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, 'setter failed'):
                configure_sampler(engine, 'feedback_both')
        self.assertTrue(all(c.node().getInitialState().isEmpty() for c in cameras))
        self.assertEqual((int(engine.pssm.depth_tex.getMinfilter()), int(engine.pssm.depth_tex.getMagfilter())), (6, 6))
        self.assertFalse(hasattr(engine, '_stage7_shadow_feedback'))

    def test_all_four_modes_are_opt_in_and_dispatch_only_for_marker(self):
        f = feedback(self)
        from scripts.native_shadow_sampler_probe import configure_sampler, terminal_sampler_probe
        for mode, filters, guard in (('feedback_baseline', [6,6], False), ('feedback_linear', [1,1], False),
                                     ('feedback_shadow_guard', [6,6], True), ('feedback_both', [1,1], True)):
            engine, cameras = self.engine()
            config = configure_sampler(engine, mode)
            self.assertEqual(config['filters_after'], filters)
            self.assertEqual(config['renderer_semantics_experimental'], mode != 'feedback_baseline')
            self.assertEqual(config['shadow_guard']['enabled'], guard)
            with terminal_sampler_probe(engine, enabled=False) as receipt:
                self.assertEqual(receipt['method'], 'terminal_feedback_inherited_state_zero_geometry_callback')
        engine, _ = self.engine(); configure_sampler(engine, 'original')
        self.assertFalse(hasattr(engine, '_stage7_shadow_feedback'))
        with terminal_sampler_probe(engine, enabled=False) as receipt:
            self.assertEqual(receipt['method'], 'terminal_inherited_state_zero_geometry_callback')
