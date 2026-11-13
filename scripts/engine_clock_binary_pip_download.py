"""Trusted pip26.2.2 launcher: reject source, editable and unapproved origin before preparation."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import urllib.parse
import pip

PREPARE_SHA='ccb9153120eef5c511d0a9c39b76d9dd0bc879a12b8492abaf5d3d5320cc94a4'
LOCAL_RELATIVE=('output/stage7-real-wheel-preparation/wheel-input-20261113-e369b2c18129/metadrive_simulator-0.4.3-1headless-py3-none-any.whl',
 'output/stage7-builder-directory-evidence/builder-20261113-07/progressbar-2.5-py3-none-any.whl')
OUTPUT='output/stage7-python-wheel-closure/python-lock-20261114-02'


class Gate:
    def __init__(self,root):
        self.local={str((root/p).absolute()) for p in LOCAL_RELATIVE}
        self.facts={'schema':'binary-pip-gate-v1','prepare_source_sha256':PREPARE_SHA,'gate_installed':False,'gate_restored':False,
                    'requirements_checked':0,'only_wheel_links_admitted':True,'only_allowed_origins_admitted':True,'rejections':[]}
    def reject(self,code):
        if len(self.facts['rejections'])<16:self.facts['rejections'].append(code)
        raise ValueError(code)
    def check(self,req):
        self.facts['requirements_checked']+=1
        if self.facts['requirements_checked']>1024:self.reject('WHEEL_ONLY_GATE_LIMIT')
        link=getattr(req,'link',None)
        if link is None or getattr(link,'is_wheel',None) is not True:self.reject('WHEEL_ONLY_SOURCE_REJECTED')
        url=urllib.parse.urlsplit(link.url_without_fragment)
        if getattr(link,'is_file',False):
            if url.scheme!='file' or url.netloc not in ('','localhost') or url.query or url.fragment or link.file_path not in self.local:self.reject('WHEEL_ONLY_LOCAL_INPUT_REJECTED')
        elif not (url.scheme=='https' and url.hostname=='files.pythonhosted.org' and url.port in (None,443) and url.username is None and url.password is None and not url.query and not url.fragment and urllib.parse.unquote(url.path.rsplit('/',1)[-1])==link.filename):self.reject('WHEEL_ONLY_ORIGIN_REJECTED')


@contextlib.contextmanager
def protect(cls,gate):
    names=('prepare_linked_requirement','prepare_linked_requirements_more','prepare_editable_requirement');originals={name:getattr(cls,name) for name in names}
    def linked(self,req,*args,**kwargs):gate.check(req);return originals['prepare_linked_requirement'](self,req,*args,**kwargs)
    def batch(self,reqs,*args,**kwargs):
        reqs=list(reqs)
        for req in reqs:gate.check(req)
        return originals['prepare_linked_requirements_more'](self,reqs,*args,**kwargs)
    def editable(self,req,*args,**kwargs):gate.reject('WHEEL_ONLY_EDITABLE_REJECTED')
    cls.prepare_linked_requirement=linked;cls.prepare_linked_requirements_more=batch;cls.prepare_editable_requirement=editable;gate.facts['gate_installed']=True
    try:yield
    finally:
        for name,fn in originals.items():setattr(cls,name,fn)
        gate.facts['gate_restored']=True


def validate_cli(arguments,out):
    from pip._internal.cli.main_parser import parse_command
    from pip._internal.commands import create_command
    name,args=parse_command(arguments)
    if name!='download':raise ValueError('UNSUPPORTED_BINARY_PIP_CONTEXT')
    opts,_=create_command(name,isolated=True).parse_args(args)
    if not (opts.index_url=='https://pypi.org/simple' and opts.extra_index_urls==[] and opts.trusted_hosts==[] and opts.find_links==[] and
            opts.format_control.only_binary=={':all:'} and not opts.ignore_dependencies and opts.download_dir==str(out/'wheels') and
            opts.requirements==[] and opts.constraints==[] and getattr(opts,'editables',[])==[] and opts.keyring_provider=='disabled'):
        raise ValueError('UNSUPPORTED_BINARY_PIP_CONTEXT')


def main():
    if len(sys.argv)<3 or sys.argv[1]!='--' or platform.python_version()!='3.11.17' or pip.__version__!='26.2.2' or not sys.flags.isolated or not sys.flags.dont_write_bytecode:return 2
    root=Path(__file__).resolve().parent.parent;out=root/OUTPUT;gate=Gate(root);code=2
    try:
        from pip._internal.cli.main import main as pip_main
        from pip._internal.operations import prepare
        if hashlib.sha256(Path(prepare.__file__).read_bytes()).hexdigest()!=PREPARE_SHA:raise ValueError('UNSUPPORTED_BINARY_PIP_CONTEXT')
        validate_cli(sys.argv[2:],out)
        with protect(prepare.RequirementPreparer,gate):code=pip_main(sys.argv[2:])
    except Exception:
        print('BINARY_ONLY_GATE_REJECTED');code=2
    finally:
        raw=(json.dumps(gate.facts,sort_keys=True,separators=(',',':'))+'\n').encode()
        try:
            fd=os.open(out/'binary-gate.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(raw)
        except Exception:code=2
    return code

if __name__=='__main__':raise SystemExit(main())
