"""Versioned entry fixing only PSSM owner matrix conversion; old observers intact."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import argparse,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import sdk3_shader_path_native as previous
from scripts.sdk3_capture_progress import stack_watchdog

def snapshot_shader(core,engine,sensor,geometry,out,nonce,journal):
    from scripts.sdk3_pssm_matrix import matrix_rows
    adapter=SimpleNamespace(_matrix=lambda value:matrix_rows(core,value))
    return previous.clone(previous.snapshot_shader,material=adapter)(core,engine,sensor,geometry,out,nonce,journal)

def material_and_shader(*args,**kwargs):return previous.clone(previous.material_and_shader,snapshot_shader=snapshot_shader)(*args,**kwargs)

@contextmanager
def shader_observe(camera,journal,out,nonce):
    observer=contextmanager(previous.clone(previous.shader_observe.__wrapped__,material_and_shader=material_and_shader))
    with observer(camera,journal,out,nonce):yield

def run_native(args):return previous.clone(previous.run_native,shader_observe=shader_observe)(args)

def owned_child_command(args,parent_pid):return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--repeat','0','--nonce',args.nonce]

def run_with_server(args):return previous.clone(previous.budget.run_with_server,owned_child_command=owned_child_command)(args)

def main():
    import faulthandler;faulthandler.enable();parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--nonce',required=True);parser.add_argument('--repeat',type=int,choices=(0,),required=True);parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);args=parser.parse_args();args.model_trial=False
    if args.owned_child:
        with stack_watchdog(Path(args.out)/'stacks.log'):run_native(args)
        return 0
    return 0 if run_with_server(args)==0 else 1
if __name__=='__main__':raise SystemExit(main())
