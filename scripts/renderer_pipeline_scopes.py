"""Common clock/Texture and a single new CPU profiler after native admission."""
from contextlib import contextmanager
from scripts import renderer_pipeline_observer as pipeline
from scripts import renderer_pipeline_binding as binding
from scripts import engine_clock_native as legacy


@contextmanager
def observers(provider,data,enabled,*,binder=binding.bind):
    if type(enabled) is not bool or data['clock_enabled'] is not True:raise ValueError('common observed clock required')
    data.update(pipeline_enabled=enabled,pipeline_trace={},callback_enabled=enabled,callback_trace={})
    data['callback_reader_counts']=dict(snapshots_attempted=0,snapshots_returned=0,named_getter_attempts=0,
        named_getter_returns=0,private_matrix_allocations=0,private_matrix_assignments=0,vector_component_reads=0,matrix_array_reads=0)
    data['submission_reader_counts']={k:v for k,v in data['callback_reader_counts'].items() if k!='vector_component_reads'}
    bound=binder(provider) if enabled else None
    if bound is not None:
        data['callback_reader_counts']=bound['reader_counts'];data['submission_reader_counts']=bound['submission_counts']
    try:
        with pipeline.pipeline_scope(provider.env.engine.taskMgr,provider.env.engine.sensors,enabled,
                data['pipeline_trace'],clock_trace=data['clock_trace'],binding=bound,max_pairs=6),\
             legacy.marker_scope(provider,True,data['markers']),\
             legacy.clock.camera_clock_scope(provider,True,data['clock_trace'],max_pairs=6):
            yield
    finally:
        if data['pipeline_trace'].get('steps') is not None:
            data['callback_trace']=pipeline.project_callbacks(data['pipeline_trace'])
