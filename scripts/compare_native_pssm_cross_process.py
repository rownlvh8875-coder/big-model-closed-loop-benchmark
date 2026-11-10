"""Stage 7: independently repeated fixed-world-pose MetaDrive camera timing A/B.

Compare the original sequential perceive / one-taskMgr-step pair schedules,
each with the normal original PSSM.update task, against distinct experimental
processes where only PSSM.update has been removed. All comparisons are BETWEEN
two *different* processes running the SAME treatment and same fixed pose.

PSSM task removal CHANGES renderer semantics. This is no-ONNX static-scene
diagnosis, not an original model path, performance score or causal proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bigbench.curved_lane_scenarios import SCENARIOS

SEEDS=(20261109,20261110)
SCENES=("s_curve_left_right","s_curve_right_left")
FRACTION=.12
FRAMES=10
WARMUP=2
ARMS={
    "sequential_original":("perceive_sequential","baseline",2),
    "paired_original":("task_step_pair","baseline",1),
    "sequential_pssm_task_removed":("perceive_sequential","shadow_off",2),
    "paired_pssm_task_removed":("task_step_pair","shadow_off",1),
}


def verified_hash_series(report:dict,section:str,camera:str|None=None)->list[str]:
    obj=report[section][camera] if camera else report[section]
    values=obj.get("all_frame_sha256")
    if (not isinstance(values,list) or len(values)!=FRAMES
        or any(not isinstance(v,str) or len(v)!=64
               or any(c not in "0123456789abcdef" for c in v)
               for v in values)):
        raise ValueError(f"invalid native RGB/I420 SHA sequence {section}/{camera}")
    return values


def validate_trial(record:dict,seed:int,scene:str,arm:str)->None:
    mode,ablation,ticks=ARMS[arm]
    if (record.get("status")!="OBSERVED_NATIVE_PIXEL_CLOCK"
        or record.get("seed")!=seed or record.get("scenario")!=scene
        or record.get("fraction")!=FRACTION
        or record.get("mode")!=mode or record.get("ablation")!=ablation
        or record.get("frames")!=FRAMES or record.get("warmup")!=WARMUP
        or record.get("raw_sensor_rgb_dims")!=[964,604]
        or record.get("model_rgb_dims")!=[512,256]
        or record.get("capture_schedule")!="existing native MetaDrive paths, no extra ticks"
        or record.get("pssm_task_identity_correct") is not True
        or record.get("all_panda_frame_count_deltas_as_expected") is not True
        or record.get("task_manager_step_invocations_from_capture_call_path")!=ticks
        or record.get("cpu_readbacks_bit_exact_without_new_render") is not True
        or record.get("scene_visual_ego_pose_unchanged") is not True
        or record.get("clock_observations_finite") is not True
        or record.get("gpu_texture_extract_calls")!=0
        or record.get("onnx_inference_used") is not False
        or record.get("model_scoring_allowed") is not False
        or record.get("real_vehicle_testing") is not False):
        raise ValueError(f"{arm}: incomplete original native camera / PSSM controls")
    if (type(record.get("process_id")) is not int
        or not record.get("process_uuid")
        or not isinstance(record["process_uuid"],str)):
        raise ValueError("separate native Python process identity missing")
    if (not isinstance(record.get("camera_pose"),list)
        or len(record["camera_pose"])!=2
        or any(record.get("camera_plus_2m_positive",{}).get(k) is not True
               for k in ("road","wide"))):
        raise ValueError("native world pose or spatial positive control missing")
    tasks=record.get("registered_tasks_before",[])
    if (not isinstance(tasks,list) or "igLoop" not in tasks
        or ("PSSM.update" in tasks)!=(ablation=="baseline")):
        raise ValueError("original PSSM task membership does not match treatment")
    if ablation=="baseline":
        if record.get("ablation_receipt") is not None:
            raise ValueError("original control unexpectedly ablated")
    elif not record.get("ablation_receipt"):
        raise ValueError("PSSM removal not evidenced")
    for cam in ("road","wide"):
        verified_hash_series(record,"source_rgb",cam)
        verified_hash_series(record,"model_rgb",cam)
    verified_hash_series(record,"onnx_i420")
    timeline=record.get("clock_timeline")
    if (not isinstance(timeline,list) or len(timeline)!=FRAMES
        or any(row.get("global_clock_frame_count_delta")!=ticks
               for row in timeline)):
        raise ValueError("unexpected task/graphics time timeline")


def _matches(a:list[str],b:list[str])->dict:
    matches=[x==y for x,y in zip(a,b)]
    if len(matches)!=FRAMES:
        raise ValueError("short native image sequence")
    return {
        "matched_full_timeline":int(sum(matches)),
        "full_timeline_frames":FRAMES,
        "matched_post_warmup":int(sum(matches[WARMUP:])),
        "post_warmup_frames":FRAMES-WARMUP,
        "first_different_step_1_based":next(
            (i for i,ok in enumerate(matches,1) if not ok),None
        ),
        "different_steps_1_based":[i for i,ok in enumerate(matches,1) if not ok],
    }


def compare_native_camera_repeats(a:dict,b:dict,seed:int,scene:str,arm:str)->dict:
    validate_trial(a,seed,scene,arm)
    validate_trial(b,seed,scene,arm)
    if a["process_uuid"]==b["process_uuid"] or a["process_id"]==b["process_id"]:
        raise ValueError("native image repeat must use separate Panda process")
    if (a["camera_pose"]!=b["camera_pose"] or
        a.get("expected_panda_global_frame_count_delta_per_pair")!=
        b.get("expected_panda_global_frame_count_delta_per_pair")):
        raise ValueError("native camera poses or schedule not comparable")
    modes={}
    for cam in ("road","wide"):
        modes[cam]={
            "source_rgb":_matches(
                verified_hash_series(a,"source_rgb",cam),
                verified_hash_series(b,"source_rgb",cam)),
            "warped_model_rgb":_matches(
                verified_hash_series(a,"model_rgb",cam),
                verified_hash_series(b,"model_rgb",cam)),
        }
    return {
        "arm":arm,"camera_capture_mode":ARMS[arm][0],
        "pssm_update_task_enabled":ARMS[arm][1]=="baseline",
        "native_original_renderer_semantics_preserved":ARMS[arm][1]=="baseline",
        "seed":seed,"scenario":scene,"lane_fraction":FRACTION,
        "camera_pose":a["camera_pose"],
        "two_independent_processes_verified":True,
        "source_and_warped_rgb_by_camera":modes,
        "model_i420_without_onnx":_matches(
            verified_hash_series(a,"onnx_i420"),
            verified_hash_series(b,"onnx_i420")),
        "comparison_is_between_identical_treatment_not_original_vs_ablation":True,
        "pssm_removal_not_a_safe_original_model_renderer_substitute":True,
        "real_vehicle_testing":False,"model_scoring_allowed":False,
    }


def scene_directory(root:Path,seed:int,scene:str)->Path:
    if seed not in SEEDS or scene not in SCENES:
        raise ValueError("unexpected fixed native scene")
    return root/f"seed-{seed}"/scene


def compare_one_native_scene(root:Path,seed:int,scene:str)->dict:
    if scene not in SCENARIOS:
        raise ValueError("unknown native MetaDrive map")
    folder=scene_directory(root,seed,scene)
    rows={}
    for arm in ARMS:
        first=json.loads((folder/f"{arm}-run_0.json").read_text(encoding="utf-8"))
        second=json.loads((folder/f"{arm}-run_1.json").read_text(encoding="utf-8"))
        rows[arm]=compare_native_camera_repeats(first,second,seed,scene,arm)
    return {
        "status":"FOUR_FIXED_POSE_TREATMENTS_EACH_INDEPENDENTLY_COMPARED",
        "seed":seed,"scenario":scene,"fraction":FRACTION,
        "native_process_count":len(ARMS)*2,
        "arm_receipts":rows,
        "original_PSSM_vs_ablation_is_not_same_renderer_semantics":True,
        "original_onxx_native_closed_loop_gate_proven":False,
        "pssm_is_unique_renderer_cause_proven":False,
        "real_vehicle_testing":False,"model_scoring_allowed":False,
    }


def aggregate_four_native_scenes(root:Path)->dict:
    scenes=[]
    for seed in SEEDS:
        for scene in SCENES:
            folder=scene_directory(root,seed,scene)
            stored=json.loads((folder/"case_comparison.json").read_text(
                encoding="utf-8"
            ))
            current=compare_one_native_scene(root,seed,scene)
            if current!=stored:
                raise ValueError("forged or stale fixed-scene cross-process summary")
            scenes.append(current)
    return {
        "status":"FOUR_NATIVE_SCENES_ORIGINAL_PSSM_VS_REMOVAL_EVIDENCE_VERIFIED",
        "official_meta_drive_version":"0.4.3",
        "all_scene_comparison_processes":len(scenes)*len(ARMS)*2,
        "arm_labels":list(ARMS),
        "per_scene":scenes,
        "pssm_task_removal_is_experimental_not_original_renderer":True,
        "independent_process_image_hash_matching_is_not_onnx_exact_gate":True,
        "stage7_original_mdv3_repeatability_proven":False,
        "unique_gpu_shadow_root_cause_proven":False,
        "real_vehicle_testing":False,"model_scoring_allowed":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description="Stage7 fixed-pose independent native PSSM scheduling A/B")
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--mode",choices=("case","aggregate"),required=True)
    p.add_argument("--seed",type=int,default=None)
    p.add_argument("--scene",choices=SCENES,default=None)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    if args.mode=="case":
        if args.seed not in SEEDS or args.scene not in SCENES:
            raise ValueError("case seed and scene are required")
        result=compare_one_native_scene(args.root,args.seed,args.scene)
        brief={"status":result["status"],"seed":args.seed,"scene":args.scene,
               "arms":{k:{
                    "I420":f'{v["model_i420_without_onnx"]["matched_full_timeline"]}/{FRAMES}',
                    "source_rgb":{cam:v["source_and_warped_rgb_by_camera"][cam][
                        "source_rgb"]["matched_full_timeline"] for cam in ("road","wide")},
               } for k,v in result["arm_receipts"].items()}}
    else:
        result=aggregate_four_native_scenes(args.root)
        brief={"status":result["status"],"native_processes":result[
            "all_scene_comparison_processes"]}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False,
                                    allow_nan=False)+"\n",encoding="utf-8")
    print("STAGE7_PSSM_CROSSPROCESS",json.dumps(brief,ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
