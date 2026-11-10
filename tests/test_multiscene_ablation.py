"""Fail-closed pure assertions; mock reports are NOT native MetaDrive evidence."""
import copy
import unittest

from scripts.native_scene_ablation_sweep import (
    ALLOWED_FRACTIONS, CONDITIONS, compare_ablation,
)


def sample(name="baseline"):
    ablation=(None if name=="baseline" else {
        "ablation":"PSSM.update", "graphics_igLoop_preserved":True,
    })
    colors={"post_warmup_unique_sha256":2}
    tensors={"after_warmup_unique_sha256":2,"after_warmup_bit_exact":False,
             "max_changed_tensor_elements_after_warmup":3}
    return {
        "status":"OBSERVED_NATIVE_SCENE", "scenario":"s_curve_left_right",
        "seed":20261109, "fraction":0.12, "camera_height_m":1.22,
        "world_pose":[[5.,0.,1.22],[-90.,0.,0.]], "condition":name,
        "frames":9, "warmup":2, "scene_visibility":"ego_hidden",
        "capture_mode":"task_step_pair","source_rgb":{"road":colors,"wide":colors},
        "model_rgb":{"road":colors,"wide":colors},"i420":tensors,
        "ablation":ablation,"gpu_texture_extract_calls":0,
        "pose_shift_positive_control":{"road":True,"wide":True},
        "real_vehicle_testing":False,"model_scoring_allowed":False,
    }


class MultisceneContracts(unittest.TestCase):
    def test_compact_receipts_cannot_rank_models(self):
        a,b=sample(),sample("shadow_off")
        out=compare_ablation(a,b)
        self.assertEqual(out["status"],
                         "MULTISCENE_NATIVE_ABLATION_OBSERVED_NO_CAUSE_PROVEN")
        self.assertFalse(out["native_onnx_closed_loop_pass"])
        self.assertFalse(out["model_scoring_allowed"])
        self.assertEqual(out["baseline"]["source_unique_road"],2)

    def test_expected_allowed_fractions(self):
        self.assertEqual(ALLOWED_FRACTIONS,(0.12,0.28))
        self.assertEqual(CONDITIONS,{"baseline":None,"shadow_off":"PSSM.update"})

    def test_incomplete_or_stale_camera_fails(self):
        a,b=sample(),sample("shadow_off")
        b["status"]="INCONCLUSIVE_NATIVE_SCENE"
        with self.assertRaises(ValueError):compare_ablation(a,b)
        b=sample("shadow_off")
        b["pose_shift_positive_control"]["wide"]=False
        with self.assertRaises(ValueError):compare_ablation(a,b)

    def test_ablation_identity_and_scope(self):
        a,b=sample(),sample("shadow_off")
        b["ablation"]["ablation"]="update main chase camera"
        with self.assertRaises(ValueError):compare_ablation(a,b)
        b=sample("shadow_off")
        b["gpu_texture_extract_calls"]=1
        with self.assertRaises(ValueError):compare_ablation(a,b)
        b=sample("shadow_off")
        b["scenario"]="out_ramp"
        with self.assertRaises(ValueError):compare_ablation(a,b)

    def test_positive_control_and_vehicle_flag(self):
        a,b=sample(),sample("shadow_off")
        a["pose_shift_positive_control"]["road"]=False
        with self.assertRaises(ValueError):compare_ablation(a,b)
        a=sample()
        a["real_vehicle_testing"]=True
        with self.assertRaises(ValueError):compare_ablation(a,b)


if __name__=="__main__":
    unittest.main()
