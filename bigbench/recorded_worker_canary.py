"""Sealed no-graph camera canary and pure, bounded evidence readers.

Native SDK imports belong only to the separate admitted CI entry. This module
does not load a graph, authorize a real-model trial, or execute evidence code.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import stat
import sys

from .full_s_recorded_worker import need, _read_receipt, _receipt_bytes, _source_snapshot

ROOT = Path(__file__).resolve().parents[1]
MODE = 'CAMERA_ONLY_NO_GRAPH'
CASE = (20261109, 's_curve_left_right')
STAT_FIELDS = ('configured','closed','error','forwarded','resolutions','paths','events')
REQUEST = 'docs/requests/recorded-worker-canary-20261118-01.json'
BRANCH = 'diagnostic/recorded-worker-canary-20261118-01'
WORKFLOW = '.github/workflows/recorded-worker-canary.yml'
APPROVAL_BRANCH = 'approval/recorded-worker-canary-20261118-01'
APPROVAL_PATH = 'docs/approvals/recorded-worker-canary-20261118-01.json'
QUALIFIED_PROBE = 'docs/evidence/four-validation-20261118/actual-02/20261109-s_curve_left_right/probe.json'
QUALIFIED_PROBE_SHA = '396c0e10a276d96905350a82928b4c9b90c63712c7cf530e872402e209d39427'
LIMITS = dict(steps=2, capture_calls=2, sensor_perceives=4, official_models=0,
    official_inferences=0, child_seconds=240, container_seconds=300,
    memory_bytes=10*1024**3, cpus=2, pids=128, tmp_bytes=512*1024**2)
FALSE_FLAGS = ('origin_authenticated','model_camera_qualified','physical_optics_validated',
    'carla_validated','hardware_gpu_qualified','all_four_validation_tracks_passed')


class NoGraphPolicy:
    """Fixture state/action for testing the actual camera/recorder wiring only."""
    is_mock = True
    _injected_session = True
    name = 'CAMERA_CANARY_SYNTHETIC_STATE_ZERO_ACTION_NO_GRAPH'

    def __init__(self, spec):
        from .onnx_contract import ModelContract
        self.contract = ModelContract.load(spec)  # Metadata only, never check_file.
        self.reset()

    def reset(self):
        import numpy as np
        self.state = {k:np.zeros(self.contract.input_shapes[k],
            dtype=np.uint8 if k=='state_img_q' else np.float32) for k in self.contract.state_keys}
        self.audit_rows, self.trace = [], []
        self.last_model_outputs = self.last_input_image_sha256 = None

    def step(self, observation):
        import numpy as np
        from .image_adapter import camera_pair_to_model
        from .kinematics import ModelAction
        from .full_s_failure_capture import _state_digest
        need(len(self.audit_rows)<2, 'sealed two-call fixture budget')
        packed = camera_pair_to_model(observation.frame, observation.wide_frame)
        self.last_input_image_sha256 = hashlib.sha256(packed.tobytes()).hexdigest()
        raw = np.zeros(4, np.float32)
        # These deterministic bytes are explicitly synthetic; there is no session.
        self.state = {k:np.full_like(v,len(self.audit_rows)+1) for k,v in self.state.items()}
        self.last_model_outputs = {'action':raw}
        self.audit_rows.append(dict(new_img_sha256=self.last_input_image_sha256,
            raw_model_action=raw.tolist(), raw_action_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),
            state_after_step_sha256=_state_digest({k:v.tobytes() for k,v in self.state.items()})))
        self.trace.append({'fixture_only':True})
        return ModelAction(0.,0.)


class ZeroModelAudit:
    def __init__(self):
        self.weight_open_attempts = self.ort_import_attempts = 0

    def __call__(self, event, args):
        if event=='import' and args and str(args[0]).split('.')[0]=='onnxruntime':
            self.ort_import_attempts += 1
            raise RuntimeError('ORT import forbidden by sealed camera canary')
        if event=='open' and args and isinstance(args[0], (str,bytes,os.PathLike)):
            name=os.fsdecode(args[0]).lower()
            if name.endswith(('.onnx','.ort')):
                self.weight_open_attempts += 1
                raise RuntimeError('weight open forbidden by sealed camera canary')

    def snapshot(self):
        return dict(weight_open_attempts=self.weight_open_attempts, ort_import_attempts=self.ort_import_attempts)


def read_native_ack(path):
    root=Path(path).parent
    launch=_read_receipt(root/'launch.json')
    native=_read_receipt(root/'native-child.json')
    need(launch.get('mode')==MODE and (launch.get('seed'),launch.get('scenario'))==CASE and
         launch.get('parent_pid')==os.getppid(), 'sealed canary parent/case required')
    need(all(k in native for k in ('pid','spawn_attempted','returncode','server_returncode')) and
         native['spawn_attempted'] is True and native['returncode'] is None and native['server_returncode'] is None,
         'live nonfinal native acknowledgement required')
    pid=native.get('pid')
    need(pid is None or type(pid) is int and pid==os.getpid(), 'actual native child PID required')
    return dict(launch,pid=pid,spawn_succeeded=True if pid is not None else None,
        child_reaped=False,returncode=None)


def verify_trial(root, *, mode):
    """Local byte/receipt validation only; caller must authenticate remote origin."""
    from .full_s_failure_capture import verify_recording
    root=Path(root)
    need(mode in (MODE,'OFFICIAL_MODEL'), 'explicit registered receiver mode required')
    trial=_read_receipt(root/'recorded-trial.json',4*1024**2)
    life=_read_receipt(root/'recorded-trial-lifecycle.json')
    report=_read_receipt(root/'recording/report.json',16*1024**2)
    verification=verify_recording(root/'recording')
    need(trial.get('protocol')=='recorded-full-s-worker-trial-v1' and
         life.get('protocol')=='recorded-full-s-worker-lifecycle-v1','worker receipt protocols required')
    keys=('pid','parent_pid','nonce','seed','scenario')
    need(all(trial.get(k)==life.get(k) for k in keys) and
         type(trial.get('pid')) is int and trial['pid']>0 and
         type(trial.get('parent_pid')) is int and trial['parent_pid']>0 and
         isinstance(trial.get('nonce'),str) and len(trial['nonce'])==32 and
         all(c in '0123456789abcdef' for c in trial['nonce']), 'worker lifecycle identity binding required')
    need(report.get('process_id')==trial['pid'] and
         (report.get('seed'),report.get('scenario'),report.get('max_steps'))==
         (trial.get('seed'),trial.get('scenario'),trial.get('max_steps')), 'original process/case binding required')
    binding=dict(manifest_sha256=hashlib.sha256(_receipt_bytes(root/'recording/manifest.json',4*1024**2)).hexdigest(),
        report_sha256=hashlib.sha256(_receipt_bytes(root/'recording/report.json',16*1024**2)).hexdigest(),
        process_uuid=report['process_uuid'])
    need(trial.get('recording_binding')==binding,'nonce-bearing worker must bind exact original report and manifest bytes')
    need(trial.get('actual_inference_bounds')==life.get('inference_bounds')==report.get('actual_inference_bounds'),
         'conservative original audit bounds binding required')
    need(life.get('status')=='RECORDED' and all(k in trial and k in life for k in ('primary_error','secondary_errors')) and trial.get('primary_error') is None and
         trial.get('secondary_errors')==[] and life.get('primary_error') is None and life.get('secondary_errors')==[] and
         all(life.get(k) is True for k in ('policy_created','provider_created','provider_received',
             'provider_close_attempted','body_provider_close_attempted','provider_closed')) and
         trial.get('provider_closed') is True, 'successful body and provider finalization required')
    need(trial.get('source_context')==_source_snapshot() and
         all(trial.get(k) is False for k in FALSE_FLAGS), 'same selected source and scoped qualifications required')
    need(trial.get('raw_rgb_observer_used') is True and trial.get('raw_rgb_source_evidence_present') is True and
         trial.get('raw_rgb_observer_requested') is True and trial.get('original_report_file')=='recording/report.json' and
         trial.get('recording_verification')==verification and verification['recording_status']=='COMPLETE',
         'complete source byte recording and original report required')
    if mode==MODE:
        need(trial.get('mode')==life.get('mode')==MODE and (trial['seed'],trial['scenario'])==CASE and
             trial['max_steps']==2 and report['completed_steps']==2 and report['outcome']=='STEP_LIMIT' and
             trial.get('fixture_policy_audit_bounds')==trial['actual_inference_bounds']==[2,2] and
             trial.get('official_inference_bounds')==life.get('official_inference_bounds')==[0,0] and
             type(trial.get('official_model_processes')) is int and trial['official_model_processes']==0 and
             trial.get('policy_data')=='SYNTHETIC_STATE_AND_ZERO_ACTION_NO_GRAPH' and
             trial.get('graph_feed_attested') is False and trial.get('onnxruntime')==
             dict(version=None,real_session=False,providers=None,session_class=None), 'sealed zero-model fixture accounting required')
        need(all(type(v) is int for v in trial['official_inference_bounds']+life['official_inference_bounds']),
             'typed official zero bounds required')
        need(all(v.get('model_test_double') is True and v.get('injected_session') is True for v in (trial,report)),
             'explicit synthetic fixture flags required')
        need(all(row['raw_model_action']==[0.,0.,0.,0.] for row in report['frames']), 'fixed zero fixture action required')
    else:
        need(trial.get('mode') is None and life.get('mode') is None and trial['max_steps']==600 and
             all(trial.get(k) is None for k in ('policy_data','fixture_policy_audit_bounds','official_model_processes','official_inference_bounds','graph_feed_attested')) and
             all(v.get('model_test_double') is False and v.get('injected_session') is False for v in (trial,report)) and
             trial.get('onnxruntime',{}).get('real_session') is True and
             trial['onnxruntime'].get('version')=='1.20.1' and
             trial['onnxruntime'].get('providers')==['CPUExecutionProvider'] and
             trial['onnxruntime'].get('session_class')=='onnxruntime.capi.onnxruntime_inference_collection.InferenceSession', 'real session required; fixtures cannot certify a model trial')
        from .full_s_receipts import validate_trajectory
        validate_trajectory(report,trial['seed'],trial['scenario'])
    return dict(verification,protocol='recorded-worker-receiver-v1',mode=mode,
        fixture_policy_audit_bounds=[2,2] if mode==MODE else None,
        official_inference_bounds=[0,0] if mode==MODE else report['actual_inference_bounds'],
        scope='Local receipts and bytes only. Fixture policy audits are not ONNX inferences. External origin requires independent API authentication.')


def qualified_geometry():
    from .full_s_failure_capture import _decode
    raw=_receipt_bytes(ROOT/QUALIFIED_PROBE,4*1024**2)
    need(hashlib.sha256(raw).hexdigest()==QUALIFIED_PROBE_SHA,'immutable prior exact-case geometry probe required')
    value=_decode(raw)
    need((value.get('seed'),value.get('scenario'))==CASE,'registered prior geometry required')
    return value


def validate_canary_trajectory(report, *, qualified=None):
    """Two-step zero-action replay; the existing 600-step validator stays frozen."""
    from dataclasses import asdict
    from .full_s_receipts import recorded_route,close
    from .full_s_validation import route_state
    from .kinematics import AgentState,ModelAction,step_ideal
    from .full_s_receipts import bind_case_geometry
    bind_case_geometry(report,qualified if qualified is not None else qualified_geometry())
    need(report.get('max_steps')==2 and report.get('completed_steps')==2 and
         report.get('outcome')=='STEP_LIMIT' and report.get('traversal_passed') is False and
         report.get('initial_fraction')==.12,
         'exact two-step diagnostic outcome required')
    lanes=recorded_route(report['geometry'])
    xy=lanes[0].position(lanes[0].length*.12,0.)
    state=AgentState(**report['initial_state'])
    need(state.t==0. and state.speed==8. and close(state.x,xy[0]) and close(state.y,xy[1]) and
         close(state.heading,lanes[0].heading_theta_at(lanes[0].length*.12)), 'unchanged initial native pose required')
    for index,row in enumerate(report['frames'],1):
        need(row['step']==index and row['raw_model_action']==[0.,0.,0.,0.] and
             row['parent_model_action']==dict(curvature_1pm=0.,acceleration_mps2=0.) and
             row['applied_world_action']==dict(curvature_1pm=0.,acceleration_mps2=0.), 'zero fixture action and single bridge required')
        state=step_ideal(state,ModelAction(0.,0.),.05,speed_override=8.)
        need(all(row[k]==v for k,v in dict(time_s=state.t,world_x_m=state.x,world_y_m=state.y,
             heading_rad=state.heading,speed_mps=state.speed).items()), 'exact two-step unchanged ideal kinematics required')
        truth=route_state(lanes,0,state)
        need(set(truth)==set(row['route']) and all(row['route'][k]==v if isinstance(v,(bool,str)) or type(v) is int else
             close(row['route'][k],v) for k,v in truth.items()) and truth['intrusion_m']==0 and
             truth['lane_index']==0 and truth['terminal_crossed'] is False, 'actual native route replay required')
    need(report['final_state']==asdict(state) and report['visited_lane_ids']==[str(lanes[0].index)], 'actual final pose/visits required')
    return dict(two_step_trajectory_valid=True,traversal_passed=False)


def check_source_map(root, mapping):
    need(isinstance(mapping,dict) and 1<=len(mapping)<=4096, 'bounded full runnable source map required')
    for name,digest in mapping.items():
        path=PurePosixPath(name)
        need(isinstance(name,str) and not path.is_absolute() and '..' not in path.parts and
             '\\' not in name and ':' not in name and name==path.as_posix(), 'safe source path required')
        actual=Path(root)/name
        need(not actual.is_symlink() and all(not p.is_symlink() for p in actual.parents) and
             actual.is_file() and actual.stat().st_size<=16*1024**2 and
             hashlib.sha256(actual.read_bytes()).hexdigest()==digest, 'actual mounted source byte binding required: '+name)
    return hashlib.sha256(json.dumps(mapping,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate_native_bundle(root):
    """Linux evidence reader; never imports Panda/MetaDrive/ORT or runs evidence."""
    from scripts import panda_sdk3_runtime as pins
    from scripts import sdk3_four_validation_runtime as runtime
    root=Path(root)
    auth=_read_receipt(root/'authentication.json',4*1024**2)
    from scripts.run_recorded_worker_canary import validate_admission,source_manifest
    need(all(k in auth for k in ('request','context','source_ci','authority','current_identity','history')),
         'complete retained source/admission API evidence required')
    regenerated=validate_admission(auth['request'],auth['context'],manifest=source_manifest(auth['source']),
        ci=auth['source_ci'],authority=auth['authority'],current=auth['current_identity'],history=auth['history'])
    need(regenerated==auth,'full retained source/approval/current-run admission binding required')
    request=auth['request']
    need(request.get('mode')==MODE and request.get('limits')==LIMITS and request.get('active') is True and
         auth.get('source')==request.get('source') and auth.get('branch')==BRANCH and
         auth.get('attempt')==1 and auth.get('event')=='push','sealed source request authentication required')
    source_hash=check_source_map(ROOT,request['source_map'])
    folder=root/'native'
    top=_read_receipt(folder/'report.json')
    launch=_read_receipt(folder/'launch.json')
    native=_read_receipt(folder/'native-child.json')
    completion=_read_receipt(folder/'parent-completion.json')
    trial=_read_receipt(folder/'observed-trial/recorded-trial.json',4*1024**2)
    verified=verify_trial(folder/'observed-trial',mode=MODE)
    report=_read_receipt(folder/'observed-trial/recording/report.json',16*1024**2)
    validate_canary_trajectory(report)
    need(top.get('protocol')=='recorded-camera-canary-native-v1' and 'failure' in top and top['failure'] is None and
         top.get('status')=='CAMERA_RECORDER_CANARY_RECORDED' and
         top.get('mode')==launch.get('mode')==MODE and (top.get('seed'),top.get('scenario'))==CASE and
         top.get('parent_admission_checked') is True,'completed admitted native canary required')
    need(all(top.get(k)==launch.get(k)==trial.get(k) for k in ('nonce','seed','scenario','parent_pid')) and
         top.get('pid')==native.get('pid')==trial.get('pid') and type(top.get('pid')) is int and top['pid']>0 and
         top.get('nonce')!='0'*32,'parent/native/observed-body identity binding required')
    need(all(k in native for k in ('spawn_attempted','pid','returncode','server_returncode')) and
         native.get('spawn_attempted') is True and type(native.get('returncode')) is int and native['returncode']==0 and
         top.get('server_returncode')==native.get('server_returncode') and
         type(native.get('server_returncode')) is int and native['server_returncode']==0 and
         native.get('failure') is None and top.get('child_finalized_before_server_stop') is True,
         'child reaped before display stop required')
    need(all(top.get(k)==launch.get(k)==auth.get(k) for k in ('source','activation','run_id')) and
         top.get('source_map_sha256')==source_hash and
         json.dumps(top.get('limits'),sort_keys=True)==json.dumps(launch.get('limits'),sort_keys=True)==json.dumps(LIMITS,sort_keys=True),
         'source/run/resource receipt binding required')
    need(top.get('approval')==launch.get('approval')==request.get('approval_sha') and
         top.get('recorded_trial_sha256')==hashlib.sha256(_receipt_bytes(folder/'observed-trial/recorded-trial.json',4*1024**2)).hexdigest(),
         'native completion must bind worker receipt and independent source approval')
    need(completion.get('protocol')=='recorded-camera-canary-parent-completion-v1' and
         completion.get('status')=='NATIVE_CHILD_REAPED' and 'failure' in completion and completion['failure'] is None and
         type(completion.get('returncode')) is int and completion['returncode']==0 and
         all(completion.get(k)==top.get(k) for k in ('pid','parent_pid','nonce','source','activation','run_id','approval','mode','container_hostname')) and
         completion.get('native_child_sha256')==hashlib.sha256(_receipt_bytes(folder/'native-child.json')).hexdigest() and
         completion.get('report_sha256')==hashlib.sha256(_receipt_bytes(folder/'report.json')).hexdigest(),
         'parent finalization must bind exact native child and completion receipts')
    need(top.get('sdk_sha256')==pins.SDK_SHA and top.get('core_sha256')==pins.CORE_SHA and
         top.get('load_order')=='core-first' and top.get('panda_version')=='1.10.13', 'actual immutable SDK/core bootstrap required')
    for stats in (top.get('source_stats_before'),top.get('source_stats_after'),trial.get('source_stats_after')):
        need(isinstance(stats,dict) and type(stats.get('returned')) is int and stats['returned']==0 and
             stats.get('guards_ok') is True and stats.get('values')=={k:0 for k in STAT_FIELDS} and
             all(type(v) is int for v in stats['values'].values()), 'default-off SDK counters required')
    need(top.get('zero_model_audit')==dict(weight_open_attempts=0,ort_import_attempts=0) and
         all(type(top['zero_model_audit'][k]) is int for k in ('weight_open_attempts','ort_import_attempts')) and
         top.get('onnxruntime_loaded') is False and top.get('official_model_processes')==0 and
         type(top.get('official_model_processes')) is int and type(top.get('official_inferences')) is int and
         top.get('official_inferences')==0 and top.get('capture_count_bounds')==[2,2] and
         top.get('sensor_perceive_bounds')==[4,4] and top.get('fixture_policy_audit_bounds')==[2,2] and
         top.get('policy_data')==trial.get('policy_data') and top.get('graph_feed_attested') is False and
         all(top.get(k) is False for k in FALSE_FLAGS),'separate actual RGB and synthetic policy accounting required')
    driver=trial.get('driver')
    need(isinstance(driver,dict) and 'llvmpipe' in str(driver.get('renderer')).lower() and
         isinstance(driver.get('vendor'),str) and driver['vendor'] and isinstance(driver.get('version'),str) and
         driver['version'], 'actual registered software renderer required')
    container=_read_receipt(folder/'container.json')
    execution=_read_receipt(folder/'execution.json')
    command=_read_receipt(folder/'command.json')
    argv=command.get('argv')
    need(isinstance(argv,list) and all(isinstance(v,str) for v in argv),'actual Docker command required')
    mounts=[argv[i+1] for i,v in enumerate(argv[:-1]) if v=='--mount']
    need(len(mounts)==3,'exact model-free mounts required')
    mounted={}
    for mount in mounts:
        fields=dict(part.split('=',1) if '=' in part else (part,'') for part in mount.split(','))
        need(fields.get('type')=='bind' and 'src' in fields and 'dst' in fields and fields['dst'] not in mounted,'canonical unique bind mount required')
        mounted[fields['dst']]=fields['src']
    need(set(mounted)=={'/work/repo','/out',pins.SDK_PATH},'no weight/dependency mounts permitted')
    from scripts.run_recorded_worker_canary import canary_command
    expected=canary_command(container['name'],Path(mounted['/work/repo']),Path(mounted[pins.SDK_PATH]),
        Path(mounted['/out']),['--source',auth['source'],'--activation',auth['activation'],'--run-id',auth['run_id'],
            '--approval',request['approval_sha']],
        owner=command['ownership_label'])
    need(argv==expected,'exact sealed no-model command/resource/environment required')
    need(container.get('name')=='recorded-camera-canary-'+auth['run_id'] and
         container.get('image')==pins.IMAGE and container.get('id')==execution.get('container_id') and
         isinstance(container.get('id'),str) and len(container['id'])==64 and
         all(v in '0123456789abcdef' for v in container['id']) and top.get('container_hostname')==container['id'][:12] and
         command.get('ownership_label')==container.get('ownership_label') and
         container.get('effective_limits')==dict(Memory=10*1024**3,MemorySwap=10*1024**3,NanoCpus=2_000_000_000,
             PidsLimit=128,ReadonlyRootfs=True,NetworkMode='none',IpcMode='private'),'immutable owned container/resources required')
    state=execution.get('stopped_state') or {}
    need(all(k in execution for k in ('returncode','failure','status','create_attempted','start_attempted','owned_container_removed',
             'ownership_unresolved','cleanup_failure','stopped_state','container_id')) and
         type(execution.get('returncode')) is int and execution['returncode']==0 and
         execution.get('failure') is None and execution.get('status')=='EXIT_OBSERVED' and
         execution.get('create_attempted') is True and execution.get('start_attempted') is True and
         execution.get('owned_container_removed') is True and execution.get('ownership_unresolved') is False and
         execution.get('cleanup_failure') is None and state.get('Running') is False and state.get('Pid')==0 and
         state.get('OOMKilled') is False and state.get('ExitCode')==0,'complete owned container stop/removal required')
    handoff=_read_receipt(root/'evidence-handoff.json')
    need(handoff.get('protocol')=='recorded-worker-evidence-handoff-v1' and handoff.get('status')=='EVIDENCE_HANDED_TO_RUNNER' and
         handoff.get('native_dir')==mounted['/out'] and type(handoff.get('uid')) is int and handoff['uid']>0 and handoff['uid']!=65534 and
         type(handoff.get('gid')) is int and handoff['gid']>=0 and handoff.get('writer_uid')==handoff.get('writer_gid')==65534 and
         handoff.get('symlinks_followed') is False and handoff.get('container_removed') is True and handoff.get('argv')==
         ['sudo','-n','chown','-R','--no-dereference','--from=65534:65534',str(handoff['uid'])+':'+str(handoff['gid']),'--',mounted['/out']],
         'stopped evidence ownership handoff required')
    return dict(verified,protocol='recorded-camera-canary-receiver-v1',camera_recorder_canary_passed=True,
        actual_source_rgb_pairs=2,actual_sensor_perceives=4,official_model_processes=0,official_inferences=0,
        source=auth['source'],activation=auth['activation'],run_id=auth['run_id'],driver=driver,
        source_map_sha256=source_hash,container_id=container['id'])



from .recorded_worker_archive import extract_archive
