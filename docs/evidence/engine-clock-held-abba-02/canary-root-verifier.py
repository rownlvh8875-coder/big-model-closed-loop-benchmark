"""Independent root byte/API checks; CPU-only decoding, no native engine/model."""
import hashlib,json,os,stat,subprocess,sys,time,zipfile
from pathlib import Path,PurePosixPath
root=Path('/workspace/big-model-closed-loop-benchmark');sys.path.insert(0,str(root))
from scripts import engine_clock_held_abba_v2 as n
from scripts import engine_clock_image_archive_v2 as archive
from scripts import engine_clock_native as old
out=root/'output/stage7-held-abba-root'/n.ID/'canary'
acq=n.image.parse((out/'acquired.json').read_bytes())
reg=n.image.parse((root/'output/stage7-held-abba-registration'/n.ID/'canary'/'registration.json').read_bytes())
assert acq['conclusion'] is None and acq['activation_sha']==reg['activation_sha']
proofs={k:n.image.parse((out/'api'/(k+'.json')).read_bytes()) for k in ('run','jobs','workflow','artifacts','unique_runs')}
run=proofs['run']
from scripts import engine_clock_held_abba_v2_archive as held_archive
approval=n.image.parse((out/'approval-input.json').read_bytes())
canary_art=next(x for x in proofs['artifacts']['artifacts'] if x['name']==n.artifact('canary'))
attest_art=next(x for x in proofs['artifacts']['artifacts'] if x['name']==n.artifact('attestation'))
n.validate_completion_api(approval,run,proofs['jobs'],canary_art,attest_art,workflow_id=run['workflow_id'])
assert proofs['workflow']['id']==run['workflow_id'] and proofs['workflow']['path']==n.WORKFLOW and proofs['workflow']['state']=='active'
assert proofs['unique_runs']['total_count']==1 and len(proofs['unique_runs']['workflow_runs'])==1 and proofs['unique_runs']['workflow_runs'][0]['id']==run['id']
assert len(acq['artifacts'])==1 and proofs['artifacts']['total_count']==3
art=acq['artifacts'][0];zpath=out/(art['name']+'.original.zip')
rawdir=out/'root-selected';rawdir.mkdir(mode=0o700,exist_ok=False)
with zipfile.ZipFile(zpath) as z:
 names=z.namelist();assert len(names)==len(set(names))
 for info in z.infolist():
  name=info.filename;p=PurePosixPath(name);mode=info.external_attr>>16
  assert info.orig_filename==name and str(p)==name and not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name and not stat.S_ISLNK(mode)
 def entry(suffix):
  assert suffix in names;return suffix
 def get(suffix,limit=16*n.MIB):
  info=z.getinfo(entry(suffix));assert info.file_size<=limit;return z.read(info)
 def obj(suffix):return n.image.parse(get(suffix))
 request_raw=get('consumed-request.json');request=n.validate_request(n.image.parse(request_raw),root)
 assert n.sha(request_raw)==reg['request_sha256'] and request['reviewed_source_sha']==reg['source_sha'] and len(request['source_closure'])==reg['source_closure_files']
 assert subprocess.check_output(['git','show',reg['activation_sha']+':'+n.REQUEST],cwd=root)==request_raw
 for path,digest in request['source_closure'].items():
  data=subprocess.check_output(['git','show',reg['source_sha']+':'+path],cwd=root,timeout=15);assert n.sha(data)==digest
 binding_raw=get('binding/binding.json');binding=n.image.parse(binding_raw);bsha=n.sha(binding_raw)
 manifest_raw=get('binding/installed-files.json');assert n.sha(manifest_raw)=='f81fa5be38bc9853b6eff1d0ea524be97f3d1e92f5c1f0f9e1449a11b4c4b59f'
 assert manifest_raw==(root/(n.AUTH+'installed-files.json')).read_bytes()
 manifest=n.image.parse(manifest_raw);entries={r['path']:r for r in manifest['entries']}
 diag=obj('launch-diagnostics.json');assert diag['gate_passed'] is True and diag['failed']==[]
 phase=obj('output/phase.json');controller=obj('controller.json');source=obj('source-authentication.json');result=obj('result.json');q=obj('docker/qualification.json');launch=obj('launch.json')
 assert result['status']==phase['status']==controller['status']=='HELD_CANARY_NATIVE_RECORDED'
 assert result['elapsed_seconds']<=2400 and phase['elapsed_seconds']<=1800
 assert source==binding['context']==phase['context']==controller['context']
 for key,value in [('run_id',run['id']),('workflow_id',run['workflow_id']),('head_sha',reg['activation_sha']),('source_sha',reg['source_sha']),('request_sha256',reg['request_sha256'])]:assert source[key]==value
 visibility=source['run_status_visibility'];assert visibility['status']=='ACTUAL_RUNNING_RUN_OBSERVED' and 1<=visibility['snapshots']<=13 and visibility['queued_snapshots']==visibility['snapshots']-1 and 0<=visibility['elapsed_seconds']<60
 snapshots=visibility['original_snapshot_paths'];assert len(snapshots)==visibility['snapshots'] and snapshots==['live-run-%02d.json'%i for i in range(len(snapshots))]
 assert visibility['selected_original_snapshot']==snapshots[-1] and get('api/live-run.json')==get('api/'+snapshots[-1]) and n.sha(get('api/live-run.json'))==visibility['selected_original_sha256']
 for i,name in enumerate(snapshots):
  item=obj('api/'+name);assert item['id']==run['id'] and item['head_sha']==reg['activation_sha'] and item['head_branch']==n.BRANCH and item['path']==n.WORKFLOW and item['event']=='push' and item['run_attempt']==1 and item['workflow_id']==run['workflow_id'] and item['repository']['full_name']==n.REPOSITORY and item['conclusion'] is None and item['status']==('in_progress' if i==len(snapshots)-1 else 'queued')

 assert binding['request']==request and binding['receipt']==n.image.parse((root/(n.AUTH+'preparation.json')).read_bytes())
 from scripts import engine_clock_sealed_native_v6 as frozen
 base=frozen.make_identity(binding['receipt'],request['image_evidence']['expected'],q['host'],q['engine'])
 core=base['core'];core['configuration']['environment_profile_sha256']=n.sha(n.contract._encode(n.environment_identity()))
 installed=n.contract.validate_identity(dict(schema='engine-clock-installed-identity-v1',core=core,core_sha256=n.sha(n.contract._encode(core))))
 details=binding['identity']['host_details']
 assert details['affinity_ids']==sorted(set(details['affinity_ids'])) and len(details['affinity_ids'])==q['host']['affinity_cpus']
 assert all(type(i) is int and 0<=i<2**20 for i in details['affinity_ids'])
 assert details['memory_total_bytes']>=n.BUDGET['minimum_host_memory_bytes']
 value=dict(installed_identity=installed,host_details=details)
 identity=dict(schema='engine-clock-held-abba-identity-v2',**value,core_sha256=n.sha(n.canonical(value)))
 n.validate_binding_requests(binding,request_raw,root)
 assert source['head_sha']==source['producer_head_sha']==source['control_head_sha']==reg['activation_sha']
 lease=obj('host-lease.json');assert binding['host_lease']==lease and n.sha(n.canonical(lease))==source['lease_sha256']==approval['lease_sha256']
 assert lease['deadline_monotonic']-lease['started_monotonic']==6000.0
 assert get('producer-request.json')==request_raw
 assert phase['mode']=='canary' and phase['identity_verified'] is True and len(phase['launches'])==1 and phase['comparisons']==[]
 assert phase['native_budget']==n.native_budget('canary') and phase['budget']==n.BUDGET
 assert binding['host']==q['host'] and binding['engine']==q['engine'] and binding['identity']==phase['identity']==controller['identity']==identity
 assert identity['installed_identity']['core']['image']['image_tar_sha256']=='f69b8ece51bcc6911aaf118d5ea091ba4d6ace8418b480e408be5b9fd8cb2921'
 assert launch['validated'] is True and launch['image_id']==identity['installed_identity']['core']['image']['config_digest'] and launch['environment']==n.environment_profile()
 assert set(launch['mounts']) in ({'/work/repo','/work/binding','/work/output','/work/cache'},{'/work/repo','/work/binding','/work/output','/work/cache','/tmp'})
 assert launch['host_configuration']['Tmpfs']=={'/tmp':n.TMPFS}
 for dest in ('/work/repo','/work/binding'):assert launch['mounts'][dest]['type']=='bind' and launch['mounts'][dest]['rw'] is False
 for dest in ('/work/output','/work/cache'):assert launch['mounts'][dest]['type']=='bind' and launch['mounts'][dest]['rw'] is True
 assert launch['labels']['stage7.request']==n.ID and launch['labels']['stage7.source']==reg['source_sha']
 assert controller['state']['Status']=='exited' and controller['state']['Running'] is False and controller['state']['ExitCode']==0 and controller['state']['OOMKilled'] is False
 assert n.sha(get('output/phase.json'))==controller['phase_sha256']
 parent=obj('output/parent-admission.json');child=obj('output/child-00-admission.json')
 selection_names=['output/preflight-parent-maps.json','output/preflight-child-00-maps.json','output/post-parent-maps.json','output/post-child-00-maps.json','output/post-parent-modules.json','output/post-child-00-modules.json']
 selections={name:obj(name) for name in selection_names}
 for name,d in selections.items():
  assert d['accepted'] is True and d['policy']==n.environment_identity()['selection_policy'] and d['rejections']==[]
  if d['schema']=='native-mapping-selection-v1':
   assert d['generated_memory_binary_equality_proven'] is False
   for path in d['image_files']:assert path in entries and entries[path]['kind']=='file'
   for path in d['source_files']:assert path.startswith('/work/repo/') and path[len('/work/repo/'):] in request['source_closure']
   for row in d['runtime_mappings']:
    if row['category'] in ('registered-cache-data','owned-tmp-data','private-shm-data','managed-config-data'):assert 'x' not in row['permissions']
 for tag in ('parent','child-00'):
  for kind in ('host','identity'):
   name='output/'+tag+'-'+kind+'-comparison.json';d=obj(name)
   assert d['equal'] is True and d['differences']==[] and d['role']==tag and d['kind']==kind
   expected=q['host'] if kind=='host' else identity
   assert d['observed']==expected and d['observed_sha256']==d['accepted_sha256']==n.sha(n.canonical(expected))
   dest=rawdir/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(get(name))
 host_memory=obj('host-memory.json');assert host_memory['total_bytes']==identity['host_details']['memory_total_bytes'] and host_memory['total_bytes']>=6*1024**3
 memories=[parent['memory_before'],child['memory_before'],obj('output/child-00-memory-after.json'),obj('output/parent-memory-after.json')]
 assert len({m['cgroup_inode'] for m in memories})==1
 for m in memories:assert m['max_bytes']==4294967296 and m['events']['oom']==m['events']['oom_kill']==0 and m['peak_is_rss'] is False and m['non_atomic'] is True
 assert launch['host_configuration']['Memory']==4294967296 and launch['host_configuration']['CgroupnsMode']=='private'
 for data in (parent,child):
  inv=data['inventory'];assert data['identity']==identity and data['binding_sha256']==bsha and inv['complete'] is True and inv['status']=='INSTALLED_FILES_MATCH' and inv['canonical_manifest_sha256']==n.sha(manifest_raw)
  assert inv['inventory_manifest']==dict(path='/work/binding/installed-files.json',nbytes=len(manifest_raw),sha256=n.sha(manifest_raw))
  assert inv['matched_entries']==44232 and inv['bytes_read']==1670492280 and inv['visited_nodes']<=100000 and inv['elapsed_s']<=180
  assert data['prefix']['status']=='PREFIX_LAYOUT_AND_OBSERVATION_MATCH'
  assert len(n.canonical(data))<=2*n.MIB
 assert child['permit']['parent_pid']==phase['parent_pid'] and child['permit']['parent_uuid']==phase['parent_uuid'] and child['permit']['nonce']==phase['launches'][0]['nonce'] and child['permit']['process_group']==phase['launches'][0]['process_group'] and child['permit']['binding_sha256']==bsha and child['permit']['identity_sha256']==identity['core_sha256']
 n.check_environment(parent['launch_environment'],'parent');n.check_environment(child['launch_environment'],'child')
 n.check_post_import_environment(parent['environment'],'parent');n.check_post_import_environment(child['environment'],'child')
 assert parent['launch_environment']==launch['environment']
 for role in ('parent','child-00'):
  loaded=obj('output/'+role+'-loaded-files.json')
  for path in loaded['maps']:assert path in entries and entries[path]['kind']=='file'
  for path in loaded['modules'].values():
   if path.startswith('/work/repo/'):assert path[len('/work/repo/'):] in request['source_closure']
   else:assert path in entries and entries[path]['kind']=='file'
 copies=[]
 for name in ('copied-code','copied-python','copied-executable'):
  info=z.getinfo(entry('docker/'+name+'.tar'));assert info.file_size<=512*n.MIB
  dest=rawdir/(name+'.tar')
  with z.open(info) as src,dest.open('xb') as f:
   for block in iter(lambda:src.read(n.MIB),b''):f.write(block)
  copies.append(dest)
 case_dir=rawdir/'case_00';case_dir.mkdir()
 case_entry=entry('output/case_00/case.json');prefix=case_entry[:-len('case.json')]
 for info in z.infolist():
  if info.filename.startswith(prefix) and not info.is_dir():
   relative=info.filename[len(prefix):];dest=old.capture._safe_path(case_dir,relative);dest.parent.mkdir(parents=True,exist_ok=True)
   assert info.file_size<=40*n.MIB
   with z.open(info) as src,dest.open('xb') as f:
    for block in iter(lambda:src.read(n.MIB),b''):f.write(block)
 for name in selection_names:
  dest=rawdir/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(get(name))
 case=old._read(case_dir/'case.json')
 for name in ('consumed-request.json','source-authentication.json','producer-authentication.json','result.json','controller.json','launch.json','launch-diagnostics.json','output/phase.json','output/parent-admission.json','output/child-00-admission.json','output/parent-loaded-files.json','output/child-00-loaded-files.json','output/parent-memory-after.json','output/child-00-memory-after.json','host-memory.json'):
  dest=rawdir/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(get(name))
 case_binding=dict(phase='canary',parent_pid=phase['parent_pid'],parent_uuid=phase['parent_uuid'],context=source,source_snapshot=request['source_closure'],runtime=identity,request_sha256=reg['request_sha256'])
 old._validate_case(case_dir,case,phase['launches'][0],case_binding)
 clock=old.clock.validate_clock_trace(case['clock_trace']);assert clock['clock_snapshots']==48 and clock['observer_clock_getter_invocations']==96 and clock['task_step_calls']==12
 assert phase['launches'][0]['reaped'] is True and phase['launches'][0]['group_gone'] is True and phase['launches'][0]['cleanup_errors']==[] and phase['launches'][0]['error'] is None and phase['launches'][0]['exit_code']==0
 assert case['provider_constructed'] is True and case['provider_closed'] is True and case['error'] is None and case['cleanup_errors']==[]
 assert phase['launches'][0]['cache_after']['files']>0 and phase['launches'][0]['cache_after']['files']<=1024 and phase['launches'][0]['cache_after']['bytes']<=64*n.MIB
source_sha=reg['source_sha'];code=[]
for name in ('__init__.py','engine_clock_runtime_inventory.py','engine_clock_image_inventory.py','engine_clock_image_installer.py'):
 raw=subprocess.check_output(['git','show',source_sha+':scripts/'+name],cwd=root,timeout=15);code.append(dict(path='scripts/'+name,kind='file',mode=0o644,nbytes=len(raw),sha256=n.sha(raw)))
members=n.image.parse((root/'docs/evidence/engine-clock-python-bootstrap/archive-members.json').read_bytes())['entries'];layout=n.image.parse((root/n.image.LAYOUT_PATH).read_bytes())
checks=[archive.verify_tree_archive(copies[0],code,prefix='stage7',deadline=time.perf_counter()+180),archive.verify_tree_archive(copies[1],members,prefix='python',deadline=time.perf_counter()+180),archive.verify_executable_archive(copies[2],layout['expected_members']['bin/python3.11'],deadline=time.perf_counter()+180)]
for actual,claimed in zip(checks,controller['copied_trees']):assert actual['archive_sha256']==claimed['archive_sha256'] and actual['archive_nbytes']==claimed['archive_nbytes']
report=dict(schema='engine-clock-sealed-native-root-acceptance-v1',status='AUTHENTICATED_HELD_CANARY_ORIGINAL_CPU_REPLAY',source_sha=reg['source_sha'],activation_sha=reg['activation_sha'],request_sha256=reg['request_sha256'],source_closure_files=reg['source_closure_files'],run_id=run['id'],workflow_id=run['workflow_id'],job_id=approval['job_id'],artifact_id=art['id'],artifact_zip_sha256=art['sha256'],artifact_zip_nbytes=art['nbytes'],config_digest=identity['installed_identity']['core']['image']['config_digest'],identity=identity,copied_checks=checks,parent_inventory_bytes=parent['inventory']['bytes_read'],child_inventory_bytes=child['inventory']['bytes_read'],parent_preflight_seconds=parent['elapsed_seconds'],child_preflight_seconds=child['elapsed_seconds'],phase_seconds=phase['elapsed_seconds'],operation_seconds=result['elapsed_seconds'],providers_constructed=1,providers_closed=1,capture_pairs=6,ram_reads=12,task_steps=12,texture_readings=24,clock_snapshots=48,observer_getters=144,clock_patterns=old._clock_patterns(case['clock_trace']),cache=phase['launches'][0]['cache_after'],memory_snapshots=memories,cgroup_peak_bytes=max(m['peak_bytes'] for m in memories),cgroup_peak_is_rss=False,host_memory=host_memory,old04_oom_confirmed=False,selection_reports=selections,generated_memory_binary_equality_proven=False,official_model_calls=0,ort_sessions=0,scientific_result_promoted=False,root_original_api_artifact_authenticated=True,fresh_raw_review_accepted=False)
checked=held_archive.validate_native_canary_archive(zpath,out/'metadata-selected-final',request,binding['context'],canary_art)
with zipfile.ZipFile(out/'attestation.original.zip') as z:
 assert z.namelist()==['canary-attestation.json'];attestation=n.image.parse(z.read('canary-attestation.json'))
held_archive.validate_attestation_receipt(attestation,approval,checked)
report.update(lease_sha256=source['lease_sha256'],attestor_job_id=approval['attestor_job_id'],attestor_artifact_id=approval['attestor_artifact_id'],attestor_artifact_sha256=approval['attestor_artifact_sha256'],whole_workflow_status_at_acceptance=run['status'],whole_workflow_completed_at_acceptance=False)
(out/'root-acceptance.json').write_bytes(n.canonical(report))
print(json.dumps({k:v for k,v in report.items() if k not in ('identity','copied_checks','clock_patterns','cache','selection_reports','memory_snapshots')}))
