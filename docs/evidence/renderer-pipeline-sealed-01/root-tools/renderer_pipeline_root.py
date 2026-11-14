from hashlib import sha256
import json
from pathlib import Path,PurePosixPath
import stat
import subprocess
import zipfile
import renderer_pipeline_control as c
from scripts import renderer_pipeline_sealed_v1 as n

def download(item,path):
    if not path.exists():
        with path.open('xb') as f:subprocess.run(['gh','api',c.PREFIX+f"actions/artifacts/{item['id']}/zip"],cwd=c.ROOT,stdout=f,check=True,timeout=240)
    assert path.stat().st_size==item['size_in_bytes']<=512*n.MIB
    h=sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(n.MIB),b''):h.update(block)
    assert item['digest']=='sha256:'+h.hexdigest()
    return h.hexdigest()

def extract_all(path,dest):
    assert not dest.exists();dest.mkdir();records={};total=0
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();assert 0<len(infos)<=512
        for r in infos:
            name=r.orig_filename;p=PurePosixPath(name);kind=stat.S_IFMT(r.external_attr>>16)
            assert name==r.filename and name not in records and not p.is_absolute() and all(x not in ('','.','..') for x in name.split('/'))
            assert '\\' not in name and not r.is_dir() and not r.flag_bits&1 and kind in (0,stat.S_IFREG)
            assert all(ord(x)>=32 and ord(x)!=127 for x in name) and 0<=r.file_size<=512*n.MIB
            total+=r.file_size;assert total<=1024*n.MIB
            keep=name.startswith('output/') or name.startswith('api/') or name in {'binding/binding.json','consumed-request.json','producer-request.json','controller.json','result.json','source-authentication.json','host-lease.json'}
            target=dest/name
            if keep:target.parent.mkdir(parents=True,exist_ok=True);sink=target.open('xb')
            else:sink=None
            h=sha256();size=0
            try:
                with z.open(r) as source:
                    for block in iter(lambda:source.read(n.MIB),b''):
                        size+=len(block);assert size<=r.file_size;h.update(block)
                        if sink:sink.write(block)
            finally:
                if sink:sink.close()
            assert size==r.file_size;records[name]=dict(nbytes=size,sha256=h.hexdigest(),selected=keep)
    return dict(members=len(records),uncompressed_bytes=total,files=records)

def replay(selected,mode,request):
    from scripts import renderer_pipeline_case as case
    from scripts import renderer_pipeline_sealed_v1_container as container
    read=lambda name:c.read(selected/name)
    phase=read('output/phase.json');binding=read('binding/binding.json');controller=read('controller.json');operation=read('result.json')
    n.validate_binding_requests(binding,n.canonical(c.read(c.ROOT/n.C_REQUEST)),c.ROOT)
    assert n.exact(binding['request'],request) and phase['mode']==mode
    assert phase['status']==controller['status']==operation['status']==n.recorded_status(mode)
    assert phase['identity_verified'] is True and phase['error'] is None
    assert n.exact(phase['context'],binding['context']) and n.exact(controller['context'],binding['context'])
    identity=n.identity_from_profiles(binding['receipt'],request['image_evidence']['expected'],binding['host'],binding['engine'],binding['identity']['host_details'])
    assert n.exact(identity,binding['identity']) and n.exact(identity,phase['identity']) and n.exact(identity,controller['identity'])
    assert phase['binding_sha256']==n.sha((selected/'binding/binding.json').read_bytes())
    assert controller['phase_sha256']==n.sha((selected/'output/phase.json').read_bytes())
    assert controller['state']['Status']=='exited' and controller['state']['Running'] is False and controller['state']['ExitCode']==0 and controller['state']['OOMKilled'] is False
    assert n.exact(phase['budget'],n.BUDGET) and n.exact(phase['native_budget'],n.native_budget(mode))
    cases=[];summaries=[]
    assert len(phase['launches'])==len(n.schedule(mode))
    for i,row in enumerate(phase['launches']):
        assert row['index']==i and row['clock_enabled'] is True and row['error'] is None and row['cleanup_errors']==[]
        assert row['exit_code']==0 and row['reaped'] is True and row['group_gone'] is True
        data=read(f'output/case_{i:02d}/case.json')
        cbinding=dict(phase=mode,parent_pid=phase['parent_pid'],parent_uuid=phase['parent_uuid'],context=phase['context'],source_snapshot=request['source_closure'],runtime=identity,request_sha256=phase['context']['request_sha256'])
        case._validate_case(selected/f'output/case_{i:02d}',data,row,cbinding);cases.append(data)
        counts=n.validate_callback_metadata(data)
        orders=[];mvp=set();poses=set();flags=set()
        if data['callback_enabled']:
            for s in data['callback_trace']['steps']:
                orders.append([e['callback'] for e in s['events'] if e['event']=='call'])
                for e in s['events']:
                    mvp.add(e['state']['mvp_sha256']);poses.add(n.canonical(e['state']['pose']).decode());flags.add(e['state']['chase_run_task'])
        summaries.append(dict(index=i,**counts,orders=orders,mvp_states=len(mvp) if data['callback_enabled'] else None,
            main_camera_pose_states=len(poses) if data['callback_enabled'] else None,chase_run_task_values=sorted(flags) if data['callback_enabled'] else None))
    assert len({d['process_uuid'] for d in cases})==len(cases)
    comparisons=case._comparisons(cases);assert n.exact(comparisons,phase['comparisons'])
    snapshots=[]
    for tag in ['parent']+[f'child-{i:02d}' for i in range(len(cases))]:
        proof=read('output/'+tag+'-admission.json');assert n.exact(proof['identity'],identity) and proof['binding_sha256']==phase['binding_sha256']
        inv=proof['inventory'];assert inv['complete'] is True and inv['status']=='INSTALLED_FILES_MATCH' and inv['canonical_manifest_sha256']==binding['receipt']['installed_files_sha256'] and inv['matched_entries']==44232
        assert proof['prefix']['status']=='PREFIX_LAYOUT_AND_OBSERVATION_MATCH'
        role='parent' if tag=='parent' else 'child';n.check_environment(proof['launch_environment'],role);n.check_post_import_environment(proof['environment'],role)
        for kind,expected in [('host',binding['host']),('identity',identity)]:
            d=read('output/'+tag+'-'+kind+'-comparison.json');assert d['equal'] is True and d['differences']==[] and n.exact(d['observed'],expected)
            assert d['observed_sha256']==d['accepted_sha256']==n.sha(n.canonical(expected))
        snapshots.extend([proof['memory_before'],read('output/'+tag+'-memory-after.json')])
        if role=='child':
            i=int(tag[-2:]);row=phase['launches'][i]
            permit=n.validate_permit(proof['permit'],ancestors=[phase['parent_pid']],group=row['process_group'],nonce=row['nonce'],binding_sha=phase['binding_sha256'],identity_sha=identity['core_sha256'],mode=mode,index=i)
            assert permit['parent_uuid']==phase['parent_uuid']
    for s in snapshots:container.require_no_oom(snapshots[0],s)
    member=n.audit_phase_members(selected/'output',mode);original=phase['member_audit']
    for k,v in member.items():
        if k!='nbytes_before_final_phase_ledger':assert n.exact(original[k],v)
    final=member['nbytes_before_final_phase_ledger'];phasebytes=(selected/'output/phase.json').stat().st_size
    assert final-phasebytes<=original['nbytes_before_final_phase_ledger']<=final
    assert all(r['official_model_calls']==r['ort_sessions']==0 and r['scientific_result_promoted'] is False for r in (phase,controller,operation))
    return dict(phase=phase,identity=identity,cases=cases,case_summaries=summaries,comparisons=comparisons,members=member,memory_records=len(snapshots))

def collect(mode):
    live=c.status();act=c.read(c.BASE/'canary-activation.json')
    if mode=='canary' and live['status']!='completed':assert live['ready_for_root_canary']
    if mode=='abba':assert live['status']=='completed'
    base=c.BASE/mode;base.mkdir(parents=True,exist_ok=True);assert not (base/'root-acceptance.json').exists()
    apidir=base/'api';apidir.mkdir(exist_ok=True)
    for name,key in [('run','run'),('jobs','jobs'),('artifacts','artifact_response')]:c.write(apidir/(name+'.json'),live[key])
    c.write(apidir/'workflow.json',c.api('actions/workflows/'+str(live['workflow_id'])))
    items=live['artifact_response']['artifacts'];item=next(a for a in items if a['name']==n.artifact(mode))
    path=base/(n.artifact(mode)+'.original.zip');digest=download(item,path)
    expected=dict(repository=n.REPOSITORY,event='push',attempt=1,run_id=live['run_id'],workflow_id=live['workflow_id'],job_id=live['host_job_id'],head_sha=act['head_sha'],source_sha=c.SOURCE)
    request=c.read(c.ROOT/(n.C_REQUEST if mode=='canary' else n.A_REQUEST))
    n.verify_sources(c.ROOT,request['source_closure'])
    for name,h in request['source_closure'].items():assert n.sha(subprocess.check_output(['git','show',c.SOURCE+':'+name],cwd=c.ROOT))==h
    if live['status']=='completed' and live['conclusion']!='success':
        audit=extract_all(path,base/'root-selected');c.write(base/'members.json',audit)
        c.write(base/'root-acceptance.json',dict(accepted=False,status='GENUINE_NATIVE_FAILURE_RETAINED',artifact_id=item['id'],artifact_sha256=digest,run_id=live['run_id'],workflow_conclusion=live['conclusion'],fresh_raw_review_accepted=False))
        print(json.dumps(dict(accepted=False,status='GENUINE_NATIVE_FAILURE_RETAINED',path=str(path))));return 1
    if mode=='canary':
        from scripts import renderer_pipeline_sealed_v1_archive as authority
        checked=authority.validate_native_canary_archive(path,base/'root-selected',request,expected,item)
        at=next(a for a in items if a['name']==n.artifact('attestation'));atpath=base/'attestation.original.zip';download(at,atpath)
        attjob=next(j for j in live['jobs']['jobs'] if j['name']=='canary-attestor')
        assert attjob['status']=='completed' and attjob['conclusion']=='success'
        with zipfile.ZipFile(atpath) as z:
            assert z.namelist()==['canary-attestation.json'];receipt=json.loads(z.read(z.infolist()[0]))
        assert n.exact(receipt,authority.attestation_record(checked,attjob['id']))
        c.write(base/'attestation.json',receipt);audit=checked['archive'];c.write(base/'metadata-acceptance.json',checked)
    else:
        audit=extract_all(path,base/'root-selected')
    selected=base/'root-selected';verified=replay(selected,mode,request);phase=verified['phase']
    for k,v in expected.items():assert n.exact(phase['context'][k],v)
    if mode=='abba':
        original=c.read(c.BASE/'canary/root-acceptance.json');assert n.exact(original['identity'],verified['identity'])
        a=c.read(c.BASE/'abba-activation.json');assert phase['context']['control_head_sha']==a['control_head_sha'] and phase['context']['producer_head_sha']==act['head_sha']
        assert len(verified['cases'])==4
    for name,desc in zip(('copied-code','copied-python','copied-executable'),c.read(selected/'controller.json')['copied_trees']):
        meta=audit['files']['docker/'+name+'.tar'];assert meta['sha256']==desc['archive_sha256'] and meta['nbytes']==desc['archive_nbytes']
    c.write(base/'members.json',audit)
    result=dict(status='ROOT_ORIGINAL_PIPELINE_CAMERA_REPLAY_ACCEPTED',accepted=True,phase=mode,source_sha=c.SOURCE,producer_head_sha=act['head_sha'],run_id=live['run_id'],workflow_id=live['workflow_id'],job_id=live['host_job_id'],artifact_id=item['id'],artifact_sha256=digest,artifact_nbytes=path.stat().st_size,
        identity=verified['identity'],lease_sha256=phase['context']['lease_sha256'],case_summaries=verified['case_summaries'],comparisons=verified['comparisons'],members=verified['members'],memory_records=verified['memory_records'],source_pins=len(n.source_paths(c.ROOT)),
        providers=len(verified['cases']),capture_pairs=6*len(verified['cases']),named_observer_getters=n.native_budget(mode)['observer_getters'],fresh_raw_review_accepted=False,
        host_status_at_acceptance=live['host_status'],workflow_status_at_acceptance=live['status'],official_model_calls=0,ort_sessions=0,original_strict_pass=False,stage7_complete=False)
    c.write(base/'root-acceptance.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('identity','comparisons','members','case_summaries')}));return 0
