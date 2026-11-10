"""Synthetic-only fixed-pose cross-process SHA validation, NOT native CI data."""
import copy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.compare_native_pssm_cross_process import (
    ARMS,SEEDS,SCENES,compare_native_camera_repeats,compare_one_native_scene,
    aggregate_four_native_scenes,scene_directory,
)


def h(value):
    return sha256(str(value).encode("utf-8")).hexdigest()


def mock_native(seed,scene,arm,index,*,diff_step=None):
    mode,ablation,ticks=ARMS[arm]
    def series(label):
        items=[h(f"{seed}-{scene}-{mode}-{ablation}-{label}-{i}")
               for i in range(10)]
        if diff_step is not None and label=="source-road":
            items[diff_step-1]=h("deliberate-original-rgb-change")
        return items
    return {
        "status":"OBSERVED_NATIVE_PIXEL_CLOCK",
        "seed":seed,"scenario":scene,"fraction":.12,
        "process_id":10000+index,"process_uuid":f"uuid-{seed}-{scene}-{arm}-{index}",
        "mode":mode,"ablation":ablation,"frames":10,"warmup":2,
        "camera_pose":[[1.1,2.2,1.22],[-90.,0.,0.]],
        "raw_sensor_rgb_dims":[964,604],"model_rgb_dims":[512,256],
        "capture_schedule":"existing native MetaDrive paths, no extra ticks",
        "pssm_task_identity_correct":True,
        "all_panda_frame_count_deltas_as_expected":True,
        "task_manager_step_invocations_from_capture_call_path":ticks,
        "expected_panda_global_frame_count_delta_per_pair":ticks,
        "cpu_readbacks_bit_exact_without_new_render":True,
        "scene_visual_ego_pose_unchanged":True,
        "clock_observations_finite":True,
        "gpu_texture_extract_calls":0,"onnx_inference_used":False,
        "model_scoring_allowed":False,"real_vehicle_testing":False,
        "camera_plus_2m_positive":{"road":True,"wide":True},
        "registered_tasks_before":["igLoop","update main chase camera"]+
            (["PSSM.update"] if ablation=="baseline" else []),
        "ablation_receipt":None if ablation=="baseline" else {"removed":"PSSM.update"},
        "source_rgb":{
            "road":{"all_frame_sha256":series("source-road")},
            "wide":{"all_frame_sha256":series("source-wide")},
        },
        "model_rgb":{
            "road":{"all_frame_sha256":series("model-road")},
            "wide":{"all_frame_sha256":series("model-wide")},
        },
        "onnx_i420":{"all_frame_sha256":series("I420")},
        "clock_timeline":[{"global_clock_frame_count_delta":ticks}
                          for _ in range(10)],
    }


def build_full_mock(root):
    for seed in SEEDS:
        for scene in SCENES:
            folder=scene_directory(root,seed,scene)
            folder.mkdir(parents=True)
            for arm in ARMS:
                for i in (0,1):
                    data=mock_native(seed,scene,arm,i,
                        diff_step=2 if arm=="sequential_original" and i==1 else None)
                    (folder/f"{arm}-run_{i}.json").write_text(json.dumps(data))
            result=compare_one_native_scene(root,seed,scene)
            (folder/"case_comparison.json").write_text(json.dumps(result))


class NativeCrossProcessPSSMContractTests(unittest.TestCase):
    def test_crossprocess_original_source_mismatch_is_not_silently_passed(self):
        a=mock_native(20261109,SCENES[0],"sequential_original",0)
        b=mock_native(20261109,SCENES[0],"sequential_original",1,diff_step=2)
        result=compare_native_camera_repeats(a,b,20261109,SCENES[0],
                                              "sequential_original")
        source=result["source_and_warped_rgb_by_camera"]["road"]["source_rgb"]
        self.assertEqual(source["matched_full_timeline"],9)
        self.assertEqual(source["first_different_step_1_based"],2)
        self.assertEqual(source["different_steps_1_based"],[2])
        self.assertTrue(result["native_original_renderer_semantics_preserved"])
        self.assertFalse(result["model_scoring_allowed"])

    def test_nonoriginal_pssm_removal_never_labeled_untouched(self):
        a=mock_native(20261109,SCENES[0],"paired_pssm_task_removed",0)
        b=mock_native(20261109,SCENES[0],"paired_pssm_task_removed",1)
        result=compare_native_camera_repeats(a,b,20261109,SCENES[0],
                                              "paired_pssm_task_removed")
        self.assertFalse(result["native_original_renderer_semantics_preserved"])
        self.assertFalse(result["pssm_update_task_enabled"])
        self.assertTrue(result["pssm_removal_not_a_safe_original_model_renderer_substitute"])
        b["ablation_receipt"]=None
        with self.assertRaises(ValueError):
            compare_native_camera_repeats(a,b,20261109,SCENES[0],
                                          "paired_pssm_task_removed")

    def test_process_identity_and_pose_must_match(self):
        a=mock_native(20261109,SCENES[0],"paired_original",0)
        b=mock_native(20261109,SCENES[0],"paired_original",1)
        b["process_uuid"]=a["process_uuid"]
        with self.assertRaises(ValueError):
            compare_native_camera_repeats(a,b,20261109,SCENES[0],"paired_original")
        b=mock_native(20261109,SCENES[0],"paired_original",1)
        b["camera_pose"][0][0]+=1
        with self.assertRaises(ValueError):
            compare_native_camera_repeats(a,b,20261109,SCENES[0],"paired_original")

    def test_stale_task_list_and_missing_positive_control_fail_closed(self):
        a=mock_native(20261109,SCENES[0],"sequential_original",0)
        b=mock_native(20261109,SCENES[0],"sequential_original",1)
        b["registered_tasks_before"].remove("PSSM.update")
        with self.assertRaises(ValueError):
            compare_native_camera_repeats(a,b,20261109,SCENES[0],
                                          "sequential_original")
        b=mock_native(20261109,SCENES[0],"sequential_original",1)
        b["camera_plus_2m_positive"]["wide"]=False
        with self.assertRaises(ValueError):
            compare_native_camera_repeats(a,b,20261109,SCENES[0],
                                          "sequential_original")

    def test_aggregate_all_raw_eight_processes_per_scene_required(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            build_full_mock(root)
            result=aggregate_four_native_scenes(root)
            self.assertEqual(result["all_scene_comparison_processes"],32)
            self.assertEqual(len(result["per_scene"]),4)
            first=result["per_scene"][0]["arm_receipts"]["sequential_original"]
            self.assertEqual(first["source_and_warped_rgb_by_camera"]["road"][
                "source_rgb"]["matched_full_timeline"],9)
            self.assertFalse(result["stage7_original_mdv3_repeatability_proven"])
            folder=scene_directory(root,20261109,SCENES[0])
            summary=folder/"case_comparison.json"
            data=json.loads(summary.read_text())
            data["arm_receipts"]["sequential_original"]["model_i420_without_onnx"][
                "matched_full_timeline"]=10
            data["arm_receipts"]["sequential_original"]["source_and_warped_rgb_by_camera"][
                "road"]["source_rgb"]["matched_full_timeline"]=10
            summary.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                aggregate_four_native_scenes(root)

    def test_missing_or_tampered_run_is_invalid(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            build_full_mock(root)
            folder=scene_directory(root,20261109,SCENES[0])
            p=folder/"sequential_original-run_1.json"
            x=json.loads(p.read_text())
            x["onnx_i420"]["all_frame_sha256"].pop()
            p.write_text(json.dumps(x))
            with self.assertRaises(ValueError):
                compare_one_native_scene(root,20261109,SCENES[0])


if __name__=="__main__":
    unittest.main()
