"""Complete new callback case replay; frozen clock validator helpers retained."""
from scripts import engine_clock_native as legacy
from scripts import renderer_pipeline_sealed_v1 as n
from scripts.engine_clock_native import (_fields,_same,_positive,_hex,_fail,_duration,_members,_sha,
    capture,clock,np,math,CAMERAS,POSES,CLAIMS,PAYLOAD_CAP,JSON_CAP,LOG_CAP,CHILD_S)

CASE_SCHEMA='renderer-pipeline-case-v1'
SCHEDULES={mode:n.schedule(mode) for mode in ('canary','abba')}
PROTOCOL=dict(legacy.PROTOCOL,schedule={k:[list(r) for r in v] for k,v in SCHEDULES.items()},
    callback_schedule={k:n.callback_schedule(k) for k in SCHEDULES},callback_trace_bytes=256*1024,
    callback_snapshots_per_on_case=48,callback_named_getters_per_snapshot=35,pipeline_trace_bytes=512*1024,
    submission_snapshots_per_on_case=24,submission_named_getters_per_snapshot=32,pipeline_events_per_on_case=168)
LIMITATION=legacy.LIMITATION+' Callback pose/MVP observations are non-atomic and intrusive, not GPU cause or neutral observer proof. Submitted source locals are CPU data; render dispatch return is not GPU completion.'

def __getattr__(name):
    return getattr(legacy,name)

def _validate_case(root,data,launch,binding):
    _fields(data,{'schema','status','phase','index','clock_enabled','callback_enabled','callback_trace','callback_reader_counts','pipeline_enabled','pipeline_trace','submission_reader_counts','repeat','nonce','parent_pid','parent_uuid',
        'process_id','process_uuid','process_group','context','source_snapshot','runtime','request_sha256',
        'protocol','claims','limitation','provider_attempted','provider_constructed','provider_closed',
        'provider_lower_bound','provider_upper_bound','texture_markers_enabled','main_thread_id','clock_trace','markers','capture_rows','accepted','capture_count',
        'observed_reads','marker_reads','retained_payload_bytes','payload_charged_bytes','error','cleanup_errors'})
    phase=binding['phase'];index=launch['index'];enabled,repeat=SCHEDULES[phase][index]
    expected=dict(schema=CASE_SCHEMA,status='RENDERER_PIPELINE_CAMERA_REPLAY_RECORDED',phase=phase,index=index,clock_enabled=enabled,repeat=repeat,
                  nonce=launch['nonce'],parent_pid=binding['parent_pid'],parent_uuid=binding['parent_uuid'],
                  process_group=launch['process_group'],context=binding['context'],source_snapshot=binding['source_snapshot'],
                  runtime=binding['runtime'],request_sha256=binding['request_sha256'],protocol=PROTOCOL,claims=CLAIMS,
                  limitation=LIMITATION,provider_attempted=True,provider_constructed=True,provider_closed=True,
                  provider_lower_bound=1,provider_upper_bound=1,capture_count=6,observed_reads=12,
                  marker_reads=24,texture_markers_enabled=True,error=None,cleanup_errors=[])
    for key,value in expected.items():_same(data[key],value)
    if not _positive(data['process_id']) or data['process_id'] in (data['parent_pid'],launch['launcher_pid']) or not _hex(data['process_uuid'],32):_fail('child identity invalid')
    if (type(data['retained_payload_bytes']) is not int or data['retained_payload_bytes']!=6*(capture.RAW_PAIR_BYTES+capture.CANVAS_PAIR_BYTES+capture.PACKED_BYTES) or
        type(data['payload_charged_bytes']) is not int or not 0<data['payload_charged_bytes']<=PAYLOAD_CAP):_fail('retention/storage bounds invalid')
    n.validate_callback_metadata(data)
    trace=data['clock_trace']
    try:clock.validate_clock_trace(trace)
    except clock.ClockObserverError as exc:raise ValueError('invalid bound clock trace') from exc
    _same(trace['max_pairs'],6);_same(trace['enabled'],enabled)
    if type(data['main_thread_id']) is not int or data['main_thread_id']<=0 or trace['owner_thread']!=data['main_thread_id']:_fail('clock/main-thread association mismatch')
    markers=data['markers'];attempts=data['capture_rows'];accepted=data['accepted']
    if any(type(v) is not list for v in (markers,attempts,accepted)) or (len(markers),len(attempts),len(accepted))!=(12,6,6):_fail('exact replay counts required')
    for i,row in enumerate(markers):
        _fields(row,{'call','camera','before','after','equal','raw_sha256','status','copy_attempted','copy_returned','copy_wall_s','wrapper_wall_s'})
        _same(row['call'],i+1);_same(row['camera'],CAMERAS[i%2]);_same(row['status'],'RETURNED')
        _same(row['copy_attempted'],True);_same(row['copy_returned'],True)
        _same((trace['calls'][i]['call'],trace['calls'][i]['camera']),(row['call'],row['camera']))
        if not _hex(row['raw_sha256'],64):_fail('marker raw SHA invalid')
        for key in ('copy_wall_s','wrapper_wall_s'):_duration(row[key],CHILD_S)
        if row['copy_wall_s']>row['wrapper_wall_s']:_fail('copy duration exceeds wrapper')
        if any(type(row[k]) is not int or not -(2**31)<=row[k]<2**31 for k in ('before','after')):_fail('signed generation integers required')
        _same(row['equal'],row['before']==row['after'])
    registered={'case.json','process.log'};payload_bytes=0
    def member(desc,name,image):
        nonlocal payload_bytes
        _fields(desc,{'path','nbytes','sha256','rgb_sha256'} if image else {'path','nbytes','sha256','actual_input_sha256','association'})
        if desc['path']!=name or name in registered or not _hex(desc['sha256'],64) or not _positive(desc['nbytes']):_fail('invalid payload descriptor/path')
        path=capture._safe_path(root,name)
        if not path.is_file() or path.stat().st_size!=desc['nbytes'] or desc['nbytes']>8*1024*1024:_fail('payload size mismatch')
        payload_bytes+=desc['nbytes']
        if payload_bytes>PAYLOAD_CAP:_fail('payload byte cap')
        raw=path.read_bytes()
        if _sha(raw)!=desc['sha256']:_fail('payload SHA mismatch')
        registered.add(name)
        return path
    for i,(attempt,row,pose) in enumerate(zip(attempts,accepted,POSES),1):
        _fields(attempt,{'capture_index','status','pose','raw_sha256','canvas_sha256','capture_wrapper_wall_s',
                        'capture_inclusive_wall_s','wrapper_observer_arithmetic_wall_s','raw_callback_nested_wall_s','accept_observation_wall_s'})
        _same(attempt['capture_index'],i);_same(attempt['status'],'RETURNED');_same(attempt['pose'],pose)
        for key in ('raw_sha256','canvas_sha256'):capture._hash_pair(attempt[key])
        for key in ('capture_wrapper_wall_s','capture_inclusive_wall_s','wrapper_observer_arithmetic_wall_s','raw_callback_nested_wall_s','accept_observation_wall_s'):_duration(attempt[key],CHILD_S)
        if (attempt['raw_callback_nested_wall_s']>attempt['capture_inclusive_wall_s'] or
            attempt['capture_inclusive_wall_s']>attempt['capture_wrapper_wall_s'] or
            not math.isclose(attempt['wrapper_observer_arithmetic_wall_s'],attempt['capture_wrapper_wall_s']-attempt['capture_inclusive_wall_s'],rel_tol=1e-9,abs_tol=1e-12)):_fail('capture wall association mismatch')
        _fields(row,{'accepted_index','capture_index','observation','intrinsics','raw','canvas','packed'})
        _same(row['accepted_index'],i);_same(row['capture_index'],i)
        _same(row['observation'],dict(speed_mps=8.,time_s=pose['t']))
        for key in ('raw','canvas','intrinsics'):_fields(row[key],CAMERAS)
        raw={};canvas={};intrinsics={}
        for j,kind in enumerate(CAMERAS):
            _fields(row['intrinsics'][kind],{'width','height','fx','fy','cx','cy'})
            iv=row['intrinsics'][kind]
            if (type(iv['width']) is not int or type(iv['height']) is not int or
                any(not capture._number(iv[k]) for k in ('fx','fy','cx','cy'))):_fail('typed finite intrinsics required')
            intrinsics[kind]=capture.PinholeIntrinsics(**iv)
            for boundary,w,h,target in (('raw',964,604,raw),('canvas',512,256,canvas)):
                desc=row[boundary][kind]
                frame=capture._read_png(member(desc,f'capture_{i:02d}/{boundary}_{kind}.png',True),w,h)
                if frame.sha256!=desc['rgb_sha256']:_fail('decoded RGB SHA mismatch')
                target[kind]=frame
            if (raw[kind].sha256!=attempt['raw_sha256'][kind] or raw[kind].sha256!=markers[2*(i-1)+j]['raw_sha256'] or
                canvas[kind].sha256!=attempt['canvas_sha256'][kind]):_fail('wrapper/capture/accepted raw association mismatch')
        reproduced,_=capture.PinholeRectifier().rectify_pair(
            np.frombuffer(raw['road'].rgb,np.uint8).reshape(capture.RAW_SHAPE),
            np.frombuffer(raw['wide'].rgb,np.uint8).reshape(capture.RAW_SHAPE),
            road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
        if any(getattr(reproduced,k).rgb!=canvas[k].rgb for k in CAMERAS):_fail('offline raw-to-canvas reconstruction mismatch')
        packed=row['packed'];path=member(packed,f'capture_{i:02d}/packed_i420.bin',False)
        if (packed['actual_input_sha256'] is not None or packed['association']!='DERIVED_ONLY_NO_MODEL_CALL' or
            packed['nbytes']!=capture.PACKED_BYTES or path.read_bytes()!=capture.camera_pair_to_model(canvas['road'],canvas['wide']).tobytes()):_fail('offline I420 reconstruction/association mismatch')
    if data['payload_charged_bytes']<payload_bytes:_fail('payload reservation below written bytes')
    members,_=_members(root,PAYLOAD_CAP+JSON_CAP+LOG_CAP)
    if members!=registered:_fail('unregistered/missing case members')
    return data

def _comparisons(cases):
    result=legacy._comparisons(cases)
    for row in result:
        a,b=(cases[row[k]] for k in ('left','right'))
        la,lb=a['callback_enabled'],b['callback_enabled']
        row['clock_observed']=a['clock_enabled'] and b['clock_enabled']
        row['callback_comparison_kind']=('ON/ON' if la else 'OFF/OFF') if la==lb else 'OFF/ON'
        row['callback_states_equal']=None;row['callback_orders_equal']=None
        if la and lb:
            left=a['callback_trace']['steps'];right=b['callback_trace']['steps']
            row['callback_orders_equal']=[[e['callback'] for e in s['events']] for s in left]==[[e['callback'] for e in s['events']] for s in right]
            row['callback_states_equal']=[[e['state'] for e in s['events']] for s in left]==[[e['state'] for e in s['events']] for s in right]
    for row in result:
        a,b=(cases[row[k]] for k in ('left','right'))
        row['pipeline_orders_equal']=None;row['submitted_cpu_matrices_equal']=None
        if a['pipeline_enabled'] and b['pipeline_enabled']:
            traces=[x['pipeline_trace']['steps'] for x in (a,b)]
            row['pipeline_orders_equal']=[[(e['event'],e['callback']) for e in s['events']+s['ram_events']] for s in traces[0]]==[[(e['event'],e['callback']) for e in s['events']+s['ram_events']] for s in traces[1]]
            row['submitted_cpu_matrices_equal']=[[e['state'] for e in s['events'] if e['callback']=='shader_inputs'] for s in traces[0]]==[[e['state'] for e in s['events'] if e['callback']=='shader_inputs'] for s in traces[1]]
    return result
