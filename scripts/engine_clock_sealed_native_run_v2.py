"""Authenticated one-use outer controller. No action occurs on import."""
import datetime
import os
from pathlib import Path
import secrets
import subprocess
import sys
from time import perf_counter

if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import engine_clock_sealed_native_v2 as n
from scripts.engine_clock_image_backend_v2 import Docker
from scripts.engine_clock_image_staging_v3 import RetainedClient


def authenticate_delta(client,request,head,tree):
    source=request['reviewed_source_sha']
    commit=client.get_json('git/commits/'+head,'activation-commit.json')
    n.need(commit['sha']==head and [p['sha'] for p in commit['parents']]==[source] and commit['tree']['sha']==tree)
    comparison=client.get_json('compare/'+source+'...'+head,'activation-compare.json')
    n.need(comparison['status']=='ahead' and comparison['ahead_by']==1 and comparison['behind_by']==0
           and comparison['total_commits']==1 and comparison['base_commit']['sha']==source
           and comparison['merge_base_commit']['sha']==source and len(comparison['commits'])==1
           and comparison['commits'][0]['sha']==head and len(comparison['files'])==1
           and comparison['files'][0]['filename']==n.REQUEST and comparison['files'][0]['status']=='added')


def launch_canary(engine,image,request,context,receipt,manifest_raw,work,root):
    """Stopped-container proof precedes the only native start; finite cleanup owns it."""
    work=Path(work);root=Path(root);nonce=secrets.token_hex(16)
    routes={'repo':str(root.resolve())}
    for name in ('binding','output','cache'):
        path=work/name;mode=0o755 if name=='binding' else 0o777
        # UID0 has no DAC capabilities. Fresh dedicated mounts must explicitly
        # allow its ordinary-other access; source and binding remain mount-RO.
        path.mkdir(mode=mode);path.chmod(mode)
        n.need(path.stat().st_mode&0o777==mode);routes[name]=str(path.resolve())
    identity=n.make_identity(receipt,request['image_evidence']['expected'],engine.host,engine.profile)
    binding=dict(schema='engine-clock-sealed-native-binding-v1',request=request,context=context,
                 receipt=receipt,identity=identity,host=engine.host,engine=engine.profile,
                 outer_provenance={k:os.environ.get(k) for k in ('ImageOS','ImageVersion')})
    (work/'binding'/'binding.json').write_bytes(n.canonical(binding))
    (work/'binding'/'installed-files.json').write_bytes(manifest_raw)
    for name in ('binding.json','installed-files.json'):(work/'binding'/name).chmod(0o644)
    engine.once('native-container')
    args=['create','--read-only','--network=none','--cap-drop=ALL','--security-opt=no-new-privileges',
          '--ipc=private','--pids-limit=128','--memory=2147483648','--cpus=2','--tmpfs','/tmp:'+n.TMPFS,
          '--user=0:0','--workdir=/work/repo','--hostname=stage7-sealed-native','--entrypoint=/opt/venv/bin/python']
    for key,value in n.environment_profile().items():args+=['--env',key+'='+value]
    for key,value in {'stage7.request':n.ID,'stage7.nonce':nonce,'stage7.source':request['reviewed_source_sha']}.items():args+=['--label',key+'='+value]
    for key,source in routes.items():
        n.need(source.startswith('/') and ',' not in source and '\n' not in source)
        args+=['--mount','type=bind,src='+source+',dst=/work/'+key+(',readonly' if key in ('repo','binding') else '')]
    cid=engine.call([*args,image['config_digest'],*n.CONTAINER_COMMAND])['_stdout'].decode().strip()
    n.need(n.image._hex(cid));copied=[]
    original_deadline=engine.deadline
    try:
        engine.deadline=min(original_deadline,perf_counter()+n.BUDGET['prestart_seconds'])
        # Prove the executable/stdlib and collector code without starting the image.
        names=['__init__.py','engine_clock_runtime_inventory.py','engine_clock_image_inventory.py','engine_clock_image_installer.py']
        entries=[]
        for name in names:
            raw=n.image.read_regular(root/'scripts'/name)
            entries.append(dict(path='scripts/'+name,kind='file',mode=0o644,nbytes=len(raw),sha256=n.sha(raw)))
        copied.append(engine.copied_tree(cid,'/usr/local/libexec/stage7','stage7',entries,'copied-code'))
        members=n.image.parse(n.image.read_regular(root/'docs/evidence/engine-clock-python-bootstrap/archive-members.json'))['entries']
        copied.append(engine.copied_tree(cid,'/opt/python','python',members,'copied-python'))
        layout=n.image.parse(n.image.read_regular(root/n.image.LAYOUT_PATH))
        copied.append(engine.copied_tree(cid,'/opt/venv/bin/python','python',layout['expected_members']['bin/python3.11'],'copied-executable'))
        engine.deadline=original_deadline
        raw=engine.json(['container','inspect',cid]);n.need(len(raw)==1)
        expected=dict(config_digest=image['config_digest'],nonce=nonce,source_sha=request['reviewed_source_sha'])
        (work/'launch-diagnostics.json').write_bytes(n.canonical(n.launch_diagnostics(raw[0],routes,expected)))
        launch=n.validate_launch(raw[0],routes,expected)
        (work/'launch.json').write_bytes(n.canonical(dict(launch,copied_trees=copied)))
        engine.once('native-start')
        engine.call(['start','--attach',cid],timeout=n.BUDGET['container_seconds'],stdout_limit=n.MIB)
        state=engine.json(['container','inspect','--format','{{json .State}}',cid])
        n.need(state['Status']=='exited' and state['Running'] is False and state['ExitCode']==0 and state['OOMKilled'] is False)
        phase=n.image.parse(n.image.read_regular(work/'output'/'phase.json'))
        n.need(phase['status']=='SEALED_NATIVE_CANARY_RECORDED' and phase['identity']==identity
               and phase['context']==context and phase['official_model_calls']==0 and phase['ort_sessions']==0)
        result=dict(schema='engine-clock-sealed-native-controller-v1',status='SEALED_NATIVE_CANARY_RECORDED',
                    context=context,identity=identity,launch=launch,copied_trees=copied,state=state,
                    phase_sha256=n.sha(n.image.read_regular(work/'output'/'phase.json')),
                    official_model_calls=0,ort_sessions=0,scientific_result_promoted=False)
        (work/'controller.json').write_bytes(n.canonical(result))
        return result
    except BaseException:
        engine.deadline=original_deadline
        engine.terminate(cid)
        raise


def run():
    root=Path(__file__).resolve().parents[1];started=perf_counter();stop=started+n.BUDGET['total_seconds']
    def git(*args):
        r=subprocess.run(['git','-C',str(root),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
        n.need(r.returncode==0 and len(r.stdout)<=16*n.MIB);return r.stdout
    raw=n.image.read_regular(root/n.REQUEST);request=n.validate_request(n.image.parse(raw),root)
    out=root/n.OUTPUT;out.mkdir(parents=True,mode=0o700,exist_ok=False)
    work=out/'execution';work.mkdir(mode=0o700);(work/'consumed-request.json').write_bytes(raw)
    stage='source-authentication';status='FAILED_OR_INCOMPLETE';error_type=None
    try:
        head=git('rev-parse','HEAD').decode().strip();n.need(head==os.environ['GITHUB_SHA'])
        n.need(not git('status','--porcelain','--untracked-files=no'))
        header=git('cat-file','-p',head).split(b'\n\n',1)[0].splitlines()
        parents=[row[7:].decode() for row in header if row.startswith(b'parent ')]
        mode=git('ls-tree',head,'--',n.REQUEST).decode().split()[0]
        n.validate_activation(request,head,parents,b'A\0'+n.REQUEST.encode()+b'\0',mode,os.environ['GITHUB_REF_NAME'])
        n.need(raw==git('show',head+':'+n.REQUEST));n.verify_sources(root,request['source_closure'])
        client=RetainedClient(work/'api',repository=n.REPOSITORY,token=os.environ['GH_TOKEN'],
               deadline=min(stop,started+n.BUDGET['download_seconds']),max_requests=n.BUDGET['http_gets'],max_payload_bytes=n.BUDGET['payload_bytes'])
        ctx=dict(repository=n.REPOSITORY,event=os.environ['GITHUB_EVENT_NAME'],attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),run_id=int(os.environ['GITHUB_RUN_ID']),head_sha=head)
        rid=ctx['run_id'];live=client.get_json('actions/runs/'+str(rid),'live-run.json');wid=live['workflow_id']
        wf=client.get_json('actions/workflows/'+str(wid),'live-workflow.json')
        unique,visibility=n.image.observe_unique(client,'actions/workflows/'+str(wid)+'/runs?branch='+n.BRANCH+'&event=push&per_page=100')
        n.validate_live(request,ctx,live,wf,unique)
        authenticate_delta(client,request,head,git('rev-parse','HEAD^{tree}').decode().strip())
        proofs=[]
        for ci in request['source_ci']:
            id=str(ci['run_id']);prefix='source-'+ci['event']
            proofs.append({key:client.get_json(endpoint,prefix+'-'+key+'.json') for key,endpoint in [('run','actions/runs/'+id),('jobs','actions/runs/'+id+'/jobs?per_page=100'),('artifacts','actions/runs/'+id+'/artifacts?per_page=100')]})
        n.validate_source_ci(request,proofs)
        context=dict(ctx,workflow_id=wid,source_sha=request['reviewed_source_sha'],request_sha256=n.sha(raw),
                     source_closure_verified=True,authenticated_api_origin='https://api.github.com',workflow_visibility=visibility)
        (work/'source-authentication.json').write_bytes(n.canonical(context))
        stage='image-authentication'
        # Authenticate the old producer against its own frozen source, separately
        # from this new canary source. No old native authorization is involved.
        old_request=n.image.parse(n.image.read_regular(root/(n.AUTH+'preflight-request.json')))
        directory,receipt,manifest,checked=n.image.authenticate_image(client,old_request,work,root)
        stage='engine-qualification';engine=Docker(work/'docker',deadline=stop,source_root=root);engine.qualify(out)
        stage='one-image-load';image=engine.load(directory/'image.tar',receipt['config_digest'],receipt['rootfs_diff_ids'])
        stage='one-native-canary';result=launch_canary(engine,image,request,context,receipt,manifest,work,root)
        status=result['status'];return 0
    except Exception as exc:error_type=type(exc).__name__;return 1
    finally:
        report=dict(schema='engine-clock-sealed-native-operation-v1',status=status,last_stage=stage,error_type=error_type,
                    elapsed_seconds=perf_counter()-started,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    request_id=n.ID,official_model_calls=0,ort_sessions=0,scientific_result_promoted=False,
                    provider_attempts='SEE_BOUND_CHILD_LEDGER_OR_UNKNOWN_0_TO_1')
        (work/'result.json').write_bytes(n.canonical(report));print(n.canonical(report).decode())


def main():
    try:
        n.need(sys.argv[1:]==['--run'] and os.environ.get('GITHUB_ACTIONS')=='true'
            and os.environ.get('GITHUB_REPOSITORY')==n.REPOSITORY and os.environ.get('GITHUB_EVENT_NAME')=='push'
            and os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and os.environ.get('GITHUB_REF_NAME')==n.BRANCH)
        return run()
    except Exception:print('SEALED_NATIVE_REJECTED');return 1


if __name__=='__main__':raise SystemExit(main())
