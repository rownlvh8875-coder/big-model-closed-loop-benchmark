"""Model-free Windows original camera probe; never downloads assets or a model."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,json,os,secrets,shutil,subprocess,sys,time
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench.windows_camera_probe import CASES,VERSIONS,camera_readiness,need,verify_probe
from scripts.run_laptop_validation import write
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['scripts/probe_laptop_camera.py','scripts/laptop_native_trial.py','bigbench/windows_camera_probe.py','bigbench/metadrive_camera.py','bigbench/native_model_campaign.py','bigbench/optical_calibration.py','bigbench/sdk3_terrain_priority.py','bigbench/full_s_validation.py','bigbench/curved_lane_scenarios.py','bigbench/native_route.py','docs/fixtures/sdk3-full-s-native-route-v1.json']
HANDSHAKE_SECONDS=5

def source_hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}

def inventory(out=None):
    from bigbench.validation_resources import collect_resources
    destination=Path.cwd() if out is None else Path(out)
    observation=collect_resources();observation['disk_free_bytes']=shutil.disk_usage(destination).free
    versions={};asset=None;assets_version=None;texture_present=False
    for name in VERSIONS:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    try:
        asset=Path(importlib.metadata.distribution('metadrive-simulator').locate_file('metadrive/assets/version.txt'))
        if asset.is_file() and asset.stat().st_size<=1024:assets_version=asset.read_text().strip()
        texture=asset.parent/'textures/grass1/GroundGrassGreen002_COL_1K.jpg'
        texture_present=texture.is_file() and texture.stat().st_size>0
    except (OSError,UnicodeError,importlib.metadata.PackageNotFoundError):pass
    return dict(protocol='windows-camera-inventory-v1',resource_observation=observation,versions=versions,assets_version=assets_version,assets_texture_present=texture_present,assets_file=str(asset) if asset else None,output_volume_observed_at=str(destination),readiness=camera_readiness(observation,versions,assets_version if texture_present else None),native_modules_imported=any(n.split('.')[0] in ('panda3d','direct','metadrive','onnxruntime') for n in sys.modules),official_model_processes=0,inferences=0)

def worker_launch():
    """Match CPython multiprocessing's direct Windows venv worker launch."""
    executable=sys.executable
    env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
    base=getattr(sys,'_base_executable',executable)
    if sys.platform=='win32' and os.path.normcase(base)!=os.path.normcase(executable):
        env['__PYVENV_LAUNCHER__']=executable
        executable=base
    return executable,env

def await_parent_admission(args):
    need(args.parent==os.getppid() and isinstance(args.nonce,str) and len(args.nonce)==32 and all(c in '0123456789abcdef' for c in args.nonce) and (args.seed,args.scenario) in CASES,'live owned camera child required before native imports')
    deadline=time.monotonic()+HANDSHAKE_SECONDS
    while True:
        owner=json.loads((args.out/'owner.json').read_text())
        cohort=json.loads((args.out.parent/'cohort.json').read_text())
        need(owner.get('nonce')==args.nonce and owner.get('parent_pid')==cohort.get('parent_pid')==args.parent and owner.get('cohort_id')==cohort.get('cohort_id') and (owner.get('seed'),owner.get('scenario'))==(args.seed,args.scenario),'matching parent-assigned cohort/case required')
        if owner.get('spawn_succeeded') is True:
            need(owner.get('pid')==os.getpid() and owner.get('returncode') is None and owner.get('child_reaped') is False,'parent must acknowledge this actual live child PID')
            return owner
        need(owner.get('spawn_succeeded') is not False and time.monotonic()<deadline,'parent admission unresolved; native imports forbidden')
        time.sleep(.02)

def deny_downloads():
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo','urllib.Request','subprocess.Popen','os.system'):
            raise PermissionError('camera probe forbids network/download and subprocess operations')
    sys.addaudithook(audit)

def _context(provider):
    from scripts.laptop_native_trial import windows_context
    from bigbench.laptop_gpu import TARGET
    context=windows_context(provider);drivers={}
    for role in ('road','wide'):
        gsg=provider.env.engine.sensors['bigbench_'+role].buffer.get_gsg()
        need(gsg is not None and gsg.is_valid(),'both original camera GSGs must be valid')
        drivers[role]=dict(renderer=gsg.get_driver_renderer(),vendor=gsg.get_driver_vendor(),version=gsg.get_driver_version())
        need(TARGET.lower() in drivers[role]['renderer'].lower() and 'nvidia' in drivers[role]['vendor'].lower(),'both original cameras must use target NVIDIA renderer')
    context.update(camera_renderers=drivers,source_sha256=source_hashes())
    need(drivers['road']==drivers['wide'],'both original camera driver tuples must match')
    return context

def run_child(args):
    owner=await_parent_admission(args)
    readiness=inventory(args.out);write(args.out/'inventory.json',readiness)
    need(readiness['readiness']['ready'],'camera packages/assets/native Windows readiness required')
    deny_downloads()
    from scripts.laptop_native_trial import world
    from bigbench.native_model_campaign import NativeWorldCamera
    from bigbench.optical_calibration import intrinsics_from_panda_lens
    from bigbench.windows_camera_probe import RawFrames,capture_probe
    life=dict(process_id=os.getpid(),parent_pid=args.parent,nonce=args.nonce,cohort_id=owner['cohort_id'],seed=args.seed,scenario=args.scenario,official_model_processes=0,inferences=0,provider_closed=False,status='NATIVE_STARTING');write(args.out/'lifecycle.json',life)
    provider=None;report=None
    try:
        provider,lanes,repair=world(args.seed,args.scenario);context=_context(provider)
        raw=RawFrames();camera=NativeWorldCamera(provider,raw_rgb_observer=raw)
        intrinsics={role:intrinsics_from_panda_lens(provider.env.engine.sensors['bigbench_'+role].get_lens(),964,604) for role in ('road','wide')}
        report=capture_probe(camera,raw,lanes,intrinsics,args.out,args.seed,args.scenario)
        need('onnxruntime' not in sys.modules,'camera-only child must not import ORT')
        report.update(context=context,renderer_candidate=repair,original_camera_preserved=type(camera) is NativeWorldCamera,ort_module_loaded=False,process_id=os.getpid(),parent_pid=args.parent,nonce=args.nonce,cohort_id=owner['cohort_id'])
    finally:
        try:
            if provider is not None:provider.close();life['provider_closed']=True
        finally:
            life['status']='CAPTURED' if report is not None and life['provider_closed'] else 'ERROR';write(args.out/'lifecycle.json',life)
    need(life['provider_closed'],'owned provider cleanup required')
    report['provider_closed']=True;write(args.out/'probe.json',report)
    life['status']='RECORDED';write(args.out/'lifecycle.json',life)
    return report

class OwnershipError(RuntimeError):pass

def launch_worker(dest,seed,scene):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=False);nonce=secrets.token_hex(16);child=None
    cohort=json.loads((dest.parent/'cohort.json').read_text());need(cohort.get('parent_pid')==os.getpid(),'live coordinator cohort required')
    owner=dict(parent_pid=os.getpid(),cohort_id=cohort['cohort_id'],seed=seed,scenario=scene,nonce=nonce,pid=None,spawn_attempted=False,spawn_succeeded=None,returncode=None,child_reaped=False,official_model_processes=0,inferences=0)
    executable,environment=worker_launch()
    command=[executable,'-I','-B',str(Path(__file__).resolve()),'--owned-child','--parent',str(os.getpid()),'--nonce',nonce,'--seed',str(seed),'--scenario',scene,'--out',str(dest)]
    try:
        with (dest/'stdout.log').open('wb') as stdout,(dest/'stderr.log').open('wb') as stderr:
            owner['spawn_attempted']=True;write(dest/'owner.json',owner)
            try:child=subprocess.Popen(command,stdout=stdout,stderr=stderr,cwd=ROOT,env=environment)
            except OSError:owner['spawn_succeeded']=False;raise
            except BaseException as exc:
                owner['spawn_succeeded']=None
                raise OwnershipError('spawn interrupted with unknown child identity; admission never acknowledged') from exc
            owner.update(spawn_succeeded=True,pid=child.pid);write(dest/'owner.json',owner)
            owner['returncode']=child.wait(timeout=240)
        need(owner['returncode']==0,'owned camera worker failed; retained logs are authoritative')
        report=json.loads((dest/'probe.json').read_text())
        need(report.get('process_id')==child.pid and report.get('nonce')==nonce and (report.get('seed'),report.get('scenario'))==(seed,scene) and report.get('provider_closed') is True,'complete owned camera receipt required')
        return report
    finally:
        if child is not None:
            try:
                if child.poll() is None:child.kill()
                child.wait(timeout=15);owner.update(returncode=child.returncode,child_reaped=child.poll() is not None)
                if not owner['child_reaped']:raise OwnershipError('owned camera child not reaped')
            except BaseException as exc:
                owner['child_reaped']=False;write(dest/'owner.json',owner)
                raise OwnershipError('unable to reap owned camera child; no further children allowed') from exc
        write(dest/'owner.json',owner)

def _verify_context(context):
    from bigbench.laptop_gpu import TARGET
    from bigbench.validation_resources import SOFTWARE
    def hash64(x):return isinstance(x,str) and len(x)==64 and all(c in '0123456789abcdef' for c in x)
    need(isinstance(context,dict) and context.get('system')=='Windows' and str(context.get('python','')).startswith('3.11.'),'actual Windows Python context required')
    need(all(context.get(k)==v for k,v in dict(panda='1.10.13',metadrive='0.4.3',numpy='2.4.6',opencv='5.0.0').items()),'exact camera runtime versions required')
    need(context.get('source_sha256')==source_hashes(),'exact executing camera sources required')
    dlls=context.get('panda_dll_sha256');need(hash64(context.get('core_sha256')) and isinstance(dlls,dict) and dlls and all(hash64(v) for v in dlls.values()),'actual core/DLL fingerprints required')
    drivers=context.get('camera_renderers');need(isinstance(drivers,dict) and set(drivers)=={'road','wide'},'both actual camera drivers required')
    for d in drivers.values():
        need(isinstance(d,dict) and all(isinstance(d.get(k),str) and d[k].strip() for k in ('renderer','vendor','version')),'actual driver strings required')
        need(TARGET.lower() in d['renderer'].lower() and 'nvidia' in d['vendor'].lower() and not any(s in d['renderer'].lower() for s in SOFTWARE),'each camera must bind target hardware renderer')
    need(all(context.get(key)==drivers['road'][other] for key,other in [('renderer','renderer'),('vendor','vendor'),('driver_version','version')]),'road context driver must match original sensor')
    need(drivers['road']==drivers['wide'],'both camera renderer/vendor/version tuples must match')
    need(context.get('linux_sdk3_qualified') is False and context.get('physical_optics_validated') is False,'no inherited Linux/physical qualification')

def _verify_inventory(packet):
    effective=packet.get('assets_version') if packet.get('assets_texture_present') is True else None
    again=camera_readiness(packet.get('resource_observation',{}),packet.get('versions',{}),effective)
    need(again['ready'] and packet.get('readiness')==again and packet.get('native_modules_imported') is False and packet.get('official_model_processes')==packet.get('inferences')==0,'successful cold camera admission evidence required')

def verify_cohort(folder):
    folder=Path(folder);rows=[];contexts=[];nonces=[]
    need(not (folder/'error.json').exists() and not (folder/'failures.json').exists(),'contradictory cohort errors must not pass')
    if (folder/'camera-summary.json').is_file():need(json.loads((folder/'camera-summary.json').read_text()).get('status')=='SCOPED_PASS','failed cohort summary must not pass')
    cohort=json.loads((folder/'cohort.json').read_text())
    need(cohort.get('protocol')=='windows-camera-cohort-owner-v1' and type(cohort.get('parent_pid')) is int and cohort['parent_pid']>0 and isinstance(cohort.get('cohort_id'),str) and len(cohort['cohort_id'])==32 and all(c in '0123456789abcdef' for c in cohort['cohort_id']) and cohort.get('cases')==[dict(seed=s,scenario=c) for s,c in CASES] and cohort.get('source_sha256')==source_hashes(),'one source-bound assigned camera cohort required')
    _verify_inventory(json.loads((folder/'inventory.json').read_text()))
    for seed,scene in CASES:
        dest=folder/f'{seed}-{scene}';r=json.loads((dest/'probe.json').read_text());owner=json.loads((dest/'owner.json').read_text())
        need((r.get('seed'),r.get('scenario'))==(seed,scene),'exact camera cohort case binding required')
        need(type(r.get('process_id')) is int and r['process_id']>0 and isinstance(r.get('nonce'),str) and len(r['nonce'])==32 and all(x in '0123456789abcdef' for x in r['nonce']),'fresh child identity required')
        need(owner.get('nonce')==r['nonce'] and owner.get('pid')==r['process_id'] and owner.get('spawn_attempted') is True and owner.get('spawn_succeeded') is True and type(owner.get('returncode')) is int and owner['returncode']==0 and owner.get('child_reaped') is True,'complete reaped parent ownership required')
        need(not (dest/'error.json').exists(),'contradictory child error must not pass')
        life=json.loads((dest/'lifecycle.json').read_text())
        identity=dict(parent_pid=cohort['parent_pid'],cohort_id=cohort['cohort_id'],seed=seed,scenario=scene)
        need(all(owner.get(k)==r.get(k)==life.get(k)==v for k,v in identity.items()) and life.get('process_id')==r['process_id'] and life.get('nonce')==r['nonce'] and life.get('status')=='RECORDED' and life.get('provider_closed') is True and life.get('official_model_processes')==life.get('inferences')==0,'matching successful assigned-case lifecycle required')
        _verify_inventory(json.loads((dest/'inventory.json').read_text()))
        need(r.get('provider_closed') is True and r.get('original_camera_preserved') is True and r.get('ort_module_loaded') is False,'original closed camera and zero ORT scope required')
        _verify_context(r.get('context'));contexts.append(r['context']);nonces.append(r['nonce']);rows.append(verify_probe(r,dest))
    need(len(set(nonces))==4 and all(context==contexts[0] for context in contexts),'four fresh workers in one exact camera context required')
    return dict(protocol='windows-camera-cohort-verification-v1',status='SCOPED_PASS',cohort_id=cohort['cohort_id'],virtual_pinhole_passed=True,cases=rows,source_images_verified=16,canvas_images_verified=16,official_model_processes=0,inferences=0,model_camera_qualified=False,linux_sdk3_qualified=False,physical_optics_validated=False,carla_validated=False,all_four_validation_tracks_passed=False,scope='original Windows virtual lens/source/warp/pose only; not camera MSAA, model inference, physical optics or full-S completion')

def run_cohort(out):
    observed=inventory(out);write(out/'inventory.json',observed)
    if not observed['readiness']['ready']:return dict(status='BLOCKED',readiness=observed['readiness'],official_model_processes=0,inferences=0,all_four_validation_tracks_passed=False)
    cohort=dict(protocol='windows-camera-cohort-owner-v1',cohort_id=secrets.token_hex(16),parent_pid=os.getpid(),cases=[dict(seed=s,scenario=c) for s,c in CASES],source_sha256=source_hashes());write(out/'cohort.json',cohort)
    failures=[]
    for seed,scene in CASES:
        try:launch_worker(out/f'{seed}-{scene}',seed,scene)
        except OwnershipError:raise
        except Exception as exc:failures.append(dict(seed=seed,scenario=scene,error=type(exc).__name__+': '+str(exc)));write(out/'failures.json',failures)
    if failures:return dict(status='ERROR',failures=failures,official_model_processes=0,inferences=0,all_four_validation_tracks_passed=False)
    return verify_cohort(out)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('inventory','probe','verify'),default='inventory');p.add_argument('--out',type=Path,required=True);p.add_argument('--results',type=Path)
    for name,options in [('owned-child',dict(action='store_true')),('parent',dict(type=int)),('nonce',{}),('seed',dict(type=int)),('scenario',{})]:p.add_argument('--'+name,help=argparse.SUPPRESS,**options)
    a=p.parse_args();a.out=a.out.resolve()
    if a.owned_child:
        try:run_child(a);return 0
        except BaseException as exc:
            if a.out.is_dir():write(a.out/'error.json',dict(status='ERROR',error=type(exc).__name__+': '+str(exc),official_model_processes=0,inferences=0))
            return 2
    if a.mode=='verify' and a.results is None:p.error('--results is required for read-only verification')
    if a.out.exists():p.error('--out must be fresh; preserve previous evidence')
    a.out.mkdir(parents=True)
    try:
        result=inventory(a.out) if a.mode=='inventory' else verify_cohort(a.results) if a.mode=='verify' else run_cohort(a.out)
        write(a.out/('inventory.json' if a.mode=='inventory' else 'camera-summary.json'),result)
        return 0 if a.mode=='inventory' or result.get('status')=='SCOPED_PASS' else 3 if result.get('status')=='BLOCKED' else 2
    except (Exception,KeyboardInterrupt) as exc:
        write(a.out/'error.json',dict(status='ERROR',error=type(exc).__name__+': '+str(exc),official_model_processes=0,inferences=0,all_four_validation_tracks_passed=False));return 2
if __name__=='__main__':raise SystemExit(main())
