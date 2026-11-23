"""Registered drivable MetaDrive ramp branches and original closed-loop evaluation."""

from dataclasses import asdict
import math
import os
import uuid

from bigbench.full_s_validation import angle, need, route_state
from bigbench.kinematics import AgentState, step_ideal
from bigbench.lane_truth import lane_curvature
from bigbench.model_world_frame import WorldFramePolicyAdapter
from bigbench.policies import ModelObservation

SEEDS = (20261109, 20261110)
SCENES = ('in_ramp', 'out_ramp')
SPEED = 8.
DT = .05
START_FRACTION = .12
MAX_STEPS = 600
CHILD_LIMIT_S = 9000


def registered_lanes(current_map, scene):
    """Bind the positive drivable lanes declared by Ramp._try_plug_into_previous_block."""
    expected = {'in_ramp': 'r', 'out_ramp': 'R'}[scene]
    initial, block = current_map.blocks
    need(initial.ID == 'I' and block.ID == expected, 'expected actual initial and ramp blocks')
    node = block.road_node
    mainline = block.pre_block_socket.positive_road.end_node
    if scene == 'in_ramp':
        nodes = [node(1, i) for i in range(4)] + [node(0, 0), node(0, 1)]
        indices = [0, 0, 0, 0, 2]
    else:
        nodes = [mainline, node(0, 0)] + [node(1, i) for i in range(4)]
        indices = [2, 0, 0, 0, 0]

    local = block.block_network.graph
    graph = current_map.road_network.graph
    lanes = []
    for start, end, index in zip(nodes, nodes[1:], indices):
        road = graph[start][end]
        need(len(road) == index + 1 and road[index] is local[start][end][index],
             'ramp branch must resolve to its native road lane')
        lane = road[index]
        need(tuple(lane.index) == (start, end, index), 'stable native lane identity required')
        lanes.append(lane)
    return tuple(lanes)


def describe(lanes, scene):
    expected = ('StraightLane', 'CircularLane', 'StraightLane', 'CircularLane', 'StraightLane')
    need(scene in SCENES and tuple(type(lane).__name__ for lane in lanes) == expected,
         'five native ramp segments required')
    rows = []
    for lane in lanes:
        length = float(lane.length)
        start = list(map(float, lane.position(0., 0.)))
        end = list(map(float, lane.position(length, 0.)))
        heading = [float(lane.heading_theta_at(s)) for s in (0., length)]
        width = float(lane.width_at(length / 2))
        curvature = lane_curvature(lane, length / 2)
        need(all(map(math.isfinite, [length, *start, *end, *heading, width, curvature]))
             and length > 0 and width == 3.5, 'finite native ramp geometry and registered width required')
        geometry = dict(lane_id=str(lane.index), kind=type(lane).__name__, length_m=length,
                        start=start, end=end, start_heading_rad=heading[0], end_heading_rad=heading[1],
                        width_m=width, curvature_1pm=curvature)
        if geometry['kind'] == 'CircularLane':
            geometry.update(radius=float(lane.radius), center=list(map(float, lane.center)),
                            start_phase=float(lane.start_phase), direction=int(lane.direction))
        rows.append(geometry)
    for before, after in zip(rows, rows[1:]):
        need(math.dist(before['end'], after['start']) < 1e-7
             and abs(angle(before['end_heading_rad'] - after['start_heading_rad'])) < 1e-7,
             'native ramp segment endpoints and tangents must be continuous')
    bends = [rows[i] for i in (1, 3)]
    need(all(bend['radius'] == 40. and abs(bend['length_m'] - math.radians(10.) * 40.) < 1e-7
             for bend in bends) and bends[0]['direction'] * bends[1]['direction'] == -1,
         'expected both native 40 m radius bends with opposing signs')
    return rows


def camera_pose(lane, fraction, t=0.):
    distance = float(lane.length) * fraction
    x, y = map(float, lane.position(distance, 0.))
    return AgentState(t, x, y, float(lane.heading_theta_at(distance)), SPEED)


def run_ramp(policy, camera, lanes, *, seed, scene, progress):
    need(type(policy) is WorldFramePolicyAdapter and seed in SEEDS and scene in SCENES,
         'registered ramp and single existing model frame adapter required')
    geometry = describe(lanes, scene)
    state = camera_pose(lanes[0], START_FRACTION)
    initial = asdict(state)
    policy.reset()
    frames = []
    active = 0
    inflight = False
    before = 0
    outcome = 'STEP_LIMIT'
    error = None

    def bounds():
        known = len(policy.inner.audit_rows)
        return [known, min(MAX_STEPS, known + int(inflight and known == before))]

    def emit(status):
        progress(dict(status=status, inference_bounds=bounds(), completed_rows=len(frames)))

    try:
        emit('EPISODE_READY')
        for step in range(1, MAX_STEPS + 1):
            pair = camera.capture(state)
            need(pair.road.sha256 != pair.wide.sha256, 'distinct original road/wide feeds')
            before = len(policy.inner.audit_rows)
            inflight = True
            emit('INFERENCE_PENDING')
            action = policy.step(ModelObservation(pair.road, state.speed, state.t, wide_frame=pair.wide))
            inflight = False
            need(len(policy.inner.audit_rows) == len(policy.bridge_receipts) == before + 1,
                 'one real inference audit and one original action bridge per step')
            after = step_ideal(state, action, DT, speed_override=SPEED)
            truth = route_state(lanes, active, after)
            active = truth['lane_index']
            source = camera.last_source_rgb_sha256
            bridge = policy.bridge_receipts[-1]
            frames.append(dict(step=step, time_s=after.t, world_x_m=after.x, world_y_m=after.y,
                               heading_rad=after.heading, speed_mps=after.speed,
                               road_frame_sha256=pair.road.sha256, wide_frame_sha256=pair.wide.sha256,
                               source_road_rgb_sha256=source['road'], source_wide_rgb_sha256=source['wide'],
                               parent_model_action=bridge['parent_model_action'],
                               applied_world_action=bridge['applied_world_action'], route=truth,
                               **policy.inner.audit_rows[-1]))
            state = after
            emit('STEP_COMMITTED')
            if truth['intrusion_m'] > 0:
                outcome = 'LANE_INTRUSION'
                break
            if truth['terminal_crossed']:
                outcome = 'RAMP_COMPLETED'
                break
    except (ValueError, RuntimeError, TypeError, KeyError, IndexError) as exc:
        outcome = 'RUNTIME_ERROR'
        error = f'{type(exc).__name__}: {exc}'

    emit('TRIAL_RECORDED')
    return dict(protocol='sdk3-native-ramp-closed-loop-v1', process_id=os.getpid(),
                process_uuid=uuid.uuid4().hex, seed=seed, scenario=scene, max_steps=MAX_STEPS,
                initial_state=initial, final_state=asdict(state), initial_fraction=START_FRACTION,
                outcome=outcome, error=error, trial_completed=outcome != 'RUNTIME_ERROR',
                traversal_passed=outcome == 'RAMP_COMPLETED', actual_inference_bounds=bounds(),
                inference_audit_rows=policy.inner.audit_rows, bridge_receipts=policy.bridge_receipts,
                frames=frames, geometry=geometry, visited_lane_ids=[row['lane_id'] for row in geometry[:active+1]],
                model_sha256=policy.contract.sha256, injected_session=policy._injected_session,
                model_test_double=policy.is_mock, ground_truth_control_used=False, pixel_tolerance=0,
                extra_render_tasks=0)
