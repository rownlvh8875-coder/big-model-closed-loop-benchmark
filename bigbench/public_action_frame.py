"""Public ONNX parent-action contract and explicit world integration boundary.

Importing this module uses only the standard library. Identity verification and
policy construction are setup work; they never run inference or select a renderer.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

OFFICIAL_MODEL_SHA256='35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'
OFFICIAL_MODEL_NBYTES=768750198
OFFICIAL_SPEC_SHA256='689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2'
MODEL_ACTION_FRAMES=('auto','model-frd','world-flu')
MODEL_BODY_FRD='MODEL_BODY_FRD'
WORLD_BODY_FLU='INTEGRATOR_BODY_FLU_WORLD_CCW'


@dataclass(frozen=True)
class ModelIdentity:
    model_path: str
    spec_path: str
    model_sha256: str
    model_nbytes: int
    spec_sha256: str


@dataclass(frozen=True)
class ActionFrameResolution:
    identity: ModelIdentity
    requested_frame: str
    parent_action_frame: str
    applied_action_frame: str
    provenance: str
    rotation_applied: bool


def _resolve_action_frame(identity: ModelIdentity, declaration: str) -> ActionFrameResolution:
    if type(declaration) is not str or declaration not in MODEL_ACTION_FRAMES:
        raise ValueError('model_action_frame must be auto, model-frd or world-flu')
    anchors=(identity.model_sha256==OFFICIAL_MODEL_SHA256,identity.model_nbytes==OFFICIAL_MODEL_NBYTES,
             identity.spec_sha256==OFFICIAL_SPEC_SHA256)
    if (anchors[0] or anchors[2]) and not all(anchors):
        raise ValueError('official MD-V3 identity conflict: full model SHA256, byte count and spec SHA256 must agree')
    if all(anchors):
        if declaration=='world-flu':raise ValueError('official MD-V3 frame conflict: parent ModelAction is model-frd')
        provenance='VERIFIED_OFFICIAL_IDENTITY';source=MODEL_BODY_FRD
    else:
        if declaration=='auto':
            raise ValueError('unknown model action basis: explicit declaration required; use --model-action-frame model-frd or world-flu')
        provenance='USER_DECLARATION';source=MODEL_BODY_FRD if declaration=='model-frd' else WORLD_BODY_FLU
    return ActionFrameResolution(identity,declaration,source,WORLD_BODY_FLU,provenance,source==MODEL_BODY_FRD)


def preflight_public_onnx_policy(model_path: Path, spec_path: Path, *, model_action_frame: str='auto') -> ActionFrameResolution:
    """Verify current full files and frame before constructing any policy/session.

    This result is informational. The public factory always repeats verification;
    it accepts no trusted/prevalidated resolution or session injection argument.
    """
    if type(model_action_frame) is not str or model_action_frame not in MODEL_ACTION_FRAMES:
        raise ValueError('model_action_frame must be auto, model-frd or world-flu')
    from .onnx_contract import ModelContract
    model_path=Path(model_path);spec_path=Path(spec_path)
    spec_bytes=spec_path.read_bytes()
    contract=ModelContract.load(spec_path)
    observed=contract.check_file(model_path)
    if spec_path.read_bytes()!=spec_bytes:raise ValueError('spec changed during identity verification')
    identity=ModelIdentity(str(model_path.resolve()),str(spec_path.resolve()),observed,model_path.stat().st_size,sha256(spec_bytes).hexdigest())
    return _resolve_action_frame(identity,model_action_frame)


def _construct_policy(model_path, spec_path, **kwargs):
    from .onnx_policy import OnnxBigModelPolicy
    return OnnxBigModelPolicy(model_path,spec_path,**kwargs)


def _bind_policy(inner, resolution):
    marker=getattr(inner,'applied_action_frame',None)
    if (getattr(inner,'world_frame_adapter_applied',False) or marker not in (None,MODEL_BODY_FRD)
            or (marker==MODEL_BODY_FRD and resolution.parent_action_frame!=MODEL_BODY_FRD)):
        raise ValueError('already bound or incompatible action frame; repeated binding prohibited')
    if resolution.rotation_applied:
        from .model_world_frame import WorldFramePolicyAdapter
        return WorldFramePolicyAdapter(inner,source_action_frame=MODEL_BODY_FRD)
    return inner


@dataclass(frozen=True)
class PublicActionFrameBinding:
    policy: Any
    resolution: ActionFrameResolution

    def receipt(self) -> dict:
        # Preserve every committed parent row and every bridge, including dangling
        # parent rows after failure. These counts cannot reveal uncommitted ORT calls.
        trace=[asdict(row) for row in self.policy.trace]
        bridge=deepcopy(self.policy.bridge_receipts) if self.resolution.rotation_applied else []
        return dict(protocol='public-onnx-action-frame-v1',**asdict(self.resolution),
            parent_trace=trace,parent_trace_count=len(trace),bridge_receipts=bridge,bridge_receipt_count=len(bridge),
            total_executed_model_calls=None,execution_count_scope='committed parent trace and completed bridges only; total execution unknown',
            episode_completion_inferred=False,parent_trace_values_rewritten=False,raw_outputs_rewritten=False,
            renderer_selected=False,source_basis_verified=self.resolution.provenance=='VERIFIED_OFFICIAL_IDENTITY')


def _write_binding_receipt(binding: PublicActionFrameBinding, path: Path) -> None:
    """Called in entrypoint finally blocks so failed episodes keep committed evidence."""
    receipt=binding.receipt();error=sys.exc_info()[1];chain=[];seen=set()
    while error is not None and id(error) not in seen:
        seen.add(id(error));chain.append(f'{type(error).__name__}: {error}')
        error=error.__cause__ if error.__cause__ is not None else error.__context__
    receipt.update(episode_error=chain[0] if chain else None,episode_error_chain=chain)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def create_public_onnx_policy(model_path: Path, spec_path: Path, *, model_action_frame: str='auto',
                              traffic_is_rhd: bool=False, lat_action_t_s: float=.175,
                              long_action_t_s: float=.175) -> PublicActionFrameBinding:
    resolution=preflight_public_onnx_policy(model_path,spec_path,model_action_frame=model_action_frame)
    inner=_construct_policy(model_path,spec_path,traffic_is_rhd=traffic_is_rhd,
        lat_action_t_s=lat_action_t_s,long_action_t_s=long_action_t_s)
    return PublicActionFrameBinding(_bind_policy(inner,resolution),resolution)
