"""Concurrent stdlib-only C completion attestor. Never starts a native provider."""
import datetime
import os
from pathlib import Path
import sys
import time
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import renderer_pipeline_sealed_v1 as n
from scripts import renderer_pipeline_sealed_v1_lifecycle as life
from scripts import renderer_pipeline_sealed_v1_archive as archive
from scripts.engine_clock_image_staging_v3 import RetainedClient


def canary_ready(jobs,context):
    n.need(type(jobs['jobs']) is list and jobs['total_count']==len(jobs['jobs'])<=2)
    names=[j['name'] for j in jobs['jobs']]
    n.need(len(names)==len(set(names)) and set(names)<={'native-host','canary-attestor'})
    for job in jobs['jobs']:
        n.need(job['run_id']==context['run_id'] and job['head_sha']==context['head_sha'] and n.exact(job['run_attempt'],1))
    hosts=[j for j in jobs['jobs'] if j['name']=='native-host']
    if not hosts:return False
    host=hosts[0]
    n.need(host['status']!='completed')
    for name in (n.C_STEP,n.C_UPLOAD):
        rows=[s for s in host['steps'] if s['name']==name];n.need(len(rows)<=1)
        if not rows:return False
        step=rows[0]
        if step['status']!='completed':return False
        n.need(step['conclusion']=='success')
    return host['status']=='in_progress'


def run():
    root=Path(__file__).resolve().parents[1];started=time.monotonic();stop=started+n.LIFECYCLE['attestor_seconds']
    out=root/n.OUTPUT/'attestor';out.mkdir(parents=True,mode=0o700,exist_ok=False)
    diagnostics=out/'diagnostics';diagnostics.mkdir(mode=0o700)
    stage='producer-authentication';status='FAILED_OR_INCOMPLETE';error=None
    try:
        with n.image.inventory.core._absolute_deadline(stop):
            n.need(not any(k.split('.',1)[0] in {'numpy','cv2','panda3d','metadrive','onnxruntime'} for k in sys.modules))
            client=RetainedClient(diagnostics/'api',repository=n.REPOSITORY,token=os.environ['GH_TOKEN'],
                deadline=stop,max_requests=n.LIFECYCLE['attestor_http_gets'],max_payload_bytes=n.LIFECYCLE['attestor_zip_bytes'])
            producer,raw,ctx=life.authenticate_producer(client,root,os.environ,'canary-attestor')
            (diagnostics/'attestor-source-authentication.json').write_bytes(n.canonical(ctx))
            stage='native-C-step-and-upload-completion';counter=[0]
            def fetch():return client.get_json('actions/runs/'+str(ctx['run_id'])+'/jobs?per_page=100','completion-jobs-%03d.json'%counter[0])
            def record(index,value):counter[0]=index+1
            jobs=life.bounded_poll(fetch,lambda v:canary_ready(v,ctx),record,
                seconds=n.LIFECYCLE['attestor_wait_seconds'],maximum=n.LIFECYCLE['control_snapshots'],deadline=min(stop,started+900))
            host=next(j for j in jobs['jobs'] if j['name']=='native-host')
            n.need(any(j['id']==ctx['job_id'] and j['name']=='canary-attestor' for j in jobs['jobs']))
            stage='original-C-artifact';counter=[0]
            def fetch_artifacts():return client.get_json('actions/runs/'+str(ctx['run_id'])+'/artifacts?per_page=100','canary-artifacts-%03d.json'%counter[0])
            def artifact_ready(value):
                n.need(value['total_count']==len(value['artifacts'])<=1)
                if not value['artifacts']:return False
                archive.artifact_api(value['artifacts'][0],ctx,n.artifact('canary'))
                n.need(value['artifacts'][0]['size_in_bytes']<=512*n.MIB)
                return True
            items=life.bounded_poll(fetch_artifacts,artifact_ready,record,seconds=30,maximum=7,deadline=stop)
            item=items['artifacts'][0];inputs=out/'inputs';inputs.mkdir(mode=0o700)
            path=inputs/'canary.original.zip'
            client.download('https://api.github.com/repos/'+n.REPOSITORY+'/actions/artifacts/'+str(item['id'])+'/zip',
                path,nbytes=item['size_in_bytes'],sha256=item['digest'][7:],kind='artifact')
            stage='original-native-C-metadata'
            checked=archive.validate_native_canary_archive(path,inputs/'selected',producer,dict(ctx,job_id=host['id']),item)
            (diagnostics/'checked-canary-metadata.json').write_bytes(n.canonical(checked))
            receipt=archive.attestation_record(checked,ctx['job_id'])
            (out/'canary-attestation.json').write_bytes(n.canonical(receipt))
            n.need(not any(k.split('.',1)[0] in {'numpy','cv2','panda3d','metadrive','onnxruntime'} for k in sys.modules))
            status='CANARY_PHASE_METADATA_AUTHENTICATED';return 0
    except Exception as exc:error=dict(type=type(exc).__name__,detail=str(exc)[:512]);return 1
    finally:
        result=dict(status=status,last_stage=stage,error=error,elapsed_seconds=time.monotonic()-started,
            finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),independent_pixel_replay=False,
            observed_installed_tree_here=False,native_providers=0,official_model_calls=0,ort_sessions=0)
        (diagnostics/'result.json').write_bytes(n.canonical(result));print(n.canonical(result).decode())


def main():
    try:
        n.need(sys.argv[1:]==['--run'] and os.environ.get('GITHUB_JOB')=='canary-attestor'
            and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')==n.REPOSITORY
            and os.environ.get('GITHUB_EVENT_NAME')=='push' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
            and os.environ.get('GITHUB_REF_NAME')==n.BRANCH)
        return run()
    except Exception:print('HELD_CANARY_ATTESTATION_REJECTED');return 1


if __name__=='__main__':raise SystemExit(main())
