"""Versioned owned driver; exact legacy stages behind retained namespace proof."""
import base64
import importlib.util
import json
from pathlib import Path
import sys
from time import monotonic


def load_owned(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def _need(ok,code):
    if not ok:raise ValueError(code)


def run_stages(legacy,steps):
    result={'steps':steps}
    helper_spec = importlib.util.spec_from_file_location('owned_sandbox', '/run/builder/sandbox.py')
    helper = importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
    config = json.loads(Path('/run/builder/config.json').read_bytes())
    for name in ('tmp', 'out', 'home'):Path('/build', name).mkdir()
    stop = monotonic() + 175
    site = Path('/build/env/lib/python3.11/site-packages')
    verification = {}
    snapshots = None
    for stage, argv in legacy.commands().items():
        receipt, raw = helper.capture(argv, timeout=max(.001, stop - monotonic()), child_environment=True)
        result['steps'].append({'stage': stage, **receipt})
        _need(receipt['status'] == 'EXITED' and receipt['returncode'] == 0, 'COMMAND_FAILED')
        if stage == 'ENSUREPIP':
            bundles = list(Path(legacy.BASE).parent.parent.joinpath('lib/python3.11/ensurepip/_bundled').glob('*.whl'))
            _need(len(bundles) == 2, 'BOOTSTRAP_MISMATCH')
            verification['bootstrap'] = legacy.verify_tools(site, bundles)
        elif stage == 'TOOLS':
            verification['tools'] = legacy.verify_tools(site, [Path('/inputs', n) for n in config['tool_filenames']])
        elif stage == 'BUILD':
            snapshots = legacy.validate_snapshots(json.loads(raw), config['source_rows'])
            verification['source'] = {k: snapshots['after'][k] for k in ('snapshot_sha256', 'files')}
        elif stage == 'SMOKE':
            _need(raw == b'progressbar2.5-import-ok\n', 'SMOKE_FAILED')
    wheel = Path(legacy.OUTPUT).read_bytes()
    _need(0 < len(wheel) <= 1048576 and sorted(p.name for p in Path('/build/out').iterdir()) == [Path(legacy.OUTPUT).name], 'OUTPUT_MISMATCH')
    result = {'schema': 'builder-driver-v1', 'status': 'BUILT', 'python': '3.11.18',
              'steps': result['steps'], 'tools_verified': True, 'source_verified': True,
              'smoke_verified': True, 'wheel_b64': base64.b64encode(wheel).decode(), 'verification': verification,
              'source_snapshots': snapshots}
    return result


def execute():
    result={'schema':'builder-driver-failure-v1','status':'FAILED','code':'DRIVER_FAILED','steps':[]}
    facts=None
    try:
        proof=load_owned('owned_namespace','/run/builder/namespace.py')
        facts={};proof.collect(facts);proof.validate(facts)
        legacy=load_owned('owned_legacy_driver','/run/builder/legacy-driver.py')
        result=run_stages(legacy,result['steps'])
    except ValueError as exc:
        if str(exc) in {'UNSUPPORTED_PYTHON','UNSUPPORTED_NAMESPACE','UNSUPPORTED_QUOTA','UNSUPPORTED_CAPABILITIES','UNSUPPORTED_NETWORK',
                        'COMMAND_FAILED','BOOTSTRAP_MISMATCH','TOOL_PAYLOAD_MISMATCH','SOURCE_PAYLOAD_MISMATCH','SMOKE_FAILED','OUTPUT_MISMATCH'}:
            result['code']=str(exc)
    except Exception:pass
    return {'schema':'builder-driver-envelope-v2','namespace':facts,'result':result},0 if result['status']=='BUILT' else 1


def main():
    if sys.argv != [sys.argv[0],'--registered-builder-v2']:return 2
    wire,rc=execute();sys.stdout.write(json.dumps(wire,sort_keys=True,separators=(',',':'))+'\n');return rc


if __name__=='__main__':raise SystemExit(main())
