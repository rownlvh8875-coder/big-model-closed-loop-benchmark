"""Resource and accounting contracts for the steering-plan diagnostic."""
import json
from pathlib import Path

BASE = '147ebad377753ed35cbc3fee0742dcf841ce23b0'
BRANCH = 'diagnostic/sdk3-post-entry-20261121-01'
WORKFLOW = '.github/workflows/sdk3-post-entry-20261121.yml'
APPROVAL = 'docs/approvals/sdk3-post-entry-20261121-01.json'
REQUEST = 'docs/requests/sdk3-post-entry-20261121-01.json'
VARIANT = 'source_yuv_nearest_even'
PROBE_CASES = tuple((seed, scene) for seed in (20261109, 20261110)
              for scene in ('s_curve_left_right', 's_curve_right_left'))
CASES = tuple((seed, scene) for seed, scene in PROBE_CASES if scene == 's_curve_left_right')
MODE = 'STEERING_POST_ENTRY_RETENTION'
REPORT_PROTOCOL = 'sdk3-post-entry-plan-v1'
OUTPUT = 'sdk3-post-entry-20261121'
LIMITS = dict(models=2, inferences=1200, steps=600, seconds=9000,
              memory=10*1024**3, cpus=2, pids=128)


def capture_pose(route, straight_length):
    lane = route['lane_index']
    # At the registered 8 m/s and dt 0.05 s, the input for the transition
    # can be at most 0.4 m before the connector ends.
    return lane == 2 or (lane == 1 and 0 <= straight_length - route['longitudinal_m'] <= .4)


def selected_steps(trajectory):
    frames = trajectory['frames']
    straight_length = trajectory['geometry'][1]['length_m']
    return [current['step'] for previous,current in zip(frames,frames[1:])
            if capture_pose(previous['route'],straight_length)]


def validate_window(trajectory, steps):
    frames = trajectory['frames']
    transition = next((row['step'] for row in frames if row['route']['lane_index']==2),None)
    if (not steps or transition not in steps or steps[-1]!=len(frames)
            or steps != list(range(steps[0], steps[-1]+1))):
        raise ValueError('incomplete post-entry capture window through terminal step')


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
