"""Real ONNX Runtime execution of a small generated TEST GRAPH (not a big model).

Only run when onnx + onnxruntime are installed. The graph really consumes the
camera tensor, returns a full action vector, and maintains recurrent state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bigbench.camera_rig import SchematicDualCamera
from bigbench.onnx_policy import OnnxBigModelPolicy
from bigbench.runner import run_episode
from bigbench.scenario import get_scenario

try:
    import onnx
    import onnxruntime
except ImportError:
    onnx = None
    onnxruntime = None


def make_small_native_onnx(path: Path) -> tuple[Path, Path]:
    assert onnx is not None
    h, T = onnx.helper, onnx.TensorProto
    inputs = [
        h.make_tensor_value_info('new_img', T.UINT8, [2,6,128,256]),
        h.make_tensor_value_info('desire', T.FLOAT, [8]),
        h.make_tensor_value_info('traffic_convention', T.FLOAT, [1,2]),
        h.make_tensor_value_info('action_t', T.FLOAT, [1,2]),
        h.make_tensor_value_info('state_img_q', T.UINT8, [2,1,6,128,256]),
        h.make_tensor_value_info('state_feat_q', T.FLOAT, [1,1,1]),
    ]
    outputs = [
        h.make_tensor_value_info('outputs', T.FLOAT, [1,18452]),
        h.make_tensor_value_info('next_state_img_q', T.UINT8, [2,1,6,128,256]),
        h.make_tensor_value_info('next_state_feat_q', T.FLOAT, [1,1,1]),
    ]
    import numpy as np
    from onnx import numpy_helper
    initializers = [
        numpy_helper.from_array(np.zeros((1,2062),dtype=np.float32),name='prefix'),
        numpy_helper.from_array(np.zeros((1,18452-2064),dtype=np.float32),name='suffix'),
        numpy_helper.from_array(np.array([[0.0]],dtype=np.float32),name='accel'),
        numpy_helper.from_array(np.array(10000.,dtype=np.float32),name='scale'),
        numpy_helper.from_array(np.array([1,1],dtype=np.int64),name='newshape'),
        numpy_helper.from_array(np.array([[[1.]]],dtype=np.float32),name='one'),
    ]
    nodes = [
        h.make_node('Cast',['new_img'],['flt'],to=T.FLOAT),
        h.make_node('ReduceMean',['flt'],['mean'],axes=[0,1,2,3],keepdims=0),
        h.make_node('Div',['mean','scale'],['lataccel_scalar']),
        h.make_node('Reshape',['lataccel_scalar','newshape'],['lataccel']),
        h.make_node('Concat',['prefix','lataccel','accel','suffix'],['outputs'],axis=1),
        h.make_node('Identity',['state_img_q'],['next_state_img_q']),
        h.make_node('Add',['state_feat_q','one'],['next_state_feat_q']),
    ]
    graph = h.make_graph(nodes,'toy-only-camera-conditioned-stateful-graph',inputs,outputs,initializer=initializers)
    model=h.make_model(graph,opset_imports=[h.make_opsetid('',13)],producer_name='bigbench-unit-test')
    model.ir_version=9
    onnx.checker.check_model(model)
    file = path/'toy_graph.onnx'
    onnx.save(model,str(file))
    manifest={
        'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
        'nbytes':file.stat().st_size,'frame_skip':4,
        'input_shapes':{i.name:list(i.type.tensor_type.shape.dim[j].dim_value for j in range(len(i.type.tensor_type.shape.dim))) for i in inputs},
        'output_shapes':{i.name:list(i.type.tensor_type.shape.dim[j].dim_value for j in range(len(i.type.tensor_type.shape.dim))) for i in outputs},
        'output_slices':{'plan':[917,1907],'action':[2062,2066]},
        'source':'TEST_GRAPH_NOT_REAL_BIG_MODEL',
    }
    spec=path/'toy_contract.json'
    spec.write_text(json.dumps(manifest),encoding='utf-8')
    return file,spec


@unittest.skipUnless(onnx and onnxruntime,'onnx+onnxruntime optional; GitHub inference CI installs both')
class NativeOrtTest(unittest.TestCase):
    def test_real_ort_uses_camera_and_updates_recurrent_state(self):
        with TemporaryDirectory() as d:
            model,spec=make_small_native_onnx(Path(d))
            policy=OnnxBigModelPolicy(model,spec)
            run=run_episode(get_scenario('s_curve'),policy,camera=SchematicDualCamera(),max_steps=3)
            self.assertEqual(run.classification,'ONNX_EXECUTED_SCHEMATIC_INPUT_UNCALIBRATED')
            self.assertEqual(len(policy.trace),3)
            self.assertEqual(float(policy.state['state_feat_q'][0,0,0]),3.0)
            self.assertTrue(all(m.raw_lateral_accel_mps2>0 for m in policy.trace))
            self.assertGreater(len({m.image_checksum for m in policy.trace}),1)
            self.assertEqual(len(run.frames),3)


if __name__ == '__main__':
    unittest.main()
