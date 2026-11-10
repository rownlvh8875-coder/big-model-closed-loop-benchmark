"""Pure fake camera/PSSM receipts; never evidence of a real Panda render."""
import copy
import unittest

from bigbench.pssm_chase_pose_trace import (
    PSSMChasePoseProfiler, PoseTraceError,
    world_camera_pose,position_distance_m,assess_pose_events,
    perturb_camera_before_tick,
)
from bigbench.pssm_mvp_trace import exact_mvp_receipt


class MockNode:
    def __init__(self):
        self.position=[0.,1.,2.]
        self.hpr=[0.,0.,0.]
    def getPos(self,origin): return self.position[:]
    def getHpr(self,origin): return self.hpr[:]
    def setPos(self,origin,*xyz): self.position=list(xyz)


class MockEngine:
    def __init__(self):
        self.camera=MockNode()
        self.render=object()


def pose(x):
    return {"xyz_m":[float(x),0.,1.22],"hpr_deg":[0.,0.,0.]}


def matrix(n):
    row=[[float(i==j) for j in range(4)] for i in range(4)]
    row[0][2]=float(n)
    return exact_mvp_receipt([row])


def event(kind,action,t,x,n=0):
    receipt=matrix(n)
    return {"event":action,"callback":kind,"perf_counter_ns":t,
            "main_camera_world_pose":pose(x),
            "pssm_mvp_cpu_sha256":receipt["all_f64_sha256"],
            "pssm_mvp_numeric":receipt,
            "chase_run_task_flag":True if kind=="MainCamera._chase_task" else None}


def original_tick(t0=10, before=0.,after=0., mvp_before=0.,mvp_after=1.):
    return [
        event("PSSM.update","call",t0,before,mvp_before),
        event("PSSM.update","return",t0+10,before,mvp_after),
        event("MainCamera._chase_task","call",t0+20,before,mvp_after),
        event("MainCamera._chase_task","return",t0+30,after,mvp_after),
    ]


class NativePoseBoundaryContractTests(unittest.TestCase):
    def test_fake_world_pose_and_2m_virtual_intervention(self):
        engine=MockEngine()
        before=world_camera_pose(engine.camera,engine.render)
        x=perturb_camera_before_tick(engine,2.)
        self.assertAlmostEqual(x["measured_delta_x_m"],2.,places=7)
        self.assertEqual(x["original_camera_world_pose"],before)
        self.assertFalse(x["untouched_renderer_semantics"])
        self.assertEqual(position_distance_m(before,
                         x["intervened_camera_world_pose"]),2.)
        with self.assertRaises(PoseTraceError):
            perturb_camera_before_tick(engine,0.)

    def test_pssm_precedes_chase_and_pose_lag_candidate_is_measured(self):
        e=original_tick(t0=10,before=2.,after=0.,mvp_before=0.,mvp_after=4.)
        d=assess_pose_events(e,expected_ticks=1)
        self.assertTrue(d["pssm_before_chase_every_tick"])
        self.assertEqual(d["observed_pre_chase_pose_differs_from_post_chase_count"],1)
        self.assertEqual(d["mvp_updates_during_pssm_count"],1)
        self.assertEqual(d["mvp_updates_during_chase_count"],0)
        self.assertEqual(d["camera_motion_during_chase_count"],1)
        t=d["per_taskmgr_tick"][0]
        self.assertEqual(t["camera_pose_difference_between_pssm_entry_and_chase_exit_m"],2.)
        self.assertEqual(t["pssm_entry_mvp_sha256"],e[0]["pssm_mvp_cpu_sha256"])
        self.assertFalse(d["pssm_gpu_shadow_pass_causality_proven"])

    def test_stationary_chase_does_not_prove_one_frame_lag(self):
        d=assess_pose_events(original_tick(before=1.,after=1.),expected_ticks=1)
        self.assertEqual(d["observed_pre_chase_pose_differs_from_post_chase_count"],0)
        self.assertEqual(d["camera_motion_during_chase_count"],0)

    def test_two_sequential_task_ticks_observed_independently(self):
        events=original_tick(1,2.,0.)+original_tick(50,0.,0.)
        d=assess_pose_events(events,expected_ticks=2)
        self.assertEqual(len(d["per_taskmgr_tick"]),2)
        self.assertEqual(d["camera_motion_during_chase_count"],1)

    def test_incomplete_or_forged_mvp_rejected(self):
        rows=original_tick()
        rows[0]["pssm_mvp_cpu_sha256"]="fake"
        with self.assertRaises(PoseTraceError):
            assess_pose_events(rows,expected_ticks=1)
        with self.assertRaises(Exception):
            assess_pose_events(original_tick()[:-1],expected_ticks=1)
        bad=original_tick()
        bad[2]["main_camera_world_pose"]["xyz_m"]=[float("nan"),0.,0.]
        with self.assertRaises(PoseTraceError):
            assess_pose_events(bad,expected_ticks=1)

    def test_pose_distance_requires_finite_vector(self):
        with self.assertRaises(PoseTraceError):
            position_distance_m(pose(0.),{"xyz_m":[1.]})
        with self.assertRaises(PoseTraceError):
            position_distance_m(pose(0.),{"xyz_m":[float("nan"),0.,0.]})


if __name__=="__main__":
    unittest.main()
