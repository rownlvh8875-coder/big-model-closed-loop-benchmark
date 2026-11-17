"""Fresh original official-model processes with an explicit RGB priority candidate."""
from pathlib import Path
import argparse,ctypes,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import sdk3_terrain_priority as repair
from scripts import panda_sdk3_runtime as pins,panda_sdk3_diagnostic as owner
from scripts.sdk3_priority_model_trial import clone,make_trial

def owned_child_command(args,parent_pid):
    return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--nonce',args.nonce,'--model-trial','--seed',str(args.seed),'--scenario',args.scenario]

def source_stats_after():
    sdk=ctypes.CDLL(pins.SDK_PATH,mode=os.RTLD_NOW|os.RTLD_NOLOAD);function=sdk.psd_get_stats;function.argtypes=[ctypes.c_void_p];function.restype=ctypes.c_int;raw=(ctypes.c_ubyte*80)(*([165]*80));returned=function(ctypes.addressof(raw)+16);fields=dict(configured=(0,4),closed=(4,4),error=(8,4),forwarded=(16,8),resolutions=(24,8),paths=(32,8),events=(40,8));data=bytes(raw[16:64]);return dict(returned=returned,guards_ok=bytes(raw[:16])==bytes(raw[64:])==bytes([165])*16,values={k:int.from_bytes(data[o:o+w],'little') for k,(o,w) in fields.items()})

def model_trial_callable(args):
    from scripts.native_mdv3_repeat_trial import run_trial,AuditedOfficialOnnx
    from bigbench.native_model_campaign import run_native_episode,NativeWorldCamera
    from metadrive.constants import Semantics,CameraTagStateKey
    def install(provider):return repair.install_rgb_terrain_priority(provider.env.engine,terrain_label=Semantics.TERRAIN.label,tag_key=CameraTagStateKey.RGB)
    return make_trial(run_trial,run_native_episode,AuditedOfficialOnnx,NativeWorldCamera,install_policy=install,out=Path(args.out),source_stats_after=source_stats_after,identity=dict(nonce=args.nonce,native_entry_sha256=pins.digest(__file__),model_spec_sha256=pins.digest('/work/repo/model_specs/md-v3.json')))

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--nonce',default='0'*32);parser.add_argument('--seed',required=True,type=int);parser.add_argument('--scenario',required=True,choices=('s_curve_left_right','s_curve_right_left'));modes=parser.add_mutually_exclusive_group(required=True);modes.add_argument('--model-pair',action='store_true');modes.add_argument('--model-trial',action='store_true');parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);parser.set_defaults(load_order='core-first',factory='manual',reference_wheel=False,full_rgb=False);args=parser.parse_args(argv);pins.need((args.seed,args.scenario) in pins.CASES,'registered official cohort condition');pins.need(len(args.nonce)==32 and all(c in '0123456789abcdef' for c in args.nonce),'bounded child nonce');pins.need(not os.environ.get('LD_PRELOAD'),'no model instrumentation preload')
    if args.model_pair:pins.need(not args.owned_child,'pair launcher is not a trial child');clone(owner.run_pair,__file__=__file__)(args);return 0
    if args.owned_child:
        pins.write(Path(args.out)/'model-trial-lifecycle.json',dict(protocol='sdk3-priority-model-lifecycle-v1',pid=os.getpid(),nonce=args.nonce,status='PRE_RUNTIME',policy_constructor_entered=False,policy_created=False,completed=False,inferences_completed_lower_bound=0,inferences_completed_upper_bound=0));clone(owner.run,model_trial_callable=model_trial_callable)(args);return 0
    return clone(owner.run_with_server,owned_child_command=owned_child_command)(args)
if __name__=='__main__':raise SystemExit(main())
