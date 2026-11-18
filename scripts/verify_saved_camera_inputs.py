"""Reconstruct archived Cloud source/warp/I420; never runs a model or renderer."""
from pathlib import Path,PurePosixPath
from contextlib import ExitStack
import argparse,hashlib,json,math,stat,sys,zipfile,zlib
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/evidence/four-validation-20261118/actual-02'
SOURCE='54e2510adf9647a14161fe55461028dfb21f4758'
ACTIVATION='2993d1b2dce2fbf25985e1be25666afa23d47a91'
RUN_ID=44176109300
CASES=[(s,c) for s in (20261109,20261110) for c in ('s_curve_left_right','s_curve_right_left')]

def need(ok,message):
 if not ok:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()

def read_member(archive,name,limit):
 need(isinstance(name,str) and not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and '\\' not in name and ':' not in name,'safe archive member required')
 entries=[info for info in archive.infolist() if info.filename==name]
 need(len(entries)==1,'unique original archive member required')
 info=entries[0];need(not info.is_dir() and not stat.S_ISLNK(info.external_attr>>16) and info.file_size<=limit,'bounded regular archive member required')
 return archive.read(info)

def _rgb(data,size):
 need(isinstance(data,bytes) and len(data)<=size+65536,'bounded compressed RGB required')
 try:
  decoder=zlib.decompressobj();raw=decoder.decompress(data,size+1)
 except zlib.error as exc:raise ValueError('invalid compressed saved RGB') from exc
 need(len(raw)==size and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,'exact single saved RGB stream required')
 return raw

def independent_pack(frames):
 import numpy as np,cv2
 packed=np.empty((2,6,128,256),dtype=np.uint8)
 for camera,frame in enumerate(frames):
  raw=cv2.cvtColor(np.frombuffer(frame.rgb,dtype=np.uint8).reshape(256,512,3),cv2.COLOR_RGB2YUV_I420).reshape(-1)
  y=raw[:131072].reshape(256,512)
  for plane,(dy,dx) in enumerate(((0,0),(1,0),(0,1),(1,1))):packed[camera,plane]=y[dy::2,dx::2]
  packed[camera,4]=raw[131072:163840].reshape(128,256);packed[camera,5]=raw[163840:].reshape(128,256)
 return packed

def replay_case(bundle,model_reports,seed,scene):
 import numpy as np,cv2
 from bigbench import image_adapter
 from bigbench.optical_calibration import PinholeIntrinsics,PinholeRectifier
 from bigbench.full_s_receipts import recorded_route
 need(np.__version__=='2.4.6' and cv2.__version__=='5.0.0','exact NumPy2.4.6/OpenCV5.0 reader required')
 need((seed,scene) in CASES and isinstance(model_reports,list) and len(model_reports)==2,'registered case and two original trial reports required')
 p=json.loads(bundle['probe.json']);reference=json.loads((EVIDENCE/f'{seed}-{scene}/probe.json').read_text())
 need(p.get('protocol')=='sdk3-four-native-probe-v1' and (p.get('seed'),p.get('scenario'))==(seed,scene) and p.get('geometry')==reference['geometry'],'original qualified case geometry required')
 need(p.get('libraries')==dict(numpy=np.__version__,opencv=cv2.__version__) and p.get('provider_closed') is True and p.get('ort_module_loaded') is False and p.get('capture_calls')==2,'complete original zero-model camera context required')
 need(all(type(p.get(k)) is int and p[k]==0 for k in ('official_model_processes','onnx_inferences','extra_render_tasks')),'original probe must be zero-model')
 lanes=recorded_route(p['geometry']);caps=p.get('captures');need(isinstance(caps,list) and len(caps)==2,'two original pose controls required');digests=[];images_by_pose=[]
 for index,cap in enumerate(caps):
  s=lanes[0].length*.12+2*index;xy=lanes[0].position(s,0.);expected=dict(t=0.,x=xy[0],y=xy[1],heading=lanes[0].heading_theta_at(s),speed=8.)
  need(cap.get('index')==index and isinstance(cap.get('pose'),dict) and set(cap['pose'])==set(expected) and all(type(cap['pose'][k]) in (int,float) and math.isfinite(cap['pose'][k]) and abs(cap['pose'][k]-v)<=1e-8 for k,v in expected.items()),'original registered probe pose required')
  rows=cap.get('images');need(isinstance(rows,list) and len(rows)==2 and [r.get('camera') for r in rows]==['road','wide'],'ordered road/wide original pair required')
  arrays={};intrinsics={}
  for row in rows:
   role=row['camera'];need(row.get('source_file')==f'pose-{index}-{role}-source.rgb.zlib' and row.get('canvas_file')==f'pose-{index}-{role}-canvas.rgb.zlib' and row.get('source_shape')==[604,964,3],'canonical source/pose/role binding required')
   raw=_rgb(bundle[row['source_file']],604*964*3);need(sha(raw)==row.get('source_sha256'),'original source RGB digest required');arrays[role]=np.frombuffer(raw,dtype=np.uint8).reshape(604,964,3);intrinsics[role]=PinholeIntrinsics(**row['measured_intrinsics'])
  pair,audits=PinholeRectifier().rectify_pair(arrays['road'],arrays['wide'],road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
  for row in rows:
   role=row['camera'];canvas=_rgb(bundle[row['canvas_file']],512*256*3)
   need(canvas==getattr(pair,role).rgb and sha(canvas)==row.get('canvas_sha256') and row.get('source_coverage')==audits[role].fraction_valid_source_pixels and row.get('warp_matrix')==[list(v) for v in audits[role].warp_dst_to_src],'exact saved warp/canvas/coverage required')
  frames=[pair.road,pair.wide];manual=independent_pack(frames);original=image_adapter.camera_pair_to_model(*frames)
  need(original.shape==(2,6,128,256) and original.dtype==np.uint8 and original.flags.c_contiguous and original.tobytes()==manual.tobytes(),'original adapter must match independent road/wide I420 six-plane layout')
  need(pair.road.sha256!=pair.wide.sha256,'distinct original road/wide views required');digests.append(sha(original.tobytes()));images_by_pose.append({r['camera']:dict(source_sha256=r['source_sha256'],canvas_sha256=r['canvas_sha256']) for r in rows})
 need(all(images_by_pose[0][role][key]!=images_by_pose[1][role][key] for role in ('road','wide') for key in ('source_sha256','canvas_sha256')) and digests[0]!=digests[1],'positive source/warp/input pose controls required')
 for report in model_reports:
  need((report.get('seed'),report.get('scenario'))==(seed,scene) and report.get('geometry')==p['geometry'] and report.get('initial_state')==caps[0]['pose'],'matching original model case/initial pose required')
  need(isinstance(report.get('frames'),list) and report['frames'] and isinstance(report.get('inference_audit_rows'),list) and report['inference_audit_rows'],'actual first committed step and audit required')
  first=report['frames'][0];audit=report['inference_audit_rows'][0]
  need(first.get('step')==1 and first.get('new_img_sha256')==audit.get('new_img_sha256')==digests[0],'actual first model feed must match reconstructed pose0 I420')
  for role in ('road','wide'):
   need(first.get('source_'+role+'_rgb_sha256')==images_by_pose[0][role]['source_sha256'] and first.get(role+'_frame_sha256')==images_by_pose[0][role]['canvas_sha256'],'model source and canvas must bind original probe pixels')
 return dict(seed=seed,scenario=scene,source_images_verified=4,canvas_images_verified=4,input_shape=[2,6,128,256],input_dtype='uint8',first_new_img_sha256=digests[0],pose_control_new_img_sha256=digests[1],first_model_inputs_bound=2,first_step_only=True,later_model_frame_pixels_verified=False,pose0_images=images_by_pose[0],pose1_scope='2m on-lane positive control, not model step2',new_model_processes=0,new_inferences=0)

def authenticate_archive(path,meta):
 need(path.is_file() and not path.is_symlink() and path.stat().st_size==meta['size_in_bytes'] and 0<path.stat().st_size<=32*1024**2,'exact bounded original archive extent required')
 digest=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):digest.update(block)
 need(meta['digest']=='sha256:'+digest.hexdigest() and meta['workflow_run']['id']==RUN_ID and meta['workflow_run']['head_sha']==ACTIVATION,'archive must match retained API-bound actual run/activation/digest')
 return dict(artifact_id=meta['id'],name=meta['name'],bytes=path.stat().st_size,sha256=digest.hexdigest(),run_id=RUN_ID,activation=ACTIVATION)

def run(cohort):
 from bigbench.full_s_receipts import validate_trajectory
 from bigbench.full_s_validation import compare_full_s
 cohort=Path(cohort);inventory=json.loads((EVIDENCE/'artifacts.json').read_text());origin=json.loads((EVIDENCE/'independent-receiver.json').read_text());need(origin.get('source')==SOURCE and origin.get('activation')==ACTIVATION and origin.get('run_id')==RUN_ID and origin.get('attempt')==1,'frozen actual cohort provenance required')
 probe_name='sdk3-four-validation-probe-20261118-02';names={probe_name}|{f'sdk3-four-validation-full-s-20261118-02-{s}-{c}' for s,c in CASES};metas=inventory['artifacts'];need(len(metas)==5 and {m['name'] for m in metas}==names,'exact five original artifacts required');origins=[authenticate_archive(cohort/(m['name']+'.zip'),m) for m in metas];results=[];verdicts=[];inputs=[];inferences=0
 with ExitStack() as stack:
  archives={m['name']:stack.enter_context(zipfile.ZipFile(cohort/(m['name']+'.zip'))) for m in metas}
  for archive in archives.values():need(len(archive.namelist())==len(set(archive.namelist())) and len(archive.namelist())<5000,'unique bounded original archive namespace required')
  for seed,scene in CASES:
   prefix=f'{seed}-{scene}/';raw_probe=read_member(archives[probe_name],prefix+'probe.json',65536);p=json.loads(raw_probe);bundle={'probe.json':raw_probe};inputs.append(dict(artifact=probe_name,member=prefix+'probe.json',sha256=sha(raw_probe),bytes=len(raw_probe)))
   for index in (0,1):
    for role in ('road','wide'):
     for kind in ('source','canvas'):
      filename=f'pose-{index}-{role}-{kind}.rgb.zlib';data=read_member(archives[probe_name],prefix+filename,2*1024**2);bundle[filename]=data;inputs.append(dict(artifact=probe_name,member=prefix+filename,sha256=sha(data),bytes=len(data)))
   name=f'sdk3-four-validation-full-s-20261118-02-{seed}-{scene}';reports=[];reference=json.loads((EVIDENCE/f'{seed}-{scene}/probe.json').read_text());need(p.get('source_context')==reference['source_context'],'frozen original camera/rectifier/policy source context required')
   for index in (0,1):
    member=f'pair/run-{index}/run.json';raw=read_member(archives[name],member,8*1024**2);need(raw==read_member(archives[name],f'run_{index}.json',8*1024**2),'unchanged duplicate actual model report required');report=json.loads(raw);need(report.get('source_context')==p['source_context'] and report.get('real_ort_session') is True and report.get('model_test_double') is False and report.get('injected_session') is False,'original saved real-model report required');validate_trajectory(report,seed,scene);reports.append(report);inferences+=report['actual_inference_bounds'][0];inputs.append(dict(artifact=name,member=member,sha256=sha(raw),bytes=len(raw)))
   verdict=compare_full_s(*reports);need(verdict==json.loads(read_member(archives[name],'strict-full-s-verdict.json',65536)),'original strict pair/traversal verdict must remain unchanged');verdicts.append(verdict);results.append(replay_case(bundle,reports,seed,scene))
 heavy=[n for n in sys.modules if n.split('.')[0] in ('panda3d','direct','metadrive','onnxruntime','carla')];need(not heavy,'saved reconstruction must not import native engines or ORT')
 return dict(protocol='cloud-saved-camera-first-input-replay-v1',actual_source=SOURCE,activation=ACTIVATION,run_id=RUN_ID,attempt=1,archive_origins=origins,input_members=inputs,cases=results,source_images_verified=16,canvas_images_verified=16,first_model_inputs_bound=8,original_model_processes=8,original_inferences=inferences,original_full_s_passed_cases=sum(v['traversal_passed'] for v in verdicts),original_strict_repeat_passed_cases=sum(v['strict_repeat_passed'] for v in verdicts),new_model_processes=0,new_inferences=0,new_native_render_calls=0,heavy_modules_loaded=heavy,verifier_sha256=sha(Path(__file__).read_bytes()),scope='retrospective actual saved source/warp/I420 and eight first committed inputs only; remaining model-step pixels, causal model quality, new traversal, Windows/RTX/physical/CARLA not qualified',all_four_validation_tracks_passed=False,model_camera_qualified=False,physical_optics_validated=False,carla_validated=False)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cohort-dir',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
 if a.out.exists():parser.error('--out must be fresh; preserve previous reports')
 a.out.mkdir(parents=True)
 try:
  result=run(a.cohort_dir);(a.out/'replay.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({k:result[k] for k in ('source_images_verified','canvas_images_verified','first_model_inputs_bound','original_full_s_passed_cases','original_strict_repeat_passed_cases','new_model_processes','new_inferences')}));return 0
 except Exception as exc:
  (a.out/'error.json').write_text(json.dumps(dict(status='ERROR',error=type(exc).__name__+': '+str(exc),new_model_processes=0,new_inferences=0,all_four_validation_tracks_passed=False),indent=2)+'\n');return 2
if __name__=='__main__':raise SystemExit(main())
