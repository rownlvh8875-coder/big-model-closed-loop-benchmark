"""Original C archive/terminal metadata attestation; no graphics imports or actions."""
from pathlib import Path
import stat
import zipfile
from scripts import engine_clock_held_abba_v2 as n
from scripts.engine_clock_sealed_abba_acceptance_v2 import audit_archive
from scripts import engine_clock_boundaries as clock


def validate_native_canary_archive(path,dest,producer,expected_context,artifact):
    stage='archive'
    try:
        path=Path(path);dest=Path(dest)
        n.need(artifact['name']==n.artifact('canary') and path.stat().st_size==artifact['size_in_bytes'])
        import hashlib
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(n.MIB),b''):digest.update(block)
        n.need('sha256:'+digest.hexdigest()==artifact['digest'])
        audited=audit_archive(path,dest,total_limit=n.LIFECYCLE['attestor_decoded_bytes'])
        with zipfile.ZipFile(path) as z:
            for name in ('binding/binding.json','producer-request.json','host-lease.json'):
                n.need(name in audited['files'] and audited['files'][name]['nbytes']<=2*n.MIB)
                target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
                raw=z.read(name);n.need(n.sha(raw)==audited['files'][name]['sha256'])
                with target.open('xb') as f:f.write(raw)
                target.chmod(0o644)
        def read(name):return n.image.parse(n.image.read_regular(dest/name,2*n.MIB))
        stage='producer-binding'
        request_raw=n.image.read_regular(dest/'consumed-request.json')
        n.need(n.exact(read('consumed-request.json'),producer) and producer['mode']=='canary'
            and request_raw==n.canonical(producer) and n.image.read_regular(dest/'producer-request.json')==request_raw)
        binding_raw=n.image.read_regular(dest/'binding/binding.json');binding=read('binding/binding.json')
        context=binding['context'];n.validate_binding_requests(binding,request_raw,Path(__file__).resolve().parents[1])
        for key in ('repository','event','attempt','run_id','workflow_id','job_id','head_sha','source_sha'):
            n.need(n.exact(context[key],expected_context[key]))
        n.need(context['head_sha']==context['producer_head_sha']==context['control_head_sha']
            and context['lease_sha256']==n.sha(n.canonical(read('host-lease.json')))
            and n.exact(binding['host_lease'],read('host-lease.json')))
        lease=read('host-lease.json')
        n.need(lease['run_id']==context['run_id'] and lease['workflow_id']==context['workflow_id']
            and lease['host_job_id']==context['job_id'] and lease['producer_head_sha']==context['head_sha']
            and lease['source_sha']==context['source_sha'])
        stage='completed-native-phase'
        phase=read('output/phase.json');controller=read('controller.json');result=read('result.json')
        n.need(n.exact(read('source-authentication.json'),context) and n.exact(phase['context'],context)
            and n.exact(controller['context'],context))
        for record in (phase,controller,result):
            n.need(record['status']==n.recorded_status('canary') and n.exact(record['official_model_calls'],0)
                and n.exact(record['ort_sessions'],0) and record['scientific_result_promoted'] is False)
        n.need(phase['mode']=='canary' and phase['identity_verified'] is True and phase['error'] is None
            and len(phase['launches'])==1 and phase['comparisons']==[] and n.exact(phase['budget'],n.BUDGET)
            and n.exact(phase['native_budget'],n.native_budget('canary')) and phase['binding_sha256']==n.sha(binding_raw)
            and controller['phase_sha256']==n.sha(n.image.read_regular(dest/'output/phase.json'))
            and 0<=phase['elapsed_seconds']<=n.BUDGET['container_seconds']
            and 0<=result['elapsed_seconds']<=n.BUDGET['total_seconds'])
        state=controller['state'];n.need(state['Status']=='exited' and state['Running'] is False
            and n.exact(state['ExitCode'],0) and state['OOMKilled'] is False)
        identity=n.identity_from_profiles(binding['receipt'],producer['image_evidence']['expected'],binding['host'],binding['engine'],binding['identity']['host_details'])
        n.need(n.exact(identity,binding['identity']) and n.exact(identity,phase['identity']) and n.exact(identity,controller['identity']))
        row=phase['launches'][0]
        n.need(row['index']==0 and row['clock_enabled'] is True and row['error'] is None
            and row['cleanup_errors']==[] and n.exact(row['exit_code'],0) and row['reaped'] is True and row['group_gone'] is True)
        stage='closed-camera-case'
        case=read('output/case_00/case.json')
        n.need(case['status']=='CLOCK_CAMERA_REPLAY_RECORDED' and case['phase']=='canary' and case['index']==0
            and case['clock_enabled'] is True and case['provider_attempted'] is True and case['provider_constructed'] is True
            and case['provider_closed'] is True and case['error'] is None and case['cleanup_errors']==[]
            and n.exact(case['context'],context) and n.exact(case['runtime'],identity)
            and n.exact(case['source_snapshot'],producer['source_closure']) and case['request_sha256']==context['request_sha256']
            and case['nonce']==row['nonce'] and case['parent_pid']==phase['parent_pid'] and case['parent_uuid']==phase['parent_uuid']
            and case['process_group']==row['process_group'] and case['process_id'] not in (phase['parent_pid'],row['launcher_pid'])
            and n.exact(case['capture_count'],6) and n.exact(case['observed_reads'],12) and n.exact(case['marker_reads'],24)
            and len(case['accepted'])==6 and len(case['capture_rows'])==6 and len(case['markers'])==12)
        trace=clock.validate_clock_trace(case['clock_trace'])
        n.need(trace['clock_snapshots']==48 and trace['observer_clock_getter_invocations']==96 and trace['task_step_calls']==12)
        for i,item in enumerate(case['accepted'],1):
            for boundary in ('raw','canvas'):
                for camera in ('road','wide'):
                    desc=item[boundary][camera];name='capture_%02d/%s_%s.png'%(i,boundary,camera)
                    n.need(desc['path']==name and n.image._hex(desc['rgb_sha256']))
                    n.need(audited['files']['output/case_00/'+name]['sha256']==desc['sha256']
                        and audited['files']['output/case_00/'+name]['nbytes']==desc['nbytes'])
            desc=item['packed'];name='capture_%02d/packed_i420.bin'%i
            n.need(desc['path']==name and desc['actual_input_sha256'] is None and desc['association']=='DERIVED_ONLY_NO_MODEL_CALL'
                and audited['files']['output/case_00/'+name]['sha256']==desc['sha256']
                and audited['files']['output/case_00/'+name]['nbytes']==desc['nbytes'])
        memories=[]
        for tag in ('parent','child-00'):
            stage='admission-'+tag
            proof=read('output/'+tag+'-admission.json');inv=proof['inventory']
            n.need(n.exact(proof['identity'],identity) and proof['binding_sha256']==n.sha(binding_raw)
                and inv['complete'] is True and inv['status']=='INSTALLED_FILES_MATCH' and n.exact(inv['bytes_read'],1670492280)
                and n.exact(inv['matched_entries'],44232) and inv['canonical_manifest_sha256']==binding['receipt']['installed_files_sha256']
                and proof['prefix']['status']=='PREFIX_LAYOUT_AND_OBSERVATION_MATCH')
            role='parent' if tag=='parent' else 'child'
            n.check_environment(proof['launch_environment'],role);n.check_post_import_environment(proof['environment'],role)
            memories.extend((proof['memory_before'],read('output/'+tag+'-memory-after.json')))
            for kind,expected in (('host',binding['host']),('identity',identity)):
                d=read('output/'+tag+'-'+kind+'-comparison.json')
                n.need(d['equal'] is True and d['differences']==[] and n.exact(d['observed'],expected)
                    and d['observed_sha256']==d['accepted_sha256']==n.sha(n.canonical(expected)))
            if tag=='child-00':
                permit=proof['permit']
                n.validate_permit(permit,ancestors=[phase['parent_pid']],group=row['process_group'],nonce=row['nonce'],
                    binding_sha=n.sha(binding_raw),identity_sha=identity['core_sha256'],mode='canary',index=0)
                n.need(permit['parent_uuid']==phase['parent_uuid'])
        n.need(len({m['cgroup_inode'] for m in memories})==1)
        for m in memories:n.need(m['max_bytes']==4294967296 and m['events']['oom']==m['events']['oom_kill']==0 and m['peak_is_rss'] is False)
        stage='copied-archive-hashes'
        n.need(len(controller['copied_trees'])==3)
        for name,desc in zip(('copied-code','copied-python','copied-executable'),controller['copied_trees']):
            entry=audited['files']['docker/'+name+'.tar']
            n.need(entry['sha256']==desc['archive_sha256'] and entry['nbytes']==desc['archive_nbytes'])
        return dict(status='CANARY_PHASE_METADATA_AUTHENTICATED',context=context,producer_head_sha=context['head_sha'],
            source_sha=context['source_sha'],run_id=context['run_id'],workflow_id=context['workflow_id'],host_job_id=context['job_id'],
            artifact_id=artifact['id'],artifact_sha256=artifact['digest'][7:],artifact_size_bytes=artifact['size_in_bytes'],
            phase_sha256=controller['phase_sha256'],binding_sha256=n.sha(binding_raw),identity=identity,
            lease_sha256=context['lease_sha256'],source_closure=producer['source_closure'],
            source_closure_sha256=n.sha(n.canonical(producer['source_closure'])),producer_request_sha256=n.sha(request_raw),
            capture_pairs=6,archive=audited,independent_pixel_replay=False,observed_installed_tree_here=False,
            raw_case_replay_required_before_abba_provider=True)
    except (KeyError,TypeError,IndexError,OSError,ValueError,zipfile.BadZipFile):
        raise ValueError('HELD_CANARY_ARCHIVE_REJECTED:'+stage) from None


def attestation_record(checked,job_id):
    fields=('run_id','workflow_id','host_job_id','producer_head_sha','source_sha','artifact_id',
        'artifact_sha256','artifact_size_bytes','lease_sha256','phase_sha256','source_closure_sha256','producer_request_sha256')
    return dict(schema='engine-clock-held-canary-attestation-v1',status='CANARY_PHASE_METADATA_AUTHENTICATED',
        **{k:checked[k] for k in fields},attestor_job_id=job_id,identity_sha256=checked['identity']['core_sha256'],
        independent_pixel_replay=False,observed_installed_tree_here=False,native_providers=0,official_model_calls=0,ort_sessions=0)


def validate_attestation_receipt(receipt,a,checked):
    want=dict(schema='engine-clock-held-canary-attestation-v1',status='CANARY_PHASE_METADATA_AUTHENTICATED',
        run_id=a['run_id'],workflow_id=a['workflow_id'],host_job_id=a['job_id'],attestor_job_id=a['attestor_job_id'],
        producer_head_sha=a['canary_head_sha'],source_sha=a['source_sha'],artifact_id=a['artifact_id'],
        artifact_sha256=a['artifact_sha256'],artifact_size_bytes=a['artifact_size_bytes'],lease_sha256=a['lease_sha256'],
        phase_sha256=checked['phase_sha256'],identity_sha256=checked['identity']['core_sha256'],
        source_closure_sha256=checked['source_closure_sha256'],producer_request_sha256=checked['producer_request_sha256'],
        independent_pixel_replay=False,observed_installed_tree_here=False,native_providers=0,official_model_calls=0,ort_sessions=0)
    n.need(n.exact(receipt,want))
    return receipt


def artifact_api(item,context,name):
    wr=item['workflow_run']
    n.need(item['name']==name and item['expired'] is False and item['size_in_bytes']>0
        and item['digest'].startswith('sha256:') and n.image._hex(item['digest'][7:])
        and wr['id']==context['run_id'] and wr['head_sha']==context['head_sha'] and wr['head_branch']==n.BRANCH)


def authenticate_canary(client,request,context,work):
    a=request['acceptance'];n.need(request['mode']=='abba')
    run=client.get_json('actions/runs/'+str(a['run_id']),'accepted-run.json')
    jobs=client.get_json('actions/runs/'+str(a['run_id'])+'/jobs?per_page=100','accepted-jobs.json')
    c=client.get_json('actions/artifacts/'+str(a['artifact_id']),'accepted-canary-artifact.json')
    att=client.get_json('actions/artifacts/'+str(a['attestor_artifact_id']),'accepted-attestor-artifact.json')
    n.validate_completion_api(a,run,jobs,c,att,workflow_id=context['workflow_id'])
    n.need(a['run_id']==context['run_id'] and a['canary_head_sha']==context['head_sha']
        and a['job_id']==context['job_id'] and a['lease_sha256']==context['lease_sha256'])
    work=Path(work);path=work/'canary.original.zip'
    client.download('https://api.github.com/repos/'+n.REPOSITORY+'/actions/artifacts/'+str(c['id'])+'/zip',
        path,nbytes=c['size_in_bytes'],sha256=c['digest'][7:],kind='artifact')
    producer=dict(request,mode='canary',acceptance=None,native_budget=n.native_budget('canary'))
    expected=dict(context,mode='canary',control_head_sha=context['head_sha'],request_sha256=context['producer_request_sha256'])
    checked=validate_native_canary_archive(path,work/'accepted-canary',producer,expected,c)
    attpath=work/'attestation.original.zip'
    client.download('https://api.github.com/repos/'+n.REPOSITORY+'/actions/artifacts/'+str(att['id'])+'/zip',
        attpath,nbytes=att['size_in_bytes'],sha256=att['digest'][7:],kind='artifact')
    with zipfile.ZipFile(attpath) as z:
        rows=z.infolist();n.need(len(rows)==1)
        row=rows[0]
        n.need(row.orig_filename==row.filename=='canary-attestation.json' and not row.flag_bits&1
            and stat.S_IFMT(row.external_attr>>16) in (0,stat.S_IFREG) and row.file_size<=2*n.MIB)
        receipt=n.image.parse(z.read(row))
    validate_attestation_receipt(receipt,a,checked)
    checked.update(attestation=receipt,api_identity=a)
    (work/'accepted-authority.json').write_bytes(n.canonical(checked))
    return checked
