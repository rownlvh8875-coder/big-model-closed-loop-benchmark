"""CPU-only literal checks. Fixtures never constitute native/model evidence."""
import subprocess
import hashlib
from pathlib import Path
import unittest
import tempfile
from types import SimpleNamespace
import numpy as np

from bigbench import preprocess_experiment as e


class SamplerTests(unittest.TestCase):
    def test_literal_pack_order(self):
        y = np.arange(16, dtype=np.uint8).reshape(4, 4)
        u = np.array([[20, 21], [22, 23]], np.uint8)
        v = u + 10
        got = e.sample_six(y, u, v, np.eye(3), 4, 4)
        np.testing.assert_array_equal(got, [
            [[0, 2], [8, 10]], [[4, 6], [12, 14]],
            [[1, 3], [9, 11]], [[5, 7], [13, 15]],
            [[20, 21], [22, 23]], [[30, 31], [32, 33]]])

    def test_uv_half_translation_and_clamping(self):
        y = np.arange(16, dtype=np.uint8).reshape(4, 4)
        u = np.array([[20, 21], [22, 23]], np.uint8)
        h = np.array([[1, 0, 2], [0, 1, -2], [0, 0, 1]])
        got = e.sample_six(y, u, u + 10, h, 4, 4)
        np.testing.assert_array_equal(got[4], [[21, 21], [21, 21]])
        np.testing.assert_array_equal(got[0], [[2, 3], [2, 3]])

    def test_nearest_even_literal_ties(self):
        p = np.array([[10, 20, 30, 40]], np.uint8)
        h = np.array([[1, 0, .5], [0, 1, 0], [0, 0, 1]])
        np.testing.assert_array_equal(e.nearest_plane(p, h, 4, 1), [[10, 30, 30, 40]])

    def test_invalid_projection_and_dtype(self):
        for p, h in [(np.zeros((4, 4)), np.eye(3)),
                     (np.zeros((4, 4), np.uint8), np.zeros((3, 3)))]:
            with self.assertRaises(ValueError):
                e.nearest_plane(p, h, 4, 4)

    def test_sampler_matches_prior_independent_implementation(self):
        # Runtime fixture optional in external CI; literal tests above are mandatory.
        root = Path('/workspace/shared/recorded-input-contract-20261120')
        if not root.exists():
            self.skipTest('prior immutable CPU study not mounted')
        import importlib.util
        spec = importlib.util.spec_from_file_location('prior_sampler', root/'cpu_sampler.py')
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        rng = np.random.default_rng(321)
        y = rng.integers(0, 256, (604, 964), np.uint8)
        u = rng.integers(0, 256, (302, 482), np.uint8)
        v = rng.integers(0, 256, (302, 482), np.uint8)
        h = np.array([[1.45, 0, 109.5], [0, 1.45, 232.5], [0, 0, 1]], np.float32)
        np.testing.assert_array_equal(e.sample_six(y, u, v, h), m.sample_six(y, u, v, h))

    def test_scoped_step_does_not_mutate_original_globals(self):
        from bigbench.onnx_policy import OnnxBigModelPolicy
        original = OnnxBigModelPolicy.step
        adapter = original.__globals__['camera_pair_to_model']
        supplied = lambda a, b: None
        bound = e.scoped_step(supplied)
        self.assertIs(bound.__code__, original.__code__)
        self.assertIs(bound.__globals__['camera_pair_to_model'], supplied)
        self.assertIs(original.__globals__['camera_pair_to_model'], adapter)
        different = {k for k in original.__globals__ if bound.__globals__[k] is not original.__globals__[k]}
        self.assertEqual(different, {'camera_pair_to_model'})

    def test_live_input_consumes_one_bound_capture(self):
        from bigbench.optical_calibration import reference_source, PinholeRectifier
        from bigbench.image_adapter import camera_pair_to_model
        rng = np.random.default_rng(45)
        images = {role:rng.integers(0,256,(604,964,3),np.uint8) for role in ('road','wide')}
        hashes = {k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in images.items()}
        intrinsics = {role:reference_source(role) for role in images}
        pair, _ = PinholeRectifier().rectify_pair(images['road'],images['wide'],
            road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
        with tempfile.TemporaryDirectory() as tmp:
            camera = SimpleNamespace(last_source_rgb_sha256=hashes)
            inputs = e.LiveInput(camera,intrinsics,'source_yuv_nearest_even',tmp)
            def capture(pose):
                inputs.record_native_rgb(images,hashes)
                return pair
            camera.capture = capture
            inputs.capture(None)
            got = inputs.prepare(pair.road,pair.wide)
            self.assertEqual(got.shape,(2,6,128,256))
            self.assertEqual(inputs.rows[0]['actual_tensor_sha256'],hashlib.sha256(got.tobytes()).hexdigest())
            np.testing.assert_array_equal(np.frombuffer((Path(tmp)/'first-baseline.bin').read_bytes(),np.uint8).reshape(got.shape),camera_pair_to_model(pair.road,pair.wide))
            with self.assertRaises(ValueError):
                inputs.prepare(pair.road,pair.wide)

    def test_frozen_baseline_files(self):
        root = Path(__file__).resolve().parents[1]
        expected = {'bigbench/onnx_policy.py': 'd983d5950296620a6ae89c88993829b4d2cebd35a6fd0e9046a980f75c9142da', 'bigbench/native_model_campaign.py': '0bcb4ca73e1404a7164be1c879a200eeff5ca41e47e3035301d40fd173000bad', 'bigbench/image_adapter.py': '7f6d53989ff072ba5b8461ba207ab68c52ac2b519d18d56d0decc68c467e6f03'}
        for name, sha in expected.items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest(), sha)

    def test_frozen_full_s_source_at_preprocess_experiment_revision(self):
        root = Path(__file__).resolve().parents[1]
        producer = 'f3928dd791677e6e22bddf48b610eb8df0633a81'
        frozen = subprocess.check_output(
            ['git', 'show', f'{producer}:bigbench/full_s_validation.py'],
            cwd=root,
        )
        self.assertEqual(hashlib.sha256(frozen.replace(b'\r\n', b'\n')).hexdigest(),
                         '3426729744a8789e2123fcaaf83972060d769fa77d4a3973142e5b8ba64c7b18')


if __name__ == '__main__':
    unittest.main()
