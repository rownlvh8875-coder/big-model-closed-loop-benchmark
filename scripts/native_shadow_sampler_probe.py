"""Opt-in PSSM sampler treatment and terminal-only OpenGL binding observations.

No shader edits, renders, task steps, GPU texture extraction or model inference.
GL queries are interventions; OFF installs no callbacks and does not load libGL.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes as C
from hashlib import sha256
from time import perf_counter
from threading import local


def classify_binding(row: dict) -> str:
    depth_formats = {0x1902, 0x81a5, 0x81a6, 0x81a7, 0x8cac, 0x88f0, 0x8cad}
    if (row.get('uniform_type') != 0x8b5e
            or row.get('bound_texture', 0) <= 0
            or row.get('bound_texture') != row.get('expected_atlas_texture')
            or row.get('texture_internal_format') not in depth_formats
            or row.get('use_pssm') != 1
            or row.get('gl_error_before') != 0 or row.get('gl_error_after') != 0):
        return 'INCONCLUSIVE_BINDING'
    if row.get('effective_compare_mode') == 0x884e:
        return 'NONSHADOW_DEPTH_COMPARE_ENABLED'
    if row.get('effective_compare_mode') == 0:
        return 'RAW_DEPTH_SAMPLER_CONSISTENT'
    return 'INCONCLUSIVE_BINDING'


def configure_sampler(engine, mode: str) -> dict:
    feedback_modes = ('feedback_baseline', 'feedback_linear', 'feedback_shadow_guard', 'feedback_both')
    if mode not in ('original', 'raw_linear', *feedback_modes):
        raise ValueError('unknown experimental shadow sampler mode')
    from metadrive.version import VERSION
    from metadrive.third_party.simplepbr import _load_shader_str
    from panda3d.core import SamplerState
    source = _load_shader_str('simplepbr.frag', {})
    if (VERSION != '0.4.3'
            or 'uniform sampler2D PSSMShadowAtlas;' not in source
            or 'texture2D(PSSMShadowAtlas,' not in source
            or 'step(ref_depth, depth_sample)' not in source):
        raise RuntimeError('unsupported MetaDrive manual-PCF shader contract')
    tex = engine.pssm.depth_tex
    before = [int(tex.getMinfilter()), int(tex.getMagfilter())]
    if before != [SamplerState.FTShadow] * 2:
        raise RuntimeError('original PSSM shadow filter contract changed')
    guard = None
    if mode in feedback_modes:
        from scripts.native_shadow_feedback_probe import configure_feedback
        guard = configure_feedback(engine, mode)
    elif mode == 'raw_linear':
        tex.setMinfilter(SamplerState.FTLinear)
        tex.setMagfilter(SamplerState.FTLinear)
    after = [int(tex.getMinfilter()), int(tex.getMagfilter())]
    result = {'mode': mode, 'filters_before': before, 'filters_after': after,
            'metadrive_version': VERSION,
            'loaded_fragment_shader_sha256': sha256(source.encode()).hexdigest(),
            'shader_edited': False, 'manual_pcf_sampler2d_confirmed': True,
            'renderer_semantics_experimental': mode not in ('original', 'feedback_baseline')}
    if guard is not None:
        result['shadow_guard'] = guard
    return result


class OpenGLQuery:
    """Small Linux libGL query surface; loaded only for an explicit ON probe."""
    def __init__(self):
        self.gl = C.CDLL('libGL.so.1')
        I, U, P = C.c_int, C.c_uint, C.POINTER
        def bind(name, result, args):
            f = getattr(self.gl, name); f.restype = result; f.argtypes = args
            return f
        self.geti = bind('glGetIntegerv', None, [U, P(I)])
        self.getp = bind('glGetProgramiv', None, [U, U, P(I)])
        self.getu = bind('glGetActiveUniform', None,
                         [U, U, I, P(I), P(I), P(U), C.c_char_p])
        self.loc = bind('glGetUniformLocation', I, [U, C.c_char_p])
        self.getuv = bind('glGetUniformiv', None, [U, I, P(I)])
        self.getix = bind('glGetIntegeri_v', None, [U, U, P(I)])
        self.gets = bind('glGetSamplerParameteriv', None, [U, U, P(I)])
        self.gett = bind('glGetTexParameteriv', None, [U, U, P(I)])
        self.gettl = bind('glGetTexLevelParameteriv', None, [U, I, U, P(I)])
        self.active = bind('glActiveTexture', None, [U])
        self.string = bind('glGetString', C.c_char_p, [U])
        self.error = bind('glGetError', U, [])

    @staticmethod
    def integer(f, *args):
        result = C.c_int(); f(*args, C.byref(result)); return result.value

    def sample(self, engine, gsg) -> dict:
        iv = self.integer
        row = {'gl_error_before': int(self.error())}
        program = iv(self.geti, 0x8b8d)  # GL_CURRENT_PROGRAM
        if not program:
            raise RuntimeError('no current GL program after scene draw')
        row['program'] = program
        uniform_type = None
        for index in range(iv(self.getp, program, 0x8b86)):
            name = C.create_string_buffer(512)
            length, size, typ = C.c_int(), C.c_int(), C.c_uint()
            self.getu(program, index, 512, C.byref(length), C.byref(size),
                      C.byref(typ), name)
            if name.value == b'PSSMShadowAtlas':
                uniform_type = typ.value
                break
        if uniform_type is None:
            raise RuntimeError('current GL program has no active PSSMShadowAtlas')
        unit = iv(self.getuv, program, self.loc(program, b'PSSMShadowAtlas'))
        use_location = self.loc(program, b'use_pssm')
        row.update(uniform_type=uniform_type, unit=unit,
                   use_pssm=iv(self.getuv, program, use_location) if use_location >= 0 else None)
        sampler = iv(self.getix, 0x8919, unit)  # GL_SAMPLER_BINDING
        old_active = iv(self.geti, 0x84e0)
        try:
            self.active(0x84c0 + unit)
            row['bound_texture'] = iv(self.geti, 0x8069)  # GL_TEXTURE_BINDING_2D
            row['texture_internal_format'] = iv(self.gettl, 0x0de1, 0, 0x1003)
            row['texture_compare_mode'] = iv(self.gett, 0x0de1, 0x884c)
            for name, parameter in (('effective_compare_mode', 0x884c),
                                    ('min_filter', 0x2801), ('mag_filter', 0x2800)):
                row[name] = (iv(self.gets, sampler, parameter) if sampler
                             else iv(self.gett, 0x0de1, parameter))
        finally:
            self.active(old_active)
        # The atlas was already rendered. This retrieves its existing context;
        # equality with the actual bound name prevents residual-program claims.
        context = engine.pssm.depth_tex.prepare_now(0, gsg.getPreparedObjects(), gsg)
        row.update(expected_atlas_texture=int(context.getNativeId()), sampler=sampler,
                   comparison_state_source='sampler_object' if sampler else 'texture',
                   gl_error_after=int(self.error()))
        row['classification'] = classify_binding(row)
        row['driver'] = {name: self.string(enum).decode()
                         for name, enum in (('vendor', 0x1f00), ('renderer', 0x1f01),
                                            ('version', 0x1f02))}
        return row


def scene_regions(engine):
    result = []
    for kind in ('road', 'wide'):
        sensor = engine.sensors['bigbench_' + kind]
        found = []
        for wi in range(engine.graphicsEngine.getNumWindows()):
            win = engine.graphicsEngine.getWindow(wi)
            if not any(win.getTexture(ti) == sensor.scene_tex
                       for ti in range(win.countTextures())):
                continue
            for ri in range(win.getNumDisplayRegions()):
                region = win.getDisplayRegion(ri)
                if region.isActive() and region.getCamera() == sensor.cam:
                    found.append((kind, win.getGsg(), region))
        if len(found) != 1:
            raise RuntimeError(f'{kind}: expected one native HDR scene display region')
        result.extend(found)
    return result


def make_callback(function):
    from panda3d.core import CallbackObject
    return CallbackObject.make(function)


@contextmanager
def state_observer(engine, callback):
    """Zero-geometry terminal node with inherited native PBR scene state.

    Panda loads this node's state before its draw callback. This is a controlled
    binding observation, NOT a trace of the state at every original primitive.
    """
    from panda3d.core import CallbackNode, OmniBoundingVolume
    from metadrive.constants import CamMask
    node = CallbackNode('stage7-terminal-sampler-state-observer')
    node.setBounds(OmniBoundingVolume())
    node.setFinal(True)
    node.setDrawCallback(make_callback(callback))
    path = engine.render.attachNewNode(node)
    path.hide(CamMask.AllOn)
    path.show(CamMask.RgbCam)
    path.setBin('fixed', 100000)
    try:
        yield
    finally:
        node.clearDrawCallback()
        path.removeNode()


@contextmanager
def terminal_sampler_probe(engine, *, enabled: bool):
    if getattr(engine, '_stage7_shadow_feedback', None) is not None:
        from scripts.native_shadow_feedback_probe import terminal_feedback_probe
        with terminal_feedback_probe(engine, enabled=enabled) as receipt:
            yield receipt
        return
    receipt = {'status': 'OFF', 'records': [], 'query_duration_s': 0.,
               'scope': 'moved_pose_positive_control_after_all_primary_frames',
               'primary_frames_instrumented': False, 'callbacks_removed': True,
               'method': 'terminal_inherited_state_zero_geometry_callback',
               'per_primitive_state_trace': False}
    if not enabled:
        yield receipt
        return
    query = OpenGLQuery()
    regions = scene_regions(engine)
    if any(region.getDrawCallback() is not None for _, _, region in regions):
        raise RuntimeError('existing draw callback would be overwritten')
    installed = []
    current = local()
    receipt.update(status='TERMINAL_QUERY', callbacks_removed=False)
    def observe(data):
        data.upcall()
        kind = getattr(current, 'camera', None)
        if kind is None:
            return
        started = perf_counter()
        try:
            record = dict(query.sample(engine, data.getGsg()), camera=kind)
        except Exception as exc:
            record = {'camera': kind, 'error': f'{type(exc).__name__}: {exc}',
                      'classification': 'INCONCLUSIVE_BINDING'}
        elapsed = perf_counter() - started
        record['query_duration_s'] = elapsed
        receipt['query_duration_s'] += elapsed
        receipt['records'].append(record)
    try:
        with state_observer(engine, observe):
            for kind, _, region in regions:
                def callback(data, kind=kind):
                    current.camera = kind
                    try:
                        data.upcall()
                    finally:
                        current.camera = None
                cb = make_callback(callback)
                region.setDrawCallback(cb)
                installed.append((region, cb))  # Keep Python callbacks alive.
            yield receipt
    finally:
        for region, _ in reversed(installed):
            region.clearDrawCallback()
        receipt['callbacks_removed'] = True
