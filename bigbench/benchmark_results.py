"""Verify owned SDK3 receipts and assemble a bounded offline comparison."""

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from .full_s_receipts import digest64, need, validate_trajectory
from .full_s_validation import compare_full_s
from .kinematics import AgentState, ModelAction, step_ideal
from .longitudinal_world import scenario
from .native_longitudinal import DeterministicLeadTimeline

MODELS = {
    'md-v3': '35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199',
    'light-speed-2': '909a140019050a9d7f00db22dd4f4085928d2af9474a82244672ddab964f95a8',
}
LATERAL_CASES = tuple((seed,scene) for seed in (20261109,20261110)
                      for scene in ('s_curve_left_right','s_curve_right_left'))
LONGITUDINAL_CASES = {'lead_brake':240, 'stop_go':240, 'cut_in':200}
SDK_SHA = '27cd80fb1c06feaa7da8b5658cce918d1e3ab71c304a0c0ce42e30688ac008f3'
CORE_SHA = '8b0372f1df91a930f18b2551f7fde5d5687e21bc79dee9ecd0dd2018cba72490'


def read(path):
    return json.loads(path.read_bytes())


def verify_input_files(folder, image):
    for role in ('road','wide'):
        raw = (folder/f'first-{role}.rgb').read_bytes()
        need(len(raw)==964*604*3 and sha256(raw).hexdigest()==image['source_sha256'][role],
             'first input must bind both retained source RGB files')
    tensor = (folder/'first-input.bin').read_bytes()
    need(len(tensor)==2*6*128*256 and sha256(tensor).hexdigest()==image['actual_tensor_sha256'],
         'first input must bind the retained tensor bytes')


def verify_capture_rows(folder, capture, audits):
    images = read(folder/'input-rows.json')
    need(len(images)>=len(capture) and len(audits)>=len(capture),'complete source and inference audits')
    if capture:
        verify_input_files(folder,images[0])
    for index,(frame,image,audit) in enumerate(zip(capture,images,audits),1):
        keys = ('road_frame_sha256','wide_frame_sha256') if 'road_frame_sha256' in frame else (
            'road_camera_sha256','wide_camera_sha256')
        actual = image['actual_tensor_sha256']
        need(frame['step']==image['step']==index and digest64(actual)
             and audit['new_img_sha256']==actual and frame.get('new_img_sha256',actual)==actual,
             'each live input must bind the real inference audit')
        need([frame[key] for key in keys]==image['canvas_sha256']
             and set(image['source_sha256'])=={'road','wide'}
             and all(digest64(value) and frame.get(f'source_{role}_rgb_sha256',value)==value
                     for role,value in image['source_sha256'].items()),
             'each receipt must bind both source/canvas hashes')
    return images


def verify_owner_and_model(folder, model, seed, scene):
    document = read(folder/'report.json')
    owner = read(folder/'native-child.json')
    life = read(folder/'lifecycle.json')
    need((document['seed'],document['scenario'])==(seed,scene)
         and document['status']=='RETURNED' and document['runtime']=='cloud-local',
         'completed runtime and registered scenario required')
    need(owner['spawn_attempted'] and owner['pid']==document['pid'] and owner['returncode']==0
         and document['provider_closed'] and document['child_finalized_before_server_stop'],
         'reaped child and closed camera required')
    need(document['nonce']==life['nonce'] and document['pid']==life['pid']
         and document['policy_created'] and document['official_model_process_bounds']==[1,1]
         and life['official_model_process_bounds']==[1,1] and document['ort']=='1.20.1'
         and document['providers']==['CPUExecutionProvider']
         and document['model_sha256']==MODELS[model],
         'observed official ORT CPU policy and model identity required')
    need(document['sdk_sha256']==SDK_SHA and document['core_sha256']==CORE_SHA
         and document['input_variant']=='source_yuv_nearest_even'
         and 'llvmpipe' in document['driver']['renderer'],
         'frozen SDK3, llvmpipe and live registered input required')
    return document


def common_camera_key(document, first):
    return dict(geometry=document['geometry'], intrinsics=document['intrinsics'], driver=document['driver'],
                variant=document['input_variant'], first_source=first['source_sha256'],
                first_canvas=first['canvas_sha256'], first_input=first['actual_tensor_sha256'])


def lateral_pair(directory, model, seed, scene):
    path = directory/f'{seed}-{scene}'
    rows, trials, camera_keys = [], [], []
    result = dict(runs=rows, strict_repeat_passed=None, traversal_passed=None, status='PENDING')
    written = [path/f'run-{index}' for index in (0,1)]
    for folder in written:
        if not (folder/'run.json').is_file():
            failure = failure_record(folder)
            if failure:
                rows.append(failure)
                result['status'] = 'EXECUTION_FAILED'
            continue
        try:
            doc = verify_owner_and_model(folder,model,seed,scene)
            trial = read(folder/'run.json')
            need(trial['model_sha256']==MODELS[model] and not trial['model_test_double']
                 and not trial['injected_session'] and doc['ordering']['state_restored']
                 and doc['ordering']['original_active_bins_restored'] and doc['geometry']==trial['geometry'],
                 'genuine model, restituted ordering and runtime-bound route geometry required')
            proof = validate_trajectory(trial,seed,scene)
            need(proof['inference_bounds']==doc['official_inference_bounds'],
                 'lifecycle and trajectory inference counts must agree')
            frames = trial['frames']
            images = verify_capture_rows(folder,frames,trial['inference_audit_rows'])
            need(bool(images) and bool(frames),'a comparison requires a retained capture')
            trials.append(trial)
            camera_keys.append(common_camera_key(doc,images[0]))
            last = frames[-1]['route']
            rows.append(dict(outcome=proof['outcome'], steps=len(frames), intrusion_m=last['intrusion_m'],
                             last_lane=last['lane_id'], last_station_m=last['longitudinal_m'],
                             frames=[{key:frame[key] for key in ('world_x_m','world_y_m')} for frame in frames]))
        except (OSError, KeyError, TypeError, ValueError) as error:
            result['status'] = 'INVALID_RECEIPT'
            rows.append(dict(outcome='INVALID_RECEIPT', steps=None, error=str(error), source=str(folder)))
    if len(trials)==2:
        try:
            ledger = read(path/'pair-ledger.json')
            need(len(ledger)==2 and ledger[0]['nonce']!=ledger[1]['nonce']
                 and all(row['returncode']==0 for row in ledger),'two independently reaped model owners required')
            pair = compare_full_s(*trials)
            result.update(strict_repeat_passed=pair['strict_repeat_passed'],
                          traversal_passed=pair['traversal_passed'],
                          first_diverging_step=pair['first_diverging_step'], status='VERIFIED')
        except (OSError, KeyError, TypeError, ValueError) as error:
            result.update(status='INVALID_RECEIPT', error=str(error))
    failure = failure_record(path)
    if not trials and not rows and failure:
        rows.append(failure)
        result['status'] = 'EXECUTION_FAILED'
    return result,camera_keys


def failure_record(folder):
    for filename,field in (('error.json','message'),('report.json','failure'),('native-child.json','failure')):
        path = folder/filename
        if path.is_file():
            try:
                error = read(path).get(field)
            except (OSError, ValueError, AttributeError) as exc:
                error = f'could not read {filename}: {exc}'
            if error:
                return dict(outcome='EXECUTION_FAILED', termination='EXECUTION_FAILED',
                            steps=None, error=error, source=str(folder))
    return None


def verify_longitudinal(folder, model, seed, scene_name, steps):
    doc = verify_owner_and_model(folder,model,seed,scene_name)
    run = read(folder/'run.json')
    scene = scenario(scene_name)
    expected = json.loads(json.dumps(asdict(scene)))
    need(doc['actor_closed'] and doc['step_limit']==steps and run['steps_requested']==steps
         and run['dt_s']==.05 and run['initial_scene']==expected and run['status']=='DIAGNOSTIC_EXECUTED'
         and run['model_sha256']==MODELS[model] and not run['model_test_double'] and not run['injected_session'],
         'registered longitudinal schedule, original model and cleaned visual actor required')
    frames = run['trace']
    need(0<len(frames)==run['steps_completed']<=steps
         and run['actual_inference_bounds']==doc['official_inference_bounds']==[len(frames),len(frames)],
         'exact longitudinal receipt and inference count required')
    audits = run['audit_rows']
    need(len(audits)==len(frames),'one original audit per integrated longitudinal step required')
    images = verify_capture_rows(folder,frames,audits)
    state = AgentState(0.,0.,0.,0.,scene.ego_speed_mps)
    lead = DeterministicLeadTimeline(scene)
    previous_acceleration = 0.
    for index,(row,audit) in enumerate(zip(frames,audits),1):
        expected_visibility = scene.merge_at_s is None or state.t>=scene.merge_at_s
        acceleration = audit['raw_model_action'][1]
        wanted = step_ideal(state,ModelAction(0.,acceleration),.05)
        target = lead.step(state.t,.05)
        gap = target.station_m-wanted.x if expected_visibility else None
        closing = wanted.speed-target.speed_mps
        ttc = max(0.,gap)/closing if gap is not None and closing>1e-9 else None
        expected_row = dict(step=index, time_s=wanted.t, ego_station_m=wanted.x, ego_speed_mps=wanted.speed,
                            lead_station_m=target.station_m, lead_speed_mps=target.speed_mps,
                            lead_in_target_lane=expected_visibility, gap_m=gap, ttc_s=ttc,
                            raw_model_accel_mps2=acceleration, jerk_mps3=(acceleration-previous_acceleration)/.05)
        need(all(row[key]==value for key,value in expected_row.items()),
             'longitudinal motion must reconstruct exactly from original ONNX acceleration and lead schedule')
        need(gap is None or gap>0 or index==len(frames),'first nonpositive gap must end the trial')
        state,previous_acceleration = wanted,acceleration
    collision = any(row['gap_m'] is not None and row['gap_m']<=0 for row in frames)
    termination = 'LEAD_GAP_NONPOSITIVE' if collision else 'STEP_LIMIT'
    need(run['termination']==termination and (collision or len(frames)==steps),'exact longitudinal termination')
    stops = next((i for i,r in enumerate(frames) if r['ego_speed_mps']==0.),None)
    restart = next((r['time_s'] for r in frames[stops+1:] if r['ego_speed_mps']>0.),None) if stops is not None else None
    result = dict(status='VERIFIED',steps=len(frames),termination=termination,
                  minimum_synthetic_gap_m=min((r['gap_m'] for r in frames if r['gap_m'] is not None),default=None),
                  minimum_ttc_s=min((r['ttc_s'] for r in frames if r['ttc_s'] is not None),default=None),
                  maximum_abs_jerk_mps3=max(abs(r['jerk_mps3']) for r in frames),
                  ego_first_stop_s=frames[stops]['time_s'] if stops is not None else None,
                  ego_first_restart_s=restart)
    need(all(run[key]==value for key,value in result.items() if key not in {'status','steps'}),
         'reported longitudinal metrics must equal the independently reconstructed values')
    return result,common_camera_key(doc,images[0])


def build_comparison(md_v3, light_speed_2, longitudinal, *, longitudinal_seed=20261109):
    roots = {'md-v3':Path(md_v3),'light-speed-2':Path(light_speed_2)}
    lateral = []
    for seed,scene in LATERAL_CASES:
        models, comparable_keys = {}, []
        for model,root in roots.items():
            models[model], keys = lateral_pair(root,model,seed,scene)
            comparable_keys.extend(keys)
        comparable = None
        if all(item['status']=='VERIFIED' for item in models.values()):
            comparable = len(comparable_keys)==4 and all(k==comparable_keys[0] for k in comparable_keys[1:])
        lateral.append(dict(seed=seed,scenario=scene,comparable=comparable,models=models))
    longitudinal_cases = []
    for scene,steps in LONGITUDINAL_CASES.items():
        models, camera_keys = {}, []
        for model in roots:
            folder = Path(longitudinal)/f'{longitudinal_seed}-{scene}-{model}'
            if not (folder/'run.json').is_file():
                failure = failure_record(folder)
                models[model] = dict(status='EXECUTION_FAILED',**failure) if failure else dict(status='PENDING')
                continue
            try:
                models[model], key = verify_longitudinal(folder,model,longitudinal_seed,scene,steps)
                camera_keys.append(key)
            except (OSError, KeyError, TypeError, ValueError) as error:
                models[model] = dict(status='INVALID_RECEIPT',termination='INVALID_RECEIPT',error=str(error))
        comparable = camera_keys[0]==camera_keys[1] if len(camera_keys)==2 else None
        longitudinal_cases.append(dict(seed=longitudinal_seed,scenario=scene,comparable=comparable,models=models))
    return dict(protocol='sdk3-benchmark-comparison-v1', model_sha256=MODELS,
                runtime='Linux SDK3 llvmpipe',lateral=lateral,longitudinal=longitudinal_cases)
