"""Explicitly compose immutable bound build logic with fixed private diagnostics."""
import importlib.util
import json
from pathlib import Path
import sys


def load_owned(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def record_failure(bound,observer,exc,facts,info):
    code=exc.args[0] if type(exc) is ValueError and len(exc.args)==1 and type(exc.args[0]) is str and exc.args[0] in observer.OWNED_CODES else 'SOURCE_SNAPSHOT_FAILED'
    try:observer.validate(facts,members=set() if info is None else info[1]);valid=True
    except Exception:valid=False
    row={'schema':'source-failure-v3','status':'FAILED','code':code,'observation_validated':valid,'observation':facts if valid else None}
    try:bound._write_manifest(Path('/build/source-failure.json'),row)
    except Exception:pass
    return row


def main():
    if sys.argv!=[sys.argv[0],'--registered-pip-wheel-v1'] or sys.version_info[:3]!=(3,11,18):return 2
    bound=observer=info=facts=None
    try:
        observer=load_owned('owned_pip_observation','/run/builder/observation.py');facts=observer.empty()
        bound=load_owned('owned_bound_build','/run/builder/bound-build.py')
        from pip._internal.cli.main import main as pip_main
        from pip._internal.operations import prepare
        info=observer.pip_context()
        config=json.loads(Path('/run/builder/config.json').read_bytes())
        proxy=observer.PrepareProxy(prepare,facts,types=info[2])
        result=bound.run_with_snapshots(proxy,lambda args:observer.observe_pip(pip_main,args,facts,context_info=info),config['source_rows'])
        sys.stdout.write(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n');return 0
    except Exception as exc:
        if bound is not None and observer is not None:record_failure(bound,observer,exc,facts,info)
        sys.stdout.write('{"schema":"source-snapshot-failure-v1","code":"SOURCE_SNAPSHOT_FAILED"}\n');return 1


if __name__=='__main__':raise SystemExit(main())
