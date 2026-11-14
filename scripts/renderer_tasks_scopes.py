"""Capture composition after external admission; importing this module is inert."""
from contextlib import contextmanager
from scripts import renderer_task_callbacks as callbacks
from scripts import renderer_task_binding as binding
from scripts import engine_clock_native as legacy


def native_binding(provider):
    # Called only inside the sealed child after identity/source/permit admission.
    from metadrive.engine.core.pssm import PSSM
    from metadrive.engine.core.main_camera import MainCamera
    from panda3d.core import LMatrix4f
    from direct.task import Task
    if type(Task.cont) is not int or Task.cont!=1:raise ValueError('registered task.cont changed')
    return binding.bind_engine(provider.env.engine,pssm_class=PSSM,chase_class=MainCamera,
                               matrix_class=LMatrix4f,task_continue=Task.cont,max_snapshots=48)


@contextmanager
def observers(provider,data,enabled,*,binder=native_binding):
    if type(enabled) is not bool or data['clock_enabled'] is not True:
        raise ValueError('callback arm and common observed clock required')
    data['callback_enabled']=enabled;data['callback_trace']={}
    data['callback_reader_counts']=dict(snapshots_attempted=0,snapshots_returned=0,
        named_getter_attempts=0,named_getter_returns=0,private_matrix_allocations=0,
        private_matrix_assignments=0,vector_component_reads=0,matrix_array_reads=0)
    bound=binder(provider) if enabled else None
    if bound is not None:data['callback_reader_counts']=bound['reader_counts']
    with (
         callbacks.task_callback_scope(provider.env.engine.taskMgr,enabled,data['callback_trace'],
            clock_trace=data['clock_trace'],targets=bound['targets'] if enabled else None,
            snapshot=bound['snapshot'] if enabled else None,task_continue=1,max_pairs=6),
         legacy.marker_scope(provider,True,data['markers']),
         legacy.clock.camera_clock_scope(provider,True,data['clock_trace'],max_pairs=6)):
        yield
