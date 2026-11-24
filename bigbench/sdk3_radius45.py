"""Registered curvature stress case for the SDK3 integrated Full-S track."""
from .curved_lane_scenarios import SCENARIOS

TIGHT_FULL_S_CASE = (20261109, 's_curve_left_right_radius45')
BASELINE_SCENE = 's_curve_left_right'


def tight_map_config():
    config = SCENARIOS[BASELINE_SCENE].map_config()
    for block in config['config'][1:]:
        block['radius'] = 45.0
    return config
