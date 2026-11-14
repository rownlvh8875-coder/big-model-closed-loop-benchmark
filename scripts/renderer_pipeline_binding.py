"""Bound CPU pipeline readers; importing this module executes no native code."""
from types import MethodType
from scripts import renderer_task_binding as old
from scripts.renderer_pipeline_observer import matrix_state, PipelineError

LINES=dict(shader_inputs=96,render_frame=2158,road_image_as=85,wide_image_as=85)


def bind_engine(engine,*,pssm_class,chase_class,matrix_class,igloop_function,c_targets,max_submissions=24):
    if type(max_submissions) is not int or not 1<=max_submissions<=24:
        raise ValueError('bounded submission snapshots required')
    legacy=old.bind_engine(engine,pssm_class=pssm_class,chase_class=chase_class,
        matrix_class=matrix_class,task_continue=1)
    render=engine.render;graphics=engine.graphicsEngine;sensors=engine.sensors
    road=sensors['bigbench_road'];wide=sensors['bigbench_wide']
    textures={name:s.copy_texture for name,s in (('road',road),('wide',wide))}
    expected={'shader_inputs':render,'render_frame':graphics,
        'road_image_as':textures['road'],'wide_image_as':textures['wide']}
    if (type(c_targets) is not dict or set(c_targets)!=set(expected) or
        any(not callable(c_targets[k]) or getattr(c_targets[k],'__self__',None) is not v or
            type(getattr(c_targets[k],'__name__',None)) is not str for k,v in expected.items())):
        raise ValueError('exact C method owners required')
    targets=dict(legacy['targets'],igLoop=igloop_function.__get__(engine,type(engine)),
        road_ram=road.get_rgb_array_cpu,wide_ram=wide.get_rgb_array_cpu)
    if any(type(v) is not MethodType for v in targets.values()):raise ValueError('Python bound methods required')
    counts=dict(snapshots_attempted=0,snapshots_returned=0,named_getter_attempts=0,
        named_getter_returns=0,private_matrix_allocations=0,private_matrix_assignments=0,matrix_array_reads=0)
    def owners():
        if (engine.render is not render or engine.graphicsEngine is not graphics or engine.sensors is not sensors or
            sensors['bigbench_road'] is not road or sensors['bigbench_wide'] is not wide or
            road.copy_texture is not textures['road'] or wide.copy_texture is not textures['wide']):
            raise ValueError('pipeline owner changed')
    def submission(raw):
        owners()
        if counts['snapshots_attempted']>=max_submissions:raise ValueError('submission cap before getters')
        counts['snapshots_attempted']+=1
        if len(raw)!=2:raise ValueError('two submitted split matrices required')
        matrices=[]
        def get(matrix,r,c):
            counts['named_getter_attempts']+=1;v=matrix.getCell(r,c);counts['named_getter_returns']+=1
            return float(v)
        for i in range(2):
            counts['matrix_array_reads']+=1;source=raw[i]
            aligned=matrix_class();counts['private_matrix_allocations']+=1
            aligned.assign(source);counts['private_matrix_assignments']+=1
            matrices.append([[get(aligned,r,c) for c in range(4)] for r in range(4)])
        result=dict(matrices=matrices)
        try:matrix_state(result)
        except PipelineError as exc:raise ValueError(str(exc)) from exc
        counts['snapshots_returned']+=1
        return result
    return dict(python=targets,c=dict(c_targets),snapshot=legacy['snapshot'],submission=submission,
        reader_counts=legacy['reader_counts'],submission_counts=counts,native_admission_proven=False)


def bind(provider):
    """Only the admitted native child calls this; no getter is invoked to bind."""
    from metadrive.engine.core.pssm import PSSM
    from metadrive.engine.core.main_camera import MainCamera
    from panda3d.core import LMatrix4f
    from direct.showbase.ShowBase import ShowBase
    from direct.task import Task
    if type(Task.cont) is not int or Task.cont!=1:raise ValueError('pinned Task.cont required')
    e=provider.env.engine
    result=bind_engine(e,pssm_class=PSSM,chase_class=MainCamera,matrix_class=LMatrix4f,
        igloop_function=ShowBase._ShowBase__igLoop,c_targets=dict(shader_inputs=e.render.set_shader_inputs,
            render_frame=e.graphicsEngine.renderFrame,road_image_as=e.sensors['bigbench_road'].copy_texture.getRamImageAs,
            wide_image_as=e.sensors['bigbench_wide'].copy_texture.getRamImageAs))
    result['lines']=dict(LINES)
    return result
