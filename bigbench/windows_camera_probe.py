"""Model-free Windows virtual-camera evidence; native imports live in the worker."""
from dataclasses import asdict
from pathlib import Path
import hashlib, json, math, time, zlib

ROOT=Path(__file__).resolve().parents[1]
CASES=[(s,c) for s in (20261109,20261110) for c in ('s_curve_left_right','s_curve_right_left')]
VERSIONS={'panda3d':'1.10.13','metadrive-simulator':'0.4.3','numpy':'2.4.6','opencv-python':'5.0.0.93'}

def need(ok,message):
    if not ok: raise ValueError(message)

def camera_readiness(inventory,versions,assets_version):
    missing=[]
    if inventory.get('system')!='Windows' or inventory.get('machine','').lower() not in ('amd64','x86_64'):missing.append('WINDOWS_NATIVE_X64_REQUIRED')
    if not str(inventory.get('python_version','')).startswith('3.11.'):missing.append('PYTHON_3_11_REQUIRED')
    missing.extend('EXACT_PACKAGE_REQUIRED:'+name+'=='+version for name,version in VERSIONS.items() if versions.get(name)!=version)
    if assets_version!='0.4.3':missing.append('EXPLICIT_METADRIVE_0_4_3_ASSETS_REQUIRED')
    if type(inventory.get('disk_free_bytes')) is not int or inventory['disk_free_bytes']<128*1024**2:missing.append('128_MIB_OUTPUT_DISK_REQUIRED')
    return dict(ready=not missing,missing=missing,official_model_processes=0,inferences=0,scope='camera-only admission; available RAM recorded, not certified; full-S8GiB gate unchanged')

class RawFrames:
    def __init__(self):self.rows=[]
    def record_native_rgb(self,images,hashes):self.rows.append((images,dict(hashes)))

def capture_probe(camera,raw,lanes,intrinsics,out,seed,scene):
    from .full_s_validation import validate_route
    from .kinematics import AgentState
    from .optical_calibration import PinholeRectifier
    out=Path(out);out.mkdir(parents=True,exist_ok=True);captures=[];pairs=[]
    for index in range(2):
        s=lanes[0].length*.12+2*index;xy=lanes[0].position(s,0.)
        pose=AgentState(0.,float(xy[0]),float(xy[1]),float(lanes[0].heading_theta_at(s)),8.)
        start=time.monotonic();pair=camera.capture(pose)
        captures.append(dict(index=index,pose=asdict(pose),capture_wall_s=time.monotonic()-start,images=[]));pairs.append(pair)
    need(len(raw.rows)==2,'two original CPU source pairs required')
    for index,((images,hashes),pair) in enumerate(zip(raw.rows,pairs)):
        rebuilt,audits=PinholeRectifier().rectify_pair(images['road'],images['wide'],road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
        for role in ('road','wide'):
            source=images[role].tobytes(order='C');canvas=getattr(pair,role).rgb;h=hashlib.sha256(source).hexdigest()
            need(h==hashes[role] and getattr(rebuilt,role).rgb==canvas,'original source and canvas must match independent warp')
            src=f'pose-{index}-{role}-source.rgb.zlib';dst=f'pose-{index}-{role}-canvas.rgb.zlib'
            (out/src).write_bytes(zlib.compress(source,6));(out/dst).write_bytes(zlib.compress(canvas,6))
            captures[index]['images'].append(dict(camera=role,source_file=src,source_shape=[604,964,3],source_sha256=h,canvas_file=dst,canvas_sha256=getattr(pair,role).sha256,measured_intrinsics=asdict(intrinsics[role]),source_coverage=audits[role].fraction_valid_source_pixels,warp_matrix=[list(row) for row in audits[role].warp_dst_to_src]))
    report=dict(protocol='windows-original-camera-probe-v1',seed=seed,scenario=scene,geometry=validate_route(lanes),capture_calls=2,captures=captures,official_model_processes=0,inferences=0,extra_render_tasks=0,model_camera_qualified=False,physical_optics_validated=False,linux_sdk3_qualified=False,carla_validated=False,all_four_validation_tracks_passed=False)
    verify_probe(report,out)
    return report

def _geometry_close(a,b):
    if isinstance(a,dict) and isinstance(b,dict):return set(a)==set(b) and all(_geometry_close(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(_geometry_close(x,y) for x,y in zip(a,b))
    if type(a) in (int,float) and type(b) in (int,float):return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-8
    return type(a)==type(b) and a==b

def _rgb(directory,name,size):
    need(isinstance(name,str) and name not in ('','.','..') and '/' not in name and '\\' not in name and ':' not in name,'safe RGB file name required')
    file=Path(directory)/name
    need(file.is_file() and not file.is_symlink() and file.stat().st_size<=size+65536,'bounded retained RGB file required')
    decoder=zlib.decompressobj();data=decoder.decompress(file.read_bytes(),size+1)
    need(len(data)==size and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,'exact single zlib RGB stream required')
    return data

def verify_probe(report,directory):
    import numpy as np,cv2
    from .full_s_receipts import recorded_route
    from .optical_calibration import PinholeIntrinsics,PinholeRectifier
    need(np.__version__=='2.4.6' and cv2.__version__=='5.0.0','exact NumPy2.4.6/OpenCV5.0 reader required')
    r=report;case=(r.get('seed'),r.get('scenario'))
    need(r.get('protocol')=='windows-original-camera-probe-v1' and case in CASES,'registered Windows camera case required')
    expected=next(row['geometry'] for row in json.loads((ROOT/'docs/fixtures/sdk3-full-s-native-route-v1.json').read_text())['cases'] if (row['seed'],row['scenario'])==case)
    need(_geometry_close(r.get('geometry'),expected),'camera case must match registered native geometry')
    lanes=recorded_route(r['geometry']);captures=r.get('captures');hashes=[]
    need(r.get('capture_calls')==2 and isinstance(captures,list) and len(captures)==2,'exactly two original captures required')
    need(r.get('official_model_processes')==r.get('inferences')==r.get('extra_render_tasks')==0,'zero model/inference/extra-render scope required')
    need(all(r.get(key) is False for key in ('model_camera_qualified','physical_optics_validated','linux_sdk3_qualified','carla_validated','all_four_validation_tracks_passed')),'broader qualification must remain false')
    for index,capture in enumerate(captures):
        s=lanes[0].length*.12+2*index;xy=lanes[0].position(s,0.)
        expected_pose=dict(t=0.,x=xy[0],y=xy[1],heading=lanes[0].heading_theta_at(s),speed=8.)
        need(capture.get('index')==index and _geometry_close(capture.get('pose'),expected_pose),'exact registered positive-pose control required')
        elapsed=capture.get('capture_wall_s');need(type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>=0,'measured finite capture time required')
        rows=capture.get('images');need(isinstance(rows,list) and len(rows)==2 and {row.get('camera') for row in rows}=={'road','wide'},'two distinct camera roles required')
        for row in rows:
            role=row['camera']
            need(row.get('source_file')==f'pose-{index}-{role}-source.rgb.zlib' and row.get('canvas_file')==f'pose-{index}-{role}-canvas.rgb.zlib','canonical pose/camera RGB binding required')
        images={row['camera']:np.frombuffer(_rgb(directory,row['source_file'],604*964*3),dtype=np.uint8).reshape(604,964,3) for row in rows}
        intrinsics={row['camera']:PinholeIntrinsics(**row['measured_intrinsics']) for row in rows}
        pair,audits=PinholeRectifier().rectify_pair(images['road'],images['wide'],road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
        current={}
        for row in rows:
            role=row['camera'];source=images[role].tobytes();canvas=_rgb(directory,row['canvas_file'],512*256*3)
            need(row.get('source_shape')==[604,964,3] and hashlib.sha256(source).hexdigest()==row.get('source_sha256'),'actual source shape/hash required')
            need(canvas==getattr(pair,role).rgb and hashlib.sha256(canvas).hexdigest()==row.get('canvas_sha256'),'exact saved canvas and CPU warp required')
            need(row.get('source_coverage')==audits[role].fraction_valid_source_pixels and row.get('warp_matrix')==[list(x) for x in audits[role].warp_dst_to_src],'exact original warp/coverage required')
            current[role]=(row['source_sha256'],row['canvas_sha256'])
        need(all(current['road'][i]!=current['wide'][i] for i in (0,1)),'road and wide actual views must differ')
        hashes.append(current)
    need(all(hashes[0][role][i]!=hashes[1][role][i] for role in ('road','wide') for i in (0,1)),'both sources and canvases must change with actual pose')
    return dict(seed=case[0],scenario=case[1],virtual_pinhole_passed=True,source_images_verified=4,canvas_images_verified=4,model_camera_qualified=False,physical_optics_validated=False,linux_sdk3_qualified=False,carla_validated=False,all_four_validation_tracks_passed=False,official_model_processes=0,inferences=0,scope='saved original source/lens/warp/positive-pose only; not model camera MSAA, physical calibration, full-S or model quality')
