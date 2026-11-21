"""Resource and accounting contracts for the steering-plan diagnostic."""
import json
from pathlib import Path

BASE = 'c6b3f931282acbf0a5dd9a9fbc920573c7839415'
BRANCH = 'diagnostic/sdk3-steering-plan-20261121-01'
WORKFLOW = '.github/workflows/sdk3-steering-plan-20261121.yml'
APPROVAL = 'docs/approvals/sdk3-steering-plan-20261121-01.json'
REQUEST = 'docs/requests/sdk3-steering-plan-20261121-01.json'
VARIANT = 'source_yuv_nearest_even'
CASES = tuple((seed, scene) for seed in (20261109, 20261110)
              for scene in ('s_curve_left_right', 's_curve_right_left'))
LIMITS = dict(models=4, inferences=2400, steps=600, seconds=9000,
              memory=10*1024**3, cpus=2, pids=128)


def live_limits(root=Path('/sys/fs/cgroup')):
    files = ('memory.max', 'memory.swap.max', 'cpu.max', 'pids.max')
    values = {name: (root/name).read_text().strip() for name in files}
    quota, period = values['cpu.max'].split()
    if (values['memory.max'] != str(LIMITS['memory']) or values['pids.max'] != str(LIMITS['pids'])
            or values['memory.swap.max'] != '0' or not all(v.isdecimal() for v in (quota, period))
            or int(period) <= 0 or int(quota) != LIMITS['cpus']*int(period)):
        raise ValueError(f'actual resource profile mismatch: {values}')
    return values


def modeled_activity(folder, execution):
    if execution.get('start_attempted') is False:
        return dict(model_process_bounds=[0,0], inference_bounds=[0,0])
    try:
        native = json.loads((folder/'native-child.json').read_text())
        life = json.loads((folder/'model-lifecycle.json').read_text())
        models, bounds = life['model_process_bounds'], life['inference_bounds']
        if (type(life['pid']) is int and life['pid']>1 and life['pid']==native['pid']
                and models in ([0,0],[0,1],[1,1]) and len(bounds)==2
                and all(type(v) is int for v in bounds) and 0<=bounds[0]<=bounds[1]<=600
                and bounds[1]-bounds[0]<=1 and (models==[1,1] or bounds==[0,0])):
            return dict(model_process_bounds=models, inference_bounds=
                        [bounds[0],600] if execution.get('ownership_unresolved') or not execution.get('owned_container_removed', True) else bounds)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return dict(model_process_bounds=[0,1], inference_bounds=[0,600])
