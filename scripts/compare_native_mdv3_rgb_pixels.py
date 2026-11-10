"""Strict CPU RAW pixel forensics of two independent instrumented native trials.

Validate both real raw-source camera byte archives against the SHA of the
original official-MD-V3 inference trace BEFORE any pixel differences are
measured. This does not infer GPU texels, shadows, scene semantics, cause or
real-vehicle performance from observed RGB pixel locations.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import zlib

import numpy as np

from scripts.aggregate_original_mdv3_current_recheck import (
    MODEL_SHA256, first_divergence_timeline,
)
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
from scripts.native_mdv3_rgb_pixel_capture import (
    SHAPE, CAMERAS, MAX_CAPTURE_STEPS, RAW_NBYTES,
)

MAX_COMPRESSED_BYTES = 3_000_000
MAX_RAW_BYTES = RAW_NBYTES


def read_capture_manifest(root: Path, report: dict) -> dict:
    archive=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    if (archive.get("status")!="CPU_ONLY_NATIVE_RGB_FIRST_STEPS_RETAINED"
        or archive.get("probe_is_not_uninstrumented_original_strict_gate") is not True
        or archive.get("camera_capture_semantics")!="original_perceive_sequential"
        or archive.get("original_pssm_chase_tasks_preserved") is not True
        or archive.get("additional_gpu_readback_or_render_tasks") is not False
        or archive.get("original_native_image_shape_hwc")!=list(SHAPE)
        or archive.get("seed")!=report.get("seed")
        or archive.get("scenario")!=report.get("scenario")
        or archive.get("model_sha256")!=MODEL_SHA256
        or archive.get("process_uuid")!=report.get("process_uuid")
        or archive.get("total_native_onnx_steps")!=12
        or archive.get("captured_step_count")!=MAX_CAPTURE_STEPS
        or report.get("trial_evidence")!="ORIGINAL_PSSM_WITH_OPT_IN_CPU_RGB_RETENTION_PROBE"
        or report.get("raw_rgb_pixel_audit",{}).get("enabled") is not True
        or report["raw_rgb_pixel_audit"].get("captured_step_count")!=MAX_CAPTURE_STEPS
        or report["raw_rgb_pixel_audit"].get("is_uninstrumented_strict_repeatability_gate") is not False
        or report.get("pssm_update_preserved") is not True
        or report.get("gpu_hdr_extraction") is not False):
        raise ValueError("original-PSSM instrumented native RGB evidence invalid")
    images=archive.get("images")
    expected=[(s,k) for s in range(1,MAX_CAPTURE_STEPS+1) for k in CAMERAS]
    if not isinstance(images,list) or [(v.get("step"),v.get("camera")) for v in images]!=expected:
        raise ValueError("missing, duplicate or reordered original RGB frame receipts")
    for record in images:
        step,kind=record["step"],record["camera"]
        if (record.get("file")!=f"step-{step:02d}-{kind}.rgb.zlib"
            or record.get("sha256")!=report["frames"][step-1].get(f"source_{kind}_rgb_sha256")
            or record.get("raw_bytes")!=RAW_NBYTES
            or type(record.get("compressed_bytes")) is not int
            or not 0<record["compressed_bytes"]<=MAX_COMPRESSED_BYTES):
            raise ValueError("original source RGB SHA/size/files are inconsistent")
    return archive


def read_verified_pixels(root:Path, receipt:dict) -> np.ndarray:
    member=receipt["file"]
    if Path(member).name!=member:
        raise ValueError("unsafe original RGB member path")
    raw_compressed=(root/member).read_bytes()
    if len(raw_compressed)!=receipt["compressed_bytes"]:
        raise ValueError("compressed source RGB byte count differs from manifest")
    if not 0<len(raw_compressed)<=MAX_COMPRESSED_BYTES:
        raise ValueError("oversize compressed image")
    decoder=zlib.decompressobj()
    raw=decoder.decompress(raw_compressed,MAX_RAW_BYTES+1)
    if (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
        or len(raw)!=RAW_NBYTES
        or sha256(raw).hexdigest()!=receipt["sha256"]):
        raise ValueError("corrupted, truncated or forged original source RGB pixels")
    return np.frombuffer(raw,dtype=np.uint8).reshape(SHAPE)


def summarize_pixel_difference(lhs:np.ndarray,rhs:np.ndarray) -> dict:
    if (lhs.dtype!=np.uint8 or rhs.dtype!=np.uint8 or lhs.shape!=rhs.shape
        or lhs.ndim!=3 or lhs.shape[2]!=3):
        raise ValueError("strict HWC uint8 RGB images required")
    difference=np.abs(lhs.astype(np.int16)-rhs.astype(np.int16))
    changed_channels=difference>0
    changed=np.any(changed_channels,axis=2)
    y,x=np.nonzero(changed)
    bbox=([int(x.min()),int(y.min()),int(x.max()),int(y.max())]
          if x.size else None)
    height,width=changed.shape
    bins=[[int(np.count_nonzero(changed[
        row*height//4:(row+1)*height//4,
        col*width//4:(col+1)*width//4]))
        for col in range(4)] for row in range(4)]
    return {
        "bit_exact":bool(not x.size),
        "changed_pixel_count":int(x.size),
        "total_pixels":int(width*height),
        "changed_channel_values":int(np.count_nonzero(changed_channels)),
        "changed_channels_rgb":[int(np.count_nonzero(changed_channels[:,:,i]))
                                for i in range(3)],
        "maximum_absolute_channel_delta":int(difference.max()),
        "bounding_box_xyxy_inclusive":bbox,
        "first_12_changed_xy":[[int(a),int(b)] for a,b in zip(x[:12],y[:12])],
        "changed_pixel_counts_grid_4x4_top_left_to_bottom_right":bins,
        "changed_mask_is_not_a_shadow_or_lane_semantic_segmentation":True,
    }


def evaluate_native_rgb_pixel_pair(root:Path,save_masks:bool=True) -> dict:
    a=json.loads((root/"run_0.json").read_text(encoding="utf-8"))
    b=json.loads((root/"run_1.json").read_text(encoding="utf-8"))
    for record in (a,b):
        if (record.get("model_sha256")!=MODEL_SHA256
            or record.get("status")!="DIAGNOSTIC_EXECUTED"
            or record.get("requested_steps")!=12 or record.get("completed_steps")!=12
            or record.get("initial_fraction")!=.12
            or record.get("camera_convergence_attempts")!=0
            or record.get("camera_pixel_tolerance")!=0
            or record.get("camera_image_interpolation_or_replay") is not False
            or record.get("model_scoring_allowed") or record.get("real_vehicle_testing")):
            raise ValueError("nonoriginal or incomplete official MD-V3 input")
    strict=compare_fresh_trials(a,b)
    timeline=first_divergence_timeline(a,b)
    manifest_a=read_capture_manifest(root/"rgb_run_0",a)
    manifest_b=read_capture_manifest(root/"rgb_run_1",b)
    if (manifest_a["seed"]!=manifest_b["seed"]
        or manifest_a["scenario"]!=manifest_b["scenario"]):
        raise ValueError("pixel comparison scene/seed mismatch")
    first_source=timeline["first_native_road_or_wide_rgb_mismatch_step"]
    per_cam={"road":[],"wide":[]}
    first_snapshot=None
    for i in range(MAX_CAPTURE_STEPS):
        for offset,kind in enumerate(CAMERAS):
            index=i*len(CAMERAS)+offset
            left=read_verified_pixels(root/"rgb_run_0",manifest_a["images"][index])
            right=read_verified_pixels(root/"rgb_run_1",manifest_b["images"][index])
            metrics=summarize_pixel_difference(left,right)
            if metrics["bit_exact"] is (
                a["frames"][i][f"source_{kind}_rgb_sha256"]!=
                b["frames"][i][f"source_{kind}_rgb_sha256"]
            ):
                raise ValueError("pixel data contradicts original source-frame digests")
            per_cam[kind].append({"step":i+1,**metrics})
            if (not metrics["bit_exact"] and first_snapshot is None
                and first_source==i+1):
                first_snapshot=(i+1,kind,left,right)
    measured_first=min(
        (r["step"] for kind in CAMERAS for r in per_cam[kind]
         if not r["bit_exact"]),default=None
    )
    if first_source is not None and first_source<=MAX_CAPTURE_STEPS:
        if measured_first!=first_source:
            raise ValueError("first RGB mismatch from pixel bytes differs from raw ONNX receipt")
        status="FIRST_SOURCE_RGB_PIXEL_MISMATCH_MEASURED"
    elif first_source is None:
        if measured_first is not None:
            raise ValueError("pixel data contradicts a fully equal source trace")
        status="SOURCE_RGB_BIT_EXACT_IN_12_STEPS"
    else:
        status="INCONCLUSIVE_FIRST_SOURCE_MISMATCH_OUTSIDE_CAPTURE_WINDOW"
    mask_file=None
    if save_masks and first_snapshot is not None:
        import cv2
        step,kind,left,right=first_snapshot
        mask=(np.any(left!=right,axis=2).astype(np.uint8)*255)
        name=f"first-difference-step-{step:02d}-{kind}-mask.png"
        if not cv2.imwrite(str(root/name),mask):
            raise ValueError("first raw RGB binary mask could not be saved")
        mask_file=name
    prior_equal=None
    if first_source and first_source>1:
        k=("time_s","world_x_m","world_y_m","heading_rad",
           "raw_action_sha256","state_after_step_sha256")
        left=a["frames"][first_source-2]
        right=b["frames"][first_source-2]
        prior_equal=all(left.get(field)==right.get(field) for field in k)
    return {
        "status":status,
        "source":"TWO_INDEPENDENT_OPT_IN_CPU_RGB_RETAINING_ORIGINAL_PSSM_NATIVE_MDV3_SESSIONS",
        "seed":a["seed"],"scenario":a["scenario"],
        "official_md_v3_model_sha256":MODEL_SHA256,
        "original_native_964x604_rgb_pairs_per_process_captured":MAX_CAPTURE_STEPS,
        "actual_onnx_steps_per_process":12,
        "independent_native_onnx_process_count":2,
        "first_raw_source_diff_step":first_source,
        "first_pixel_measured_mismatch_step":measured_first,
        "source_to_onnx_first_divergence":timeline,
        "prior_step_virtual_pose_and_action_and_recurrent_equal":prior_equal,
        "pixel_metrics":per_cam,
        "first_difference_binary_mask":mask_file,
        "instrumented_pixel_probe_does_not_establish_uninstrumented_repeatability":True,
        "strict_native_repeat_status_in_instrumented_runs":strict["status"],
        "all_four_original_uninstrumented_strict_gate_passed":False,
        "gpu_shadow_texel_or_unique_causality_proven":False,
        "model_scoring_allowed":False,"real_vehicle_testing":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description="Native official MD-V3 raw RGB first-difference pixels")
    p.add_argument("--root",required=True,type=Path)
    args=p.parse_args(argv)
    result=evaluate_native_rgb_pixel_pair(args.root)
    (args.root/"raw_rgb_pixel_comparison.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8",
    )
    print("NATIVE_MDV3_FIRST_RGB_PIXEL_EVIDENCE",json.dumps({
        "status":result["status"],"seed":result["seed"],
        "scenario":result["scenario"],"first_source_step":result["first_raw_source_diff_step"],
        "first_pixel_step":result["first_pixel_measured_mismatch_step"],
        "first_frame_changed_pixel_count":{
            k:next((v["changed_pixel_count"] for v in vals
                    if v["step"]==result["first_raw_source_diff_step"]),None)
            for k,vals in result["pixel_metrics"].items()
        },
        "warning":"CPU-retention diagnostic != original uninstrumented strict pass",
    },ensure_ascii=False),flush=True)
    return 0 if result["status"]!="INCONCLUSIVE_FIRST_SOURCE_MISMATCH_OUTSIDE_CAPTURE_WINDOW" else 2


if __name__=="__main__":
    raise SystemExit(main())
