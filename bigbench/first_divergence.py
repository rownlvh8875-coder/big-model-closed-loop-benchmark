"""Opt-in accepted CPU-buffer evidence, never an original repeatability verdict.

Importing this module creates no provider/session. Camera observation changes wall
latency/allocation; nested callback time is included in inclusive capture time.
Offline warp/I420 derivation happens only after the provider owner marks closure.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
import importlib.metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import struct
import sys
from time import perf_counter
from typing import Any
import uuid
import zlib

import numpy as np

from .camera import RGBFrame
from .camera_rig import SchematicPair
from .image_adapter import camera_pair_to_model
from .optical_calibration import PinholeIntrinsics, PinholeRectifier, intrinsics_from_panda_lens

PAYLOAD_CAP_BYTES = 256 * 1024 * 1024
DATASET_CAP_BYTES = 1024 * 1024 * 1024
RAW_SHAPE = (604, 964, 3)
CANVAS_SHAPE = (256, 512, 3)
PACKED_SHAPE = (2, 6, 128, 256)
RAW_PAIR_BYTES = 2 * math.prod(RAW_SHAPE)
CANVAS_PAIR_BYTES = 2 * math.prod(CANVAS_SHAPE)
PACKED_BYTES = math.prod(PACKED_SHAPE)
ARMS = ('original', 'proxy', 'retention')
SCHEMA = 'first-divergence-capture-v1'
CANARY_PROTOCOL = dict(seed=20261109, scenario='s_curve_left_right', speed_mps=8.,
                       dt_s=.05, initial_fraction=.12, full_s_route=False,
                       convergence=dict(max_captures=6, max_changed_pixels=16, max_rgb_delta=10))
CLAIMS = dict(original_strict_pass=False, model_scoring_allowed=False,
              real_vehicle_testing=False, default_renderer_promoted=False,
              camera_fidelity_proven=False, observer_effects_absent=False)
LIMITATION = ('Observer copies/hashes and lens CPU getters can change wall timing/allocation; '
              'nested callback wall time is included in capture_inclusive_wall_s. '
              'Derived I420 is not an intercepted graph feed. No original strict PASS.')
REPO_ROOT = Path(__file__).resolve().parents[1]

# Literal protected source pins are embedded below; no CI dependence on /tmp.
FROZEN_SOURCE_PINS = {
    "bigbench/onnx_policy.py": "d983d5950296620a6ae89c88993829b4d2cebd35a6fd0e9046a980f75c9142da",
    "scripts/native_mdv3_repeat_trial.py": "ddaf0510a775c3a44c908bb4dedf4879ae88bfcb80e1f2d022a8b513a4f42427",
    "scripts/native_mdv3_renderer_candidate.py": "5a9058102004e2f5eaa4c9dcab4c24d97a9d42702b7a9e7c248c4f576a30d22e",
    "scripts/native_mdv3_candidate_expansion.py": "d86b3be67c8ac3dee31f0bf9928014d3880c8c55a6cd829bb3c46c464d16b42c",
    "bigbench/kinematics.py": "58c92e9a5b584932cfe73ebbf7de888f2595e88ceacdabe9a457a78fa77bb70a",
    "bigbench/native_model_campaign.py": "0bcb4ca73e1404a7164be1c879a200eeff5ca41e47e3035301d40fd173000bad",
    "bigbench/metadrive_camera.py": "1c5661e6c9eea6445ebe55cb246e6b48d3384dd5a731353ba3f1a45599e338f9",
    "bigbench/model_world_frame.py": "275f5359a975d9e152f61df74cd57803e1322e1f9618784f0993e780516ec092",
    "scripts/native_mdv3_world_frame.py": "cd57c4d407e96459921ca61c78eb81ef55851cd4fafa92ca917bbc7f494a3e38",
    "model_specs/light-speed-2.json": "2ce9b7caaa50649612d8323c66d9bc193b4c89d39fb399ec00553055d3f87afa",
    "model_specs/light-speed.json": "f25bd9ef91503831b64de47be68c65a6a336e2f9fd348894e1c67902998ebe5a",
    "model_specs/md-v3.json": "689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2",
    "model_specs/n16.json": "7ac354499ec4cc2277b99eed5497ae4d11c98e9975f438743cb7ac3192e0762c"
}
EXISTING_BIGBENCH_PINS = {
    "bigbench/__init__.py": "4f8820be6e19183413fe12a5cd5d40eba31161c6fdb7dc045291e56c525cb038",
    "bigbench/camera.py": "4dc9230176b06fcfc55d776824d915f7ee7b3266cba28c1029d4863ddb4151ae",
    "bigbench/camera_convergence.py": "f71a4fbc9008aaa3467eb2bc70fa3f030428b826b39583fbfbcb33bc68118a43",
    "bigbench/camera_rig.py": "f3de46ee7a0b57485713dad3cf95dbc777fae941a701118bebbdf5f9ba837d0c",
    "bigbench/cli.py": "844233763416536d9f7ef18f3825699bb7ad5cd744ce7f004dafdc76eee45364",
    "bigbench/cross_engine.py": "e24ff682112f87e36af0780eed3672058d40338e14b9ad616becd0d6477a4cc6",
    "bigbench/curved_lane_scenarios.py": "49013b0bf16b2969382bbcd890db559df9b78e2eb2a0aefec94d88b02d1af7d0",
    "bigbench/dashboard.py": "5f6c760cab5ae85e08ba3799ca0e5526b168645d8ba14e9cab0205ab5113d5bf",
    "bigbench/frame_stability.py": "8573965c8092db93b740b0acf37b9fd8edce31fe7b36edcd64bcecff48858b8d",
    "bigbench/frozen_camera_diagnostic.py": "61f88429e71497ab1afccf57135d3aae10ab420c563aeab9924dd7ef77ef6562",
    "bigbench/geometry.py": "9615bce13a5dbb5c3abee3210b1ea5b3f648545d3576b80c35fcd035adb038e9",
    "bigbench/image_adapter.py": "7f6d53989ff072ba5b8461ba207ab68c52ac2b519d18d56d0decc68c467e6f03",
    "bigbench/kinematics.py": "58c92e9a5b584932cfe73ebbf7de888f2595e88ceacdabe9a457a78fa77bb70a",
    "bigbench/lane_reprojection.py": "92e77ea0458a2b153960fc494452f558f6ccdc1b7736da4222d17fdf77c4ce12",
    "bigbench/lane_truth.py": "20850755f7e3ea78666e83ff276a918adb64b72aaa5fac68fb3b0d393dddc449",
    "bigbench/longitudinal_world.py": "24ba109669ce410dea6d317c33c6a836b088ddbc4bc2d3dc39be0583a1eacab3",
    "bigbench/metadrive_camera.py": "1c5661e6c9eea6445ebe55cb246e6b48d3384dd5a731353ba3f1a45599e338f9",
    "bigbench/metrics.py": "7e72813179f8ab3e8cbaf829dd48f31e7885406e665571e51d0b8dbc52082ce5",
    "bigbench/model_eligibility.py": "22e7966e47e81d7c1a083c72be31fe83babd7f0f978d3fe0a543083436ac7855",
    "bigbench/model_inventory.py": "ea920f44c18719b8ed9ce4c9240beda7463b917f577ae9089707c9b1aa71786e",
    "bigbench/model_world_frame.py": "275f5359a975d9e152f61df74cd57803e1322e1f9618784f0993e780516ec092",
    "bigbench/native_callback_profiler.py": "c3b175a3b2d1de25db220ddd5a79c0820f1c2f7cc9d472120e73c0fe0dff6c3f",
    "bigbench/native_longitudinal.py": "61e5439ffac8028f548f1db0a4f8e2fff3dae00aa9e235dcea22d1bcd1fc49d4",
    "bigbench/native_model_campaign.py": "0bcb4ca73e1404a7164be1c879a200eeff5ca41e47e3035301d40fd173000bad",
    "bigbench/native_pixel_clock.py": "ed0c72cd4e84048bb7f39a246efbb30ed932170b3efe7efd1bb1fbff309572fa",
    "bigbench/native_route.py": "42be717e92b14dba482904a4c651a56c4af6c70e1a5bfd7a386ab40c626d632c",
    "bigbench/onnx_contract.py": "9e78baa8b9f7ccedb1be086277d83f356038825d54f31b309678126ddcfda73f",
    "bigbench/onnx_inspect.py": "d4b980f649c36b1047e3262fb77a0d5084492c65015febcc9d3b65226573afd6",
    "bigbench/onnx_policy.py": "d983d5950296620a6ae89c88993829b4d2cebd35a6fd0e9046a980f75c9142da",
    "bigbench/optical_calibration.py": "1a3852d67ea2f15ef31a4224916fb71275f25010a5038179a7e0dd8e984c09ce",
    "bigbench/panda_clock.py": "c2d3efd98b1f3c2d8598f294abb9741f364cc9577f0dbd16bfcbc8fd64b372d1",
    "bigbench/policies.py": "d9ac20c3ac2530d9e8fa35f9d78aae3f433afe811ce9e058dd233ead48d687ab",
    "bigbench/pssm_chase_pose_trace.py": "e2e3ead8be6743457a4e8162481cd1a70fcdb99b605bd7bc66e8702d5ce00e3d",
    "bigbench/pssm_mvp_trace.py": "8373629bc0eca7d8c1256300bee125512fb91f79ffd80e7417dee6f4afd74487",
    "bigbench/public_action_frame.py": "7d2beb3b8dc1a0fd020209d416626fbfd416b31e1aa4f4cd920fecd3bf544454",
    "bigbench/render_causality.py": "ab3deee0370e6479973547f1ea46bf6842725dfdab3e9f070488d77b9751ac5a",
    "bigbench/report.py": "fec998e2ca57b28ddf230947df5be2c2bad7c759166d6d2630e520b426dbe294",
    "bigbench/reproducibility.py": "b7aca90982237e7cbda5a03badca7514ee43458beb46ee7498bcefdbcb817c19",
    "bigbench/runner.py": "b80e983edde8f8523c47567f5d1a35422b5782e947ca550bc4e710f7276a6127",
    "bigbench/scenario.py": "7f9ff731487b9c5e5745c365901ad15c386be4299b10cf2c4af37233f4db3281",
    "bigbench/task_ablation.py": "1e8c2c7ac1c96c04a7feb21e8b046a5c0743f9afab00c51c4012dad91adc41c1",
    "pyproject.toml": "367aa37f01d25a873a3336967ba182df85be725351fb6a48f26ab84834c20a0b",
    "scripts/hf_models.py": "bf8661ebfdc1d90cd5326571d19bc8ccdc34fce0f272ed9f96a0456c5764f7e5"
}
# Task2 must extend this fixed producer registry before a native canary is run.
PRODUCER_SOURCE_PATHS = ('bigbench/first_divergence.py',
                         'scripts/first_divergence_audit.py',
                         'tests/test_first_divergence.py',
                         'scripts/hf_models.py', 'pyproject.toml')


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _exact(value: Any, expected: Any) -> bool:
    if type(value) is not type(expected):
        return False
    if isinstance(expected,dict):
        return value.keys() == expected.keys() and all(_exact(value[k],v) for k,v in expected.items())
    return value == expected


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _safe_path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or '\\' in name or '\0' in name:
        raise ValueError('unsafe member name')
    p = PurePosixPath(name)
    if p.is_absolute() or any(s in ('', '.', '..') for s in name.split('/')) or ':' in name:
        raise ValueError('unsafe member path')
    current = root
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('dataset/source root or ancestor may not be a symlink')
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('symlink member prohibited')
    return current


def required_source_paths() -> tuple[str, ...]:
    """Fixed checkout-owned registry; never derive required paths from artifacts."""
    return tuple(sorted(set(FROZEN_SOURCE_PINS) | set(EXISTING_BIGBENCH_PINS) |
                        set(PRODUCER_SOURCE_PATHS)))


def source_snapshot(repo: Path = REPO_ROOT) -> dict[str, str]:
    snapshot = {}
    for name in required_source_paths():
        path = _safe_path(Path(repo), name)
        if not path.is_file():
            raise ValueError('required source missing: ' + name)
        snapshot[name] = _digest(path.read_bytes())
    for pins in (FROZEN_SOURCE_PINS, EXISTING_BIGBENCH_PINS):
        if any(snapshot.get(k) != v for k, v in pins.items()):
            raise ValueError('protected source bytes changed')
    return snapshot


def verify_source_snapshot(snapshot: dict, repo: Path = REPO_ROOT) -> None:
    if snapshot != source_snapshot(repo):
        raise ValueError('source snapshot differs from fixed current source registry')


def capture_payload_estimate(accepted_pairs: int, *, extra_retained_bytes: int = 0) -> int:
    """Conservative owned payload, including latest attempt and accepted-copy overlap.

    Not RSS. Task2 includes all typed pre/post state/action/plan copies in extra.
    Packed reservations cover post-close derivation while raw/canvas remain alive.
    """
    if type(accepted_pairs) is not int or accepted_pairs < 0 or type(extra_retained_bytes) is not int or extra_retained_bytes < 0:
        raise ValueError('invalid payload estimate inputs')
    return (accepted_pairs * (RAW_PAIR_BYTES + CANVAS_PAIR_BYTES + PACKED_BYTES) +
            RAW_PAIR_BYTES + CANVAS_PAIR_BYTES + extra_retained_bytes)


@dataclass
class AcceptedCapture:
    capture_index: int
    pair: SchematicPair | None
    raw_rgb: dict[str, np.ndarray] | None
    raw_sha256: dict[str, str]
    intrinsics: dict[str, PinholeIntrinsics] | None
    observation: dict[str, float]
    actual_input_sha256: str | None = None

    def bind_actual_input(self, actual_input_sha256: str) -> None:
        """Task2 calls once AFTER the identical parent observation returns.

        Association is recorded now; byte-equivalence is checked offline only.
        """
        if not _is_hash(actual_input_sha256) or self.actual_input_sha256 is not None:
            raise ValueError('valid, once-only actual parent input SHA required')
        self.actual_input_sha256 = actual_input_sha256


class CaptureCollector:
    def __init__(self, arm: str = 'retention', *, payload_cap_bytes: int = PAYLOAD_CAP_BYTES,
                 max_captures: int = 12):
        if arm not in ARMS or type(payload_cap_bytes) is not int or not 0 < payload_cap_bytes <= PAYLOAD_CAP_BYTES:
            raise ValueError('invalid arm/payload cap')
        if type(max_captures) is not int or not 1 <= max_captures <= 24:
            raise ValueError('invalid bounded pair capture limit')
        self.arm, self.payload_cap_bytes, self.max_captures = arm, payload_cap_bytes, max_captures
        self.records: list[AcceptedCapture] = []
        self.capture_rows: list[dict] = []
        self.capture_count = 0
        self._retained_bytes = 0
        self._transient_bytes = 0
        self._active = False
        self._closed = False
        self._pending = None
        self._latest = None
        self._raw_callback_wall_s = 0.

    @property
    def payload_bytes(self) -> int:
        return self._retained_bytes + self._transient_bytes

    def reserve_payload(self, nbytes: int) -> None:
        """Account for Task2's retained typed copies before allocating them."""
        if type(nbytes) is not int or nbytes < 0 or self.payload_bytes + nbytes > self.payload_cap_bytes:
            raise ValueError('observer retained payload cap exceeded')
        self._retained_bytes += nbytes

    def _begin(self) -> None:
        if self._closed or self._active or self.capture_count >= self.max_captures:
            raise ValueError('closed, nested, or over-budget capture')
        self._latest = self._pending = None
        self._transient_bytes = 0
        self._raw_callback_wall_s = 0.
        if self.arm == 'retention':
            # Reserve latest buffers before the delegate's allocation/readback.
            estimate = RAW_PAIR_BYTES + CANVAS_PAIR_BYTES
            if self._retained_bytes + estimate > self.payload_cap_bytes:
                raise ValueError('latest-attempt payload cap exceeded')
            self._transient_bytes = estimate
        self.capture_count += 1
        self._active = True

    def record_native_rgb(self, images: dict, sha_map: dict) -> None:
        started = perf_counter()
        try:
            if not self._active or self._pending is not None:
                raise ValueError('fresh once-only raw callback required inside capture')
            if not isinstance(images, dict) or set(images) != {'road', 'wide'} or not isinstance(sha_map, dict) or set(sha_map) != set(images):
                raise ValueError('raw Road/Wide pair required')
            for kind, image in images.items():
                if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.shape != RAW_SHAPE or not image.flags.c_contiguous:
                    raise ValueError('expected contiguous native 964x604 uint8 RGB')
                if not _is_hash(sha_map[kind]) or _digest(memoryview(image)) != sha_map[kind]:
                    raise ValueError('native raw buffer/hash mismatch')
            self._pending = (dict(images) if self.arm == 'retention' else None, dict(sha_map))
        finally:
            self._raw_callback_wall_s += perf_counter() - started

    @staticmethod
    def _verify_raw(images: dict, hashes: dict) -> None:
        for kind, image in images.items():
            if image.dtype != np.uint8 or image.shape != RAW_SHAPE or not image.flags.c_contiguous or _digest(memoryview(image)) != hashes[kind]:
                raise ValueError('native raw buffer mutated after callback')

    def _finish(self, pair: SchematicPair, provider: Any):
        if self._pending is None or not isinstance(pair, SchematicPair):
            raise ValueError('capture must return a paired frame and fresh callback')
        for frame in (pair.road, pair.wide):
            if not isinstance(frame, RGBFrame) or (frame.width, frame.height) != (512, 256) or not isinstance(frame.rgb, bytes) or len(frame.rgb) != math.prod(CANVAS_SHAPE):
                raise ValueError('actual immutable returned model canvas required')
        images, hashes = self._pending
        intrinsics = None
        if self.arm == 'retention':
            self._verify_raw(images, hashes)
            # CPU lens getters only, after original capture. Offline equality is
            # evidence of equivalence, not interception of original warp args.
            intrinsics = {kind: intrinsics_from_panda_lens(
                provider.env.engine.sensors['bigbench_' + kind].get_lens(),
                provider.source_width, provider.source_height) for kind in ('road', 'wide')}
        self._latest = (self.capture_count, pair, images, hashes, intrinsics)

    def accept_observation(self, observation: Any, actual_input_sha256: str | None = None) -> AcceptedCapture:
        started = perf_counter()
        if self._closed or self._active or self._latest is None:
            raise ValueError('fresh returned pair required for accepted observation')
        index, pair, images, hashes, intrinsics = self._latest
        if observation.frame is not pair.road or observation.wide_frame is not pair.wide:
            raise ValueError('observation must select actual latest returned Road/Wide objects')
        if not all(type(v) in (int, float) and math.isfinite(v) for v in (observation.speed_mps, observation.time_s)):
            raise ValueError('finite observed speed/time required')
        if actual_input_sha256 is not None and not _is_hash(actual_input_sha256):
            raise ValueError('invalid actual input SHA')
        raw = None
        if images is not None:
            self._verify_raw(images, hashes)
            # Reserve accepted copies + canvas + future packed bytes before copy.
            self.reserve_payload(RAW_PAIR_BYTES + CANVAS_PAIR_BYTES + PACKED_BYTES)
            raw = {kind: np.array(a, copy=True, order='C') for kind, a in images.items()}
            for image in raw.values():
                image.setflags(write=False)
        record = AcceptedCapture(index, pair if self.arm == 'retention' else None, raw, hashes, intrinsics,
                                 dict(speed_mps=float(observation.speed_mps), time_s=float(observation.time_s)),
                                 actual_input_sha256)
        self.records.append(record)
        self._latest = self._pending = None
        self._transient_bytes = 0
        self.capture_rows[-1]['accept_observation_wall_s'] = perf_counter() - started
        return record

    def mark_closed(self) -> None:
        """Provider owner calls only after its provider-close finally completed."""
        if self._active:
            raise ValueError('cannot close during capture')
        self._closed = True
        self._latest = self._pending = None
        self._transient_bytes = 0

    def serialize_captures(self, root: Path) -> list[dict]:
        """Post-close retained evidence rows; Task2 can embed these in its sidecar."""
        if not self._closed or self.arm != 'retention':
            raise ValueError('serialization requires retained captures and provider closure')
        root = Path(root)
        _safe_path(root, 'manifest.json')  # Check ancestors before mkdir/write.
        root.mkdir(parents=True, exist_ok=True)
        result = []
        for accepted_index, record in enumerate(self.records, 1):
            if record.raw_rgb is None or record.intrinsics is None:
                raise ValueError('missing retained payload')
            self._verify_raw(record.raw_rgb, record.raw_sha256)
            pair, _ = PinholeRectifier().rectify_pair(record.raw_rgb['road'], record.raw_rgb['wide'],
                road_intrinsics=record.intrinsics['road'], wide_intrinsics=record.intrinsics['wide'])
            if pair.road.rgb != record.pair.road.rgb or pair.wide.rgb != record.pair.wide.rgb:
                raise ValueError('raw-to-actual-returned-canvas warp mismatch')
            row = dict(accepted_index=accepted_index, capture_index=record.capture_index,
                       observation=record.observation, intrinsics={k: asdict(v) for k, v in record.intrinsics.items()},
                       raw={}, canvas={})
            for kind in ('road', 'wide'):
                for boundary, frame in (
                    ('raw', RGBFrame(964, 604, record.raw_rgb[kind].tobytes())),
                    ('canvas', getattr(record.pair, kind))):
                    name = f'capture_{accepted_index:02d}/{boundary}_{kind}.png'
                    path = _safe_path(root, name)
                    if path.exists():
                        raise ValueError('refuse to overwrite evidence member')
                    frame.save_png(path)
                    row[boundary][kind] = dict(path=name, nbytes=path.stat().st_size,
                        sha256=_digest(path.read_bytes()), rgb_sha256=frame.sha256)
            packed = camera_pair_to_model(record.pair.road, record.pair.wide).tobytes(order='C')
            packed_sha = _digest(packed)
            if record.actual_input_sha256 is not None and packed_sha != record.actual_input_sha256:
                raise ValueError('derived packed image differs from actual parent graph input SHA')
            name = f'capture_{accepted_index:02d}/packed_i420.bin'
            path = _safe_path(root, name)
            if path.exists():
                raise ValueError('refuse to overwrite evidence member')
            path.write_bytes(packed)
            row['packed'] = dict(path=name, nbytes=len(packed), sha256=packed_sha,
                                 actual_input_sha256=record.actual_input_sha256,
                                 association=('ACTUAL_INPUT_SHA_EQUIVALENT' if record.actual_input_sha256
                                              else 'DERIVED_ONLY_NO_MODEL_CALL'))
            result.append(row)
        return result

    def write_failure_dataset(self, root: Path, error: BaseException, *,
                              provider_closed: bool, cleanup_error: BaseException | None = None) -> dict:
        """Preserve failed-prefix evidence; never accepted by the canary validator.

        If closure was not confirmed, write descriptions only, with no bulk
        image serialization and no provider_closed assertion. Sensor calls in
        the interrupted capture are unknown inside the registered upper bound.
        """
        if provider_closed is not self._closed or self._active:
            raise ValueError('failure closure status does not match collector lifecycle')
        root = Path(root)
        target = _safe_path(root, 'manifest.json')
        if target.exists():
            raise ValueError('refuse to overwrite failure ledger')
        root.mkdir(parents=True, exist_ok=True)
        returned = sum(row['status'] == 'RETURNED' for row in self.capture_rows)
        data = dict(schema=SCHEMA, kind='camera-only-canary', status='FAILED_OR_INCOMPLETE',
                    provider_closed=provider_closed, error=f'{type(error).__name__}: {error}',
                    cleanup_error=(f'{type(cleanup_error).__name__}: {cleanup_error}' if cleanup_error else None),
                    claims=dict(CLAIMS), limitation=LIMITATION, model_calls=0, ort_sessions=0,
                    accepted_pairs=len(self.records), capture_count=self.capture_count,
                    sensor_calls=None, sensor_calls_lower_bound=2*returned,
                    sensor_calls_upper_bound=2*self.capture_count,
                    capture_rows=self.capture_rows, retained_payload_bytes=self.payload_bytes,
                    protocol=CANARY_PROTOCOL, source_snapshot=source_snapshot(),
                    accepted_prefix_descriptions=[dict(capture_index=r.capture_index,
                        raw_sha256=r.raw_sha256, observation=r.observation) for r in self.records])
        if provider_closed:
            try:
                data['accepted'] = self.serialize_captures(root)
            except Exception as exc:
                data['serialization_error'] = f'{type(exc).__name__}: {exc}'
        target.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        return data

    def write_dataset(self, root: Path, metadata: dict | None = None) -> dict:
        if not self._closed:
            raise ValueError('provider must be closed before writing')
        if len(self.records) != 2 or self.capture_count > 12 or any(r.actual_input_sha256 is not None for r in self.records):
            raise ValueError('canary requires two accepted captures, <=12 attempts and no model inputs')
        manifest = dict(schema=SCHEMA, kind='camera-only-canary', status='CAPTURE_ASSOCIATION_VALIDATED',
                        claims=dict(CLAIMS), limitation=LIMITATION, model_calls=0, ort_sessions=0,
                        provider_closed=True,
                        accepted_pairs=2, capture_count=self.capture_count, sensor_calls=2*self.capture_count,
                        retained_payload_bytes=self.payload_bytes, payload_cap_bytes=self.payload_cap_bytes,
                        source_snapshot=source_snapshot(), capture_rows=self.capture_rows,
                        protocol=CANARY_PROTOCOL,
                        metadata=metadata or {})
        manifest['accepted'] = self.serialize_captures(root)
        path = _safe_path(Path(root), 'manifest.json')
        if path.exists():
            raise ValueError('refuse to overwrite manifest')
        path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        validate_capture_dataset(root)
        return manifest


class _ObservedCamera:
    def __init__(self, delegate: Any, collector: CaptureCollector):
        self.delegate, self.collector = delegate, collector

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def capture(self, pose):
        c = self.collector
        started = perf_counter()
        c._begin()
        native_elapsed = 0.
        row = dict(capture_index=c.capture_count, status='FAILED_OR_INCOMPLETE',
                   pose=asdict(pose))
        try:
            native_started = perf_counter()
            try:
                pair = self.delegate.capture(pose)  # Exactly the one existing capture.
            finally:
                native_elapsed = perf_counter() - native_started
            c._finish(pair, self.delegate.provider)
            row['raw_sha256'] = dict(c._pending[1])
            row['canvas_sha256'] = dict(road=pair.road.sha256, wide=pair.wide.sha256)
            row['status'] = 'RETURNED'
            return pair
        except BaseException as exc:
            c._latest = c._pending = None
            c._transient_bytes = 0
            row['error'] = f'{type(exc).__name__}: {exc}'
            raise
        finally:
            c._active = False
            row['capture_wrapper_wall_s'] = perf_counter() - started
            row['capture_inclusive_wall_s'] = native_elapsed
            # Arithmetic subtraction of inclusive wall durations, not CPU time.
            row['wrapper_observer_arithmetic_wall_s'] = row['capture_wrapper_wall_s'] - native_elapsed
            row['raw_callback_nested_wall_s'] = c._raw_callback_wall_s
            c.capture_rows.append(row)


_scope_active = False


@contextmanager
def capture_scope(arm: str, collector: CaptureCollector):
    """Temporarily interpose only the campaign camera factory; serial use only.

    No provider ownership, policy wrapping, reset/step, rendering, or I420 here.
    Original is untouched. Existing non-null raw observers are rejected.
    """
    global _scope_active
    if arm not in ARMS or collector.arm != arm:
        raise ValueError('collector/scope arm mismatch')
    if _scope_active:
        raise ValueError('nested/concurrent camera interposition prohibited')
    if arm == 'original':
        yield collector
        return
    from . import native_model_campaign as campaign
    original = campaign.NativeWorldCamera
    def factory(provider, raw_rgb_observer=None):
        if raw_rgb_observer is not None:
            raise ValueError('cannot replace an existing raw observer')
        return _ObservedCamera(original(provider, raw_rgb_observer=collector), collector)
    _scope_active = True
    campaign.NativeWorldCamera = factory
    try:
        yield collector
    finally:
        campaign.NativeWorldCamera = original
        _scope_active = False


def _read_png(path: Path, width: int, height: int) -> RGBFrame:
    """Check bounded RGB8 PNG framing/CRC/decompression BEFORE OpenCV decoding."""
    data = path.read_bytes()
    if len(data) > width*height*4 + 65536 or data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('invalid or over-budget PNG')
    offset, kinds, compressed = 8, [], bytearray()
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError('truncated PNG chunk')
        size = struct.unpack('!I', data[offset:offset+4])[0]
        kind = data[offset+4:offset+8]
        end = offset+12+size
        if end > len(data):
            raise ValueError('PNG chunk outside member')
        body = data[offset+8:offset+8+size]
        crc = struct.unpack('!I', data[offset+8+size:end])[0]
        if zlib.crc32(kind+body) & 0xffffffff != crc:
            raise ValueError('PNG CRC mismatch')
        kinds.append(kind)
        if kind == b'IHDR':
            if len(kinds) != 1 or body != struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0):
                raise ValueError('unexpected PNG dimensions/format')
        elif kind == b'IDAT':
            compressed.extend(body)
        elif kind == b'IEND':
            if size or end != len(data):
                raise ValueError('invalid PNG end/trailing bytes')
        else:
            raise ValueError('unregistered PNG chunk')
        offset = end
    if len(kinds) < 3 or kinds[0] != b'IHDR' or kinds[-1] != b'IEND' or any(k != b'IDAT' for k in kinds[1:-1]):
        raise ValueError('PNG requires IHDR, IDAT, IEND')
    expected = height*(1+3*width)
    inflater = zlib.decompressobj()
    try:
        decoded = inflater.decompress(bytes(compressed), expected+1)
    except zlib.error as exc:
        raise ValueError('invalid PNG compressed data') from exc
    if len(decoded) != expected or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
        raise ValueError('PNG decoded byte budget mismatch')
    if any(decoded[y*(1+3*width)] > 4 for y in range(height)):
        raise ValueError('invalid PNG row filter')
    import cv2
    bgr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None or bgr.shape != (height, width, 3) or bgr.dtype != np.uint8:
        raise ValueError('PNG decoding failed')
    return RGBFrame(width, height, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).tobytes())


def _read_json(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > 8*1024*1024:
        raise ValueError('missing or over-budget manifest')
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError('duplicate JSON key')
            result[k] = v
        return result
    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid JSON manifest') from exc


def validate_capture_dataset(root: Path) -> dict:
    """Pure post-close canary validation. No model/native imports or source claims.

    Source hashes must equal the checkout-owned fixed registry, not artifact names.
    Task2 separately binds that registry to actual GitHub/API commit blobs.
    """
    root = Path(root)
    manifest = _read_json(_safe_path(root, 'manifest.json'))
    expected_keys = {'schema','kind','status','claims','limitation','model_calls','ort_sessions',
                     'accepted_pairs','capture_count','sensor_calls','retained_payload_bytes','provider_closed',
                     'payload_cap_bytes','source_snapshot','capture_rows','protocol','metadata','accepted'}
    if not isinstance(manifest, dict) or set(manifest) != expected_keys or manifest.get('schema') != SCHEMA or manifest.get('kind') != 'camera-only-canary' or manifest.get('status') != 'CAPTURE_ASSOCIATION_VALIDATED':
        raise ValueError('unknown or incomplete camera-only dataset')
    if manifest.get('provider_closed') is not True:
        raise ValueError('provider closure was not confirmed')
    if not _exact(manifest.get('claims'), CLAIMS) or type(manifest.get('model_calls')) is not int or manifest['model_calls'] != 0 or type(manifest.get('ort_sessions')) is not int or manifest['ort_sessions'] != 0 or manifest.get('limitation') != LIMITATION:
        raise ValueError('camera-only dataset cannot make model/original PASS claims')
    if not _exact(manifest.get('protocol'), CANARY_PROTOCOL):
        raise ValueError('registered canary protocol changed')
    verify_source_snapshot(manifest.get('source_snapshot'))
    cap, retained = manifest.get('payload_cap_bytes'), manifest.get('retained_payload_bytes')
    if type(cap) is not int or not 0 < cap <= PAYLOAD_CAP_BYTES or type(retained) is not int or not 2*(RAW_PAIR_BYTES+CANVAS_PAIR_BYTES+PACKED_BYTES) <= retained <= cap:
        raise ValueError('invalid retained payload budget')
    count = manifest.get('capture_count')
    if type(count) is not int or not 4 <= count <= 12 or manifest.get('sensor_calls') != 2*count:
        raise ValueError('invalid bounded camera capture count')
    metadata = manifest.get('metadata')
    if not isinstance(metadata,dict) or set(metadata) - {'process_id','process_uuid','runtime_versions','convergence_receipts','source_binding'}:
        raise ValueError('unregistered canary metadata/claim')
    receipts = metadata.get('convergence_receipts')
    if not isinstance(receipts,list) or len(receipts) != 2:
        raise ValueError('missing native convergence receipts')
    attempts = manifest.get('capture_rows')
    if not isinstance(attempts, list) or len(attempts) != count or any(not isinstance(r,dict) for r in attempts) or [r.get('capture_index') for r in attempts] != list(range(1,count+1)):
        raise ValueError('missing or unordered attempt receipts')
    for row in attempts:
        if row.get('status') != 'RETURNED':
            raise ValueError('incomplete capture attempt')
        inclusive, nested = row.get('capture_inclusive_wall_s'), row.get('raw_callback_nested_wall_s')
        if any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in (inclusive,nested)) or nested > inclusive:
            raise ValueError('invalid inclusive/nested observer wall timing')
    rows = manifest.get('accepted')
    if manifest.get('accepted_pairs') != 2 or not isinstance(rows,list) or len(rows) != 2:
        raise ValueError('two accepted canary pairs required')
    registered, total = {'manifest.json'}, 0
    for p in root.rglob('*'):
        if p.is_symlink() or not (p.is_dir() or p.is_file()):
            raise ValueError('unsafe dataset member')
        if p.is_file():
            total += p.stat().st_size
    if total > DATASET_CAP_BYTES:
        raise ValueError('dataset byte cap exceeded')
    def member(desc):
        if not isinstance(desc,dict) or not _is_hash(desc.get('sha256')) or type(desc.get('nbytes')) is not int:
            raise ValueError('invalid file descriptor')
        name = desc.get('path')
        path = _safe_path(root,name)
        if name in registered or not path.is_file() or not 0 < desc['nbytes'] <= 8*1024*1024 or path.stat().st_size != desc['nbytes']:
            raise ValueError('missing, duplicated or over-budget evidence member')
        registered.add(name)
        if _digest(path.read_bytes()) != desc['sha256']:
            raise ValueError('evidence member hash mismatch')
        return path
    previous = 0
    first_pose = None
    for accepted_index, row in enumerate(rows,1):
        if not isinstance(row,dict):
            raise ValueError('malformed accepted record')
        index = row.get('capture_index')
        if type(index) is not int or not previous+2 <= index <= min(previous+6,count) or row.get('accepted_index') != accepted_index:
            raise ValueError('accepted pair not associated with bounded latest attempt')
        receipt = receipts[accepted_index-1]
        receipt_keys = {'attempts','stable','road_sha256','wide_sha256','road_changed_pixels','wide_changed_pixels','max_rgb_delta'}
        if not isinstance(receipt,dict) or set(receipt) != receipt_keys or receipt.get('stable') is not True or type(receipt.get('attempts')) is not int or receipt['attempts'] != index-previous:
            raise ValueError('invalid associated convergence receipt')
        for key, limit in (('road_changed_pixels',16),('wide_changed_pixels',16),('max_rgb_delta',10)):
            if type(receipt.get(key)) is not int or not 0 <= receipt[key] <= limit:
                raise ValueError('convergence tolerance exceeded')
        group = attempts[previous:index]
        pose = group[0].get('pose')
        from .kinematics import AgentState, ModelAction, step_ideal
        try:
            state = AgentState(**pose)
            if any(not math.isfinite(v) for v in asdict(state).values()):
                raise ValueError('nonfinite accepted capture pose')
            if first_pose is None:
                first_pose = state
                if state.t != 0. or state.speed != 8.:
                    raise ValueError('invalid initial capture clock/speed')
            else:
                expected = step_ideal(first_pose, ModelAction(0.,0.), .05, speed_override=8.)
                if state != expected:
                    raise ValueError('second canary pose is not the single straight ideal step')
            if any(r.get('pose') != pose for r in group):
                raise ValueError('convergence attempts changed same-pose state')
            if row.get('observation') != dict(speed_mps=state.speed,time_s=state.t):
                raise ValueError('accepted observation clock/speed mismatch')
        except (TypeError, KeyError) as exc:
            raise ValueError('missing/malformed accepted pose') from exc
        previous = index
        raw, canvas, intrinsics = {}, {}, {}
        for kind in ('road','wide'):
            try:
                intrinsics[kind] = PinholeIntrinsics(**row['intrinsics'][kind])
                for boundary, width, height, target in (('raw',964,604,raw), ('canvas',512,256,canvas)):
                    desc = row[boundary][kind]
                    frame = _read_png(member(desc),width,height)
                    if frame.sha256 != desc.get('rgb_sha256'):
                        raise ValueError('decoded RGB SHA mismatch')
                    target[kind] = frame
            except (KeyError, TypeError) as exc:
                raise ValueError('missing/malformed raw/canvas/intrinsics') from exc
        reproduced, _ = PinholeRectifier().rectify_pair(
            np.frombuffer(raw['road'].rgb,np.uint8).reshape(RAW_SHAPE),
            np.frombuffer(raw['wide'].rgb,np.uint8).reshape(RAW_SHAPE),
            road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
        if reproduced.road.rgb != canvas['road'].rgb or reproduced.wide.rgb != canvas['wide'].rgb:
            raise ValueError('raw/intrinsics do not reproduce actual saved canvas')
        if receipt['road_sha256'] != canvas['road'].sha256 or receipt['wide_sha256'] != canvas['wide'].sha256:
            raise ValueError('convergence receipt selected another canvas')
        selected = attempts[index-1]
        if selected.get('raw_sha256') != {k: row['raw'][k]['rgb_sha256'] for k in ('road','wide')} or selected.get('canvas_sha256') != {k: canvas[k].sha256 for k in ('road','wide')}:
            raise ValueError('accepted raw/canvas hashes differ from selected returned attempt')
        packed = row.get('packed')
        actual = camera_pair_to_model(canvas['road'],canvas['wide']).tobytes()
        if member(packed).read_bytes() != actual or packed.get('nbytes') != PACKED_BYTES:
            raise ValueError('packed I420 derivation mismatch')
        if packed.get('actual_input_sha256') is not None or packed.get('association') != 'DERIVED_ONLY_NO_MODEL_CALL':
            raise ValueError('canary must not claim intercepted model feed')
    if previous != count:
        raise ValueError('unselected trailing attempts in complete canary')
    actual_members = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual_members != registered:
        raise ValueError('unregistered or missing dataset member')
    return dict(status='CAPTURE_ASSOCIATION_VALIDATED', accepted_pairs=2,
                capture_count=count, sensor_calls=2*count, model_calls=0,
                original_strict_pass=False, source_snapshot=manifest['source_snapshot'])


def _require_ephemeral_ci(out: Path) -> None:
    temp = os.environ.get('RUNNER_TEMP')
    if os.environ.get('GITHUB_ACTIONS') != 'true' or not temp:
        raise ValueError('native canary is ephemeral GitHub CI only')
    target, base = Path(out).resolve(), Path(temp).resolve()
    if target == base or base not in target.parents:
        raise ValueError('native output must be below RUNNER_TEMP')


def runtime_versions() -> dict:
    """Distribution identity metadata; does not claim binary/system equality."""
    result = dict(python=sys.version, executable=sys.executable)
    for name in ('numpy','opencv-python-headless','panda3d','metadrive-simulator','onnxruntime'):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def capture_canary(out: Path) -> dict:
    """Registered one-provider, two-pair 6/16/10 no-model CI path; no retry."""
    _require_ephemeral_ci(out)
    source_snapshot()  # Fail before native construction on missing/drifted files.
    if capture_payload_estimate(2) > PAYLOAD_CAP_BYTES:
        raise ValueError('canary payload preflight failed')
    from . import native_model_campaign as campaign
    from .camera_convergence import StrictConsecutiveCamera
    from .curved_lane_scenarios import SCENARIOS, select_native_curve_lanes
    from .kinematics import AgentState, ModelAction, step_ideal
    from .metadrive_camera import NativeMetaDriveProvider
    from .policies import ModelObservation
    collector = CaptureCollector()
    provider = None
    failure = cleanup_error = None
    provider_closed = False
    try:
        provider = NativeMetaDriveProvider(seed=20261109,
            map_config=SCENARIOS['s_curve_left_right'].map_config())
        lanes = select_native_curve_lanes(provider.env.current_map,SCENARIOS['s_curve_left_right'])
        if not lanes:
            raise ValueError('registered S scene has no curve lane')
        lane = lanes[0]
        station = float(lane.length)*.12
        xy = lane.position(station,0.)
        pose = AgentState(0.,float(xy[0]),float(xy[1]),float(lane.heading_theta_at(station)),8.)
        with capture_scope('retention',collector):
            renderer = StrictConsecutiveCamera(campaign.NativeWorldCamera(provider),
                max_captures=6,max_changed_pixels=16,max_rgb_delta=10)
            for _ in range(2):
                pair = renderer.capture(pose)
                collector.accept_observation(ModelObservation(pair.road,pose.speed,pose.t,wide_frame=pair.wide))
                pose = step_ideal(pose,ModelAction(0.,0.),.05,speed_override=8.)
    except BaseException as exc:
        failure = exc
    finally:
        if provider is not None:
            try:
                provider.close()
                provider_closed = True
                collector.mark_closed()
            except BaseException as exc:
                if failure is None:
                    failure = exc
                else:
                    cleanup_error = exc
    if failure is not None:
        try:
            collector.write_failure_dataset(Path(out),failure,provider_closed=provider_closed,
                                             cleanup_error=cleanup_error)
        except BaseException as write_error:
            failure.add_note(f'Failure ledger write error: {type(write_error).__name__}: {write_error}')
        if cleanup_error is not None:
            failure.add_note(f'Provider cleanup error: {type(cleanup_error).__name__}: {cleanup_error}')
        raise failure
    return collector.write_dataset(Path(out),metadata=dict(process_id=os.getpid(),
        process_uuid=uuid.uuid4().hex,runtime_versions=runtime_versions(),
        convergence_receipts=[asdict(r) for r in renderer.receipts],
        source_binding='CHECKOUT_BYTES_ONLY_GITHUB_API_BINDING_REQUIRED_BY_TASK2'))
