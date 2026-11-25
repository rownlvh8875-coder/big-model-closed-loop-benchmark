"""Verify recorded Add/Tanh tensors and attribute the measured residual logit change."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import onnx
from onnx import TensorProto, numpy_helper
from bigbench.sdk3_action_terms import digest
from scripts.panda_sdk3_runtime import MODEL_SHA
from scripts.verify_sdk3_action_terms import need, original_edge, read_json

# The first tuple contains the original input names, preserving the node's order.
NODES = {
    'node_add_74': ('Add', ('select_5', 'linear_154'), 'add_74'),
    'node_add_75': ('Add', ('linear_156', 'add_74'), 'add_75'),
    'node_tanh': ('Tanh', ('linear_157',), 'tanh'),
    'node_add_76': ('Add', ('slice_6', 'tanh'), 'add_76'),
}
FEATURES = ('select_5', 'linear_154', 'linear_156')


def size(value):
    return (1, 512) if value in {*FEATURES, 'add_74', 'add_75'} else (1, 2)


def graph_contract(model, *, expected_sha=MODEL_SHA):
    sha = digest(model)
    need(sha == expected_sha, 'pinned ONNX bytes')
    graph = onnx.load(model, load_external_data=False).graph
    nodes = {name: node for node in graph.node for name in node.output}
    types = {item.name:item.type.tensor_type.elem_type for item in (*graph.input,*graph.value_info,*graph.output)}
    for name, (op, inputs, output) in NODES.items():
        node = nodes[output]
        need((node.name, node.op_type, tuple(node.input)) == (name, op, inputs), f'original graph mapping {name}')
        need(types[output] == TensorProto.FLOAT16, f'original graph dtype {output}')
    initializers = {item.name:item for item in graph.initializer}
    readout = nodes['linear_157']
    mat_input, weight_name, bias_name = readout.input
    attrs = {a.name: onnx.helper.get_attribute_value(a) for a in readout.attribute}
    need(readout.op_type == 'Gemm' and mat_input == 'add_75'
         and attrs == {'alpha':1., 'beta':1., 'transA':0, 'transB':1}, 'exact affine residual readout')
    weights = numpy_helper.to_array(initializers[weight_name]).astype(np.float64)
    bias = numpy_helper.to_array(initializers[bias_name]).astype(np.float64)
    need(weights.shape == (2,512) and bias.shape == (2,) and np.isfinite(weights).all() and np.isfinite(bias).all(),
         'finite 2-by-512 readout and pair of biases')
    action, output = nodes['cat_4'], nodes['outputs']
    packed, = output.input
    need(action.op_type == nodes[packed].op_type == 'Concat' and action.input[0] == 'add_76'
         and 'cat_4' in nodes[packed].input and output.op_type == 'Cast'
         and all(types[key]==TensorProto.FLOAT16 for key in ('add_76','cat_4',packed))
         and types['outputs']==TensorProto.FLOAT, 'official FP16 action boundary')
    proof = dict(model_sha256=sha, nodes=NODES, readout_weight=weight_name, readout_bias=bias_name,
                 public_path=['add_76','cat_4',packed,'outputs'],
                 public_path_dtypes=['FLOAT16','FLOAT16','FLOAT16','FLOAT'])
    return weights, bias, proof


def logged_edges(log, steps):
    text = log.read_text(errors='replace')
    headers = list(re.finditer(r'^(Add|Tanh) node: (\w+)$', text, re.M))
    groups = {node: [] for node in NODES}
    for index, m in enumerate(headers):
        op, name = m.groups()
        need(name in NODES and op == NODES[name][0], f'unregistered native node {name}')
        section = text[m.end():headers[index+1].start() if index+1<len(headers) else len(text)]
        names = re.findall(r'^(Input|Output) (\d+) Name: (\S+)$', section, re.M)
        expected = [('Input',str(i)) for i in range(len(NODES[name][1]))]+[('Output','0')]
        need([(kind,idx) for kind,idx,_ in names] == expected, f'unexpected inputs/output for {name}')
        names = tuple(value for _,_,value in names)
        need(tuple(map(original_edge,names)) == (*NODES[name][1], NODES[name][2]), f'original edge names {name}')
        groups[name].append(names)
    need('Placement: CPUExecutionProvider' in text, 'native CPU placement')
    need(all(len(items)==steps and len(set(items))==1 for items in groups.values()), 'one stable execution per node per inference')
    return {name: items[0] for name,items in groups.items()}


def load_step(folder, edges):
    arrays = {}
    files = {}
    for path in sorted(folder.iterdir()):
        need(not path.is_symlink() and path.is_file() and path.suffix == '.tensorproto'
             and 0<path.stat().st_size<=4096, f'unexpected native dump {path.name}')
        blob = path.read_bytes()
        tensor = TensorProto.FromString(blob)
        arr = numpy_helper.to_array(tensor)
        need(tensor.name not in arrays and not tensor.external_data
             and arr.dtype in (np.float16,np.float32) and arr.shape==size(original_edge(tensor.name))
             and np.isfinite(arr).all(), f'invalid native tensor {path.name}')
        arrays[tensor.name] = arr
        files[tensor.name] = dict(file=path.name,sha256=hashlib.sha256(blob).hexdigest())
    need(set(arrays)=={edge for chain in edges.values() for edge in chain}, f'incomplete native tensor group {folder.name}')
    return arrays, files


def checked_add(arrays, edges, node):
    a, b, out = (arrays[key] for key in edges[node])
    need(a.dtype==b.dtype==out.dtype and np.add(a,b,dtype=out.dtype).tobytes()==out.tobytes(),
         f'actual CPU Add arithmetic {node}')
    return a, b, out


def verify_step(folder, edges, frame, weights, bias):
    arrays, files = load_step(folder, edges)
    select, encoded, merge = checked_add(arrays, edges, 'node_add_74')
    mlp, pre_merge, readout = checked_add(arrays, edges, 'node_add_75')
    base, residual, summed = checked_add(arrays, edges, 'node_add_76')
    logits, tanh = (arrays[key] for key in edges['node_tanh'])
    need(pre_merge.tobytes()==merge.astype(pre_merge.dtype).tobytes(), 'native merge feeds affine path')
    need(residual.tobytes()==tanh.astype(residual.dtype).tobytes() and np.all(np.abs(residual)<=1),
         'native Tanh feeds public Add')
    public = np.asarray(frame['raw_model_action'], dtype='<f4')
    need(public.shape==(4,) and public[:2].tobytes()==summed.astype('<f2').astype('<f4').tobytes()
         and hashlib.sha256(public.tobytes()).hexdigest()==frame['raw_action_sha256'],
         f'original FP16 export/public action binding {folder.name}')

    terms = {name:(weights@value[0].astype(np.float64)).tolist()
             for name,value in zip(FEATURES,(select,encoded,mlp),strict=True)}
    affine = (weights@readout[0].astype(np.float64))+bias
    native_logit = logits[0].astype(np.float64)
    abs_operands = np.abs(weights) @ np.abs(readout[0].astype(np.float64)) + np.abs(bias)
    # Conservative dot-product bound allowing 1026 separately rounded FP32 operations.
    unit = 2.**-24
    gamma = 1026*unit/(1-1026*unit)
    comparison = affine.astype(logits.dtype).astype(np.float64)
    bound = gamma*abs_operands + 2e-7 + np.abs(comparison-affine)
    if logits.dtype==np.dtype('float16'):
        bound += np.abs(np.spacing(logits[0]).astype(np.float64))
    need(np.all(np.abs(native_logit-affine)<=bound), f'actual Tanh input matches pinned affine equivalent {folder.name}')
    projected = sum(np.asarray(v) for v in terms.values())+bias
    return dict(step=frame['step'], native_add_dtype=str(summed.dtype),
                logit=native_logit.tolist(), tanh=residual[0].tolist(), base=base[0].tolist(),
                public_frd=public[:2].tolist(), direct_logit_terms=terms,
                projection_remainder=(native_logit-projected).tolist(),
                affine_arithmetic_error=(native_logit-affine).tolist(),
                tanh_reference_error=(residual[0].astype(np.float64)-np.tanh(native_logit)).tolist(),
                tensorproto=files)


def verify_native(native, model):
    report = read_json(native/'report.json')
    frames = report['trajectory']['frames']
    need(0<len(frames)<=600 and report['inference_bounds']==[len(frames)]*2, 'one frame per actual inference')
    weights, bias, graph = graph_contract(model)
    need(report['model_sha256']==graph['model_sha256'], 'verified graph is the actual model')
    edges = logged_edges(native/'stdout.log',len(frames))
    folder = native/'action-terms'
    need({p.name for p in folder.iterdir()}=={str(f['step']) for f in frames}, 'all native dumps retained')
    rows=[verify_step(folder/str(f['step']),edges,f,weights,bias) for f in frames]
    return dict(status='NATIVE_RESIDUAL_TERMS_VERIFIED',build_graph=graph,edges=edges,rows=rows,
                report_sha256=digest(native/'report.json'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native',type=Path)
    parser.add_argument('model',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify_native(args.native,args.model),indent=2,allow_nan=False))
