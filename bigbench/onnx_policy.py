"""Standalone large-driving ONNX executor with recurrent-state continuity.

This is an inference harness, NOT a camera-fidelity or driving-performance proof.
It never imports the small internal CD210 model or any Carrot controller.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

import numpy as np

from .image_adapter import camera_pair_to_model
from .kinematics import ModelAction
from .onnx_contract import ModelContract, ModelContractError
from .policies import ModelObservation


@dataclass(frozen=True)
class ModelTiming:
    step_index: int
    elapsed_ms: float
    raw_lateral_accel_mps2: float
    raw_longitudinal_accel_mps2: float
    curvature_1pm: float
    image_checksum: int


class OnnxBigModelPolicy:
    """Run one statically pinned stateful ONNX graph per synthetic camera step.

    The image tensor is 2x6x128x256 packed uint8 I420; the synthetic camera
    doesn't reproduce comma sensor distortion/intrinsics. Model outputs are raw
    and are never adjusted by Carrot MPC, steer torque or longitudinal planners.
    """
    is_mock = False
    needs_dual_camera = True

    def __init__(self, model_path: Path, spec_path: Path, *, session: Any = None,
                 traffic_is_rhd: bool = False,
                 lat_action_t_s: float = 0.175, long_action_t_s: float = 0.175):
        self.contract = ModelContract.load(spec_path)
        self.model_path = Path(model_path)
        self.contract.check_file(self.model_path)
        self._injected_session = session is not None
        if session is None:
            try:
                import onnxruntime as ort
            except ImportError as exc:
                raise RuntimeError('install optional dependencies: pip install ".[inference]"') from exc
            options = ort.SessionOptions()
            options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
            session = ort.InferenceSession(str(self.model_path), sess_options=options,
                                           providers=['CPUExecutionProvider'])
        self.session = session
        self._types = self.contract.validate_session(session)
        if (not np.isfinite(lat_action_t_s) or not np.isfinite(long_action_t_s)
                or lat_action_t_s < 0 or long_action_t_s < 0):
            raise ModelContractError('action_t values must be finite nonnegative seconds')
        self.action_t = np.array([[lat_action_t_s, long_action_t_s]], dtype=np.float32)
        self.traffic_convention = np.array([[0., 1.] if traffic_is_rhd else [1., 0.]], dtype=np.float32)
        self.name = f'big-onnx-{self.contract.sha256[:12]}'
        self.evidence_class = ('TEST_DOUBLE_NOT_REAL_ONNX' if self._injected_session
                               else 'ONNX_EXECUTED_SCHEMATIC_INPUT_UNCALIBRATED')
        self.state: dict[str, np.ndarray] = {}
        self.trace: list[ModelTiming] = []
        self.last_model_outputs: dict[str, np.ndarray] | None = None
        self.reset()

    def reset(self) -> None:
        self.state = {name: np.zeros(self.contract.input_shapes[name], dtype=self._types[name])
                      for name in self.contract.state_keys}
        self.trace = []
        self.last_model_outputs = None

    def step(self, observation: ModelObservation) -> ModelAction:
        if observation.wide_frame is None:
            raise ModelContractError('two distinct model camera frames required; do not duplicate road image')
        if not np.isfinite(observation.speed_mps) or observation.speed_mps < 0:
            raise ModelContractError('invalid synthetic speed')
        rgb_planes = camera_pair_to_model(observation.frame, observation.wide_frame)
        if tuple(rgb_planes.shape) != self.contract.input_shapes['new_img']:
            raise ModelContractError('image adapter output shape mismatch')
        if rgb_planes.dtype != self._types['new_img']:
            raise ModelContractError('image adapter dtype mismatch')
        feed: dict[str, np.ndarray] = {
            'new_img': rgb_planes,
            'desire': np.zeros(self.contract.input_shapes['desire'], dtype=np.float32),
            'traffic_convention': self.traffic_convention.copy(),
            'action_t': self.action_t.copy(),
            **self.state,
        }
        if self.contract.needs_navigation:
            nav = observation.nav_inputs
            if not isinstance(nav, dict) or set(nav) != {'nav_map', 'navigation'}:
                raise ModelContractError('navigation model needs explicit nav_map and navigation; zero-fill forbidden')
            for name in ('nav_map', 'navigation'):
                value = np.asarray(nav[name], dtype=np.float32)
                if value.shape != self.contract.input_shapes[name] or not np.all(np.isfinite(value)):
                    raise ModelContractError(f'invalid {name} input shape or values')
                if name == 'nav_map' and (value.min() < 0 or value.max() > 255):
                    raise ModelContractError('nav_map expected 0..255 float32 pixels')
                feed[name] = value
        if set(feed) != set(self.contract.input_shapes):
            raise ModelContractError('missing or extra model inputs')
        for name, value in feed.items():
            if tuple(value.shape) != self.contract.input_shapes[name] or value.dtype != self._types[name]:
                raise ModelContractError(f'{name} runtime input shape/dtype mismatch')
        output_names = list(self.contract.output_shapes)
        started = time.perf_counter()
        values = self.session.run(output_names, feed)
        elapsed = (time.perf_counter() - started) * 1000
        if len(values) != len(output_names):
            raise ModelContractError('ONNX output count mismatch')
        out = {name: np.asarray(value) for name, value in zip(output_names, values)}
        for name, shape in self.contract.output_shapes.items():
            value = out[name]
            if tuple(value.shape) != shape:
                raise ModelContractError(f'{name} output shape mismatch')
            if value.dtype != self._types.get(name, value.dtype):
                # Inferred recurrent output dtype must exactly agree with its state input.
                if name.startswith('next_state_') and value.dtype != self._types[name[5:]]:
                    raise ModelContractError(f'{name} output dtype mismatch')
            if not np.all(np.isfinite(value)):
                raise ModelContractError(f'{name} contains nonfinite output')
        raw = out['outputs'].reshape(-1)
        a, b = self.contract.output_slices['action']
        raw_action = raw[a:b]
        if raw_action.size not in (2, 4):
            raise ModelContractError('invalid raw action width')
        lat_accel = float(raw_action[0])
        long_accel = float(raw_action[1])
        # carrot-wip modeld.py: action[0] is lateral acceleration; convert to curvature.
        curvature = lat_accel / max(2.5, observation.speed_mps)**2
        action = ModelAction(curvature_1pm=curvature, acceleration_mps2=long_accel)
        # Commit recurrent states only after all outputs and action have been validated.
        self.state = {k: np.array(out['next_' + k], copy=True) for k in self.contract.state_keys}
        self.last_model_outputs = {
            'action': raw_action.copy(),
            'plan': raw[slice(*self.contract.output_slices['plan'])].copy(),
        }
        self.trace.append(ModelTiming(len(self.trace), elapsed, lat_accel, long_accel,
                                      curvature, int(np.sum(rgb_planes, dtype=np.uint64) % (2**32))))
        return action
