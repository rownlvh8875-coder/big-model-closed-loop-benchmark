"""Authenticate a new canary's external identity and bounded original ZIP as data."""
import hashlib
from pathlib import Path
import stat
import zipfile
from scripts import engine_clock_sealed_abba_v2 as n


def validate_accepted_api(a,run,jobs,artifact,*,workflow_id):
    n.validate_acceptance(a,a['source_sha'])
    n.need(run['id']==a['run_id'] and run['head_sha']==a['canary_head_sha']
        and run['head_branch']==n.BRANCH and run['workflow_id']==workflow_id==a['workflow_id']
        and run['path']==n.WORKFLOW and run['event']=='push' and n.exact(run['run_attempt'],1)
        and run['status']=='completed' and run['conclusion']=='success'
        and run['repository']['full_name']==n.REPOSITORY)
    n.need(n.exact(jobs['total_count'],1) and len(jobs['jobs'])==1)
    job=jobs['jobs'][0]
    n.need(job['id']==a['job_id'] and job['run_id']==a['run_id'] and job['name']=='campaign'
        and job['head_sha']==a['canary_head_sha'] and n.exact(job['run_attempt'],1)
        and job['status']=='completed' and job['conclusion']=='success')
    wr=artifact['workflow_run']
    n.need(artifact['id']==a['artifact_id'] and artifact['name']==a['artifact_name']
        and artifact['expired'] is False and n.exact(artifact['size_in_bytes'],a['artifact_size_bytes'])
        and artifact['digest']=='sha256:'+a['artifact_sha256']
        and wr['id']==a['run_id'] and wr['head_sha']==a['canary_head_sha'] and wr['head_branch']==n.BRANCH
        and wr.get('repository_id',run['repository']['id'])==run['repository']['id'])


ROOT_RECORDS={'consumed-request.json','controller.json','result.json','source-authentication.json'}


def audit_archive(path,dest,*,total_limit=1024*n.MIB):
    """Read every original member/CRC, retaining only data under a fresh directory."""
    path=Path(path);dest=Path(dest)
    n.need(path.is_file() and not path.is_symlink() and path.stat().st_size<=512*n.MIB)
    n.need(not dest.exists());dest.mkdir(parents=True,mode=0o755)
    members={};selected=0;total=0
    with zipfile.ZipFile(path) as z:
        rows=z.infolist();n.need(0<len(rows)<=256)
        for row in rows:
            name=row.orig_filename;parts=name.split('/')
            n.need(name==row.filename and type(name) is str and len(name.encode())<=4096 and not name.startswith('/')
                and '\\' not in name and all(v not in ('','.','..') for v in parts)
                and all(ord(c)>=32 and ord(c)!=127 for c in name)
                and name not in members and not row.is_dir() and not row.flag_bits&1)
            kind=stat.S_IFMT(row.external_attr>>16)
            n.need(kind in (0,stat.S_IFREG) and 0<=row.file_size<=512*n.MIB)
            total+=row.file_size;n.need(total<=total_limit)
            keep=name.startswith('output/') or name in ROOT_RECORDS
            if keep:
                n.need(row.file_size<=n.BUDGET['case_bytes'])
                target=dest.joinpath(*parts);target.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
                # An earlier file at a parent component cannot become a directory.
                n.need(not target.exists() and not target.is_symlink())
                output=target.open('xb')
            else:output=None
            digest=hashlib.sha256();count=0
            try:
                with z.open(row) as stream:
                    while True:
                        block=stream.read(n.MIB)
                        if not block:break
                        count+=len(block);n.need(count<=row.file_size)
                        digest.update(block)
                        if output is not None:output.write(block)
            finally:
                if output is not None:output.close()
            n.need(count==row.file_size)
            if keep:target.chmod(0o644);selected+=1
            members[name]=dict(nbytes=count,sha256=digest.hexdigest(),selected=keep)
    return dict(members=len(members),selected_members=selected,uncompressed_bytes=total,files=members)


def stage_accepted_archive(path,dest,a,request):
    path=Path(path)
    n.need(path.stat().st_size==a['artifact_size_bytes'])
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            block=stream.read(n.MIB)
            if not block:break
            digest.update(block)
    n.need(digest.hexdigest()==a['artifact_sha256'])
    report=audit_archive(path,dest)
    dest=Path(dest)
    def read(name):return n.image.parse(n.image.read_regular(dest/name,2*n.MIB))
    consumed=read('consumed-request.json');phase=read('output/phase.json')
    controller=read('controller.json');result=read('result.json');source=read('source-authentication.json')
    expected=dict(request,mode='canary',acceptance=None,native_budget=n.native_budget('canary'))
    n.need(n.exact(consumed,expected))
    context=phase['context']
    for key,value in dict(repository=n.REPOSITORY,event='push',attempt=1,run_id=a['run_id'],
        workflow_id=a['workflow_id'],head_sha=a['canary_head_sha'],source_sha=a['source_sha'],
        source_closure_verified=True,authenticated_api_origin='https://api.github.com',
        request_sha256=n.sha(n.image.read_regular(dest/'consumed-request.json'))).items():
        n.need(n.exact(context[key],value))
    n.need(n.exact(source,context) and n.exact(controller['context'],context))
    for record in (phase,controller,result):
        n.need(record['status']=='SEALED_ABBA_CANARY_RECORDED' and record['official_model_calls']==0
            and record['ort_sessions']==0 and record['scientific_result_promoted'] is False)
    n.need(phase['mode']=='canary' and phase['identity_verified'] is True and len(phase['launches'])==1 and phase['comparisons']==[]
        and phase['native_budget']==n.native_budget('canary') and phase['budget']==n.BUDGET
        and n.exact(controller['identity'],phase['identity'])
        and controller['phase_sha256']==n.sha(n.image.read_regular(dest/'output/phase.json'))
        and controller['state']['ExitCode']==0 and controller['state']['Running'] is False
        and controller['state']['OOMKilled'] is False)
    return dict(schema='sealed-abba-canary-archive-v1',api_identity=a,context=context,
                identity=phase['identity'],source_closure=consumed['source_closure'],archive=report,
                raw_case_replay_required_before_abba_provider=True)


def authenticate_canary(client,request,context,work):
    """All network actions use the bounded, externally authenticated existing client."""
    a=request['acceptance'];n.need(request['mode']=='abba')
    rid=str(a['run_id']);aid=str(a['artifact_id'])
    run=client.get_json('actions/runs/'+rid,'accepted-canary-run.json')
    jobs=client.get_json('actions/runs/'+rid+'/jobs?per_page=100','accepted-canary-jobs.json')
    artifact=client.get_json('actions/artifacts/'+aid,'accepted-canary-artifact.json')
    validate_accepted_api(a,run,jobs,artifact,workflow_id=context['workflow_id'])
    # Client transport follows its registered artifact URL, bounded by exact size.
    path=Path(work)/'accepted-canary.original.zip'
    client.download('https://api.github.com/repos/'+n.REPOSITORY+'/actions/artifacts/'+aid+'/zip',
                    path,nbytes=a['artifact_size_bytes'],sha256=a['artifact_sha256'],kind='artifact')
    return stage_accepted_archive(path,Path(work)/'accepted-canary',a,request)
