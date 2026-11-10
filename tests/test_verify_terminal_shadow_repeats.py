"""Synthetic artifact ZIPs ONLY; not actual MetaDrive/Panda GPU evidence."""
from __future__ import annotations

from hashlib import sha256
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile
import zlib

from scripts.native_terminal_shadow_sync import CONDITIONS,STAGES
from scripts.verify_terminal_shadow_repeats import (
    read_verified_run,compare_repeated_artifacts,
)


def build_mock_native_zip(path:Path,*,mutate_frame:bool=False,corrupt_gpu:bool=False,
                          scenario:str="s_curve_left_right"):
    root="output/terminal-shadow/seed-20261109-"+scenario
    summary={
        "status":"NATIVE_TERMINAL_GPU_SHADOW_CAUSAL_DIAGNOSTIC_OBSERVED",
        "seed":20261109,"scenario":scenario,"frames":5,
        "per_arm_receipts":{},
    }
    content={}
    for name,(injected,extra,terminal) in CONDITIONS.items():
        cams={}
        for cam in ("road","wide"):
            hashes=[f"{name}:{cam}:{i}" for i in range(5)]
            if mutate_frame and name=="natural_no_gpu":
                hashes[3]+="changed-in-repeat"
            cams[cam]={"all_frame_sha256":hashes}
        i420=[f"{name}:model:{i}" for i in range(5)]
        if mutate_frame and name=="natural_no_gpu":
            i420[3]+="changed-in-repeat"
        stage={}
        for st in STAGES:
            if terminal:
                data=(st+"-"+name).encode("ascii")+bytes(range(80))
                payload=zlib.compress(data)
                member=f"{name}-{st}.bin.zlib"
                content[f"{root}/{member}"]=(
                    b"CORRUPT_PAYLOAD" if corrupt_gpu and name=="natural_terminal"
                    and st=="pssm_depth" else payload
                )
                stage[st]={
                    "status":"EXTRACTED","source":st,
                    "sha256":sha256(data).hexdigest(),
                    "byte_count":len(data),
                    "compressed_byte_count":len(payload),
                    "lossless_compressed_filename":member,
                }
            else:
                stage[st]={"status":"SKIPPED_BY_DESIGN_NO_GPU"}
        record={
            "status":"OBSERVED_NATIVE_TERMINAL_SHADOW_GPU_SAMPLE"
                if terminal else "OBSERVED_NATIVE_NO_GPU_CONTROL",
            "condition":name,"seed":20261109,"scenario":scenario,"frames":5,
            "injected_camera_offset_last_frame":injected,
            "post_chase_extra_task_kind":extra,
            "terminal_gpu_probe":terminal,
            "gpu_extraction_before_or_during_rgb_capture":False,
            "model_scoring_allowed":False,"real_vehicle_testing":False,
            "both_camera_plus_2m_positive":{"road":True,"wide":True},
            "same_tick_final_ram_rgb_unchanged_after_terminal":{
                "road":True,"wide":True,
            },
            "source_rgb":cams,"onnx_i420":{"all_frame_sha256":i420},
            "gpu_stage_receipts":stage,"gpu_compressed_files":[
                f"{name}-{st}.bin.zlib" for st in STAGES
            ] if terminal else [],
        }
        summary["per_arm_receipts"][name]={
            "final_native_i420_sha":i420[-1],
            "final_native_source_rgb_sha":{
                cam:cams[cam]["all_frame_sha256"][-1] for cam in ("road","wide")
            },
            "terminal_gpu_stage_sha":{
                st:stage[st]["sha256"] for st in STAGES
            } if terminal else None,
        }
        content[f"{root}/{name}.json"]=json.dumps(record).encode("utf-8")
    content[f"{root}/shadow_gpu_comparison.json"]=json.dumps(summary).encode("utf-8")
    with ZipFile(path,"w") as archive:
        for name,data in content.items():
            archive.writestr(name,data)


class CrossCIArtifactContractTests(unittest.TestCase):
    def setUp(self):
        d=TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root=Path(d.name)
        self.first=self.root/"first.zip"
        self.second=self.root/"second.zip"
        build_mock_native_zip(self.first)
        build_mock_native_zip(self.second)

    def test_two_consistent_raw_archives_require_crypto_verification(self):
        first=read_verified_run(self.first)
        self.assertEqual(first["seed"],20261109)
        result=compare_repeated_artifacts(self.first,self.second)
        self.assertEqual(result["terminal_gpu_stages_exact_sha_count"],12)
        self.assertEqual(result["terminal_gpu_stages_total"],12)
        self.assertEqual(result["final_I420_sha_equal_count"],7)
        self.assertEqual(result["final_RGB_sha_equal_count"],14)
        self.assertEqual(result["all_I420_frame_sha_equal_count"],35)
        self.assertEqual(result["all_RGB_frame_sha_equal_count"],70)
        self.assertEqual(result["status"],
             "TWO_REAL_NATIVE_TERMINAL_GPU_RUNS_AGREE_AT_FINAL_FRAME")
        self.assertFalse(result["model_scoring_allowed"])

    def test_late_frame_drift_preserved_despite_final_image_match(self):
        build_mock_native_zip(self.second,mutate_frame=True)
        result=compare_repeated_artifacts(self.first,self.second)
        self.assertEqual(result["all_I420_frame_sha_equal_count"],34)
        self.assertEqual(result["all_RGB_frame_sha_equal_count"],68)
        self.assertEqual(result["final_I420_sha_equal_count"],7)
        self.assertEqual(
            result["per_arm_evidence"]["natural_no_gpu"]
                  ["i420_different_frame_indices_zero_based"],[3]
        )

    def test_corrupted_compressed_gpu_payload_fails_not_inconclusive_pass(self):
        build_mock_native_zip(self.second,corrupt_gpu=True)
        with self.assertRaises(ValueError):
            compare_repeated_artifacts(self.first,self.second)

    def test_mismatched_scene_and_missing_original_archive_fails(self):
        build_mock_native_zip(self.second,scenario="s_curve_right_left")
        with self.assertRaises(ValueError):
            compare_repeated_artifacts(self.first,self.second)
        self.second.unlink()
        with self.assertRaises(ValueError):
            read_verified_run(self.second)


if __name__=="__main__":
    unittest.main()
