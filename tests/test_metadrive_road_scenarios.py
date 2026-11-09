"""No-MetaDrive-dependency tests for the 7-stage curve/ramp scene catalog."""
from __future__ import annotations

import math
import unittest
from types import SimpleNamespace

from bigbench.metadrive_road_scenarios import (
    SCENES, scene_map_config, map_signatures, check_scene_topology,
)


class FakeLane:
    def __init__(self, heading_change, index):
        self.length = 50.0
        self.index = index
        self.change = heading_change

    def heading_theta_at(self, longitudinal):
        return self.change * longitudinal / self.length


def road_graph(changes):
    graph = {}
    for index, change in enumerate(changes):
        graph[str(index)] = {str(index + 1): [FakeLane(change, index)]}
    return SimpleNamespace(graph=graph)


class CurveAndRampCatalogTests(unittest.TestCase):
    def test_s_curve_directions_are_explicitly_opposite(self):
        one = scene_map_config('s_left_right')
        two = scene_map_config('s_right_left')
        self.assertEqual(one['type'], 'pg_map_file')
        self.assertEqual(two['type'], 'pg_map_file')
        self.assertEqual([b['id'] for b in one['config']], ['I','C','C'])
        self.assertEqual([b['dir'] for b in one['config'][1:]], [0, 1])
        self.assertEqual([b['dir'] for b in two['config'][1:]], [1, 0])
        self.assertEqual(set(one['config'][1]), set(two['config'][1]))
        self.assertEqual(scene_map_config('s_left_right'),one)

    def test_native_ramp_block_ids(self):
        self.assertEqual(scene_map_config('on_ramp')['config'],'r')
        self.assertEqual(scene_map_config('off_ramp')['config'],'R')
        self.assertEqual(len(SCENES),4)

    def test_unknown_scene_fail_closed(self):
        with self.assertRaises(ValueError):
            scene_map_config('random')
        with self.assertRaises(ValueError):
            check_scene_topology('bogus',road_graph([.2,-.2]))

    def test_geometry_checks_signs_independently(self):
        graph=road_graph([.4,-.2,0.0])
        info=map_signatures(graph)
        self.assertTrue(info['has_opposing_bends'])
        self.assertEqual(info['positive_bends'],1)
        self.assertEqual(info['negative_bends'],1)
        self.assertEqual(check_scene_topology('s_left_right',graph)['status'],
                         'TOPOLOGY_GATE_PASS_ONLY')

    def test_same_sign_or_flat_curve_never_count_as_s(self):
        for shape in ([.1,.1],[0.0,0.0],[.01,-.01]):
            decision=check_scene_topology('s_right_left',road_graph(shape))
            self.assertEqual(decision['status'],'UNQUALIFIED')

    def test_ramp_is_unqualified_without_branch_topology_and_image(self):
        report=check_scene_topology('on_ramp',road_graph([.1,-.1]))
        self.assertFalse(report['topology_candidate_verified'])
        self.assertEqual(report['status'],'UNQUALIFIED')


if __name__ == '__main__':
    unittest.main()
