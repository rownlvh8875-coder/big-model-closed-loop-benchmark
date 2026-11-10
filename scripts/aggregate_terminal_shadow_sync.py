"""Strict independent-process terminal PSSM depth/HDR + road/wide RGB A-B.

GPU raw byte comparisons are ONLY for final-frame textures after the frame
series; they are NOT time-series GPU measurements, texels or physical pixels.
Never claim post-Chase extra PSSM update is the original MetaDrive renderer.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zlib

import numpy as np

from scripts.native_terminal_shadow_sync import CONDITIONS, STAGES,EXTRA_TASK_NAME


def _verified_stage_bytes(root:Path,name:str,stage:str,info:dict) -> bytes:
    expected=f"{name}-{stage}.bin.zlib"
    if (info.get("status")!="EXTRACTED"
            or info.get("source") !=stage
            or info.get("lossless_compressed_filename")!=expected):
        raise ValueError(f"{name}/{stage}: no exact named terminal GPU receipt")
    path=root/expected
    if not path.is_file() or path.stat().st_size>64*1024*1024:
        raise ValueError(f"{name}/{stage}: absent or oversized compressed GPU data")
    compressed=path.read_bytes()
    if (len(compressed)!=info.get("compressed_byte_count")
            or type(info.get("byte_count")) is not int
            or not 0<info["byte_count"]<=64*1024*1024):
        raise ValueError(f"{name}/{stage}: compressed size / claimed raw size mismatch")
    decoder=zlib.decompressobj()
    raw=decoder.decompress(compressed,64*1024*1024+1)
    if (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
            or len(raw)!=info["byte_count"]):
        raise ValueError(f"{name}/{stage}: incomplete/unsafe GPU binary payload")
    if sha256(raw).hexdigest()!=info.get("sha256"):
        raise ValueError(f"{name}/{stage}: raw GPU SHA mismatch")
    return raw


def raw_gpu_byte_difference(a:bytes,b:bytes,ia:dict,ib:dict) -> dict:
    if not isinstance(a,bytes) or not isinstance(b,bytes):
        raise ValueError("raw GPU byte buffers required")
    if not a or not b:
        raise ValueError("empty terminal GPU textures cannot be compared")
    meta_a=ia.get("metadata")
    meta_b=ib.get("metadata")
    same_layout=(len(a)==len(b) and meta_a is not None and meta_a==meta_b)
    if not same_layout:
        return {
            "status":"INCONCLUSIVE_GPU_TEXTURE_LAYOUT_CHANGED",
            "bytes_equal":None,
            "changed_byte_count":None,
            "raw_byte_count_a":len(a),"raw_byte_count_b":len(b),
            "raw_bytes_are_not_pixels":True,
        }
    lhs=np.frombuffer(a,dtype=np.uint8)
    rhs=np.frombuffer(b,dtype=np.uint8)
    positions=np.flatnonzero(lhs!=rhs)
    return {
        "status":"RAW_GPU_BYTES_COMPARED_DIFFERENT_PROCESSES",
        "bytes_equal":bool(not positions.size),
        "changed_byte_count":int(positions.size),
        "raw_byte_count":len(a),
        "first_12_changed_byte_offsets":[int(v) for v in positions[:12]],
        "max_unsigned_byte_delta":int(
            np.max(np.abs(lhs.astype(np.int16)-rhs.astype(np.int16)))
        ),
        "raw_bytes_are_not_pixels":True,
        "gpu_stage_is_one_final_frame_not_a_time_series":True,
        "independent_process_variation_can_confound_ablation":True,
    }


def aggregate_gpu_shadow(root:Path,reports:dict[str,dict]) -> dict:
    if set(reports)!=set(CONDITIONS):
        raise ValueError("all seven independently executed terminal/noGPU arms required")
    baseline=reports["natural_no_gpu"]
    compare_keys=("seed","scenario","fraction","camera_pose","frames","warmup")
    retained={}
    raw_bytes={}
    for name,(inject,extra,terminal) in CONDITIONS.items():
        row=reports[name]
        expected_status=("OBSERVED_NATIVE_TERMINAL_SHADOW_GPU_SAMPLE" if terminal
                         else "OBSERVED_NATIVE_NO_GPU_CONTROL")
        if row.get("status")!=expected_status or row.get("condition")!=name:
            raise ValueError(f"{name}: invalid native CI evidence or missing positive control")
        if any(row.get(k)!=baseline.get(k) for k in compare_keys):
            raise ValueError(f"{name}: mismatched original MetaDrive seed/pose/framerate")
        if (row.get("terminal_gpu_probe") is not terminal
                or row.get("injected_camera_offset_last_frame") is not inject
                or row.get("post_chase_extra_task_kind")!=extra):
            raise ValueError(f"{name}: experimental intervention mislabeled")
        if row.get("gpu_extraction_before_or_during_rgb_capture") is not False:
            raise ValueError("GPU shadow/HDR extraction during RGB time series forbidden")
        if row.get("terminal_gpu_extraction_after_complete_rgb_i420") is not terminal:
            raise ValueError(f"{name}: GPU terminal-only extraction contract broken")
        if (row.get("real_vehicle_testing") or row.get("model_scoring_allowed")
                or row.get("native_onnx_inference_performed") is not False):
            raise ValueError("real vehicle or model ranking forbidden")
        if any(row.get("both_camera_plus_2m_positive",{}).get(k) is not True
               for k in ("road","wide")):
            raise ValueError(f"{name}: stale camera pose positive control")
        rows=row.get("per_frame_cpu_and_extra_task",[])
        if len(rows)!=row["frames"]:
            raise ValueError(f"{name}: missing native frame timeline")
        if (row.get("task_registry_unchanged_during_frames") is not True or
                any(frame.get("panda_frame_count_delta")!=1 for frame in rows)):
            raise ValueError(f"{name}: unexpected Panda rendering task state")
        task_list=row.get("tasks_with_optional_extra_sort25",[])
        target=[x for x in task_list if x.get("name")==EXTRA_TASK_NAME]
        if len(target)!=(1 if extra else 0):
            raise ValueError(f"{name}: post-Chase sort25 task missing or unexpectedly added")
        if extra and target[0].get("sort")!=25:
            raise ValueError(f"{name}: post-Chase sort task registered at wrong priority")
        if (row.get("original_renderer_semantics_unchanged") is not
                (not inject and not extra)):
            raise ValueError(f"{name}: altered renderer mislabeled as original")
        intervention_rows=[x for x in rows if x.get("virtual_camera_injection")]
        if len(intervention_rows)!=(1 if inject else 0):
            raise ValueError(f"{name}: missing/extra deliberate last-frame camera offset")
        if inject:
            if intervention_rows[0].get("frame_index_zero_based")!=row["frames"]-1:
                raise ValueError(f"{name}: controlled offset not on final frame")
            if abs(intervention_rows[0]["virtual_camera_injection"].get(
                    "measured_delta_x_m",0)-2.)>1e-5:
                raise ValueError("last-frame camera +2m intervention did not occur")
        if extra:
            if any(x.get("sort25_event") is None for x in rows):
                raise ValueError(f"{name}: actual extra Panda task callback not observed")
            if any(x["sort25_event"].get("post_chase_probe_mode")!=extra for x in rows):
                raise ValueError(f"{name}: wrong extra task mode")
            for frame in rows:
                event=frame["sort25_event"]
                if event.get("main_camera_pose_at_sort25")!=event.get(
                        "camera_pose_after_sort25"):
                    raise ValueError("extra post-Chase task changed main-camera pose")
            if extra=="sync" and not rows[-1]["sort25_event"].get(
                    "mvp_changed_by_sort25_callback"):
                raise ValueError("post-Chase PSSM update did not change final numeric MVP")
        elif any(x.get("sort25_event") is not None for x in rows):
            raise ValueError("baseline cannot contain post-Chase sort25 callback")
        for k in ("road","wide"):
            if len(row["source_rgb"][k]["all_frame_sha256"])!=row["frames"]:
                raise ValueError(f"{name}: native source RGB sequence incomplete")
            if len(row["warped_rgb"][k]["all_frame_sha256"])!=row["frames"]:
                raise ValueError(f"{name}: model canvas RGB sequence incomplete")
        if len(row["onnx_i420"]["all_frame_sha256"])!=row["frames"]:
            raise ValueError(f"{name}: I420 image stream incomplete")
        if row.get("final_cpu_pssm_mvp",{}).get("status")!="MVP_VALUES_CAPTURED":
            raise ValueError(f"{name}: final CPU PSSM MVP not measured")
        payload={}
        stage_receipts=row.get("gpu_stage_receipts",{})
        if set(stage_receipts)!=set(STAGES):
            raise ValueError(f"{name}: GPU stage metadata incomplete")
        if terminal:
            if set(row.get("gpu_compressed_files",[]))!={f"{name}-{s}.bin.zlib" for s in STAGES}:
                raise ValueError(f"{name}: GPU binary source list incomplete")
            if any(row.get("same_tick_final_ram_rgb_unchanged_after_terminal",{}).get(k)
                   is not True for k in ("road","wide")):
                raise ValueError(f"{name}: post GPU-readback RAM RGB changed")
            for stage in STAGES:
                payload[stage]=_verified_stage_bytes(
                    root,name,stage,stage_receipts[stage]
                )
        else:
            if row.get("gpu_compressed_files"):
                raise ValueError(f"{name}: noGPU process must not write GPU texture bytes")
            if any(stage_receipts[stage].get("status")!="SKIPPED_BY_DESIGN_NO_GPU"
                   for stage in STAGES):
                raise ValueError(f"{name}: noGPU arm unexpectedly performed GPU extraction")
        raw_bytes[name]=payload
        retained[name]={
            "final_native_source_rgb_sha":{k:row["source_rgb"][k]["all_frame_sha256"][-1]
                                           for k in ("road","wide")},
            "final_native_i420_sha":row["onnx_i420"]["all_frame_sha256"][-1],
            "warmup_unique_i420_sha":row["onnx_i420"]["post_warmup_unique_sha256"],
            "raw_rgb_max_changed_pixels":{k:row["source_rgb"][k]["max_changed_pixels_post_warmup"]
                                          for k in ("road","wide")},
            "terminal_gpu_stage_sha":(
                {stage:stage_receipts[stage]["sha256"] for stage in STAGES}
                if terminal else None
            ),
            "cpu_pssm_mvp_sha":row["final_cpu_pssm_mvp"]["all_f64_sha256"],
            "last_frame_sort25_extra_MVP_updated":(
                rows[-1]["sort25_event"]["mvp_changed_by_sort25_callback"]
                if extra else None
            ),
        }
    # These data were generated by independent Panda processes. Their GPU
    # byte differences are correlations, NOT a controlled within-process
    # counterfactual. Never label a mismatch as proof of a shader defect.
    pairs=(
        ("natural_terminal","offset_terminal"),
        ("offset_terminal","offset_probe_terminal"),
        ("offset_probe_terminal","offset_sync_terminal"),
        ("offset_terminal","offset_sync_terminal"),
    )
    gpu_comparisons={}
    for left,right in pairs:
        gpu_comparisons[left+" VS "+right]={
            stage:raw_gpu_byte_difference(
                raw_bytes[left][stage],raw_bytes[right][stage],
                reports[left]["gpu_stage_receipts"][stage],
                reports[right]["gpu_stage_receipts"][stage],
            )
            for stage in STAGES
        }
    no_gpu_and_terminal={
        title:{
            "road_matched_frame_count":sum(
                a==b for a,b in zip(
                    reports[without]["source_rgb"]["road"]["all_frame_sha256"],
                    reports[with_gpu]["source_rgb"]["road"]["all_frame_sha256"],
                )
            ),
            "wide_matched_frame_count":sum(
                a==b for a,b in zip(
                    reports[without]["source_rgb"]["wide"]["all_frame_sha256"],
                    reports[with_gpu]["source_rgb"]["wide"]["all_frame_sha256"],
                )
            ),
            "i420_matched_frame_count":sum(
                a==b for a,b in zip(
                    reports[without]["onnx_i420"]["all_frame_sha256"],
                    reports[with_gpu]["onnx_i420"]["all_frame_sha256"],
                )
            ),
            "total_frames":baseline["frames"],
        }
        for title,without,with_gpu in (
            ("natural","natural_no_gpu","natural_terminal"),
            ("offset_no_extra","offset_no_gpu","offset_terminal"),
            ("offset_with_post_chase_sync","offset_sync_no_gpu","offset_sync_terminal"),
        )
    }
    return {
        "status":"NATIVE_TERMINAL_GPU_SHADOW_CAUSAL_DIAGNOSTIC_OBSERVED",
        "seed":baseline["seed"],"scenario":baseline["scenario"],
        "camera_pose":baseline["camera_pose"],"frames":baseline["frames"],
        "per_arm_receipts":retained,
        "gpu_raw_byte_difference_between_independent_processes":gpu_comparisons,
        "independent_noGPU_vs_terminal_capture_matches":no_gpu_and_terminal,
        "source_gpu_depth_is_not_a_model_quality_metric":True,
        "single_terminal_gpu_snapshot_not_time_series":True,
        "post_chase_PSSM_update_changes_renderer_semantics":True,
        "GPU_shadow_causality_proven":False,
        "official_new_frame_ONNX_repeatability_proven":False,
        "model_scoring_allowed":False,"real_vehicle_testing":False,
        "warnings":[
            "GPU raw texture changed bytes must not be interpreted as RGB pixel locations.",
            "Terminal extraction is only after final source RGB and I420 snapshots.",
            "All compared GPU depth/HDR snapshots come from different Python/Panda worlds.",
            "A camera offset and extra PSSM.update at sort25 deliberately change native rendering semantics.",
        ],
    }


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="Aggregate terminal-only native GPU shadow A/B")
    parser.add_argument("--root",type=Path,required=True)
    args=parser.parse_args(argv)
    reports={
        name:json.loads((args.root/(name+".json")).read_text(encoding="utf-8"))
        for name in CONDITIONS
    }
    result=aggregate_gpu_shadow(args.root,reports)
    (args.root/"shadow_gpu_comparison.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8",
    )
    print("NATIVE_TERMINAL_GPU_DEPTH_HDR",json.dumps({
        "status":result["status"],"seed":result["seed"],
        "scenario":result["scenario"],
        "gpu_stage_comparisons":{
            pair:{
                stage:{
                    "changed_byte_count":info["changed_byte_count"],
                    "bytes_equal":info["bytes_equal"],
                } for stage,info in data.items()
            } for pair,data in result[
                "gpu_raw_byte_difference_between_independent_processes"
            ].items()
        },
        "natural_vs_sync_final_i420":{
            k:result["per_arm_receipts"][k]["final_native_i420_sha"]
            for k in ("offset_terminal","offset_probe_terminal","offset_sync_terminal")
        },
    },ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
