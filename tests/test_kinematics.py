import math
import unittest
from bigbench.kinematics import AgentState, ModelAction, step_ideal
from bigbench.geometry import CurveSection, Centerline


class KinematicTests(unittest.TestCase):
    def test_straight_and_constant_curvature(self):
        state=AgentState(0,0,0,0,10)
        after=step_ideal(state,ModelAction(.01,0),.1)
        self.assertAlmostEqual(after.heading,.01)
        self.assertAlmostEqual(after.x,math.cos(.005))
        self.assertGreater(after.y,0)
        self.assertAlmostEqual(after.speed,10)

    def test_stop_at_zero_does_not_reverse(self):
        after=step_ideal(AgentState(0,0,0,0,1),ModelAction(0,-5),1)
        self.assertEqual(after.speed,0)
        self.assertAlmostEqual(after.x,.1)

    def test_invalid_action_is_rejected(self):
        with self.assertRaises(ValueError):
            step_ideal(AgentState(0,0,0,0,10),ModelAction(float('nan'),0),.05)

    def test_centerline_curvature_signed_error(self):
        road=Centerline((CurveSection(50,0,0),CurveSection(30,.02,.02)))
        s,err,k=road.project(5,1)
        self.assertAlmostEqual(s,5,places=1)
        self.assertAlmostEqual(err,1,places=1)
        self.assertAlmostEqual(k,0)

if __name__ == '__main__': unittest.main()
