"""Finite Docker metadata/build/collection backend. Import performs no operations."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import time
from scripts import engine_clock_image_process as process
from scripts import engine_clock_image_archive as archive


def need(value):
    if not value:raise ValueError('IMAGE_DOCKER_REJECTED')


class Docker:
    def __init__(self,out,*,deadline,source_root=None):
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.deadline=deadline;self.source_root=Path(source_root) if source_root else None;self.counter=0;self.used=set()
        self.config=self.out/'offline-config';self.config.mkdir(mode=0o700)
        (self.config/'config.json').write_text('{"auths":{},"proxies":{}}\n')
        self.env={k:v for k,v in os.environ.items() if not k.startswith(('DOCKER_','GH_','GITHUB_','AWS_','AZURE_','OPENAI_','ANTHROPIC_')) and k.upper() not in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY')}
        from scripts.engine_clock_image_preparation import make_redactor
        self.redact=make_redactor(os.environ)
    def once(self,name):
        need(name not in self.used);self.used.add(name)
    def call(self,args,*,timeout=60,private=True,stdout_limit=4*1024**2,stdin=None,file_limit=None):
        self.counter+=1;left=min(timeout,self.deadline-time.perf_counter());need(left>0)
        result=process.capture(['docker','--host=unix:///var/run/docker.sock','--config',str(self.config),*args],self.out/('command-%03d'%self.counter),timeout=left,stdout_limit=stdout_limit if private else 512*1024,stderr_limit=1024**2 if private else 512*1024,stdin=stdin,env=self.env,keep_stdout=not private,keep_stderr=not private,redact=None if private else self.redact,file_size_limit=file_limit)
        need(result['status']=='EXITED' and result['returncode']==0 and result['streams_complete'] is True)
        return result
    def json(self,args):
        result=self.call(args)
        from scripts.engine_clock_image_preparation import parse
        return parse(result['_stdout'])
    def qualify(self,archive_path):
        from scripts.engine_clock_image_preparation import canonical,storage_union,parse
        from scripts.engine_clock_image_inventory import collect_host_profile
        fields=['Driver','DockerRootDir','ServerVersion','KernelVersion','OSType','Architecture','DefaultRuntime']
        template='{'+','.join('"'+k+'":{{json .'+k+'}}' for k in fields)+',"RuncCommit":{{json .RuncCommit.ID}}}'
        info=parse(self.call(['info','--format',template])['_stdout'])
        version=self.json(['version','--format','{{json .}}'])
        self.host=collect_host_profile()
        need(info['OSType']=='linux' and info['Architecture']=='x86_64' and info['KernelVersion']==self.host['release'])
        self.profile={'docker_client':version['Client']['Version'],'docker_server':version['Server']['Version'],'docker_api':version['Server'].get('ApiVersion',version['Server'].get('APIVersion')),'oci_runtime':info['DefaultRuntime']+':'+info['RuncCommit'],'storage_driver':info['Driver']}
        need(all(type(v) is str and 0<len(v)<=256 for v in self.profile.values()))
        rows=[]
        for label,path in [('archive',str(archive_path)),('docker',info['DockerRootDir'])]:
            try:
                s=os.stat(path);v=os.statvfs(path);row={'st_dev':s.st_dev,'free_bytes':v.f_bavail*v.f_frsize}
            except PermissionError:
                code='import os,json,sys;s=os.stat(sys.argv[1]);v=os.statvfs(sys.argv[1]);print(json.dumps({"st_dev":s.st_dev,"free_bytes":v.f_bavail*v.f_frsize}))'
                self.counter+=1
                r=process.capture(['sudo','-n','/usr/bin/python3','-I','-S','-B','-c',code,path],self.out/('command-%03d'%self.counter),timeout=10,stdout_limit=4096,stderr_limit=4096,env=self.env,keep_stdout=False,keep_stderr=False)
                need(r['returncode']==0 and r['streams_complete']);row=parse(r['_stdout'])
            rows.append({'label':label,**row})
        self.storage=storage_union(rows)
        (self.out/'qualification.json').write_bytes(canonical({'host':self.host,'engine':self.profile,'storage':self.storage}))
    def inspect_image(self,reference):
        values=self.json(['image','inspect',reference]);need(type(values) is list and len(values)==1);v=values[0]
        need(v['Os']=='linux' and v['Architecture']=='amd64' and archive._digest(v['Id']) and v['RootFS']['Type']=='layers')
        env={}
        for item in v['Config']['Env']:
            key,sep,value=item.partition('=');need(sep and key not in env);env[key]=value
        need(env in (archive.IMAGE_ENV,{'PATH':archive.IMAGE_ENV['PATH']}))
        return {'config_digest':v['Id'],'rootfs_diff_ids':v['RootFS']['Layers'],'platform':'linux/amd64','environment':env}
    def load_base(self,path,cid,diffs):
        self.once('base-load');self.call(['image','load','--input',str(path)],timeout=120,private=False)
        from scripts.engine_clock_image_preparation import BASE_TAG
        v=self.inspect_image(BASE_TAG);need(v['config_digest']==cid and v['rootfs_diff_ids']==diffs and v['environment']=={'PATH':archive.IMAGE_ENV['PATH']})
    def load(self,path,cid,diffs):
        self.once('image-load');self.call(['image','load','--input',str(path)],timeout=180,private=False)
        from scripts.engine_clock_image_preparation import IMAGE_TAG
        v=self.inspect_image(IMAGE_TAG);need(v['config_digest']==cid and v['rootfs_diff_ids']==diffs and v['environment']==archive.IMAGE_ENV);return v
    def build(self,context,source_sha):
        from scripts.engine_clock_image_preparation import IMAGE_TAG
        self.once('build');need(archive._hex(source_sha,40))
        iid=self.out/'iid'
        self.call(['build','--network=none','--pull=false','--platform=linux/amd64','--build-arg','SOURCE_SHA='+source_sha,'--tag',IMAGE_TAG,'--iidfile',str(iid),'--file',str(Path(context)/'Dockerfile'),str(context)],timeout=600,private=False)
        raw=iid.read_text().strip();need(archive._digest(raw));v=self.inspect_image(IMAGE_TAG);need(v['config_digest']==raw and v['environment']==archive.IMAGE_ENV);return v
    def save(self,image,path):
        from scripts.engine_clock_image_preparation import IMAGE_TAG
        self.once('save');self.call(['image','save','--output',str(path),IMAGE_TAG],timeout=180,private=False,file_limit=2*1024**3)
    def copied_tree(self,cid,remote,prefix,entries,name):
        target=self.out/(name+'.tar')
        result=self.call(['cp',cid+':'+remote,'-'],timeout=120,stdout_limit=512*1024**2)
        # Private binary bytes are retained only after successful bounded capture.
        raw=result['_stdout'];need(len(raw)<=512*1024**2)
        with target.open('xb') as f:f.write(raw)
        return archive.verify_tree_archive(target,entries,prefix=prefix,deadline=min(self.deadline,time.perf_counter()+180))
    def collect(self,image,request,*,expected_manifest=None,precheck=False):
        from scripts.engine_clock_image_preparation import SCRIPT_PATH,canonical,parse,normalize_launch
        self.once('container');nonce=secrets.token_hex(16);verify=expected_manifest is not None
        command=['-I','-S','-B',SCRIPT_PATH,'--verify' if verify else '--candidate','--nonce',nonce]
        if verify:command+=['--expected-sha',hashlib.sha256(expected_manifest).hexdigest(),'--expected-bytes',str(len(expected_manifest))]
        labels={'stage7.request':request['request_id'],'stage7.nonce':nonce,'stage7.source':request['reviewed_source_sha']}
        args=['create','--read-only','--network=none','--cap-drop=ALL','--security-opt=no-new-privileges','--ipc=private','--pids-limit=128','--memory=2147483648','--cpus=2','--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=67108864,mode=0700','--user=0:0','--workdir=/','--entrypoint=/opt/venv/bin/python']
        for k,v in labels.items():args+=['--label',k+'='+v]
        if verify:args+=['--interactive']
        cid=self.call([*args,image['config_digest'],*command])['_stdout'].decode().strip();need(archive._hex(cid))
        actual=self.json(['container','inspect',cid]);need(len(actual)==1)
        launch=normalize_launch(actual[0],{'config_digest':image['config_digest'],'request_id':request['request_id'],'source_sha':request['reviewed_source_sha'],'command':command},nonce)
        (self.out/'launch.json').write_bytes(canonical(launch))
        copied=[]
        if precheck:
            need(self.source_root is not None)
            names=['__init__.py','engine_clock_runtime_inventory.py','engine_clock_image_inventory.py','engine_clock_image_installer.py']
            entries=[]
            for name in names:
                raw=(self.source_root/'scripts'/name).read_bytes()
                entries.append({'path':'scripts/'+name,'kind':'file','mode':0o644,'nbytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
            copied.append(self.copied_tree(cid,'/usr/local/libexec/stage7','stage7',entries,'copied-code'))
            members=parse((self.source_root/'docs/evidence/engine-clock-python-bootstrap/archive-members.json').read_bytes())['entries']
            copied.append(self.copied_tree(cid,'/opt/python','python',members,'copied-python'))
        inp=None
        try:
            if verify:
                path=self.out/'expected-manifest.json';path.write_bytes(expected_manifest);inp=path.open('rb')
            r=self.call(['start','--attach',*(['--interactive'] if verify else []),cid],timeout=180,stdout_limit=16*1024**2,stdin=inp)
        except Exception:
            # Bound the owned container lifetime; retain the stopped container, never remove it.
            try:self.call(['stop','--time=2',cid],timeout=5,private=True)
            except Exception:
                try:self.call(['kill',cid],timeout=5,private=True)
                except Exception:pass
            raise
        finally:
            if inp is not None:inp.close()
        state=self.json(['container','inspect','--format','{{json .State}}',cid])
        need(state['Status']=='exited' and state['Running'] is False and state['ExitCode']==0 and state['OOMKilled'] is False)
        summary=parse(r['_stderr']);need(summary['nonce']==nonce and summary['host']==self.host)
        (self.out/'collector-summary.json').write_bytes(canonical(summary))
        (self.out/'collector-stdout.bin').write_bytes(r['_stdout'])
        if verify:
            result=parse(r['_stdout']);need(result['status']=='INSTALLED_FILES_MATCH')
            return {'result':result,'summary':summary,'launch':launch,'copied_trees':copied}
        return {'manifest_raw':r['_stdout'],'summary':summary,'launch':launch}
