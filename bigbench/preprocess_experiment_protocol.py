"""Fresh sealed eight-arm experiment. Portable metadata/CPU verification only."""
from pathlib import Path
import hashlib,json,os
from . import recorded_official_execution as base
from .full_s_recorded_worker import need,_read_receipt,_receipt_bytes
from .recorded_worker_canary import check_source_map,QUALIFIED_PROBE,STAT_FIELDS

ROOT=Path(__file__).resolve().parents[1]
MODE='EXPERIMENTAL_RGB_DERIVED_YUV_AB'
CASE=(20261109,'s_curve_left_right')
TRIALS=tuple((seed,scene,variant) for seed in (20261109,20261110)
    for scene in ('s_curve_left_right','s_curve_right_left')
    for variant in ('rgb_linear','source_yuv_nearest_even'))
REQUEST='docs/requests/preprocess-experiment-20261120-01.json'
BRANCH='diagnostic/preprocess-experiment-20261120-01'
WORKFLOW='.github/workflows/preprocess-experiment.yml'
APPROVAL_BRANCH='approval/preprocess-experiment-20261120-01'
APPROVAL_PATH='docs/approvals/preprocess-experiment-20261120-01.json'
RUNTIME=base.RUNTIME
LIMITS=dict(base.LIMITS,official_models=8,official_inferences=4800,trials=[list(t) for t in TRIALS])
FALSE_FLAGS=base.FALSE_FLAGS
MODEL_SHA='35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'
TRIAL_PROTOCOL='preprocess-intervention-native-v1'
POLICY_SCOPE='EXPERIMENTAL_INPUT_INTERVENTION_REAL_ONNX_NOT_BASELINE_CLASS'
clone=base.clone
model_memory_gate=base.model_memory_gate
validate_public_activity=base.validate_public_activity
finalize_preserving_primary=base.finalize_preserving_primary


def validate_trial(seed,scene,variant):
    need(type(seed) is int and (seed,scene,variant) in TRIALS,'registered experimental arm required')


def read_native_ack(path):
    root=Path(path).parent
    launch=_read_receipt(root/'launch.json');native=_read_receipt(root/'native-child.json')
    validate_trial(launch.get('seed'),launch.get('scenario'),launch.get('variant'))
    need(launch.get('mode')==MODE and launch.get('limits')==LIMITS and launch.get('parent_pid')==os.getppid(),
         'sealed experimental parent and cohort required')
    need(native.get('spawn_attempted') is True and native.get('returncode') is None and
         native.get('server_returncode') is None and 'pid' in native,'live owned child acknowledgement required')
    pid=native['pid'];need(pid is None or type(pid) is int and pid==os.getpid(),'actual child identity required')
    return dict(launch,pid=pid,spawn_succeeded=True if pid is not None else None,child_reaped=False,returncode=None)


def validate_trial_receipt(r):
    validate_trial(r.get('seed'),r.get('scenario'),r.get('variant'))
    need(r.get('protocol')==TRIAL_PROTOCOL and r.get('status')=='RETURNED' and
         type(r.get('pid')) is int and r['pid']>1 and type(r.get('parent_pid')) is int and r['parent_pid']>0 and r['pid']!=r['parent_pid'] and
         all(isinstance(r.get(k),str) and len(r[k])==n and all(x in '0123456789abcdef' for x in r[k])
             for k,n in (('nonce',32),('source',40),('activation',40),('approval',40))) and
         isinstance(r.get('run_id'),str) and r['run_id'].isdecimal(),'typed admitted native identity required')
    need(r.get('real_session') is True and r.get('injected_session') is False and
         r.get('providers')==['CPUExecutionProvider'] and r.get('ort_version')=='1.20.1' and
         r.get('provider_closed') is True and r.get('model_process_bounds')==[1,1],
         'original real ORT CPU session and closed provider required')
    t=r.get('trajectory',{});n=t.get('completed_steps');bounds=r.get('inference_bounds')
    need(type(n) is int and 1<=n<=600 and bounds==[n,n] and t.get('actual_inference_bounds')==bounds and
         t.get('protocol')=='full-s-closed-loop-v1' and t.get('trial_completed') is True and
         t.get('model_sha256')==MODEL_SHA and t.get('model_test_double') is False and
         t.get('injected_session') is False and t.get('ground_truth_control_used') is False,
         'complete actual bounded original-model trajectory required')
    need(t.get('experimental_policy_scope')==POLICY_SCOPE and t.get('input_variant')==r['variant'] and
         t.get('initial_recurrent_sha256')==r.get('initial_recurrent_sha256') and
         isinstance(r.get('initial_recurrent_sha256'),str) and len(r['initial_recurrent_sha256'])==64,
         'explicit experimental class/input scope and actual reset state required')
    inputs=r.get('input_rows');frames=t.get('frames')
    need(isinstance(inputs,list) and isinstance(frames,list) and len(inputs)==len(frames)==n,
         'one tensor audit per committed inference required')
    need(inputs[0].get('initial_recurrent_sha256')==r['initial_recurrent_sha256'],'first actual feed must bind the observed reset state')
    for index,(i,f) in enumerate(zip(inputs,frames),1):
        need(i.get('step')==f.get('step')==index and i.get('actual_tensor_sha256')==f.get('new_img_sha256') and
             isinstance(i.get('actual_tensor_sha256'),str) and len(i['actual_tensor_sha256'])==64,
             'prepared/actual feed hash binding required')
    return dict(variant=r['variant'],steps=n,outcome=t.get('outcome'),traversal_passed=t.get('traversal_passed'))


def verify_native(folder,auth,trial,dependency_sha):
    """Complete receipts only. Partial files remain preserved without a PASS."""
    from scripts import panda_sdk3_runtime as p
    from .full_s_receipts import validate_trajectory
    from . import recorded_official_dependencies as deps
    folder=Path(folder);r=_read_receipt(folder/'report.json',16*1024**2)
    result=validate_trial_receipt(r)
    need(tuple(r[k] for k in ('seed','scenario','variant'))==trial,'ordered arm identity required')
    need(all(r[k]==auth[k] for k in ('source','activation','run_id')) and
         r['approval']==auth['request']['approval_sha'] and r.get('dependencies_sha256')==dependency_sha,
         'source/approval/run/dependency identity required')
    need(r.get('source_map_sha256')==check_source_map(ROOT,auth['request']['source_map']),
         'complete native runnable source binding required')
    need(r.get('core_sha256')==p.CORE_SHA and r.get('sdk_sha256')==p.SDK_SHA and
         r.get('load_order')=='core-first' and r.get('model_sha256')==MODEL_SHA and
         r.get('model_nbytes')==768750198,'actual original core/SDK/model bytes required')
    descriptor=_read_receipt(folder/'model-dependencies.json',4*1024**2)
    need(hashlib.sha256(_receipt_bytes(folder/'model-dependencies.json',4*1024**2)).hexdigest()==dependency_sha and
         r.get('dependencies')==dict(versions=deps.VERSIONS,
             declaration_sha256=deps.DECLARATION_SHA,file_count=len(descriptor['files'])),
         'mounted dependency bytes and descriptor required')
    m=r.get('model_memory',{})
    need(m==model_memory_gate(m.get('host_available_bytes'),m.get('cgroup_limit_bytes'),m.get('cgroup_current_bytes')),
         'preconstructor 8GiB available model RAM required')
    for key in ('source_stats_before','source_stats_after'):
        s=r.get(key,{})
        need(type(s.get('returned')) is int and s['returned']==0 and s.get('guards_ok') is True and
             s.get('values')=={k:0 for k in STAT_FIELDS},'default-off native instrumentation required')
    need(all(r.get(k) is False for k in FALSE_FLAGS) and not r.get('failure') and not r.get('secondary_errors'),
         'unqualified experimental scope and no hidden failures required')
    need(r['trajectory'].get('process_id')==r['pid'],'trajectory and admitted actual process must agree')
    validate_trajectory(r['trajectory'],trial[0],trial[1])
    need(r.get('driver')==base.qualified_geometry()['driver'],'same qualified software renderer context required')
    fixture=_read_receipt(ROOT/'docs/fixtures/sdk3-full-s-native-route-v1.json',4*1024**2)
    expected=next(x['geometry'] for x in fixture['cases'] if (x['seed'],x['scenario'])==trial[:2])
    need(r['trajectory']['geometry']==expected,'unchanged independently registered native geometry required')
    verify_input_records(folder,r)
    container=_read_receipt(folder/'container.json');execution=_read_receipt(folder/'execution.json')
    command=_read_receipt(folder/'command.json');native=_read_receipt(folder/'native-child.json')
    completion=_read_receipt(folder/'parent-completion.json');launch=_read_receipt(folder/'launch.json')
    bind_owner(r,launch,native,completion)
    need(container.get('image')==p.IMAGE and container.get('ownership_label')==command.get('ownership_label') and
         container.get('id')==execution.get('container_id') and r.get('container_hostname')==container['id'][:12] and
         container.get('effective_limits')==dict(Memory=10*1024**3,MemorySwap=10*1024**3,NanoCpus=2_000_000_000,
             PidsLimit=128,ReadonlyRootfs=True,NetworkMode='none',IpcMode='private'),'immutable owned bounded container required')
    state=execution.get('stopped_state') or {}
    need(execution.get('returncode')==0 and execution.get('owned_container_removed') is True and
         execution.get('failure') is None and execution.get('cleanup_failure') is None and
         state.get('Running') is False and state.get('Pid')==0 and state.get('OOMKilled') is False,
         'successful reaped non-OOM container and completed cleanup required')
    need(native.get('pid')==r['pid'] and native.get('returncode')==native.get('server_returncode')==0 and
         r.get('child_finalized_before_server_stop') is True and not native.get('failure') and
         completion.get('returncode')==0 and completion.get('parent_pid')==r['parent_pid'] and
         completion.get('nonce')==r['nonce'] and completion.get('report_sha256')==p.digest(folder/'report.json') and
         completion.get('native_child_sha256')==p.digest(folder/'native-child.json') and
         launch.get('parent_pid')==r['parent_pid'] and launch.get('nonce')==r['nonce'],
         'live parent/child/display/terminal bytes required')
    verify_command(folder,auth,trial,dependency_sha,container,command)
    return result


def verify_command(folder,auth,trial,dep_sha,container,command):
    from scripts import run_preprocess_experiment as host,panda_sdk3_runtime as pins
    argv=command.get('argv');need(isinstance(argv,list),'actual container command required')
    mounted={}
    for i,x in enumerate(argv):
        if x!='--mount':continue
        fields=dict(part.split('=',1) if '=' in part else (part,'') for part in argv[i+1].split(','))
        need(fields.get('type')=='bind' and 'src' in fields and 'dst' in fields and fields['dst'] not in mounted,
            'unique explicit bind mounts required')
        mounted[fields['dst']]=fields['src']
    need(set(mounted)=={'/work/repo','/out',pins.SDK_PATH,'/model.onnx','/model-deps'},'exact original mounts required')
    name='preprocess-'+auth['run_id']+'-'+str(TRIALS.index(trial))
    need(container.get('name')==name,'ordered owned container name required')
    args=['--source',auth['source'],'--activation',auth['activation'],'--run-id',auth['run_id'],
        '--approval',auth['request']['approval_sha'],'--dependencies-sha256',dep_sha,
        '--seed',str(trial[0]),'--scenario',trial[1],'--variant',trial[2]]
    expected=host.official_command(name,Path(mounted['/work/repo']),Path(mounted[pins.SDK_PATH]),
        Path(mounted['/out']),args,owner=command['ownership_label'],model=Path(mounted['/model.onnx']),deps=Path(mounted['/model-deps']))
    need(argv==expected,'exact immutable bounded source/model/dependency/variant command required')
    handoff=_read_receipt(Path(folder)/'evidence-handoff.json')
    need(handoff.get('status')=='EVIDENCE_HANDED_TO_RUNNER' and handoff.get('container_removed') is True and
        handoff.get('writer_uid')==handoff.get('writer_gid')==65534 and handoff.get('symlinks_followed') is False and
        handoff.get('native_dir')==mounted['/out'] and type(handoff.get('uid')) is int and handoff['uid']>0 and handoff['uid']!=65534,
        'stopped owned writer handoff required')


def verify_input_records(folder,r):
    import numpy as np
    from .optical_calibration import PinholeIntrinsics,PinholeRectifier
    from .image_adapter import camera_pair_to_model
    from .preprocess_experiment import LiveInput
    from types import SimpleNamespace
    from tempfile import TemporaryDirectory
    folder=Path(folder);rows=r['input_rows'];frames=r['trajectory']['frames']
    for row,frame in zip(rows,frames):
        need(row.get('source_sha256')=={role:frame['source_'+role+'_rgb_sha256'] for role in ('road','wide')} and
            row.get('canvas_sha256')==[frame['road_frame_sha256'],frame['wide_frame_sha256']],
            'actual capture/source/canvas hashes must bind each committed input')
        if r['variant']=='rgb_linear':need(row.get('baseline_tensor_sha256')==row['actual_tensor_sha256'],'baseline input must remain unchanged')
    images={role:np.frombuffer(_receipt_bytes(folder/('first-'+role+'.rgb'),2*1024**2),np.uint8).reshape(604,964,3)
        for role in ('road','wide')}
    hashes={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in images.items()}
    need(hashes==rows[0]['source_sha256'],'saved first actual source bytes required')
    intrinsics={role:PinholeIntrinsics(**r['intrinsics'][role]) for role in images}
    pair,_=PinholeRectifier().rectify_pair(images['road'],images['wide'],road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
    need([pair.road.sha256,pair.wide.sha256]==rows[0]['canvas_sha256'],'first source/measured-lens/canvas reconstruction required')
    baseline=camera_pair_to_model(pair.road,pair.wide).tobytes()
    need(_receipt_bytes(folder/'first-baseline.bin',400000)==baseline,'byte-exact baseline input required')
    with TemporaryDirectory() as tmp:
        camera=SimpleNamespace(last_source_rgb_sha256=hashes)
        live=LiveInput(camera,intrinsics,r['variant'],tmp)
        live.record_native_rgb(images,hashes);live.expected=(pair.road.sha256,pair.wide.sha256)
        expected=live.prepare(pair.road,pair.wide).tobytes()
    actual=_receipt_bytes(folder/'first-input.bin',400000)
    need(actual==expected and hashlib.sha256(actual).hexdigest()==rows[0]['actual_tensor_sha256'],
        'first real ORT tensor bytes independently recomputed from captured RGB and measured lenses')


def resource_gate(snapshot):
    need(isinstance(snapshot,dict) and type(snapshot.get('memory_available_bytes')) is int and
         snapshot['memory_available_bytes']>=12*1024**3 and type(snapshot.get('disk_free_bytes')) is int and
         snapshot['disk_free_bytes']>=1024**3,'12GiB available host RAM and 1GiB post-staging disk required before each arm')
    return dict(snapshot,admitted=True,minimum_host_ram_bytes=12*1024**3,minimum_post_staging_disk_bytes=1024**3)


def pair_eligibility(a,b):
    reasons=[]
    for key in ('seed','scenario','intrinsics','initial_recurrent_sha256'):
        if a.get(key)!=b.get(key):reasons.append(key+' differs')
    if (a.get('variant'),b.get('variant'))!=('rgb_linear','source_yuv_nearest_even'):reasons.append('arm order differs')
    for key in ('nonce','container_hostname'):
        if not a.get(key) or a.get(key)==b.get(key):reasons.append(key+' not fresh')
    ta,tb=a.get('trajectory',{}),b.get('trajectory',{})
    for key in ('initial_state','geometry'):
        if ta.get(key)!=tb.get(key):reasons.append(key+' differs')
    if not ta.get('process_uuid') or ta.get('process_uuid')==tb.get('process_uuid'):reasons.append('episode UUID not fresh')
    ia=(a.get('input_rows') or [{}])[0];ib=(b.get('input_rows') or [{}])[0]
    for key in ('source_sha256','canvas_sha256','baseline_tensor_sha256','initial_recurrent_sha256'):
        if ia.get(key)!=ib.get(key) or ia.get(key) is None:reasons.append('first '+key+' differs/absent')
    if ia.get('initial_recurrent_sha256')!=a.get('initial_recurrent_sha256') or ib.get('initial_recurrent_sha256')!=b.get('initial_recurrent_sha256'):
        reasons.append('initial state/feed not bound')
    return dict(protocol='preprocess-pair-eligibility-v1',seed=a.get('seed'),scenario=a.get('scenario'),
        eligible=not reasons,reasons=reasons,scope='Combined preprocessing intervention; no sensor NV12, GPU parity, quality ranking or new-variant repeatability proof')


def pairing_verdicts(root):
    result=[]
    for i in range(0,8,2):
        a=_read_receipt(Path(root)/f'trial-{i}/native/report.json',16*1024**2)
        b=_read_receipt(Path(root)/f'trial-{i+1}/native/report.json',16*1024**2)
        result.append(pair_eligibility(a,b))
    return result


def partial_activity(folder,identity,execution):
    """Retain uncertainty unless bounded actual progress binds the owned child."""
    fallback=dict(model_process_bounds=[0,1],inference_bounds=[0,600],primary_error=None,secondary_errors=[],linked=False)
    if execution.get('start_attempted') is False:
        fallback.update(model_process_bounds=[0,0],inference_bounds=[0,0])
    try:
        folder=Path(folder);launch=_read_receipt(folder/'launch.json');native=_read_receipt(folder/'native-child.json')
        value=None
        for name in ('report.json','progress.json'):
            try:value=_read_receipt(folder/name,16*1024**2);break
            except FileNotFoundError:continue
        if value is None:return fallback
        need(value.get('protocol')==TRIAL_PROTOCOL and all(value.get(k)==v and launch.get(k)==v for k,v in identity.items()) and
             value.get('pid')==native.get('pid') and type(value.get('pid')) is int and value['pid']>1 and
             value.get('parent_pid')==launch.get('parent_pid') and type(value['parent_pid']) is int and value['parent_pid']>0 and
             value.get('nonce')==launch.get('nonce') and isinstance(value.get('nonce'),str) and len(value['nonce'])==32,
             'linked partial progress identity required')
        models=value.get('model_process_bounds');bounds=value.get('inference_bounds')
        need(models in ([0,0],[0,1],[1,1]) and all(type(x) is int for x in models) and
             isinstance(bounds,list) and len(bounds)==2 and all(type(x) is int for x in bounds) and
             0<=bounds[0]<=bounds[1]<=600 and bounds[1]-bounds[0]<=1 and (models==[1,1] or bounds==[0,0]),
             'typed linked partial activity required')
        if execution.get('ownership_unresolved') is True:
            bounds=[bounds[0],600]
        return dict(model_process_bounds=models,inference_bounds=bounds,primary_error=value.get('trajectory',{}).get('error') or value.get('failure'),
            secondary_errors=value.get('secondary_errors',[]),linked=True)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        fallback['secondary_errors'].append('Partial progress unavailable: '+str(exc)[:1024])
        return fallback


def verify_bundle(root):
    """Offline retained-source/cohort verifier; artifact origin is external."""
    from scripts import run_preprocess_experiment as host
    root=Path(root);auth=_read_receipt(root/'authentication.json',4*1024**2)
    def admission(value):
        result=host.validate_admission(value['request'],value['context'],manifest=host.source_manifest(value['source']),
            ci=value['source_ci'],authority=value['authority'],current=value['current_identity'],history=value['history'])
        need(all(result[k]==auth[k] for k in ('request','source','activation','run_id','context','current_identity','history')),
            'same immutable retained source/activation authority required')
    admission(auth)
    from .full_s_failure_capture import _decode
    ledger=_decode(_receipt_bytes(root/'trial-ledger.json',4*1024**2))
    need(isinstance(ledger,list) and len(ledger)<=8,'bounded serial cohort ledger required')
    verdicts=[]
    dep=hashlib.sha256(_receipt_bytes(root/'model-dependencies.json',4*1024**2)).hexdigest() if (root/'model-dependencies.json').exists() else None
    for index,row in enumerate(ledger):
        trial=TRIALS[index]
        need(row.get('index')==index and row.get('trial')==list(trial),'exact ordered arm ledger required')
        admission(_read_receipt(root/f'authentication-trial-{index}.json',4*1024**2))
        pages=_read_receipt(root/f'public-activity-trial-{index}.json',4*1024**2)['pages']
        validate_public_activity(pages,current_id=int(auth['run_id']))
        resource_gate(_read_receipt(root/f'resources-trial-{index}.json'))
        if row.get('status')=='COMPLETE_DIAGNOSTIC':
            verdict=verify_native(root/f'trial-{index}/native',auth,trial,dep)
            need(row.get('model_process_bounds')==[1,1] and row.get('inference_bounds')==[verdict['steps']]*2,
                'cohort and verified actual arm accounting must agree')
            verdicts.append(dict(index=index,status='COMPLETE_DIAGNOSTIC',**verdict))
        else:
            identity=dict(seed=trial[0],scenario=trial[1],variant=trial[2],source=auth['source'],activation=auth['activation'],run_id=auth['run_id'],approval=auth['request']['approval_sha'])
            verdicts.append(dict(index=index,status='INCOMPLETE_OR_FAILED',**partial_activity(root/f'trial-{index}/native',identity,row.get('execution',{}))))
    complete=len(verdicts)==8 and all(v['status']=='COMPLETE_DIAGNOSTIC' for v in verdicts)
    pairs=pairing_verdicts(root) if complete else []
    model_bounds=[sum((v.get('model_process_bounds') or [1,1])[i] for v in verdicts) for i in (0,1)]
    call_bounds=[sum((v.get('inference_bounds') or [v.get('steps',0)]*2)[i] for v in verdicts) for i in (0,1)]
    if complete:
        summary=_read_receipt(root/'summary.json',4*1024**2)
        need(summary.get('status')=='EIGHT_EXPERIMENTAL_TRIALS_RETURNED' and
             summary.get('official_model_process_bounds')==model_bounds and summary.get('official_inference_bounds')==call_bounds,
             'summary must agree with independently recomputed cohort activity')
        recorded_pairs=_decode(_receipt_bytes(root/'pairing.json',4*1024**2))
        need(recorded_pairs==pairs,'retained causal eligibility must match recomputation')
    return dict(protocol='preprocess-retained-bundle-v1',status='EIGHT_EXPERIMENTAL_TRIALS_RETURNED' if complete else 'INCOMPLETE_OR_FAILED',
        source=auth['source'],activation=auth['activation'],run_id=auth['run_id'],trials=verdicts,pairing=pairs,
        official_model_process_bounds=model_bounds,official_inference_bounds=call_bounds,
        artifact_origin_authenticated=False,all_four_validation_tracks_passed=False)


def bind_owner(report,launch,native,completion):
    need(native.get('pid')==report['pid'] and launch.get('parent_pid')==completion.get('parent_pid')==report['parent_pid'] and
         launch.get('nonce')==completion.get('nonce')==report['nonce'],'same live child/parent/nonce required')
    for key in ('seed','scenario','variant','source','activation','approval','run_id','dependencies_sha256'):
        if key in report:
            need(launch.get(key)==completion.get(key)==report[key],'same owned launch/completion '+key+' required')
