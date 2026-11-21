"""Exercise the linked multi-node dump and FP16 action boundary on a synthetic full path."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper, shape_inference
from bigbench.sdk3_action_terms import DEBUG_FLAGS, digest, release_build
from scripts.verify_sdk3_residual_terms import (
    FEATURES, graph_contract, logged_edges, need, verify_step,
)


def fixture(path):
    nodes = [
        helper.make_node('Add', ['select_5','linear_154'], ['add_74'], name='node_add_74'),
        helper.make_node('Add', ['linear_156','add_74'], ['add_75'], name='node_add_75'),
        helper.make_node('Gemm', ['add_75','weights','bias'], ['linear_157'], name='node_linear_157',
                         alpha=1.,beta=1.,transA=0,transB=1),
        helper.make_node('Tanh', ['linear_157'], ['tanh'], name='node_tanh'),
        helper.make_node('Add', ['slice_6','tanh'], ['add_76'], name='node_add_76'),
        helper.make_node('Concat',['add_76','tail'],['cat_4'],name='node_cat_4',axis=1),
        helper.make_node('Concat',['cat_4','padding'],['cat_5'],name='node_cat_5',axis=1),
        helper.make_node('Cast',['cat_5'],['outputs'],name='fp32_export',to=TensorProto.FLOAT),
    ]
    weights = np.zeros((2,512),np.float16)
    weights[:,:3] = [[.25,.375,-.0625],[-.125,.5,.25]]
    bias = np.asarray([.0625,-.125],dtype=np.float16)
    inputs = [helper.make_tensor_value_info(name,TensorProto.FLOAT16,[1,count])
              for name,count in [*((key,512) for key in FEATURES),('slice_6',2),('tail',2),('padding',2)]]
    graph = helper.make_graph(nodes,'residual_fixture',inputs,
                              [helper.make_tensor_value_info('outputs',TensorProto.FLOAT,[1,6])],
                              [numpy_helper.from_array(weights,'weights'),numpy_helper.from_array(bias,'bias')])
    model = shape_inference.infer_shapes(helper.make_model(graph,ir_version=9,opset_imports=[helper.make_opsetid('',17)]))
    onnx.checker.check_model(model)
    with path.open('xb') as out:
        out.write(model.SerializeToString())


def worker(site, evidence):
    sys.path.insert(0,str(site))
    import onnxruntime as ort
    need(ort.__version__=='1.20.1' and release_build(ort.get_build_info())
         and Path(ort.__file__).is_relative_to(site),'candidate release runtime')
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(evidence/'fixture.onnx'), options, providers=['CPUExecutionProvider'])
    frames = []
    for step, sample in enumerate(((1.,.5,-.75),(.5,.625,.25),(-1.,-.125,.75)),1):
        folder = evidence/str(step)
        folder.mkdir()
        feed = {name:np.zeros((1,512),dtype=np.float16) for name in FEATURES}
        for name,values in zip(FEATURES,(sample,sample[::-1],(.25,-.25,.5)),strict=True):
            feed[name][0,:3]=values
        feed.update(slice_6=np.array([[.3125,-.125]],dtype=np.float16),
                    tail=np.zeros((1,2),dtype=np.float16),padding=np.zeros((1,2),dtype=np.float16))
        os.chdir(folder)
        action = session.run(['outputs'],feed)[0][0,:4].astype('<f4')
        frames.append(dict(step=step,raw_model_action=action.tolist(),
                           raw_action_sha256=hashlib.sha256(action.tobytes()).hexdigest()))
    (evidence/'frames.json').write_text(json.dumps(frames,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('site',type=Path)
    p.add_argument('evidence',type=Path)
    p.add_argument('--worker',action='store_true')
    args=p.parse_args()
    site,evidence=args.site.resolve(),args.evidence.resolve()
    if args.worker:
        worker(site,evidence)
        return
    evidence.mkdir(parents=True)
    model=evidence/'fixture.onnx'
    fixture(model)
    with (evidence/'stdout.log').open('xb') as stdout, (evidence/'stderr.log').open('xb') as stderr:
        subprocess.run([sys.executable,'-I','-B',__file__,str(site),str(evidence),'--worker'],
                       env=os.environ | DEBUG_FLAGS,stdout=stdout,stderr=stderr,timeout=90,check=True)
    weights,bias,graph=graph_contract(model,expected_sha=digest(model))
    frames=json.loads((evidence/'frames.json').read_bytes())
    edges=logged_edges(evidence/'stdout.log',len(frames))
    rows=[verify_step(evidence/str(frame['step']),edges,frame,weights,bias) for frame in frames]
    need(len(rows)==3 and len({tuple(row['logit']) for row in rows})==3,'three distinct fixture frames')
    (evidence/'qualification.json').write_text(json.dumps(dict(
        status='SYNTHETIC_RESIDUAL_PATH_VERIFIED', nodes=list(edges), rows=len(rows),
        official_model_processes=0, official_inferences=0, graph=graph),indent=2)+'\n')


if __name__=='__main__':
    main()
