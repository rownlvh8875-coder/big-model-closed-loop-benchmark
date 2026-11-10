"""Fail-closed task ablation tests; fake Panda task manager, no native rendering."""
import unittest
from bigbench.task_ablation import TaskAblationError,remove_visual_scene_task


class Task:
    def __init__(self,name):self.name=name
    def getName(self):return self.name


class TaskManager:
    def __init__(self,names):
        self.names=list(names)
    def getAllTasks(self):
        return [Task(n) for n in self.names]
    def remove(self,name):
        self.names=[n for n in self.names if n!=name]


class AblationContractTests(unittest.TestCase):
    def test_remove_shadow_only_preserves_graphics(self):
        mgr=TaskManager(['igLoop','PSSM.update','dataLoop'])
        info=remove_visual_scene_task(mgr,'PSSM.update')
        self.assertEqual(mgr.names,['igLoop','dataLoop'])
        self.assertTrue(info['graphics_igLoop_preserved'])
        self.assertFalse(info['real_vehicle_testing'])
        self.assertFalse(info['model_scoring_allowed'])

    def test_remove_chase_only(self):
        mgr=TaskManager(['igLoop','update main chase camera'])
        info=remove_visual_scene_task(mgr,'update main chase camera')
        self.assertEqual(info['ablation'],'update main chase camera')

    def test_never_erase_render_or_unapproved_task(self):
        mgr=TaskManager(['igLoop','PSSM.update'])
        with self.assertRaises(TaskAblationError):
            remove_visual_scene_task(mgr,'igLoop')
        with self.assertRaises(TaskAblationError):
            remove_visual_scene_task(mgr,'dataLoop')
        self.assertIn('igLoop',mgr.names)

    def test_no_missing_duplicate_or_disabled_igloop(self):
        for names in (['igLoop'],['PSSM.update'],['igLoop','PSSM.update','PSSM.update']):
            with self.assertRaises(TaskAblationError):
                remove_visual_scene_task(TaskManager(names),'PSSM.update')


if __name__=='__main__':
    unittest.main()
