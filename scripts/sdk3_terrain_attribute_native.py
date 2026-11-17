"""Versioned sparse terrain observer with unchanged borrowed lifecycle."""
from contextlib import contextmanager
from pathlib import Path
import os,resource,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import sdk3_terrain_state_native as previous,sdk3_terrain_attribute as sparse
p=previous.p

def snapshot_terrain(core,engine,sensor,geometry,out,nonce,journal):
    started=time.monotonic();rss_before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result=sparse.clone(previous.snapshot_terrain,terrain=sparse.proxy())(core,engine,sensor,geometry,out,nonce,journal)
    result.update(sparse_policy=dict(sparse.SPARSE_POLICY),sparse_sample_bytes_captured=sparse.sample_bytes(result))
    rss_after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;result['sparse_rss_peak_kib']=[rss_before,rss_after]
    if rss_after-rss_before>32768:result.update(status='TERRAIN_PARTIAL',selection_complete=False,truncation_reasons=sorted(set(result['truncation_reasons'])|{'rss_delta_budget'}))
    stopped=time.monotonic();result.update(terrain_enter_elapsed_s=started-journal.started,terrain_exit_elapsed_s=stopped-journal.started,elapsed_wall_seconds=stopped-started)
    if stopped-started>20:result.update(status='TERRAIN_PARTIAL',selection_complete=False,truncation_reasons=sorted(set(result['truncation_reasons'])|{'time_budget'}))
    p.write(Path(out)/'terrain.json',result);return result

def material_shader_terrain(*args,**kwargs):return sparse.clone(previous.material_shader_terrain,snapshot_terrain=snapshot_terrain)(*args,**kwargs)

@contextmanager
def terrain_observe(camera,journal,out,nonce):
    observer=contextmanager(sparse.clone(previous.terrain_observe.__wrapped__,material_shader_terrain=material_shader_terrain))
    with observer(camera,journal,out,nonce):yield

def run_native(args):return sparse.clone(previous.run_native,terrain_observe=terrain_observe)(args)
def owned_child_command(args,parent_pid):return sparse.clone(previous.owned_child_command,__file__=__file__)(args,parent_pid)
def run_with_server(args):return sparse.clone(previous.run_with_server,owned_child_command=owned_child_command)(args)
def main():return sparse.clone(previous.main,run_native=run_native,run_with_server=run_with_server)()
if __name__=='__main__':raise SystemExit(main())
