"""Read-only ONNX graph contract inspection; no model download or implicit fallback."""
from __future__ import annotations
import hashlib
from pathlib import Path


def inspect_onnx(path: Path) -> dict:
    if not path.is_file() or path.suffix.lower() != '.onnx':
        raise ValueError('existing .onnx model file required')
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError('ONNX inspection requires pip install onnxruntime (optional)') from exc
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            hasher.update(block)
    # Disable graph optimizations: inspect the original contract only.
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    session = ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])
    def detail(o):
        return {'name':o.name, 'shape':list(o.shape), 'type':o.type}
    return {'path':str(path), 'sha256':hasher.hexdigest(),
            'size_bytes':path.stat().st_size,
            'inputs':[detail(i) for i in session.get_inputs()],
            'outputs':[detail(o) for o in session.get_outputs()],
            'status':'CONTRACT_INSPECTED_NOT_DRIVING_VALIDATED'}
