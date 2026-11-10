"""Tests of the real ONNX feed shape, recurrence, and schematic camera boundary.

Injected sessions are explicitly TEST DOUBLES, not performance benchmarks.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import numpy as np

from bigbench.camera import RGBFrame
from bigbench.camera_rig import SchematicDualCamera
from bigbench.image_adapter import i420_planes_to_six, camera_pair_to_model
from bigbench.onnx_contract import ModelContract, ModelContractError
from bigbench.onnx_policy import OnnxBigModelPolicy
from bigbench.policies import ModelObservation
from bigbench.runner import run_episode
from bigbench.scenario import get_scenario


class TinySession:
    """Minimal fake graph; action output depends on camera + recurrent state."""
    def __init__(self, spec):
        self.spec = spec
        self.feeds = []
    def _node(self, name, shape, *, output=False):
        dtype = 'tensor(uint8)' if name in ('new_img', 'state_img_q', 'next_state_img_q') else 'tensor(float)'
        return SimpleNamespace(name=name, shape=shape, type=dtype)
    def get_inputs(self):
        return [self._node(k,list(v)) for k,v in self.spec['input_shapes'].items()]
    def get_outputs(self):
        return [self._node(k,list(v),output=True) for k,v in self.spec['output_shapes'].items()]
    def run(self, output_names, inputs):
        self.feeds.append({k:v.copy() for k,v in inputs.items()})
        outputs = np.zeros((1, 18452),dtype=np.float32)
        outputs[0,2062] = float(np.mean(inputs['new_img'])) / 250.0  # synthetic lateral accel
        outputs[0,2063] = -0.2
        state = {'next_state_img_q':inputs['state_img_q'].copy(),
                 'next_state_feat_q':inputs['state_feat_q']+1}
        # Deliberately mutate a corner of the image queue to verify next-state wiring.
        state['next_state_img_q'].flat[0] += 1
        lookup = {'outputs':outputs, **state}
        return [lookup[name] for name in output_names]


def make_manifest(path, *, nav=False):
    fake_model = path / 'tiny.onnx'
    fake_model.write_bytes(b'fake-session-only-not-a-real-onnx')
    specs = {
        'sha256':hashlib.sha256(fake_model.read_bytes()).hexdigest(),
        'nbytes':fake_model.stat().st_size,
        'frame_skip':4,
        'input_shapes':{
            'new_img':[2,6,128,256], 'desire':[8],
            'traffic_convention':[1,2], 'action_t':[1,2],
            'state_img_q':[2,1,6,128,256], 'state_feat_q':[1,1,1],
        },
        'output_shapes':{
            'outputs':[1,18452],
            'next_state_img_q':[2,1,6,128,256],
            'next_state_feat_q':[1,1,1],
        },
        'output_slices':{'plan':[917,1907], 'action':[2062,2066]},
    }
    if nav:
        specs['input_shapes']['nav_map'] = [1,1,256,256]
        specs['input_shapes']['navigation'] = [1,47]
    p = path / 'manifest.json'
    p.write_text(json.dumps(specs),encoding='utf-8')
    return fake_model,p,specs


class ModelIntegrationTests(unittest.TestCase):
    def test_six_channel_exact_index_order(self):
        y = np.arange(4*6,dtype=np.uint8).reshape(4,6)
        u = np.full((2,3),55,dtype=np.uint8)
        v = np.full((2,3),66,dtype=np.uint8)
        out=i420_planes_to_six(y,u,v)
        self.assertEqual(out.shape,(6,2,3))
        np.testing.assert_array_equal(out[0], y[0::2,0::2])
        np.testing.assert_array_equal(out[1], y[1::2,0::2])
        np.testing.assert_array_equal(out[2], y[0::2,1::2])
        np.testing.assert_array_equal(out[3], y[1::2,1::2])
        self.assertTrue(np.all(out[4]==55) and np.all(out[5]==66))

    def test_dual_synthetic_camera_has_two_distinct_views(self):
        scene=get_scenario('s_curve')
        s=scene.road.at(0)
        from bigbench.kinematics import AgentState
        cam=SchematicDualCamera()
        pair=cam.render_pair(scene,AgentState(0,s.x,s.y,s.heading,15),0)
        self.assertNotEqual(pair.road.sha256,pair.wide.sha256)
        self.assertEqual(camera_pair_to_model(pair.road,pair.wide).shape,(2,6,128,256))

    def test_pinned_contract_rejects_hash_mismatch(self):
        with TemporaryDirectory() as d:
            model, spec, _=make_manifest(Path(d))
            model.write_bytes(b'not-the-same')
            with self.assertRaises(ModelContractError):
                ModelContract.load(spec).check_file(model)

    def test_recurrence_and_float_action_interpretation(self):
        with TemporaryDirectory() as d:
            model, manifest, spec=make_manifest(Path(d))
            fake=TinySession(spec)
            policy=OnnxBigModelPolicy(model,manifest,session=fake)
            cam=SchematicDualCamera()
            road=get_scenario('s_curve')
            from bigbench.kinematics import AgentState
            a=road.road.at(0)
            pair=cam.render_pair(road,AgentState(0,a.x,a.y,a.heading,15),0)
            obs=ModelObservation(pair.road, 15.0, 0, wide_frame=pair.wide)
            first=policy.step(obs)
            second=policy.step(obs)
            self.assertAlmostEqual(first.acceleration_mps2,-.2,places=5)
            self.assertAlmostEqual(first.curvature_1pm, policy.trace[0].raw_lateral_accel_mps2 / 225, places=7)
            self.assertEqual(float(fake.feeds[0]['state_feat_q'].flat[0]),0)
            self.assertEqual(float(fake.feeds[1]['state_feat_q'].flat[0]),1)
            self.assertEqual(int(fake.feeds[1]['state_img_q'].flat[0]),1)
            self.assertEqual(policy.evidence_class,'TEST_DOUBLE_NOT_REAL_ONNX')
            # Audit exactly the new_img payload delivered to ORT, not a
            # reconstructed/different frame from the renderer.
            self.assertEqual(
                policy.last_input_image_sha256,
                hashlib.sha256(fake.feeds[1]['new_img'].tobytes()).hexdigest(),
            )
            policy.reset()
            self.assertIsNone(policy.last_input_image_sha256)
            self.assertEqual(len(policy.trace),0)
            self.assertEqual(float(policy.state['state_feat_q'].flat[0]),0)

    def test_navigation_missing_fails_instead_of_zero_filling(self):
        with TemporaryDirectory() as d:
            model, manifest, spec=make_manifest(Path(d),nav=True)
            fake=TinySession(spec)
            policy=OnnxBigModelPolicy(model,manifest,session=fake)
            dummy=RGBFrame(512,256,bytes([64,64,64])*(512*256))
            with self.assertRaisesRegex(ModelContractError,'navigation model needs explicit'):
                policy.step(ModelObservation(dummy,10,0,wide_frame=dummy))
            self.assertEqual(len(fake.feeds),0)

    def test_legacy_queued_contract_fails_closed(self):
        with TemporaryDirectory() as d:
            model,manifest,spec=make_manifest(Path(d))
            spec['input_shapes'].pop('new_img')
            spec['input_shapes']['img']=[1,12,128,256]
            manifest.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ModelContractError,'legacy queued'):
                ModelContract.load(manifest)

    def test_structural_closed_loop_with_fake_session(self):
        with TemporaryDirectory() as d:
            model,manifest,spec=make_manifest(Path(d))
            fake=TinySession(spec)
            policy=OnnxBigModelPolicy(model,manifest,session=fake)
            run=run_episode(get_scenario('s_curve'),policy,camera=SchematicDualCamera(),max_steps=5)
            self.assertEqual(run.classification,'TEST_DOUBLE_NOT_REAL_ONNX')
            self.assertEqual(len(run.frames),5)
            self.assertGreater(run.summary['distinct_camera_frames'],1)
            self.assertEqual(len(policy.trace),5)
            self.assertNotEqual(fake.feeds[0]['new_img'].tobytes(),fake.feeds[-1]['new_img'].tobytes())


if __name__=='__main__':
    unittest.main()
