"""Aggregate genuinely independent MetaDrive PROCESS experiments.

Every condition must be recorded in its own Python/Panda3D process. This
removes the prior six-condition experiment's shared ClockObject/task lifetime
confound; it does NOT control GPU driver nondeterminism or OS scheduling.
"""
from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from bigbench.render_causality import interpret_pipeline

MODES=('perceive_sequential','task_step_pair','graphics_frame_pair')
SCENES=('ego_visible','ego_hidden')


def combine_independent_processes(root:Path, *, scenes=SCENES, modes=MODES) -> dict:
    conditions={}
    invalid=[]
    provenance=[]
    for scene,mode in product(scenes,modes):
        key=f'{scene}_{mode}'
        path=root/key/(key+'.json')
        if not path.is_file():
            invalid.append(f'{key}: file missing')
            conditions[key]={'status':'ERROR','error':'independent process report missing'}
            continue
        record=json.loads(path.read_text(encoding='utf-8'))
        if record.get('condition')!=key:
            invalid.append(f'{key}: condition identity mismatch')
            conditions[key]={'status':'ERROR','error':'condition identity mismatch'}
            continue
        if record.get('status')!='OBSERVED':
            invalid.append(f'{key}: {record.get("status","MISSING")}')
        if not record.get('pose_shift_positive_control',{}).get('road') or not record.get('pose_shift_positive_control',{}).get('wide'):
            invalid.append(f'{key}: camera pose-shift control missing/failed')
        if record.get('real_vehicle_testing') is not False or record.get('model_scoring_allowed') is not False:
            invalid.append(f'{key}: provenance guard missing')
        provenance.append({
            'condition':key,
            'seed':record.get('seed'),
            'start_frame_count':record.get('scene_before',{}).get('clock_frame_count'),
            'end_frame_count':record.get('scene_after',{}).get('clock_frame_count'),
            'start_frame_time_s':record.get('scene_before',{}).get('clock_frame_time_s'),
            'end_frame_time_s':record.get('scene_after',{}).get('clock_frame_time_s'),
            'frames':record.get('frames'),
        })
        conditions[key]=record
    observed=[v for v in conditions.values() if v.get('status')=='OBSERVED']
    if observed:
        if len({r.get('seed') for r in observed})!=1 or len({r.get('frames') for r in observed})!=1:
            invalid.append('seed or frame count mismatch between processes')
    conclusion=interpret_pipeline(conditions)
    table=[]
    for key,entry in conditions.items():
        if entry.get('status')!='OBSERVED':
            table.append({'condition':key,'status':entry.get('status'),'error':entry.get('error')})
            continue
        models=entry['model_frame_stability']
        sources=entry['source_frame_stability']
        reads=entry['cpu_readback']
        tensor=entry['onnx_packed_tensor_stability']
        table.append({
            'condition':key,'status':entry['status'],
            'source_changed_pixels_after_warmup':{
                cam:sources[cam]['max_changed_pixels_after_warmup'] for cam in ('road','wide')},
            'model_changed_pixels_after_warmup':{
                cam:models[cam]['max_changed_pixels_after_warmup'] for cam in ('road','wide')},
            'cpu_read_without_render_bit_exact':{
                cam:reads[cam]['readback_bit_exact'] for cam in ('road','wide')},
            'onnx_tensor_bit_exact_after_warmup':tensor['after_warmup_bit_exact'],
            'onnx_tensor_changed_elements_after_warmup':tensor['max_changed_tensor_elements_after_warmup'],
            'positively_proved_pose_affects_both_cameras':all(entry['pose_shift_positive_control'].values()),
        })
    return {
        'status':'PROCESS_ISOLATED_COMPARISON_RECORDED' if not invalid else 'INCONCLUSIVE_MISSING_OR_INVALID_PROCESS_EVIDENCE',
        'scope':'DIFFERENTIAL_RENDER_TASK_GPU_RAM_SCENE_OBSERVATION_NOT_CAUSAL_PROOF',
        'all_conditions_valid':not invalid,
        'invalid_conditions':invalid,
        'os_process_isolation_required':True,
        'independent_python_processes_expected':len(scenes)*len(modes),
        'model_scoring_allowed':False,'real_vehicle_testing':False,
        'per_condition':table,'process_provenance':provenance,
        'interpretation':conclusion,
        'warning':'No model ranking, no real camera fidelity, no exact-ONNX-feedback repeatability claim',
    }


def main(argv=None):
    p=argparse.ArgumentParser(description='Combine isolated MetaDrive causality reports only')
    p.add_argument('--root',type=Path,default=Path('output/process-isolated'))
    p.add_argument('--out',type=Path,default=None)
    args=p.parse_args(argv)
    result=combine_independent_processes(args.root)
    dst=args.out or args.root/'process_isolation_summary.json'
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',
                   encoding='utf-8')
    print('PROCESS_ISOLATION_SUMMARY',json.dumps(
        {'status':result['status'],
         'conditions':len(result['per_condition']),
         'interpretation':result['interpretation']['task_vs_graphics'],
         'readback':result['interpretation']['readback_status']},
        ensure_ascii=False),flush=True)
    return 0 if result['all_conditions_valid'] else 2


if __name__=='__main__':
    raise SystemExit(main())
