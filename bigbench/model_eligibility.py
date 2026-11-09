"""Read-only inventory of SHA-pinned large ONNX contracts; no weights fallback.

Contract declaration is NOT graph validation, inference, camera fidelity or
model qualification. Navigation models require explicit valid nav inputs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .onnx_contract import ModelContract, ModelContractError


@dataclass(frozen=True)
class Candidate:
    name: str
    spec_path: str
    sha256: str
    size_bytes: int
    recurrent_states: tuple[str,...]
    needs_navigation: bool
    status: str

    def to_dict(self):
        o=asdict(self)
        o['recurrent_states']=list(self.recurrent_states)
        return o


def inspect_candidate(spec_path: Path, model_path: Path | None = None) -> Candidate:
    contract=ModelContract.load(spec_path)
    if model_path is not None:
        contract.check_file(model_path)
        status='WEIGHTS_HASH_VERIFIED_GRAPH_AND_CAMERA_NOT_VALIDATED'
    else:
        status='MANIFEST_ONLY_MODEL_WEIGHTS_NOT_VERIFIED'
    return Candidate(spec_path.stem,str(spec_path),contract.sha256,contract.nbytes,
                     contract.state_keys,contract.needs_navigation,status)


def scan_candidates(spec_dir: Path) -> dict:
    if not spec_dir.is_dir():
        raise ModelContractError('spec directory is unavailable')
    candidates=[]
    for path in sorted(spec_dir.glob('*.json')):
        candidates.append(inspect_candidate(path).to_dict())
    hashes=[v['sha256'] for v in candidates]
    if len(hashes)!=len(set(hashes)):
        raise ModelContractError('duplicate model weights found in candidate manifest list')
    return {
        'classification':'READ_ONLY_PINNED_MODEL_MANIFEST_INVENTORY',
        'model_scoring_allowed':False,
        'real_vehicle_testing':False,
        'candidate_count':len(candidates),
        'navigation_required':[v['name'] for v in candidates if v['needs_navigation']],
        'candidates':candidates,
    }
