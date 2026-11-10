"""Aggregate official native .28 lane-fraction terminal GPU PSSM depth/HDR sweep.

This checks that every fixed-pose MetaDrive 0.4.3 native trial completed with
seven independent controls. GPU raw byte counts are experiment observations,
NOT GPU texel/pixel counts or driving-model scores.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bigbench.curved_lane_scenarios import SCENARIOS
from scripts.native_terminal_shadow_sync import CONDITIONS, STAGES


SWEEP_SEEDS = (20261109, 20261110)
SWEEP_SCENARIOS = tuple(SCENARIOS)
SWEEP_FRACTION = .28
REQUIRED_PAIRS=(
    "natural_terminal VS offset_terminal",
    "natural_terminal VS offset_sync_terminal",
    "offset_terminal VS offset_probe_terminal",
    "offset_probe_terminal VS offset_sync_terminal",
    "offset_terminal VS offset_sync_terminal",
)


def sweep_directory(root:Path,seed:int,scenario:str) -> Path:
    if seed not in SWEEP_SEEDS or scenario not in SWEEP_SCENARIOS:
        raise ValueError("unknown planned sweep seed/scene")
    return root / f"seed-{seed}-{scenario}-fraction-0.28"


def summarize_terminal_pose_sweep(root:Path) -> dict:
    rows=[]
    seen_poses=set()
    for seed in SWEEP_SEEDS:
        for scenario in SWEEP_SCENARIOS:
            directory=sweep_directory(root,seed,scenario)
            if not directory.is_dir():
                raise ValueError(f"missing original GitHub native scene evidence: {directory}")
            base=json.loads(
                (directory/"natural_no_gpu.json").read_text(encoding="utf-8")
            )
            result=json.loads(
                (directory/"shadow_gpu_comparison.json").read_text(encoding="utf-8")
            )
            if (base.get("status")!="OBSERVED_NATIVE_NO_GPU_CONTROL"
                or base.get("seed")!=seed or base.get("scenario")!=scenario
                or base.get("fraction") != SWEEP_FRACTION
                or base.get("condition")!="natural_no_gpu"):
                raise ValueError(f"wrong seed/scenario/fraction or native control: {directory}")
            if (result.get("status")!="NATIVE_TERMINAL_GPU_SHADOW_CAUSAL_DIAGNOSTIC_OBSERVED"
                or result.get("seed")!=seed or result.get("scenario")!=scenario
                or result.get("frames") != base.get("frames")
                or set(result.get("per_arm_receipts",{}))!=set(CONDITIONS)):
                raise ValueError(f"incomplete terminal GPU stage comparison: {directory}")
            if result.get("GPU_shadow_causality_proven") is not False:
                raise ValueError("native original shader cause must not be claimed")
            if result.get("official_new_frame_ONNX_repeatability_proven") is not False:
                raise ValueError("model closed-loop PASS cannot be claimed")
            if result.get("real_vehicle_testing") or result.get("model_scoring_allowed"):
                raise ValueError("real vehicle or model scoring prohibited")
            pose=base.get("camera_pose")
            if not isinstance(pose,list) and not isinstance(pose,tuple):
                raise ValueError("native lane-derived WORLD pose absent")
            serialized=json.dumps(pose,sort_keys=True)
            if (seed,scenario,serialized) in seen_poses:
                raise ValueError("duplicate native world-camera pose entry")
            seen_poses.add((seed,scenario,serialized))
            for name,(injected,extra,terminal) in CONDITIONS.items():
                item=json.loads((directory/(name+".json")).read_text(encoding="utf-8"))
                if (item.get("seed")!=seed or item.get("scenario")!=scenario
                    or item.get("fraction")!=SWEEP_FRACTION
                    or item.get("camera_pose") != pose
                    or item.get("injected_camera_offset_last_frame") is not injected
                    or item.get("post_chase_extra_task_kind")!=extra
                    or item.get("terminal_gpu_probe") is not terminal
                    or item.get("gpu_extraction_before_or_during_rgb_capture") is not False
                    or item.get("status") != ("OBSERVED_NATIVE_TERMINAL_SHADOW_GPU_SAMPLE" if terminal
                                             else "OBSERVED_NATIVE_NO_GPU_CONTROL")):
                    raise ValueError(f"unmatched seven-arm native receipt: {directory}/{name}")
                if not all(item.get("both_camera_plus_2m_positive",{}).get(k) is True
                           for k in ("road","wide")):
                    raise ValueError(f"{name}: stale native camera with invalid 2m positive")
                if terminal and not all(
                    item.get("same_tick_final_ram_rgb_unchanged_after_terminal",{}).get(k) is True
                    for k in ("road","wide")
                ):
                    raise ValueError(f"{name}: GPU terminal probe altered source RAM frame")
            pairs=result.get("gpu_raw_byte_difference_between_independent_processes",{})
            if set(pairs)!=set(REQUIRED_PAIRS):
                raise ValueError("GPU comparison pairs missing/wrong")
            stages={}
            for pair in REQUIRED_PAIRS:
                values=pairs[pair]
                if set(values)!=set(STAGES):
                    raise ValueError(f"missing GPU depth/HDR stage: {pair}")
                stages[pair]={}
                for stage,record in values.items():
                    if (record.get("status")!="RAW_GPU_BYTES_COMPARED_DIFFERENT_PROCESSES"
                        or record.get("raw_bytes_are_not_pixels") is not True
                        or type(record.get("changed_byte_count")) is not int
                        or record["changed_byte_count"]<0
                        or record.get("bytes_equal") is not (record["changed_byte_count"]==0)):
                        raise ValueError(f"{pair}/{stage}: invalid GPU raw byte evidence")
                    stages[pair][stage]=record["changed_byte_count"]
            rows.append({
                "seed":seed,
                "scenario":scenario,
                "lane_fraction":SWEEP_FRACTION,
                "world_camera_pose":pose,
                "frames":result["frames"],
                "gpu_changed_bytes_by_pair":stages,
                "pre_gpu_source_i420_unique_sha":{
                    condition:result["per_arm_receipts"][condition]["warmup_unique_i420_sha"]
                    for condition in CONDITIONS
                },
                "original_vs_terminal_process_source_sha_matches":result.get(
                    "independent_noGPU_vs_terminal_capture_matches",{}
                ),
            })
    if len(rows)!=len(SWEEP_SEEDS)*len(SWEEP_SCENARIOS):
        raise ValueError("incomplete native pose/ramp matrix")
    return {
        "status":"NATIVE_PSSM_SHADOW_TERMINAL_POSE_RAMP_SWEEP_RECORDED",
        "official_metadrive_version":"0.4.3",
        "seed_count":len(SWEEP_SEEDS),
        "scenarios":list(SWEEP_SCENARIOS),
        "lane_fraction":SWEEP_FRACTION,
        "independent_meta_drive_processes":len(rows)*len(CONDITIONS),
        "native_matrix_conditions":len(rows),
        "per_scene":rows,
        "gpu_depth_atlas_is_terminal_snapshot_not_time_series":True,
        "independent_process_render_difference_is_not_unique_causality":True,
        "post_chase_pssm_sync_alters_original_rendering":True,
        "original_renderer_md_v3_native_onnx_repeatability_proven":False,
        "real_vehicle_testing":False,
        "model_scoring_allowed":False,
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    report=summarize_terminal_pose_sweep(args.root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False,
                                   allow_nan=False)+"\n",encoding="utf-8")
    print("NATIVE_PSSM_POSE_RAMP_SWEEP",json.dumps({
        "status":report["status"],
        "native_conditions":report["native_matrix_conditions"],
        "processes":report["independent_meta_drive_processes"],
        "data":[{"seed":x["seed"],"scene":x["scenario"],
                 "natural_shadow_recovery_bytes":
                    x["gpu_changed_bytes_by_pair"][
                        "natural_terminal VS offset_sync_terminal"
                    ]["pssm_depth"]
                 } for x in report["per_scene"]],
    },ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
