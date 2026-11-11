"""Opt-in shadow-camera inputs and terminal controlled GL binding observations.

No shader replacement, geometry, capture, clock, task or lens changes. A binding
hazard is not proof that an original primitive executed a texture fetch.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes as C
import math
from threading import local
from time import perf_counter

from scripts.native_shadow_sampler_probe import OpenGLQuery, make_callback, scene_regions

MODES = ('feedback_baseline', 'feedback_linear', 'feedback_shadow_guard', 'feedback_both')
PRIORITY = 1000000
GL_TEXTURE, GL_RENDERBUFFER = 0x1702, 0x8d41
DEPTH_FORMATS = {0x1902, 0x81a5, 0x81a6, 0x81a7, 0x8cac, 0x88f0, 0x8cad}
SCOPE = 'moved_pose_positive_control_after_all_primary_frames'
METHOD = 'terminal_feedback_inherited_state_zero_geometry_callback'


def shadow_cameras(engine):
    if engine.pssm.num_splits != 2:
        raise RuntimeError('expected exactly two original shadow cameras')
    return [engine.pssm.camera_rig.get_camera(i) for i in range(2)]


def apply_guard_state(camera, state):
    camera.node().setInitialState(state)


def setup_shadow_guard(engine, *, enabled: bool) -> dict:
    """Check both originals before mutation; roll back all states on setup error."""
    from panda3d.core import RenderState, ShaderAttrib, ShaderInput, Texture, SamplerState
    cameras = shadow_cameras(engine)
    originals = [camera.node().getInitialState() for camera in cameras]
    if any(not state.isEmpty() for state in originals):
        raise RuntimeError('both original shadow camera initial states must be empty')
    receipt = dict(enabled=enabled, original_camera_states_empty=[True, True],
                   camera_count=2, shader_replaced=False, input_priority=PRIORITY,
                   inputs=['use_pssm', 'PSSMShadowAtlas'] if enabled else [],
                   placeholder=None)
    if not enabled:
        return receipt
    tex = Texture('stage7-shadow-feedback-placeholder')
    tex.setup2dTexture(1, 1, Texture.TUnsignedByte, Texture.FRgba8)
    tex.setRamImage(b'\xff' * 4)
    tex.setMinfilter(SamplerState.FTLinear)
    tex.setMagfilter(SamplerState.FTLinear)
    attrib = ShaderAttrib.make()
    attrib = attrib.setShaderInput(ShaderInput('use_pssm', False, PRIORITY))
    attrib = attrib.setShaderInput(ShaderInput('PSSMShadowAtlas', tex, PRIORITY))
    state = RenderState.make(attrib)
    try:
        for camera in cameras:
            apply_guard_state(camera, state)
    except BaseException:
        for camera, original in zip(cameras, originals):
            camera.node().setInitialState(original)
        raise
    # Keep the texture alive through the native process, without serializing it.
    engine._stage7_shadow_feedback_placeholder = tex
    receipt['placeholder'] = dict(dimensions=[1, 1], format='RGBA8', rgba=[255]*4,
                                   filters=[1, 1])
    return receipt


def configure_feedback(engine, mode):
    from panda3d.core import SamplerState
    if hasattr(engine, '_stage7_shadow_feedback'):
        raise RuntimeError('feedback experiment already configured')
    tex = engine.pssm.depth_tex
    originals = [camera.node().getInitialState() for camera in shadow_cameras(engine)]
    if any(not state.isEmpty() for state in originals):
        raise RuntimeError('both original shadow camera initial states must be empty')
    before = [tex.getMinfilter(), tex.getMagfilter()]
    try:
        guard = setup_shadow_guard(engine, enabled=mode in ('feedback_shadow_guard', 'feedback_both'))
        if mode in ('feedback_linear', 'feedback_both'):
            tex.setMinfilter(SamplerState.FTLinear)
            tex.setMagfilter(SamplerState.FTLinear)
        engine._stage7_shadow_feedback = mode
        return guard
    except BaseException:
        for camera, original in zip(shadow_cameras(engine), originals):
            camera.node().setInitialState(original)
        tex.setMinfilter(before[0]); tex.setMagfilter(before[1])
        for name in ('_stage7_shadow_feedback', '_stage7_shadow_feedback_placeholder'):
            if hasattr(engine, name):
                delattr(engine, name)
        raise


def _attachment_valid(a):
    if not isinstance(a, dict):
        return False
    kind, name, level = (a.get(k) for k in ('object_type', 'object_name', 'texture_level'))
    if type(kind) is not int or type(name) is not int:
        return False
    return ((kind == 0 and name == 0 and level is None)
            or (kind == GL_RENDERBUFFER and name > 0 and level is None)
            or (kind == GL_TEXTURE and name > 0 and type(level) is int and level >= 0))


def classify_feedback_binding(row: dict) -> str:
    """Classify the observed controlled state, never executed shader accesses."""
    attachments = row.get('attachments', {})
    if (row.get('camera') not in ('road', 'wide', 'shadow0', 'shadow1')
            or row.get('uniform_type') != 0x8b5e
            or row.get('gl_error_before') != 0 or row.get('gl_error_after') != 0
            or any(not _attachment_valid(attachments.get(k)) for k in ('depth', 'color0'))
            or type(row.get('draw_framebuffer')) is not int or row['draw_framebuffer'] <= 0):
        return 'INCONCLUSIVE_BINDING'
    atlas, bound = row.get('expected_atlas_texture', 0), row.get('bound_texture', 0)
    if type(atlas) is not int or atlas <= 0 or type(bound) is not int or bound <= 0:
        return 'INCONCLUSIVE_BINDING'
    depth = attachments['depth']
    shadow = row['camera'].startswith('shadow')
    if shadow and depth != dict(object_type=GL_TEXTURE, object_name=atlas, texture_level=0):
        return 'INCONCLUSIVE_BINDING'
    # Texture and renderbuffer names belong to different namespaces. Only a
    # texture image at the sampled mip level aliases this sampler2D image.
    aliases = any(a['object_type'] == GL_TEXTURE and a['object_name'] == bound
                  and a['texture_level'] == 0 for a in attachments.values())
    if (shadow and row.get('use_pssm') == 0 and bound != atlas
            and bound == row.get('expected_placeholder_texture')
            and row.get('texture_internal_format') == 0x8058
            and row.get('effective_compare_mode') == 0 and not aliases):
        return 'SHADOW_GUARD_PLACEHOLDER_BOUND'
    if (bound != atlas or row.get('use_pssm') != 1
            or row.get('texture_internal_format') not in DEPTH_FORMATS
            or row.get('effective_compare_mode') not in (0, 0x884e)):
        return 'INCONCLUSIVE_BINDING'
    if shadow and aliases:
        return 'SHADOW_ATLAS_READ_WRITE_BINDING_HAZARD'
    if not shadow and not aliases:
        return 'RGB_ATLAS_RAW_LINEAR' if row['effective_compare_mode'] == 0 else 'RGB_ATLAS_COMPARE_ENABLED'
    return 'INCONCLUSIVE_BINDING'


def validate_feedback_binding(row: dict, *, guarded: bool, linear: bool) -> None:
    shadow = str(row.get('camera', '')).startswith('shadow')
    expected = ('SHADOW_GUARD_PLACEHOLDER_BOUND' if shadow and guarded
                else 'SHADOW_ATLAS_READ_WRITE_BINDING_HAZARD' if shadow
                else 'RGB_ATLAS_RAW_LINEAR' if linear else 'RGB_ATLAS_COMPARE_ENABLED')
    compare = 0 if shadow and guarded or linear else 0x884e
    driver = row.get('driver', {})
    if ('error' in row or classify_feedback_binding(row) != expected
            or row.get('classification') != expected
            or row.get('effective_compare_mode') != compare
            or any(type(row.get(k)) is not int or row[k] < lower
                   for k, lower in (('program', 1), ('unit', 0), ('sampler', 0),
                                    ('expected_placeholder_texture', int(guarded))))
            or row.get('texture_compare_mode') not in (0, 0x884e)
            or (row['sampler'] == 0 and row['texture_compare_mode'] != compare)
            or row.get('comparison_state_source') != ('sampler_object' if row['sampler'] else 'texture')
            or row.get('min_filter') != 0x2601 or row.get('mag_filter') != 0x2601
            or any(type(row.get(k)) is not int or row[k] < 0
                   for k in ('framebuffer_samples', 'framebuffer_sample_buffers'))
            or row['framebuffer_sample_buffers'] not in (0, 1)
            or (row['framebuffer_samples'] == 0) != (row['framebuffer_sample_buffers'] == 0)
            or type(row.get('query_duration_s')) not in (int, float)
            or not math.isfinite(row['query_duration_s']) or row['query_duration_s'] <= 0
            or any(not isinstance(driver.get(k), str) or not driver[k]
                   for k in ('vendor', 'renderer', 'version'))):
        raise ValueError('GPU state does not verify shadow/RGB feedback treatment')


class FeedbackOpenGLQuery(OpenGLQuery):
    def __init__(self):
        super().__init__()
        self.get_attachment = self.gl.glGetFramebufferAttachmentParameteriv
        self.get_attachment.restype = None
        self.get_attachment.argtypes = [C.c_uint, C.c_uint, C.c_uint, C.POINTER(C.c_int)]

    def attachment(self, point):
        kind = self.integer(self.get_attachment, 0x8ca9, point, 0x8cd0)
        return dict(object_type=kind,
                    object_name=self.integer(self.get_attachment, 0x8ca9, point, 0x8cd1) if kind else 0,
                    texture_level=self.integer(self.get_attachment, 0x8ca9, point, 0x8cd2)
                    if kind == GL_TEXTURE else None)

    def sample(self, engine, gsg, camera):
        """Read the actual bound framebuffer, independent of requested MSAA."""
        row = super().sample(engine, gsg)
        placeholder = getattr(engine, '_stage7_shadow_feedback_placeholder', None)
        context = placeholder.prepare_now(0, gsg.getPreparedObjects(), gsg) if placeholder else None
        row.update(camera=camera, expected_placeholder_texture=int(context.getNativeId()) if context else 0,
                   draw_framebuffer=self.integer(self.geti, 0x8ca6),
                   framebuffer_samples=self.integer(self.geti, 0x80a9),
                   framebuffer_sample_buffers=self.integer(self.geti, 0x80a8))
        row['attachments'] = {name: self.attachment(point) for name, point in
                              (('depth', 0x8d00), ('color0', 0x8ce0))}
        attachment_error = int(self.error())
        row['gl_error_after'] = row['gl_error_after'] or attachment_error
        row['classification'] = classify_feedback_binding(row)
        return row


def feedback_regions(engine):
    result = scene_regions(engine)
    cameras = shadow_cameras(engine)
    if len(engine.pssm.split_regions) != 2:
        raise RuntimeError('expected two original shadow display regions')
    for i, (region, camera) in enumerate(zip(engine.pssm.split_regions, cameras)):
        if not region.isActive() or region.getCamera() != camera:
            raise RuntimeError('unexpected original shadow display region camera')
        result.append((f'shadow{i}', engine.pssm.buffer.getGsg(), region))
    return result


@contextmanager
def feedback_state_observer(engine, callback):
    from panda3d.core import CallbackNode, OmniBoundingVolume
    from metadrive.constants import CamMask
    node = CallbackNode('stage7-terminal-feedback-state-observer')
    node.setBounds(OmniBoundingVolume()); node.setFinal(True)
    node.setDrawCallback(make_callback(callback))
    path = engine.render.attachNewNode(node)
    try:
        path.hide(CamMask.AllOn); path.show(CamMask.RgbCam | CamMask.Shadow)
        path.setBin('fixed', 100000)
        yield
    finally:
        node.clearDrawCallback(); path.removeNode()


@contextmanager
def terminal_feedback_probe(engine, *, enabled: bool):
    receipt = dict(status='OFF', records=[], query_duration_s=0., scope=SCOPE,
                   primary_frames_instrumented=False, callbacks_removed=True,
                   method=METHOD, per_primitive_state_trace=False,
                   texture_pixel_extraction=False)
    if not enabled:
        yield receipt
        return
    query = FeedbackOpenGLQuery()
    regions = feedback_regions(engine)
    if any(region.getDrawCallback() is not None for _, _, region in regions):
        raise RuntimeError('existing draw callback would be overwritten')
    installed, current = [], local()
    receipt.update(status='TERMINAL_QUERY', callbacks_removed=False)
    def observe(data):
        data.upcall()
        camera = getattr(current, 'camera', None)
        if camera is None:
            return
        started = perf_counter()
        try:
            record = query.sample(engine, data.getGsg(), camera)
        except Exception as exc:
            record = dict(camera=camera, error=f'{type(exc).__name__}: {exc}', classification='INCONCLUSIVE_BINDING')
        elapsed = perf_counter() - started
        record['query_duration_s'] = elapsed
        receipt['query_duration_s'] += elapsed
        receipt['records'].append(record)
    try:
        with feedback_state_observer(engine, observe):
            for camera, _, region in regions:
                def callback(data, camera=camera):
                    current.camera = camera
                    try:
                        data.upcall()
                    finally:
                        current.camera = None
                cb = make_callback(callback)
                installed.append((region, cb))
                region.setDrawCallback(cb)
            yield receipt
    finally:
        for region, _ in reversed(installed):
            region.clearDrawCallback()
        receipt['callbacks_removed'] = True
