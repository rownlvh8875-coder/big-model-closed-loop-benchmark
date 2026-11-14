"""Authenticate the sole original terminal pre-native admission failure."""
import copy,hashlib,json,subprocess,sys,zipfile,stat
from pathlib import Path,PurePosixPath
root=Path('/workspace/big-model-closed-loop-benchmark');sys.path.insert(0,str(root))
from scripts import engine_clock_held_abba as n
out=root/'output/stage7-held-abba-root'/n.ID/'terminal-failure'
reg=n.image.parse((root/'output/stage7-held-abba-registration'/n.ID/'canary/registration.json').read_bytes())
def load(p):return n.image.parse(Path(p).read_bytes())
proofs={k:load(out/'api'/(k+'.json')) for k in ('run','jobs','workflow','artifacts','unique_runs')}
r=proofs['run'];assert r['id']==43563102068 and r['head_sha']==reg['activation_sha'] and r['head_branch']==n.BRANCH and r['path']==n.WORKFLOW and r['event']=='push' and r['run_attempt']==1 and r['status']=='completed' and r['conclusion']=='failure' and r['repository']['full_name']==n.REPOSITORY
assert proofs['workflow']['id']==r['workflow_id']==418051491 and proofs['workflow']['path']==n.WORKFLOW and proofs['workflow']['state']=='active'
assert proofs['unique_runs']['total_count']==1 and len(proofs['unique_runs']['workflow_runs'])==1 and proofs['unique_runs']['workflow_runs'][0]['id']==r['id']
jobs=proofs['jobs'];assert jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'native-host','canary-attestor'}
byname={j['name']:j for j in jobs['jobs']}
for j in jobs['jobs']:assert j['run_id']==r['id'] and j['head_sha']==r['head_sha'] and j['run_attempt']==1 and j['status']=='completed' and j['conclusion']=='failure'
def step(job,name):
 rows=[s for s in job['steps'] if s['name']==name];assert len(rows)==1;return rows[0]
assert step(byname['native-host'],n.C_STEP)['conclusion']=='failure' and step(byname['native-host'],n.C_UPLOAD)['conclusion']=='success' and step(byname['native-host'],'Wait for approved A and run ABBA')['conclusion']=='skipped'
assert step(byname['canary-attestor'],'Attest completed native C evidence')['conclusion']=='failure' and step(byname['canary-attestor'],'Upload terminal C attestation')['conclusion']=='skipped'
assert proofs['artifacts']['total_count']==2
request_raw=subprocess.check_output(['git','show',reg['activation_sha']+':'+n.C_REQUEST],cwd=root);request=n.validate_request(n.image.parse(request_raw),root)
assert n.sha(request_raw)==reg['request_sha256'] and request['reviewed_source_sha']==reg['source_sha'] and len(request['source_closure'])==235
parents=subprocess.check_output(['git','show','-s','--format=%P',reg['activation_sha']],cwd=root).decode().strip().split()
changes=subprocess.check_output(['git','diff','--name-status','-z',reg['source_sha'],reg['activation_sha']],cwd=root)
n.validate_activation(request,reg['activation_sha'],parents,changes,'100644',n.BRANCH)
for p,d in request['source_closure'].items():
 assert n.sha(subprocess.check_output(['git','show',reg['source_sha']+':'+p],cwd=root))==d
 assert n.sha(subprocess.check_output(['git','show',reg['activation_sha']+':'+p],cwd=root))==d
qdir=root/'output/stage7-source-qualification/held-abba-v1'/reg['source_sha']
ci=[{k:load(qdir/(str(c['run_id'])+'-'+k+'.json')) for k in ('run','jobs','artifacts')} for c in request['source_ci']]
n.validate_source_ci(request,ci)
results={};members={};snapshots={};counterfactuals={}
for a in proofs['artifacts']['artifacts']:
 assert a['name'] in (n.artifact('canary'),n.artifact('attestor-diagnostics')) and a['expired'] is False and a['workflow_run']['id']==r['id'] and a['workflow_run']['head_sha']==r['head_sha'] and a['workflow_run']['head_branch']==n.BRANCH
 p=out/(a['name']+'.original.zip');assert p.stat().st_size==a['size_in_bytes'] and n.sha(p.read_bytes())==a['digest'][7:]
 manifest=load(out/(a['name']+'.members.json'));assert manifest['artifact_id']==a['id'] and manifest['zip_sha256']==a['digest'][7:]
 expected={v['path']:v for v in manifest['entries']};names=set()
 with zipfile.ZipFile(p) as z:
  for info in z.infolist():
   name=info.orig_filename;path=PurePosixPath(name);assert name==info.filename and name not in names and str(path)==name and not path.is_absolute() and all(v not in ('','.','..') for v in name.split('/')) and '\\' not in name and not info.flag_bits&1 and stat.S_IFMT(info.external_attr>>16) in (0,stat.S_IFREG)
   names.add(name);b=z.read(info);assert len(b)==info.file_size==expected[name]['nbytes'] and n.sha(b)==expected[name]['sha256']
   selected=out/'selected'/a['name']/name
   if selected.exists():assert selected.read_bytes()==b
  assert names==set(expected)
  result=n.image.parse(z.read('result.json'));assert result['status']=='FAILED_OR_INCOMPLETE' and result['last_stage']=='producer-authentication' and result['official_model_calls']==result['ort_sessions']==0
  if a['name']==n.artifact('canary'):
   assert result['elapsed_seconds']<2 and result['native_failure_summary']['provider_bounds']==[0,4] and result['scientific_result_promoted'] is False
  else:assert result['native_providers']==0 and result['independent_pixel_replay'] is False
  assert not any(name.startswith(('docker/','binding/','output/')) or name in ('host-lease.json','source-authentication.json','consumed-request.json','controller.json') for name in names)
  recorded={k:n.image.parse(z.read('api/'+v)) for k,v in [('run','live-run.json'),('workflow','live-workflow.json'),('unique','live-unique-00.json')]}
  assert recorded['run']['id']==r['id'] and recorded['run']['status']=='queued' and recorded['run']['head_sha']==r['head_sha'] and recorded['run']['run_attempt']==1 and recorded['run']['conclusion'] is None
  assert recorded['unique']['total_count']==1 and recorded['unique']['workflow_runs'][0]['id']==r['id']
  ctx=dict(repository=n.REPOSITORY,event='push',attempt=1,run_id=r['id'],head_sha=r['head_sha'])
  try:n.validate_live(request,ctx,recorded['run'],recorded['workflow'],recorded['unique'])
  except ValueError:pass
  else:raise AssertionError('original queued snapshot unexpectedly admitted')
  hypothetical=copy.deepcopy(recorded['run']);hypothetical['status']='in_progress'
  n.validate_live(request,ctx,hypothetical,recorded['workflow'],recorded['unique'])
  results[a['name']]=result;members[a['name']]=len(names);snapshots[a['name']]=recorded['run']['status'];counterfactuals[a['name']]='ONLY_STATUS_CHANGED_IN_MEMORY_PASSES_PURE_GATE_NOT_OBSERVED'
assert not (root/n.A_REQUEST).exists()
report=dict(schema='engine-clock-held-abba-terminal-root-acceptance-v1',status='AUTHENTICATED_TERMINAL_QUEUED_API_ADMISSION_FAILURE',source_sha=reg['source_sha'],activation_sha=reg['activation_sha'],request_sha256=reg['request_sha256'],source_closure_files=235,run_id=r['id'],workflow_id=r['workflow_id'],jobs={k:j['id'] for k,j in byname.items()},artifacts=[dict(id=a['id'],name=a['name'],nbytes=a['size_in_bytes'],sha256=a['digest'][7:]) for a in proofs['artifacts']['artifacts']],members=members,recorded_live_status=snapshots,counterfactual_pure_gate=counterfactuals,results=results,first_rejected_boundary='validate_live_requires_in_progress_but_original_successful_API_snapshot_is_queued',controller_stage='producer-authentication',source_backed_native_counts=dict(image_loads=0,containers=0,native_starts=0,providers=0,capture_pairs=0,observer_getters=0),counts_are_os_attestation=False,original_generic_provider_bounds=[0,4],canary_accepted=False,attestor_accepted=False,abba_control_issued=False,abba_cases_status='NOT_RUN',six_comparisons_status='NOT_RUN',retry_performed=False,remaining_campaign_native_allowance=0,official_model_calls=0,ort_sessions=0,scientific_result_promoted=False,root_original_api_artifact_authenticated=True,fresh_raw_review_accepted=False)
(out/'root-acceptance.json').write_bytes(n.canonical(report));print(json.dumps({k:v for k,v in report.items() if k!='results'}))
