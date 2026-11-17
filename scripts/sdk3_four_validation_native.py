"""Owned zero-model native probe and independent full-S model pairs."""
from pathlib import Path
import argparse,ctypes,os,secrets,subprocess,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_runtime as p,panda_sdk3_diagnostic as owner
from scripts.sdk3_priority_model_trial import clone

def owned_child_command(args,parent_pid):
 return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--nonce',args.nonce,'--model-trial' if args.model_trial else '--probe','--seed',str(args.seed),'--scenario',args.scenario]

def prepare_nonce(args):
 if not args.owned_child and not args.model_pair and args.nonce=='0'*32:args.nonce=secrets.token_hex(16)
 p.need(args.model_pair or args.nonce!='0'*32,'fresh nonce required; owned child cannot rebind zero')

def bootstrap(report):
 sys.path.insert(0,p.SITE);import panda3d.core as core
 preload=ctypes.CDLL(p.SITE+'/panda3d/libpanda.so.1.10',mode=os.RTLD_NOW|os.RTLD_GLOBAL);sdk=ctypes.CDLL(p.SDK_PATH,mode=os.RTLD_NOW|os.RTLD_LOCAL);report.update(core_sha256=p.digest(core.__file__),sdk_sha256=p.digest(p.SDK_PATH),load_order='core-first',panda_version=core.PandaSystem.get_version_string());p.need(report['core_sha256']==p.CORE_SHA and report['sdk_sha256']==p.SDK_SHA,'actual immutable SDK/core bytes');return core,preload,sdk

def run_child(args):
 from scripts.sdk3_four_validation_trial import atomic_json,probe_trial,full_trial
 from scripts.sdk3_priority_model_native import source_stats_after
 out=Path(args.out);report=dict(protocol='sdk3-four-native-owner-v1',status='FAILED',pid=os.getpid(),nonce=args.nonce,seed=args.seed,scenario=args.scenario,model_trial=args.model_trial)
 if args.model_trial:atomic_json(out/'model-lifecycle.json',dict(protocol='sdk3-four-model-lifecycle-v1',pid=os.getpid(),nonce=args.nonce,status='PRE_RUNTIME',policy_created=False,inference_bounds=[0,0]))
 try:
  p.need(args.server_owner==os.getppid() and Path('/tmp/.X11-unix/X99').exists(),'live owned X server parent');core,preload,sdk=bootstrap(report);report['source_stats_before']=source_stats_after()
  if args.model_trial:sys.path.insert(0,'/model-deps')
  result=full_trial(args) if args.model_trial else probe_trial(args);p.write(out/('run.json' if args.model_trial else 'probe.json'),result);report['source_stats_after']=source_stats_after();report['status']='FOUR_VALIDATION_NATIVE_RECORDED';return 0
 except BaseException as exc:report['failure']=type(exc).__name__+': '+str(exc);raise
 finally:p.write(out/'report.json',report)

def run_pair(args):
 out=Path(args.out);ledger=[];failure=None;started=time.monotonic()
 try:
  for index in (0,1):
   p.need(time.monotonic()-started<7320,'bounded full-S pair');dest=out/f'run-{index}';dest.mkdir();nonce=secrets.token_hex(16);row=dict(index=index,launcher_spawn_attempted=True,launcher_pid=None,spawn_attempted=False,pid=None,returncode=None);ledger.append(row);p.write(out/'pair-ledger.json',ledger);env=dict(os.environ,HOME='/tmp/home-'+nonce,XDG_CACHE_HOME='/tmp/cache-'+nonce);Path(env['HOME']).mkdir()
   with (dest/'stdout.log').open('wb') as stdout,(dest/'stderr.log').open('wb') as stderr:
    launcher=subprocess.Popen([sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--model-trial','--out',str(dest),'--nonce',nonce,'--seed',str(args.seed),'--scenario',args.scenario],stdout=stdout,stderr=stderr,env=env);row['launcher_pid']=launcher.pid;p.write(out/'pair-ledger.json',ledger)
    try:row['returncode']=launcher.wait(timeout=min(3630,max(1,7320-(time.monotonic()-started))))
    except subprocess.TimeoutExpired:launcher.kill();launcher.wait(timeout=10);row['returncode']=launcher.returncode;raise
    finally:
     path=dest/'native-child.json'
     if path.exists():
      import json
      native=json.loads(path.read_text());row.update(spawn_attempted=native['spawn_attempted'],pid=native['pid'])
     p.write(out/'pair-ledger.json',ledger)
   p.need(row['returncode']==0,'complete owned full-S trial receipt; traversal may still fail')
 except BaseException as exc:failure=type(exc).__name__+': '+str(exc);raise
 finally:p.write(out/'pair.json',dict(status='PAIR_RECORDED' if failure is None else 'FAILED',failure=failure,counts=p.observed_model_processes(ledger)))

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);parser.add_argument('--nonce',default='0'*32);parser.add_argument('--seed',required=True,type=int);parser.add_argument('--scenario',required=True,choices=('s_curve_left_right','s_curve_right_left'));m=parser.add_mutually_exclusive_group(required=True);m.add_argument('--probe',action='store_true');m.add_argument('--model-trial',action='store_true');m.add_argument('--model-pair',action='store_true');parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);args=parser.parse_args(argv);p.need((args.seed,args.scenario) in p.CASES and len(args.nonce)==32 and all(x in '0123456789abcdef' for x in args.nonce),'registered case and owned nonce');p.need(not os.environ.get('LD_PRELOAD'),'no draw instrumentation preload');prepare_nonce(args)
 if args.model_pair:p.need(not args.owned_child,'pair is parent only');run_pair(args);return 0
 if args.owned_child:return run_child(args)
 def bounded_wait(child,server,original_limit):return owner.wait_child_then_stop_server(child,server,3600 if args.model_trial else 240)
 return clone(owner.run_with_server,owned_child_command=owned_child_command,wait_child_then_stop_server=bounded_wait)(args)
if __name__=='__main__':raise SystemExit(main())
