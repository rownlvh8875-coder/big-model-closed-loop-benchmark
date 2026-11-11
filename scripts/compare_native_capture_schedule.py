"""Independent static-scene camera order/tick isolation; never an ONNX gate."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scripts.compare_native_pssm_cross_process import (
    SEEDS, SCENES, FRAMES, scene_directory, validate_capture_trial,
    verified_hash_series, _matches,
)

SCHEDULES={
    'sequential_road_first':('perceive_sequential',2),
    'sequential_wide_first':('perceive_reverse',2),
    'paired_one_tick':('task_step_pair',1),
    'paired_two_ticks':('task_step_pair_twice',2),
}


def compare_schedule_repeats(a:dict,b:dict,seed:int,scene:str,arm:str)->dict:
    if arm not in SCHEDULES or seed not in SEEDS or scene not in SCENES:
        raise ValueError('unknown native schedule condition')
    mode,ticks=SCHEDULES[arm]
    for d in (a,b):
        validate_capture_trial(d,seed,scene,mode=mode,ablation='baseline',ticks=ticks)
        pose=d['camera_pose']
        if (any(not isinstance(v,list) or len(v)!=3 for v in pose)
            or any(type(x) not in (int,float) or not math.isfinite(x)
                   for v in pose for x in v)):
            raise ValueError('finite WORLD position and orientation triples required')
        after_tasks=d.get('registered_tasks_after')
        if (not isinstance(after_tasks,list)
            or not all(isinstance(t,str) for t in after_tasks)
            or sorted(after_tasks)!=sorted(d['registered_tasks_before'])):
            raise ValueError('original PSSM/Chase task registry changed during capture')
        if d.get('expected_panda_global_frame_count_delta_per_pair')!=ticks:
            raise ValueError('mislabeled expected clock count')
        previous_after=None
        for i,row in enumerate(d['clock_timeline']):
            before=row.get('before',{}).get('frame_count')
            after=row.get('after',{}).get('frame_count')
            if (row.get('render_frame_index_zero_based')!=i
                or type(before) is not int or type(after) is not int
                or after-before!=ticks
                or (previous_after is not None and before!=previous_after)):
                raise ValueError('raw Panda clock timeline does not prove the schedule')
            previous_after=after
    if a['process_uuid']==b['process_uuid'] or a['process_id']==b['process_id']:
        raise ValueError('two separate native processes required')
    if a['camera_pose']!=b['camera_pose']:
        raise ValueError('native WORLD camera poses differ')
    source={c:_matches(verified_hash_series(a,'source_rgb',c),
                       verified_hash_series(b,'source_rgb',c)) for c in ('road','wide')}
    warped={c:_matches(verified_hash_series(a,'model_rgb',c),
                       verified_hash_series(b,'model_rgb',c)) for c in ('road','wide')}
    packed=_matches(verified_hash_series(a,'onnx_i420'),verified_hash_series(b,'onnx_i420'))
    all_fields=[*source.values(),*warped.values(),packed]
    return {
        'arm':arm,'mode':mode,'task_ticks_per_pair':ticks,
        'seed':seed,'scenario':scene,'camera_pose':a['camera_pose'],
        'process_uuids':[a['process_uuid'],b['process_uuid']],
        'source_rgb':source,'warped_rgb':warped,'i420':packed,
        'all_image_fields_bit_exact':all(x['matched_full_timeline']==FRAMES for x in all_fields),
        'original_pssm_chase_tasks_preserved':True,
        'is_original_sequential_control':arm=='sequential_road_first',
        'capture_schedule_is_experimental':arm!='sequential_road_first',
        'original_mdv3_repeatability_proven':False,
        'unique_renderer_cause_proven':False,
        'onnx_inference_used':False,'model_scoring_allowed':False,'real_vehicle_testing':False,
    }


def compare_scene(root:Path,seed:int,scene:str)->dict:
    folder=scene_directory(root,seed,scene)
    results={}
    ids=set()
    pids=set()
    poses=[]
    for arm in SCHEDULES:
        runs=[json.loads((folder/f'{arm}-run_{i}.json').read_text()) for i in (0,1)]
        result=compare_schedule_repeats(*runs,seed,scene,arm)
        for trial in runs:
            if trial['process_id'] in pids:
                raise ValueError('same-runner native PID reused across schedule arms')
            pids.add(trial['process_id'])
        for uid in result['process_uuids']:
            if uid in ids: raise ValueError('all schedule arms must use independent processes')
            ids.add(uid)
        poses.append(result['camera_pose'])
        results[arm]=result
    if any(p!=poses[0] for p in poses):
        raise ValueError('different WORLD camera poses between treatments')
    return {'status':'NATIVE_CAPTURE_ORDER_TICK_CASE_VERIFIED','seed':seed,'scenario':scene,
            'arms':results,'independent_process_count':len(ids),
            'original_mdv3_repeatability_proven':False,'unique_renderer_cause_proven':False}


def aggregate_scenes(root:Path)->dict:
    cases=[]
    ids=set()
    for seed in SEEDS:
        for scene in SCENES:
            result=compare_scene(root,seed,scene)
            stored=json.loads((scene_directory(root,seed,scene)/'case_comparison.json').read_text())
            if result!=stored: raise ValueError('stale or modified schedule summary')
            for arm in result['arms'].values():
                for uid in arm['process_uuids']:
                    if uid in ids: raise ValueError('process UUID reused across native scenes')
                    ids.add(uid)
            cases.append(result)
    return {'status':'FOUR_NATIVE_CAPTURE_ORDER_TICK_SCENES_VERIFIED',
            'independent_process_count':len(ids),'per_scene':cases,
            'original_mdv3_repeatability_proven':False,'unique_renderer_cause_proven':False,
            'onnx_inference_used':False,'model_scoring_allowed':False,'real_vehicle_testing':False}


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=('case','aggregate'),required=True)
    p.add_argument('--seed',type=int)
    p.add_argument('--scene',choices=SCENES)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    result=compare_scene(a.root,a.seed,a.scene) if a.mode=='case' else aggregate_scenes(a.root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('NATIVE_CAPTURE_ORDER_TICK',result['status'],result['independent_process_count'],flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
