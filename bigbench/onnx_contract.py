"""Fail-closed graph/weight identity and recurrent I/O contract for stateful big ONNX models.

The schema is pinned to the relevant carrot-wip model catalog file.  It is NOT an
assertion that a model's image calibration or simulator driving is validated.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

import numpy as np

_HASH = re.compile(r"[0-9a-f]{64}\Z")
_MAX_ELEMENTS = 32_000_000
_DTYPES = {'tensor(uint8)': np.dtype('uint8'), 'tensor(float)': np.dtype('float32'),
           'tensor(float16)': np.dtype('float16')}


class ModelContractError(ValueError):
    """Model is incompatible with the explicitly pinned input/output contract."""


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class ModelContract:
    sha256: str
    nbytes: int
    frame_skip: int
    input_shapes: dict[str, tuple[int, ...]]
    output_shapes: dict[str, tuple[int, ...]]
    output_slices: dict[str, tuple[int, int]]
    source: str = 'local-manifest'

    @classmethod
    def load(cls, path: Path) -> 'ModelContract':
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ModelContractError('model manifest must be an object')
        digest = data.get('sha256')
        if not isinstance(digest, str) or not _HASH.fullmatch(digest):
            raise ModelContractError('manifest needs a lowercase 64-digit SHA256')
        nbytes = data.get('nbytes')
        if type(nbytes) is not int or nbytes <= 0:
            raise ModelContractError('manifest nbytes must be a positive integer')
        frame_skip = data.get('frame_skip')
        if frame_skip != 4:
            raise ModelContractError('only the verified frame_skip=4 contract is supported')

        def shapes(key: str) -> dict[str, tuple[int, ...]]:
            raw = data.get(key)
            if not isinstance(raw, dict) or not raw:
                raise ModelContractError(f'{key} missing')
            result = {}
            for name, shape in raw.items():
                if (not isinstance(name, str) or not name or not isinstance(shape, list)
                        or not shape or any(type(n) is not int or n <= 0 for n in shape)):
                    raise ModelContractError(f'invalid shape for {name!r}')
                product = 1
                for n in shape:
                    product *= n
                if product > _MAX_ELEMENTS:
                    raise ModelContractError(f'oversized tensor: {name}')
                result[name] = tuple(shape)
            return result

        inputs, outputs = shapes('input_shapes'), shapes('output_shapes')
        if 'new_img' not in inputs:
            raise ModelContractError('legacy queued-graph models are not yet supported; expected new_img')
        if inputs['new_img'] != (2, 6, 128, 256):
            raise ModelContractError(f'unknown new_img contract: {inputs["new_img"]}')
        for key, expected in {'desire': (8,), 'traffic_convention': (1, 2),
                              'action_t': (1, 2)}.items():
            if inputs.get(key) != expected:
                raise ModelContractError(f'unsupported {key}: {inputs.get(key)}')
        if not set(inputs).issubset({'new_img', 'desire', 'traffic_convention', 'action_t',
                                      'nav_map', 'navigation'} | {x for x in inputs if x.startswith('state_')}):
            raise ModelContractError('unrecognized driving model input')
        nav_present = {k for k in ('nav_map', 'navigation') if k in inputs}
        if nav_present and (nav_present != {'nav_map', 'navigation'}
                            or inputs['nav_map'] != (1, 1, 256, 256)
                            or inputs['navigation'] != (1, 47)):
            raise ModelContractError('unsupported navigation input contract')
        state_keys = {x for x in inputs if x.startswith('state_')}
        if not state_keys:
            raise ModelContractError('expected at least one recurrent state tensor')
        required_outputs = {'outputs'} | {'next_' + k for k in state_keys}
        if set(outputs) != required_outputs:
            raise ModelContractError('recurrent state output pairs do not match inputs')
        for key in state_keys:
            if outputs['next_' + key] != inputs[key]:
                raise ModelContractError(f'state shape mismatch: {key}')
        if len(outputs['outputs']) != 2 or outputs['outputs'][0] != 1:
            raise ModelContractError('expected one flattened output tensor')
        raw_slices = data.get('output_slices')
        if not isinstance(raw_slices, dict) or not raw_slices:
            raise ModelContractError('missing output slices')
        slices = {}
        width = outputs['outputs'][1]
        for name, bounds in raw_slices.items():
            if (not isinstance(bounds, list) or len(bounds) != 2 or
                any(type(i) is not int for i in bounds) or not 0 <= bounds[0] < bounds[1] <= width):
                raise ModelContractError(f'invalid slice: {name}')
            slices[name] = tuple(bounds)
        if 'action' not in slices or slices['action'][1] - slices['action'][0] not in (2, 4):
            raise ModelContractError('missing or incompatible model action output')
        if 'plan' not in slices or slices['plan'][1] - slices['plan'][0] not in (990, 4955):
            raise ModelContractError('missing or incompatible model plan')
        ordered = sorted(slices.values())
        if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
            raise ModelContractError('overlapping model output slices')
        return cls(digest, nbytes, frame_skip, inputs, outputs, slices,
                   str(data.get('source') or path))

    @property
    def needs_navigation(self) -> bool:
        return 'nav_map' in self.input_shapes

    @property
    def state_keys(self) -> tuple[str, ...]:
        return tuple(k for k in self.input_shapes if k.startswith('state_'))

    def check_file(self, model_path: Path) -> str:
        if not model_path.is_file() or model_path.suffix.lower() != '.onnx':
            raise ModelContractError('an existing .onnx file is required')
        if model_path.stat().st_size != self.nbytes:
            raise ModelContractError('ONNX byte count does not match pinned manifest')
        observed = file_sha256(model_path)
        if observed != self.sha256:
            raise ModelContractError(f'ONNX SHA256 does not match pinned manifest: {observed}')
        return observed

    def validate_session(self, session: Any) -> dict[str, np.dtype]:
        def check_nodes(nodes: list, expected: dict[str, tuple[int, ...]], label: str) -> dict[str, np.dtype]:
            lookup = {node.name: node for node in nodes}
            if set(lookup) != set(expected):
                raise ModelContractError(f'{label} graph names mismatch: missing={sorted(set(expected)-set(lookup))}; '
                                         f'extra={sorted(set(lookup)-set(expected))}')
            dtype_by_name = {}
            for name, dims in expected.items():
                node = lookup[name]
                if tuple(node.shape) != dims:
                    raise ModelContractError(f'{label} {name} shape differs from manifest: {node.shape} != {dims}')
                if node.type not in _DTYPES:
                    raise ModelContractError(f'unsupported ONNX tensor type {name}: {node.type}')
                dtype_by_name[name] = _DTYPES[node.type]
            return dtype_by_name

        ins = check_nodes(session.get_inputs(), self.input_shapes, 'input')
        outs = check_nodes(session.get_outputs(), self.output_shapes, 'output')
        for name, value in ins.items():
            if name in ('new_img', 'state_img_q'):
                if value != np.dtype('uint8'):
                    raise ModelContractError(f'{name} should be uint8 in the pinned camera contract')
            elif value != np.dtype('float32'):
                raise ModelContractError(f'{name} should be float32 in the pinned scalar/state contract')
        for key in self.state_keys:
            if outs['next_' + key] != ins[key]:
                raise ModelContractError(f'ONNX recurrent dtype mismatch for {key}')
        if outs['outputs'] != np.dtype('float32'):
            raise ModelContractError('driving output must be float32')
        return ins
