"""Bind the original tensor files to every public md-v3 action and frame."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigbench.full_s_validation import STRICT
import numpy as np
import onnx
from onnx import TensorProto, numpy_helper


def need(value, message):
    if not value:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_bytes())


def original_edge(optimized):
    return optimized.removeprefix('InsertedPrecisionFreeCast_')


def logged_edges(log, steps):
    text = log.read_text(errors='replace')
    matches = re.findall(r'Add node: node_add_76\nInput 0 Name: (\S+)\n'
                         r'(?:[^\n]*\n)*?Input 1 Name: (\S+)\n'
                         r'(?:[^\n]*\n)*?Output 0 Name: (\S+)\n', text)
    need(len(matches) == steps and len(set(matches)) == 1, 'one stable Add execution per inference')
    edges = matches[0]
    need(tuple(map(original_edge, edges)) == ('slice_6', 'tanh', 'add_76'), f'Add edge mapping: {edges}')
    need('Placement: CPUExecutionProvider' in text, 'native CPU placement')
    return edges


def verify_step(folder, edges, frame):
    arrays = {}
    files = {}
    for path in sorted(folder.iterdir()):
        need(not path.is_symlink() and path.is_file() and path.suffix == '.tensorproto'
             and 0 < path.stat().st_size <= 4096, f'unexpected native dump: {path.name}')
        blob = path.read_bytes()
        tensor = TensorProto.FromString(blob)
        need(tensor.name not in arrays and tensor.data_type in (TensorProto.FLOAT, TensorProto.FLOAT16)
             and not tensor.external_data, f'unexpected dump dtype/metadata: {path.name}')
        array = numpy_helper.to_array(tensor)
        need(array.shape == (1, 2) and np.isfinite(array).all(), f'nonfinite or invalid Add shape: {path.name}')
        arrays[tensor.name] = array
        files[tensor.name] = {'file': path.name, 'sha256': hashlib.sha256(blob).hexdigest()}
    need(set(arrays) == set(edges), f'expected three original tensors: {folder.name}')
    base, residual, summed = (arrays[name] for name in edges)
    need(base.dtype == residual.dtype == summed.dtype, 'native Add inputs and output have the same dtype')
    need(np.all(np.abs(residual) <= 1), 'tanh residual outside [-1, 1]')
    need(np.add(base, residual, dtype=summed.dtype).tobytes() == summed.tobytes(),
         f'native result is not the sum: {folder.name}')
    public = np.asarray(frame['raw_model_action'], dtype='<f4')
    need(public.shape == (4,) and public[:2].tobytes() == summed.astype('<f4').tobytes(),
         f'native Add result differs from public acceleration: {folder.name}')
    need(hashlib.sha256(public.tobytes()).hexdigest() == frame['raw_action_sha256'],
         f'public action hash differs: {folder.name}')
    return dict(step=frame['step'], dtype=str(summed.dtype),
                base_frd_mps2=base[0].tolist(), residual_frd_mps2=residual[0].tolist(),
                sum_frd_mps2=summed[0].tolist(), tensorproto=files)


def verify_native(native):
    report = read_json(native/'report.json')
    frames = report['trajectory']['frames']
    need(bool(frames) and len(frames) <= 600, 'bounded native trial')
    need(report['inference_bounds'] == [len(frames)] * 2, 'one committed frame per actual inference')
    edges = logged_edges(native/'stdout.log', len(frames))
    root = native/'action-terms'
    need({path.name for path in root.iterdir()} == {str(f['step']) for f in frames}, 'all steps accounted for')
    rows = [verify_step(root/str(frame['step']), edges, frame) for frame in frames]
    return dict(status='NATIVE_ACTION_TERMS_VERIFIED', edges=edges, rows=rows,
                report_sha256=hashlib.sha256((native/'report.json').read_bytes()).hexdigest())


def compare_history(current, previous):
    now = current['trajectory']
    old = previous['trajectory']
    need((now['seed'], now['scenario']) == (old['seed'], old['scenario']), 'same archived condition')
    need(now['geometry'] == old['geometry'] and now['initial_state'] == old['initial_state'],
         'same route and initial pose')
    for a, b in zip(now['frames'], old['frames']):
        differences = [key for key in STRICT if a[key] != b[key]]
        if differences:
            return dict(shared_prefix=a['step']-1, first_divergence=a['step'], fields=differences)
    shared = min(len(now['frames']), len(old['frames']))
    same_length = len(now['frames']) == len(old['frames'])
    return dict(shared_prefix=shared, first_divergence=None if same_length else shared+1,
                fields=[] if same_length else ['completed_steps'],
                same_outcome=now['outcome']==old['outcome'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native', type=Path)
    parser.add_argument('--historical-report', type=Path)
    args = parser.parse_args()
    result = verify_native(args.native)
    if args.historical_report:
        result['historical_comparison'] = compare_history(read_json(args.native/'report.json'),
                                                           read_json(args.historical_report))
    print(json.dumps(result, indent=2))
