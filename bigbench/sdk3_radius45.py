"""Registered curvature stress cases for the SDK3 integrated Full-S track."""
from .curved_lane_scenarios import SCENARIOS

BASELINE_SCENES = {
    's_curve_left_right_radius45': 's_curve_left_right',
    's_curve_right_left_radius45': 's_curve_right_left',
}
TIGHT_FULL_S_CASES = frozenset((seed, scene) for seed in (20261109, 20261110)
                              for scene in BASELINE_SCENES)


def tight_map_config(scene='s_curve_left_right_radius45'):
    config = SCENARIOS[BASELINE_SCENES[scene]].map_config()
    for block in config['config'][1:]:
        block['radius'] = 45.0
    return config
