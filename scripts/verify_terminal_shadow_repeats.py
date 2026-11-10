"""Cross-workflow audit of actual MetaDrive terminal-shadow CI artifact ZIPs.

Read two independently produced GitHub Actions artifact ZIPs for one fixed
(seed, native scenario) and verify all final GPU shadow/HDR binary payloads,
original native road/wide RGB series and model I420 SHA series. No network,
no GPU rendering, no ONNX, no model ranking, no permissive pixel tolerance.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path,PurePosixPath
from zipfile import ZipFile
import zlib

from scripts.native_terminal_shadow_sync import CONDITIONS, STAGES


MAX_COMPRESSED=64*1024*1024
MAX_UNCOMPRESSED=64*1024*1024


def _one_name(names:list[str],tail:str) -> str:
    matched=[n for n in names if n==tail or n.endswith("/"+tail)]
    if len(matched)!=1:
        raise ValueError(f"expected one exact artifact member: {tail}")
    return matched[0]


def _verified_terminal_payload(zip_file:ZipFile,names:list[str],condition:str,
                               stage:str,info:dict) -> str:
    expected=f"{condition}-{stage}.bin.zlib"
    if (info.get("status")!="EXTRACTED"
            or info.get("source")!=stage
            or info.get("lossless_compressed_filename")!=expected):
        raise ValueError("terminal GPU receipt absent/forged")
    compressed=zip_file.read(_one_name(names,expected))
    if not compressed or len(compressed)>MAX_COMPRESSED:
        raise ValueError("compressed terminal GPU binary missing/oversized")
    if len(compressed)!=info.get("compressed_byte_count"):
        raise ValueError("terminal GPU compressed byte size wrong")
    decoder=zlib.decompressobj()
    raw=decoder.decompress(compressed,MAX_UNCOMPRESSED+1)
    if (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
            or len(raw)!=info.get("byte_count")
            or not 0<len(raw)<=MAX_UNCOMPRESSED):
        raise ValueError("GPU depth/HDR raw stage failed bounded lossless decoding")
    digest=sha256(raw).hexdigest()
    if digest!=info.get("sha256"):
        raise ValueError("GPU stage cryptographic evidence mismatched its binary")
    return digest


def read_verified_run(zip_path:Path) -> dict:
    if not zip_path.is_file():
        raise ValueError("actual GitHub artifact ZIP path required")
    with ZipFile(zip_path) as z:
        members=z.namelist()
        if any(PurePosixPath(n).is_absolute() or ".." in PurePosixPath(n).parts
               for n in members):
            raise ValueError("unsafe artifact ZIP path")
        summary=json.loads(z.read(_one_name(members,"shadow_gpu_comparison.json")))
        if (summary.get("status")!="NATIVE_TERMINAL_GPU_SHADOW_CAUSAL_DIAGNOSTIC_OBSERVED"
                or set(summary.get("per_arm_receipts",{}))!=set(CONDITIONS)):
            raise ValueError("incomplete GitHub native terminal GPU result")
        # The aggregate's geometry is the fixed, unperturbed WORLD camera pose.
        # Never compare render archives from different lane fractions/poses
        # as repeats, even if seed, map and frame count are identical.
        pose=summary.get("camera_pose")
        if (not isinstance(pose,list) or len(pose)!=2
                or any(not isinstance(part,list) or len(part)!=3
                       or any(type(v) not in (int,float) or not math.isfinite(v)
                              for v in part) for part in pose)):
            raise ValueError("native CI summary has no finite WORLD camera pose")
        fraction=None
        rows={}
        for name,(injected,extra,terminal) in CONDITIONS.items():
            report=json.loads(z.read(_one_name(members,name+".json")))
            expected_status=("OBSERVED_NATIVE_TERMINAL_SHADOW_GPU_SAMPLE" if terminal
                             else "OBSERVED_NATIVE_NO_GPU_CONTROL")
            if (report.get("status")!=expected_status or
                    report.get("condition")!=name or
                    report.get("seed")!=summary.get("seed") or
                    report.get("scenario")!=summary.get("scenario") or
                    report.get("frames")!=summary.get("frames")):
                raise ValueError("native condition/run metadata mismatch")
            if (report.get("injected_camera_offset_last_frame") is not injected
                    or report.get("post_chase_extra_task_kind")!=extra
                    or report.get("terminal_gpu_probe") is not terminal
                    or report.get("gpu_extraction_before_or_during_rgb_capture") is not False
                    or report.get("model_scoring_allowed")
                    or report.get("real_vehicle_testing")):
                raise ValueError("invasive/invalid native experiment arm")
            row_fraction=report.get("fraction")
            if (type(row_fraction) not in (int,float)
                    or not math.isfinite(row_fraction)
                    or row_fraction not in (0.12,0.28)):
                raise ValueError("native terminal artifact has invalid lane fraction")
            if report.get("camera_pose")!=pose:
                raise ValueError(f"{name}: native WORLD camera pose differs from aggregate")
            if fraction is None:
                fraction=row_fraction
            elif row_fraction!=fraction:
                raise ValueError(f"{name}: camera lane fraction differs across arms")
            for kind in ("road","wide"):
                if report.get("both_camera_plus_2m_positive",{}).get(kind) is not True:
                    raise ValueError("original native camera pose positive control invalid")
            source={
                kind:report["source_rgb"][kind]["all_frame_sha256"]
                for kind in ("road","wide")
            }
            i420=report["onnx_i420"]["all_frame_sha256"]
            if any(len(x)!=summary["frames"] for x in (*source.values(),i420)):
                raise ValueError("truncated native sensor/model input time series")
            gpu={}
            if terminal:
                if any(report["same_tick_final_ram_rgb_unchanged_after_terminal"].get(kind)
                       is not True for kind in ("road","wide")):
                    raise ValueError("GPU extraction altered last RAM RGB")
                gpu={
                    stage:_verified_terminal_payload(
                        z,members,name,stage,
                        report["gpu_stage_receipts"][stage]
                    )
                    for stage in STAGES
                }
            elif report.get("gpu_compressed_files"):
                raise ValueError("noGPU control recorded a GPU texture")
            if (summary["per_arm_receipts"][name]["final_native_i420_sha"]
                    !=i420[-1] or
                    any(summary["per_arm_receipts"][name][
                        "final_native_source_rgb_sha"][kind]!=source[kind][-1]
                        for kind in ("road","wide"))):
                raise ValueError("summary final RGB/I420 SHA differs from raw JSON")
            if terminal and summary["per_arm_receipts"][name]["terminal_gpu_stage_sha"]!=gpu:
                raise ValueError("terminal stage summary does not match raw GPU files")
            rows[name]={"source":source,"i420":i420,"gpu":gpu}
        return {
            "seed":summary["seed"],"scenario":summary["scenario"],
            "fraction":fraction,"camera_pose":pose,
            "frames":summary["frames"],"arms":rows,
        }


def compare_repeated_artifacts(first:Path,second:Path) -> dict:
    a=read_verified_run(first)
    b=read_verified_run(second)
    if (a["seed"],a["scenario"],a["frames"],a["fraction"],a["camera_pose"])!=(
            b["seed"],b["scenario"],b["frames"],b["fraction"],b["camera_pose"]):
        raise ValueError("cross-CI runs have different seed/scene/frames/camera pose/fraction")
    frames=a["frames"]
    gpu_total=0
    gpu_matches=0
    rgb_total=0
    rgb_matches=0
    i420_total=0
    i420_matches=0
    final_rgb_total=0
    final_rgb_matches=0
    final_i420_matches=0
    by_arm={}
    for name,(_,_,terminal) in CONDITIONS.items():
        left,right=a["arms"][name],b["arms"][name]
        camera={}
        for kind in ("road","wide"):
            one,two=left["source"][kind],right["source"][kind]
            exact=sum(x==y for x,y in zip(one,two))
            rgb_total+=frames
            rgb_matches+=exact
            final_rgb_total+=1
            final_rgb_matches+=int(one[-1]==two[-1])
            camera[kind]={
                "matched_all_frames":exact,
                "total_frames":frames,
                "different_frame_indices_zero_based":[
                    i for i,(x,y) in enumerate(zip(one,two)) if x!=y
                ],
                "final_rgb_sha_identical":one[-1]==two[-1],
            }
        li,ri=left["i420"],right["i420"]
        m=sum(x==y for x,y in zip(li,ri))
        i420_total+=frames
        i420_matches+=m
        final_i420_matches+=int(li[-1]==ri[-1])
        equal_gpu={}
        if terminal:
            for stage in STAGES:
                eq=left["gpu"][stage]==right["gpu"][stage]
                gpu_total+=1
                gpu_matches+=int(eq)
                equal_gpu[stage]=eq
        by_arm[name]={
            "source_rgb":camera,
            "i420_frames_identical":m,
            "i420_total_frames":frames,
            "i420_different_frame_indices_zero_based":[
                i for i,(x,y) in enumerate(zip(li,ri)) if x!=y
            ],
            "final_i420_sha_identical":li[-1]==ri[-1],
            "terminal_gpu_stage_sha_identical":equal_gpu if terminal else None,
        }
    return {
        "status":("TWO_REAL_NATIVE_TERMINAL_GPU_RUNS_AGREE_AT_FINAL_FRAME"
                  if gpu_matches==gpu_total and
                     final_rgb_matches==final_rgb_total and
                     final_i420_matches==len(CONDITIONS)
                  else "TWO_REAL_NATIVE_TERMINAL_GPU_RUNS_HAVE_MISMATCHES"),
        "seed":a["seed"],"scenario":a["scenario"],"frames":frames,
        "terminal_gpu_stages_exact_sha_count":gpu_matches,
        "terminal_gpu_stages_total":gpu_total,
        "all_RGB_frame_sha_equal_count":rgb_matches,
        "all_RGB_frame_sha_count":rgb_total,
        "all_I420_frame_sha_equal_count":i420_matches,
        "all_I420_frame_sha_count":i420_total,
        "final_RGB_sha_equal_count":final_rgb_matches,
        "final_RGB_sha_count":final_rgb_total,
        "final_I420_sha_equal_count":final_i420_matches,
        "final_I420_sha_count":len(CONDITIONS),
        "per_arm_evidence":by_arm,
        "two_separate_actions_runs_are_not_original_onnx_closed_loop_repeatability_proof":True,
        "real_vehicle_testing":False,"model_scoring_allowed":False,
    }


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="Cross-GitHub-workflow native shadow raw-byte audit")
    parser.add_argument("--first",type=Path,required=True)
    parser.add_argument("--second",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args(argv)
    result=compare_repeated_artifacts(args.first,args.second)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(
        json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8",
    )
    print("TWO_INDEPENDENT_TERMINAL_GPU_RUNS",json.dumps({
        "status":result["status"],
        "seed":result["seed"],
        "scene":result["scenario"],
        "gpu":f'{result["terminal_gpu_stages_exact_sha_count"]}/{result["terminal_gpu_stages_total"]}',
        "I420":f'{result["all_I420_frame_sha_equal_count"]}/{result["all_I420_frame_sha_count"]}',
    },ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
