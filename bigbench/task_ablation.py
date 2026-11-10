"""Experiment-only Panda task ablation with strict allowlist and evidence.

Never remove igLoop or camera render tasks: that would produce stale images
and a false deterministic result. Only selected scene-update tasks may be
removed in a FRESH temporary MetaDrive environment, not a real device.
"""
from __future__ import annotations


ALLOWED_VISUAL_TASKS=frozenset({'PSSM.update','update main chase camera'})


class TaskAblationError(RuntimeError):
    pass


def remove_visual_scene_task(task_manager, name:str) -> dict:
    if name not in ALLOWED_VISUAL_TASKS:
        raise TaskAblationError('unapproved scene task ablation')
    before=[str(t.getName()) for t in task_manager.getAllTasks()]
    matched=before.count(name)
    if matched!=1:
        raise TaskAblationError(f'expect exactly one {name} task; found {matched}')
    if 'igLoop' not in before:
        raise TaskAblationError('graphics loop is not present, cannot isolate scene update')
    task_manager.remove(name)
    after=[str(t.getName()) for t in task_manager.getAllTasks()]
    if name in after or 'igLoop' not in after:
        raise TaskAblationError('scene task removal failed or renderer disabled')
    return {
        'ablation':name,
        'before_registered_tasks':sorted(before),
        'after_registered_tasks':sorted(after),
        'graphics_igLoop_preserved':True,
        'real_vehicle_testing':False,'model_scoring_allowed':False,
        'warning':'Experimental scene-task removal changes virtual rendering semantics, not a camera calibration fix',
    }
