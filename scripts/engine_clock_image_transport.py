"""Finite HTTPS data transfer with query/auth sanitization and retained partial files."""
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import ssl
from time import monotonic
import urllib.error
import urllib.parse
import urllib.request


def _need(value):
    if not value:raise ValueError('IMAGE_TRANSPORT_REJECTED')


def _pairs(rows):
    result={}
    for k,v in rows:_need(k not in result);result[k]=v
    return result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class Client:
    def __init__(self,out:Path,*,repository,token,deadline,max_requests=384,max_payload_bytes=1536*1024**2,opener=None):
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True,mode=0o700);_need(not self.out.is_symlink())
        self.repository=repository;self.token=token;self.registry_token=None;self.deadline=deadline;self.max_requests=max_requests;self.max_payload_bytes=max_payload_bytes;self.requests=0;self.payload_bytes=0;self.json_bytes=0;self.events=[];self.errors=[]
        context=ssl.create_default_context();_need(context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED)
        self.opener=opener or urllib.request.build_opener(_NoRedirect(),urllib.request.HTTPSHandler(context=context))
    def _url(self,url,kind):
        p=urllib.parse.urlsplit(url);_need(p.scheme=='https' and p.hostname and p.port in (None,443) and p.username is None and p.password is None and not p.fragment)
        if kind in ('api','artifact'):
            _need(p.hostname=='api.github.com' and p.path.startswith('/repos/'+self.repository+'/'))
        elif kind=='token':_need(p.hostname=='auth.docker.io' and p.path=='/token')
        elif kind=='registry':_need(p.hostname=='registry-1.docker.io' or p.hostname.endswith(('.docker.com','.cloudflarestorage.com')))
        elif kind=='asset':_need(p.hostname in ('github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'))
        elif kind=='public':_need(p.hostname in ('files.pythonhosted.org','snapshot.ubuntu.com'))
        elif kind=='artifact-blob':_need(p.hostname.endswith(('.blob.core.windows.net','.actions.githubusercontent.com','.githubusercontent.com')))
        else:raise ValueError('IMAGE_TRANSPORT_REJECTED')
        return p
    def _open(self,url,kind):
        self._url(url,kind);headers={'Accept-Encoding':'identity','User-Agent':'engine-clock-sealed-inputs/1'}
        if kind in ('api','artifact') and self.token:headers['Authorization']='Bearer '+self.token
        elif kind=='registry' and self.registry_token:headers['Authorization']='Bearer '+self.registry_token
        hops=[];origin_kind=kind
        while True:
            _need(monotonic()<self.deadline and self.requests<self.max_requests);self.requests+=1
            try:return self.opener.open(urllib.request.Request(url,headers=headers),timeout=min(20,max(.1,self.deadline-monotonic()))),hops
            except urllib.error.HTTPError as err:
                if err.code not in (301,302,303,307,308) or origin_kind not in ('artifact','asset','registry'):raise
                _need(len(hops)<3);target=urllib.parse.urljoin(url,err.headers['Location']);nextkind='artifact-blob' if origin_kind=='artifact' else origin_kind;p=self._url(target,nextkind)
                hops.append({'http_status':err.code,'from_host':urllib.parse.urlsplit(url).hostname,'to_host':p.hostname,'authorization_forwarded':False});err.close();headers={k:v for k,v in headers.items() if k!='Authorization'};url=target;kind=nextkind
    def _event(self,url,record):
        p=urllib.parse.urlsplit(url);row={'source_url':urllib.parse.urlunsplit((p.scheme,p.hostname or '',p.path,'','')),**record};self.events.append(row)
        with (self.out/'http-events.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n')
        return row
    def _json_url(self,url,name,kind='api'):
        path=None
        try:
            if name is not None:_need(Path(name).name==name);path=self.out/name;_need(not path.exists() and not path.is_symlink())
            start=monotonic();response,hops=self._open(url,kind);raw=bytearray()
            with response:
                _need(response.status==200)
                while True:
                    _need(monotonic()<self.deadline);block=response.read(min(65536,4*1024**2-len(raw)+1))
                    if not block:break
                    raw.extend(block);_need(len(raw)<=4*1024**2 and self.json_bytes+len(raw)<=64*1024**2)
            body=bytes(raw);self.json_bytes+=len(body)
            if path is not None:
                with path.open('xb') as f:f.write(body)
            self._event(url,{'http_status':200,'nbytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'redirects':hops,'seconds':monotonic()-start,'raw_body_preserved':path is not None,'tls_default_context_verified':True})
            return json.loads(body,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('IMAGE_TRANSPORT_REJECTED')))
        except Exception as exc:
            self.errors.append({'stage':'json','http_status':exc.code if isinstance(exc,urllib.error.HTTPError) else None})
            if path is not None and 'raw' in locals() and raw and not path.exists():
                with path.with_name(path.name+'.partial').open('xb') as f:f.write(raw)
            raise ValueError('IMAGE_TRANSPORT_REJECTED') from None
    def get_json(self,endpoint,name):
        _need(type(endpoint) is str and not endpoint.startswith('/') and '..' not in endpoint.split('/'))
        return self._json_url('https://api.github.com/repos/'+self.repository+'/'+endpoint,name)
    def registry_authenticate(self):
        result=self._json_url('https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/ubuntu:pull',None,'token');_need(type(result.get('token')) is str and len(result['token'])<=20000);self.registry_token=result['token']
    def download(self,url,path:Path,*,nbytes,sha256,kind):
        path=Path(path);partial=path.with_name(path.name+'.partial')
        try:
            _need(type(nbytes) is int and 0<nbytes<=2*1024**3 and type(sha256) is str and re.fullmatch('[0-9a-f]{64}',sha256) is not None and not path.exists() and not path.is_symlink() and not partial.exists())
            path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);start=monotonic();response,hops=self._open(url,kind);digest=hashlib.sha256();count=0
            with response,partial.open('xb') as target:
                _need(response.status==200)
                if response.headers.get('Content-Length') is not None:_need(int(response.headers['Content-Length'])==nbytes)
                while True:
                    _need(monotonic()<self.deadline);block=response.read(min(1024**2,nbytes-count+1))
                    if not block:break
                    count+=len(block);self.payload_bytes+=len(block);_need(count<=nbytes and self.payload_bytes<=self.max_payload_bytes);target.write(block);digest.update(block)
            _need(count==nbytes and digest.hexdigest()==sha256);partial.rename(path)
            return self._event(url,{'http_status':200,'nbytes':count,'sha256':digest.hexdigest(),'redirects':hops,'seconds':monotonic()-start,'raw_body_preserved':True,'tls_default_context_verified':True})
        except Exception as exc:
            self.errors.append({'stage':'payload','http_status':exc.code if isinstance(exc,urllib.error.HTTPError) else None})
            raise ValueError('IMAGE_TRANSPORT_REJECTED') from None
