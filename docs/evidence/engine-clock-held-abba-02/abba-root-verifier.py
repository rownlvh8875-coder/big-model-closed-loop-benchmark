"""Original terminal held ABBA CPU verification. No native/provider execution."""
import json,subprocess,sys,time,zipfile,hashlib,stat
from pathlib import Path,PurePosixPath
root=Path('/workspace/big-model-closed-loop-benchmark');sys.path.insert(0,str(root))
from scripts import engine_clock_held_abba_v2 as n
from scripts import engine_clock_native as old
from scripts import engine_clock_image_archive_v2 as archives
out=root/'output/stage7-held-abba-root'/n.ID/'abba';cdir=out.parent/'canary'
reg=n.image.parse((root/'output/stage7-held-abba-registration'/n.ID/'abba/registration.json').read_bytes())
acq=n.image.parse((out/'acquired.json').read_bytes());assert acq['conclusion']=='failure'
proofs={k:n.image.parse((out/'api'/(k+'.json')).read_bytes()) for k in ('run','jobs','workflow','artifacts','unique_runs')}
r=proofs['run'];assert r['status']=='completed' and r['conclusion']=='failure' and r['run_attempt']==1 and r['head_sha']==reg['producer_head_sha'] and r['head_branch']==n.BRANCH and r['path']==n.WORKFLOW and r['event']=='push' and r['repository']['full_name']==n.REPOSITORY
jobs=proofs['jobs'];assert jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'native-host','canary-attestor'} and all(j['status']=='completed' and j['conclusion']==('failure' if j['name']=='native-host' else 'success') and j['run_id']==r['id'] and j['run_attempt']==1 and j['head_sha']==r['head_sha'] for j in jobs['jobs'])
assert proofs['workflow']['id']==r['workflow_id'] and proofs['workflow']['path']==n.WORKFLOW and proofs['workflow']['state']=='active'
assert proofs['unique_runs']['total_count']==1 and proofs['unique_runs']['workflow_runs'][0]['id']==r['id']
assert proofs['artifacts']['total_count']==4
art=acq['artifacts'][0];meta=next(a for a in proofs['artifacts']['artifacts'] if a['id']==art['id']);path=out/(art['name']+'.original.zip')
h=hashlib.sha256()
with path.open('rb') as f:
 for b in iter(lambda:f.read(n.MIB),b''):h.update(b)
assert h.hexdigest()==art['sha256']==meta['digest'][7:] and path.stat().st_size==art['nbytes']==meta['size_in_bytes'] and meta['expired'] is False
selected=out/'root-selected';selected.mkdir(mode=0o700,exist_ok=False)
with zipfile.ZipFile(path) as z:
 rows=z.infolist();assert 0<len(rows)<=1024;names=set();total=0
 for info in rows:
  name=info.orig_filename;p=PurePosixPath(name)
  assert name==info.filename and name not in names and str(p)==name and not p.is_absolute() and all(v not in ('','.','..') for v in name.split('/')) and '\\' not in name and ':' not in name and not info.flag_bits&1 and stat.S_IFMT(info.external_attr>>16) in (0,stat.S_IFREG) and not info.is_dir()
  names.add(name);total+=info.file_size;assert info.file_size<=512*n.MIB and total<=2*1024**3
 def raw(name,cap=16*n.MIB):
  assert z.getinfo(name).file_size<=cap;return z.read(name)
 def obj(name):return n.image.parse(raw(name))
 request_raw=raw('consumed-request.json');request=n.validate_request(n.image.parse(request_raw),root)
 assert request['mode']=='abba' and n.sha(request_raw)==reg['request_sha256'] and request['acceptance']==reg['acceptance']
 assert subprocess.check_output(['git','show',reg['activation_sha']+':'+n.A_REQUEST],cwd=root)==request_raw
 producer_raw=raw('producer-request.json');producer=n.validate_request(n.image.parse(producer_raw),root)
 assert subprocess.check_output(['git','show',reg['producer_head_sha']+':'+n.C_REQUEST],cwd=root)==producer_raw
 for p,d in request['source_closure'].items():assert n.sha(subprocess.check_output(['git','show',reg['source_sha']+':'+p],cwd=root))==d
 binding_raw=raw('binding/binding.json');binding=n.image.parse(binding_raw);bsha=n.sha(binding_raw);n.validate_binding_requests(binding,producer_raw,root)
 phase=obj('output/phase.json');result=obj('result.json');ctx=obj('source-authentication.json');q=obj('docker/qualification.json');launch=obj('launch.json')
 assert ctx==binding['context']==phase['context'] and ctx['head_sha']==ctx['producer_head_sha']==reg['producer_head_sha'] and ctx['control_head_sha']==reg['activation_sha'] and ctx['request_sha256']==reg['request_sha256'] and ctx['run_id']==r['id'] and ctx['workflow_id']==r['workflow_id'] and ctx['job_id']==reg['acceptance']['job_id']
 visibility=ctx['run_status_visibility'];assert visibility['status']=='ACTUAL_RUNNING_RUN_OBSERVED' and 1<=visibility['snapshots']<=13 and visibility['queued_snapshots']==visibility['snapshots']-1 and 0<=visibility['elapsed_seconds']<60
 snapshots=visibility['original_snapshot_paths'];assert snapshots==['live-run-%02d.json'%i for i in range(visibility['snapshots'])]
 assert raw('control-api/live-run.json')==raw('control-api/'+snapshots[-1]) and n.sha(raw('control-api/live-run.json'))==visibility['selected_original_sha256']
 for i,name in enumerate(snapshots):
  item=obj('control-api/'+name);assert item['id']==r['id'] and item['head_sha']==reg['producer_head_sha'] and item['head_branch']==n.BRANCH and item['path']==n.WORKFLOW and item['event']=='push' and item['run_attempt']==1 and item['workflow_id']==r['workflow_id'] and item['repository']['full_name']==n.REPOSITORY and item['conclusion'] is None and item['status']==('in_progress' if i==len(snapshots)-1 else 'queued')
 assert raw('control-request.json')==request_raw
 control_commit=obj('control-api/control-commit.json');control_compare=obj('control-api/control-compare.json');content=obj('control-api/control-content.json');control_tree=obj('control-api/control-tree.json')
 n.validate_control_delta(producer,request,reg['activation_sha'],control_commit,control_compare,content['sha'],request_raw)
 n.validate_control_tree(control_tree,control_commit['tree']['sha'],content['sha'])
 lease=obj('host-lease.json');assert binding['host_lease']==lease and n.sha(n.canonical(lease))==ctx['lease_sha256']==reg['acceptance']['lease_sha256']
 assert binding['request']==request and binding['producer_request']==producer and binding['receipt']==n.image.parse((root/(n.AUTH+'preparation.json')).read_bytes())
 identity=n.identity_from_profiles(binding['receipt'],request['image_evidence']['expected'],q['host'],q['engine'],binding['identity']['host_details'])
 croot=n.image.parse((cdir/'root-acceptance.json').read_bytes());assert identity==croot['identity']==binding['identity']==phase['identity']
 for value in (phase,result):assert value['status']=='FAILED_OR_INCOMPLETE' and value['official_model_calls']==value['ort_sessions']==0 and value['scientific_result_promoted'] is False
 assert phase['mode']=='abba' and phase['identity_verified'] is True and phase['error']==dict(type='ValueError',detail='dataset byte/member cap') and phase['binding_sha256']==bsha and phase['native_budget']==n.native_budget('abba') and phase['budget']==n.BUDGET and len(phase['launches'])==4 and len(phase['comparisons'])==6 and phase['elapsed_seconds']<=1800
 assert result['phase_operation_seconds']<=2400 and result['control_elapsed_seconds']<=900
 assert 'controller.json' not in names
 state=obj('docker/state-observation-012.json');assert state==dict(ExitCode=1,OOMKilled=False,Running=False,Status='exited')
 assert result['last_stage']=='one-native-phase' and result['error_detail']=='IMAGE_DOCKER_REJECTED'
 diag=obj('launch-diagnostics.json');assert diag['gate_passed'] is True and diag['failed']==[] and launch['validated'] is True and launch['environment']==n.environment_profile()
 assert launch['image_id']==identity['installed_identity']['core']['image']['config_digest'] and launch['labels']['stage7.request']==n.ID and launch['labels']['stage7.source']==reg['source_sha']
 for p in ('/work/repo','/work/binding'):assert launch['mounts'][p]['type']=='bind' and launch['mounts'][p]['rw'] is False
 for p in ('/work/output','/work/cache'):assert launch['mounts'][p]['type']=='bind' and launch['mounts'][p]['rw'] is True
 assert launch['host_configuration']['Memory']==4294967296 and launch['host_configuration']['CgroupnsMode']=='private' and launch['host_configuration']['Tmpfs']=={'/tmp':n.TMPFS}
 assert obj('acceptance-identity.json')['equal'] is True and obj('acceptance-identity.json')['differences']==[]
 assert obj('output/accepted-canary-replay.json')==dict(status='ACCEPTED_CANARY_CPU_RAW_REPLAY',capture_pairs=6,identity=identity)
 manifest_raw=raw('binding/installed-files.json');assert manifest_raw==(root/(n.AUTH+'installed-files.json')).read_bytes();entries={v['path']:v for v in n.image.parse(manifest_raw)['entries']}
 memories=[];inventories=[];selections={}
 tags=['parent']+['child-%02d'%i for i in range(4)]
 for tag in tags:
  proof=obj('output/'+tag+'-admission.json');inv=proof['inventory'];inventories.append(inv)
  assert proof['identity']==identity and proof['binding_sha256']==bsha and inv['complete'] is True and inv['status']=='INSTALLED_FILES_MATCH' and inv['bytes_read']==1670492280 and inv['matched_entries']==44232 and inv['canonical_manifest_sha256']==n.sha(manifest_raw) and inv['elapsed_s']<=180
  assert proof['prefix']['status']=='PREFIX_LAYOUT_AND_OBSERVATION_MATCH'
  role='parent' if tag=='parent' else 'child';n.check_environment(proof['launch_environment'],role);n.check_post_import_environment(proof['environment'],role)
  if role=='child':
   i=int(tag[-2:]);row=phase['launches'][i]
   n.validate_permit(proof['permit'],ancestors=[phase['parent_pid']],group=row['process_group'],nonce=row['nonce'],binding_sha=bsha,identity_sha=identity['core_sha256'],mode='abba',index=i)
   assert proof['permit']['parent_uuid']==phase['parent_uuid']
  for kind,expected in (('host',q['host']),('identity',identity)):
   d=obj('output/'+tag+'-'+kind+'-comparison.json');assert d['equal'] is True and d['differences']==[] and d['observed']==expected and d['observed_sha256']==d['accepted_sha256']==n.sha(n.canonical(expected))
  memories.extend([proof['memory_before'],obj('output/'+tag+'-memory-after.json')])
  for position in ('preflight','post'):
   name='output/'+position+'-'+tag+'-maps.json';d=obj(name);selections[name]=d
   assert d['accepted'] is True and d['rejections']==[] and d['policy']==n.environment_identity()['selection_policy'] and d['generated_memory_binary_equality_proven'] is False
   assert all(p in entries and entries[p]['kind']=='file' for p in d['image_files'])
   assert all(p.startswith('/work/repo/') and p[11:] in request['source_closure'] for p in d['source_files'])
   assert all('x' not in v['permissions'] for v in d['runtime_mappings'] if v['category'] in ('registered-cache-data','owned-tmp-data','private-shm-data','managed-config-data'))
  d=obj('output/post-'+tag+'-modules.json');assert d['accepted'] is True and d['rejections']==[] and d['policy']==n.environment_identity()['selection_policy']
  loaded=obj('output/'+tag+'-loaded-files.json');assert all(p in entries and entries[p]['kind']=='file' for p in loaded['maps'])
  for p in loaded['modules'].values():assert (p[11:] in request['source_closure']) if p.startswith('/work/repo/') else (p in entries and entries[p]['kind']=='file')
 assert len({v['cgroup_inode'] for v in memories})==1
 for v in memories:assert v['max_bytes']==4294967296 and v['events']['oom']==v['events']['oom_kill']==0 and v['peak_is_rss'] is False and v['non_atomic'] is True
 cases=[]
 for i,row in enumerate(phase['launches']):
  prefix='output/case_%02d/'%i;case_dir=selected/('case_%02d'%i);case_dir.mkdir()
  for info in rows:
   if info.filename.startswith(prefix):
    dest=old.capture._safe_path(case_dir,info.filename[len(prefix):]);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw(info.filename,40*n.MIB))
  case=old._read(case_dir/'case.json');old._validate_case(case_dir,case,row,dict(phase='abba',parent_pid=phase['parent_pid'],parent_uuid=phase['parent_uuid'],context=ctx,source_snapshot=request['source_closure'],runtime=identity,request_sha256=reg['request_sha256']))
  assert row['index']==i and row['clock_enabled']==n.schedule('abba')[i][0] and row['error'] is None and row['cleanup_errors']==[] and row['exit_code']==0 and row['reaped'] is True and row['group_gone'] is True and 0<row['cache_after']['files']<=1024 and row['cache_after']['bytes']<=64*n.MIB
  cases.append(case)
 assert old._comparisons(cases)==phase['comparisons']
 copies=[]
 for name in ('copied-code','copied-python','copied-executable'):
  dest=selected/(name+'.tar')
  with z.open('docker/'+name+'.tar') as src,dest.open('xb') as f:
   for b in iter(lambda:src.read(n.MIB),b''):f.write(b)
  copies.append(dest)
 # Retain every small original record needed for external inspection, no cache/image bytes.
 for info in rows:
  if info.filename.endswith('.json') and info.file_size<=2*n.MIB and not info.filename.startswith('binding/accepted-canary/'):
   dest=selected/info.filename;dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():dest.write_bytes(raw(info.filename,2*n.MIB))
code=[]
for name in ('__init__.py','engine_clock_runtime_inventory.py','engine_clock_image_inventory.py','engine_clock_image_installer.py'):
 b=subprocess.check_output(['git','show',reg['source_sha']+':scripts/'+name],cwd=root);code.append(dict(path='scripts/'+name,kind='file',mode=0o644,nbytes=len(b),sha256=n.sha(b)))
members=n.image.parse((root/'docs/evidence/engine-clock-python-bootstrap/archive-members.json').read_bytes())['entries'];layout=n.image.parse((root/n.image.LAYOUT_PATH).read_bytes())
checks=[archives.verify_tree_archive(copies[0],code,prefix='stage7',deadline=time.perf_counter()+180),archives.verify_tree_archive(copies[1],members,prefix='python',deadline=time.perf_counter()+180),archives.verify_executable_archive(copies[2],layout['expected_members']['bin/python3.11'],deadline=time.perf_counter()+180)]
for actual,claimed in zip(checks,launch['copied_trees']):assert actual['archive_sha256']==claimed['archive_sha256'] and actual['archive_nbytes']==claimed['archive_nbytes']
# Reproduce the unchanged final membership guard on all original output data.
with zipfile.ZipFile(path) as z:
 output_rows=[item for item in z.infolist() if item.filename.startswith('output/')]
 original_output=selected/'output-original';original_output.mkdir()
 for item in output_rows:
  dest=original_output/item.filename[len('output/'):];dest.parent.mkdir(parents=True,exist_ok=True)
  with z.open(item) as src,dest.open('xb') as f:
   for block in iter(lambda:src.read(n.MIB),b''):f.write(block)
 decoded=sum(item.file_size for item in output_rows);assert len(output_rows)==170 and decoded==65433113 and decoded<192*n.MIB
 try:old._members(original_output,n.BUDGET['case_bytes'])
 except ValueError as exc:assert str(exc)=='dataset byte/member cap'
 else:raise AssertionError('frozen final membership cap did not reject original output')
report=dict(status='AUTHENTICATED_TERMINAL_MEMBER_CAP_WITH_FOUR_CASE_DIAGNOSTICS',source_sha=reg['source_sha'],producer_head_sha=reg['producer_head_sha'],control_head_sha=reg['activation_sha'],run_id=r['id'],workflow_id=r['workflow_id'],job_id=reg['acceptance']['job_id'],artifact_id=art['id'],artifact_zip_sha256=art['sha256'],artifact_zip_nbytes=art['nbytes'],identity=identity,lease_sha256=ctx['lease_sha256'],copied_checks=checks,providers_constructed=4,providers_closed=4,capture_pairs=24,ram_reads=48,task_steps=48,texture_readings=96,clock_snapshots=96,observer_getters=384,comparisons=phase['comparisons'],clock_patterns=[old._clock_patterns(c['clock_trace']) if c['clock_enabled'] else None for c in cases],memory_snapshots=memories,cgroup_peak_bytes=max(v['peak_bytes'] for v in memories),cgroup_peak_is_rss=False,phase_seconds=phase['elapsed_seconds'],phase_operation_seconds=result['phase_operation_seconds'],control_elapsed_seconds=result['control_elapsed_seconds'],official_model_calls=0,ort_sessions=0,scientific_result_promoted=False,root_original_api_artifact_authenticated=True,fresh_raw_review_accepted=False)
report.update(native_phase_accepted=False,terminal_workflow_conclusion='failure',container_state=state,successful_controller_record_present=False,original_output_files=170,original_output_bytes=65433113,unchanged_member_cap=129,member_cap_failure_reproduced=True,byte_cap_exceeded=False,components_scope='four reconstructed cases and six retained comparisons are diagnostics from a rejected phase',original_generic_provider_bounds=[0,4],remaining_campaign_native_allowance=0)
(out/'root-acceptance.json').write_bytes(n.canonical(report));print(json.dumps({k:v for k,v in report.items() if k not in ('identity','copied_checks','memory_snapshots','clock_patterns')}))
