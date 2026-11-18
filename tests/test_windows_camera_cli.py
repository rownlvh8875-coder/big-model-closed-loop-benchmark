"""Pure/fake orchestration only; never an actual Windows camera PASS."""
from pathlib import Path
from unittest import mock
import copy,json,os,subprocess,sys,tempfile,unittest,venv
from types import SimpleNamespace
from tests.test_windows_camera_probe import RawCamera
from bigbench.full_s_receipts import RecordedLane
from bigbench.optical_calibration import reference_source
try:from scripts import probe_laptop_camera as c
except ImportError:c=None
ROOT=Path(__file__).resolve().parents[1]

def admission():
    from bigbench.windows_camera_probe import camera_readiness,VERSIONS
    o=dict(system='Windows',machine='AMD64',python_version='3.11.9',memory_available_bytes=4550258688,disk_free_bytes=52635979776)
    return dict(resource_observation=o,versions=dict(VERSIONS),assets_version='0.4.3',assets_texture_present=True,readiness=camera_readiness(o,VERSIONS,'0.4.3'),native_modules_imported=False,official_model_processes=0,inferences=0)

def cohort_header():
    return dict(protocol='windows-camera-cohort-owner-v1',cohort_id='a'*32,parent_pid=os.getpid(),cases=[dict(seed=s,scenario=n) for s in (20261109,20261110) for n in ('s_curve_left_right','s_curve_right_left')],source_sha256=c.source_hashes())

class CameraCliContracts(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(c,'separate model-free Windows camera CLI missing')
        self.enterContext(mock.patch('numpy.__version__','2.4.6'));self.enterContext(mock.patch('cv2.__version__','5.0.0'))
    def cohort(self,folder):
        from bigbench.windows_camera_probe import RawFrames,capture_probe,CASES
        geometry=json.loads((ROOT/'docs/fixtures/sdk3-full-s-native-route-v1.json').read_text())['cases']
        cohort=cohort_header();c.write(Path(folder)/'cohort.json',cohort);c.write(Path(folder)/'inventory.json',admission())
        driver=dict(renderer='NVIDIA GeForce RTX 3050 Ti Laptop GPU/UNIT',vendor='NVIDIA Corporation',version='4.6 unit')
        context=dict(system='Windows',python='3.11.9',panda='1.10.13',metadrive='0.4.3',numpy='2.4.6',opencv='5.0.0',renderer=driver['renderer'],vendor=driver['vendor'],driver_version=driver['version'],core_sha256='f'*64,panda_dll_sha256={'libpanda.dll':'d'*64},source_sha256=c.source_hashes(),camera_renderers={role:dict(driver) for role in ('road','wide')},linux_sdk3_qualified=False,physical_optics_validated=False)
        for index,(seed,scene) in enumerate(CASES):
            path=Path(folder)/f'{seed}-{scene}';path.mkdir()
            rows=next(row['geometry'] for row in geometry if (row['seed'],row['scenario'])==(seed,scene))
            lanes=[type(row['lane_class'].rsplit('.',1)[1],(RecordedLane,),{'__module__':row['lane_class'].rsplit('.',1)[0]})(row) for row in rows]
            raw=RawFrames();r=capture_probe(RawCamera(raw),raw,lanes,{role:reference_source(role) for role in ('road','wide')},path,seed,scene)
            r.update(context=copy.deepcopy(context),nonce=f'{index+1:032x}',process_id=100+index,parent_pid=cohort['parent_pid'],cohort_id=cohort['cohort_id'],provider_closed=True,original_camera_preserved=True,ort_module_loaded=False)
            c.write(path/'probe.json',r);c.write(path/'owner.json',dict(nonce=r['nonce'],pid=r['process_id'],parent_pid=cohort['parent_pid'],cohort_id=cohort['cohort_id'],seed=seed,scenario=scene,spawn_attempted=True,spawn_succeeded=True,returncode=0,child_reaped=True))
            c.write(path/'inventory.json',admission());c.write(path/'lifecycle.json',dict(status='RECORDED',provider_closed=True,process_id=r['process_id'],parent_pid=cohort['parent_pid'],nonce=r['nonce'],cohort_id=cohort['cohort_id'],seed=seed,scenario=scene,official_model_processes=0,inferences=0))
        return path
    def test_cold_help_and_inventory_need_no_optional_engines(self):
        with tempfile.TemporaryDirectory() as d:
            entry=str(ROOT/'scripts/probe_laptop_camera.py')
            for args in (['--help'],['--mode','inventory','--out',str(Path(d)/'inventory')]):
                r=subprocess.run([sys.executable,'-I','-S','-B',entry,*args],capture_output=True,text=True,timeout=20)
                self.assertEqual(r.returncode,0,r.stderr)
            result=json.loads((Path(d)/'inventory/inventory.json').read_text())
            self.assertEqual(result['official_model_processes'],0);self.assertFalse(result['native_modules_imported'])
    def test_real_four_case_receiver_recomputes_all_synthetic_rgb_without_native_import(self):
        with tempfile.TemporaryDirectory() as d:
            self.cohort(d);r=c.verify_cohort(Path(d));self.assertEqual(r['status'],'SCOPED_PASS')
            self.assertEqual(r['source_images_verified'],16);self.assertFalse(r['model_camera_qualified']);self.assertFalse(r['all_four_validation_tracks_passed'])
    def test_incomplete_cohort_driver_source_or_ownership_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=self.cohort(d);original=json.loads((path/'probe.json').read_text());owner=json.loads((path/'owner.json').read_text())
            for field in ('case','intel','source','closed','ort','ownership'):
                r=copy.deepcopy(original);o=dict(owner)
                if field=='case':r['scenario']='s_curve_left_right'
                elif field=='intel':r['context']['camera_renderers']['wide']['renderer']='Intel UHD'
                elif field=='source':r['context']['source_sha256']['bigbench/metadrive_camera.py']='a'*64
                elif field=='closed':r['provider_closed']=False
                elif field=='ort':r['ort_module_loaded']=True
                else:o['nonce']='0'*32
                c.write(path/'probe.json',r);c.write(path/'owner.json',o)
                with self.subTest(field=field),self.assertRaises(ValueError):c.verify_cohort(Path(d))
            c.write(path/'probe.json',original);c.write(path/'owner.json',owner);(path/'probe.json').unlink()
            with self.assertRaises((ValueError,FileNotFoundError)):c.verify_cohort(Path(d))
    def test_wrong_parent_is_rejected_before_native_import(self):
        with tempfile.TemporaryDirectory() as d:
            r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/probe_laptop_camera.py'),'--owned-child','--parent','-1','--nonce','a'*32,'--seed','20261109','--scenario','s_curve_left_right','--out',d],capture_output=True,text=True,timeout=20)
            self.assertEqual(r.returncode,2);self.assertNotIn('ModuleNotFoundError',r.stderr)
    def test_child_python_downloads_and_subprocesses_are_denied(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);from scripts.probe_laptop_camera import deny_downloads;deny_downloads();import socket;socket.create_connection(('127.0.0.1',9),timeout=.1)"
        r=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(ROOT)],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(r.returncode,0);self.assertIn('camera probe forbids network/download',r.stderr)
    def test_timeout_and_interrupt_reap_exact_owned_process(self):
        class Child:
            pid=1234
            def __init__(self,exc):self.exc=exc;self.dead=False;self.returncode=None
            def wait(self,timeout):
                if not self.dead:raise self.exc
                self.returncode=-9;return -9
            def poll(self):return -9 if self.dead else None
            def kill(self):self.dead=True
        for exc in (subprocess.TimeoutExpired('unit',240),KeyboardInterrupt()):
            with tempfile.TemporaryDirectory() as d:
                c.write(Path(d)/'cohort.json',cohort_header())
                child=Child(exc)
                with mock.patch.object(c.subprocess,'Popen',return_value=child):
                    with self.assertRaises((subprocess.TimeoutExpired,KeyboardInterrupt)):c.launch_worker(Path(d)/'child',20261109,'s_curve_left_right')
                owner=json.loads((Path(d)/'child/owner.json').read_text());self.assertTrue(owner['child_reaped']);self.assertEqual(owner['pid'],1234);self.assertEqual(owner['returncode'],-9)
    def test_linux_probe_is_blocked_without_spawning_native_workers(self):
        with tempfile.TemporaryDirectory() as d:
            inventory=dict(readiness=dict(ready=False,missing=['ASSETS_REQUIRED']),official_model_processes=0,inferences=0)
            with mock.patch.object(c,'inventory',return_value=inventory),mock.patch.object(c,'launch_worker',side_effect=AssertionError('native spawn forbidden')):
                result=c.run_cohort(Path(d))
            self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['official_model_processes'],0)
    def test_worker_launch_uses_base_interpreter_and_venv_launcher_environment(self):
        self.assertTrue(callable(getattr(c,'worker_launch',None)),'direct Windows venv worker launcher missing')
        with mock.patch.object(c.sys,'platform','win32'),mock.patch.object(c.sys,'executable','C:/venv/Scripts/python.exe'),mock.patch.object(c.sys,'_base_executable','C:/Python311/python.exe'):
            exe,env=c.worker_launch()
        self.assertEqual(exe,'C:/Python311/python.exe');self.assertEqual(env['__PYVENV_LAUNCHER__'],'C:/venv/Scripts/python.exe')
    @unittest.skipUnless(sys.platform=='win32','actual stdlib Windows venv redirector only')
    def test_windows_venv_worker_pid_parent_and_prefix_are_actual(self):
        with tempfile.TemporaryDirectory() as d:
            venv.EnvBuilder(with_pip=False,symlinks=False).create(d)
            exe=str(Path(d)/'Scripts/python.exe')
            code="import sys,os,json,subprocess;sys.path.insert(0,sys.argv[1]);from scripts.probe_laptop_camera import worker_launch;exe,env=worker_launch();p=subprocess.Popen([exe,'-I','-B','-c','import sys,os,json;print(json.dumps(dict(pid=os.getpid(),parent=os.getppid(),prefix=sys.prefix)))'],env=env,stdout=subprocess.PIPE,text=True);out,_=p.communicate(timeout=20);r=json.loads(out);print(json.dumps(dict(handle=p.pid,worker=r,parent=os.getpid(),status=p.returncode)))"
            result=subprocess.run([exe,'-I','-B','-c',code,str(ROOT)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr);r=json.loads(result.stdout)
            self.assertEqual(r['status'],0);self.assertEqual(r['handle'],r['worker']['pid']);self.assertEqual(r['parent'],r['worker']['parent']);self.assertEqual(Path(r['worker']['prefix']).resolve(),Path(d).resolve())
    def test_version_only_wide_driver_difference_in_all_cases_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            self.cohort(d)
            for file in Path(d).glob('20*/probe.json'):
                r=json.loads(file.read_text());r['context']['camera_renderers']['wide']['version']='DIFFERENT';c.write(file,r)
            with self.assertRaises(ValueError):c.verify_cohort(Path(d))
    def test_conflicting_lifecycle_parent_cohort_or_errors_never_pass(self):
        for field in ('lifecycle','parent','cohort','failure','child-error','admission'):
            with tempfile.TemporaryDirectory() as d:
                path=self.cohort(d)
                if field=='lifecycle':
                    r=json.loads((path/'lifecycle.json').read_text());r.update(status='ERROR',provider_closed=False);c.write(path/'lifecycle.json',r)
                elif field in ('parent','cohort'):
                    r=json.loads((path/'owner.json').read_text());r['parent_pid' if field=='parent' else 'cohort_id']=99999 if field=='parent' else 'b'*32;c.write(path/'owner.json',r)
                elif field=='failure':c.write(Path(d)/'failures.json',[dict(error='retained failure')])
                elif field=='child-error':c.write(path/'error.json',dict(status='ERROR'))
                else:
                    r=admission();r['readiness']['ready']=False;c.write(path/'inventory.json',r)
                with self.subTest(field=field),self.assertRaises(ValueError):c.verify_cohort(Path(d))
    def test_version_marker_without_texture_blocks_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            version=Path(d)/'metadrive/assets/version.txt';version.parent.mkdir(parents=True);version.write_text('0.4.3')
            with mock.patch('bigbench.validation_resources.collect_resources',return_value=admission()['resource_observation']),mock.patch.object(c.importlib.metadata,'version',side_effect=lambda n:admission()['versions'][n]),mock.patch.object(c.importlib.metadata,'distribution',return_value=SimpleNamespace(locate_file=lambda _:version)):
                r=c.inventory()
            self.assertFalse(r['readiness']['ready']);self.assertFalse(r['native_modules_imported'])
    def test_output_volume_headroom_controls_admission(self):
        with tempfile.TemporaryDirectory() as d:
            asset=Path(d)/'metadrive/assets';version=asset/'version.txt';version.parent.mkdir(parents=True);version.write_text('0.4.3');texture=asset/'textures/grass1/GroundGrassGreen002_COL_1K.jpg';texture.parent.mkdir(parents=True);texture.write_bytes(b'present')
            out=Path(d)/'different-volume';out.mkdir();o=admission()['resource_observation'];o['disk_free_bytes']=1024**3
            with mock.patch('bigbench.validation_resources.collect_resources',return_value=o),mock.patch.object(c.importlib.metadata,'version',side_effect=lambda n:admission()['versions'][n]),mock.patch.object(c.importlib.metadata,'distribution',return_value=SimpleNamespace(locate_file=lambda _:version)),mock.patch('shutil.disk_usage',side_effect=lambda p:SimpleNamespace(free=128*1024**2-1 if Path(p)==out else 1024**3)):
                self.assertTrue(callable(getattr(c,'inventory',None)))
                try:r=c.inventory(out)
                except TypeError:self.fail('inventory cannot inspect the selected output volume')
            self.assertFalse(r['readiness']['ready']);self.assertIn('128_MIB_OUTPUT_DISK_REQUIRED',r['readiness']['missing'])
    def test_interrupted_spawn_is_unknown_and_child_waits_for_parent_ack(self):
        with tempfile.TemporaryDirectory() as d:
            c.write(Path(d)/'cohort.json',cohort_header())
            with mock.patch.object(c.subprocess,'Popen',side_effect=KeyboardInterrupt()):
                with self.assertRaises(BaseException):c.launch_worker(Path(d)/'child',20261109,'s_curve_left_right')
            owner=json.loads((Path(d)/'child/owner.json').read_text());self.assertIsNone(owner['spawn_succeeded']);self.assertFalse(owner['child_reaped'])
            self.assertTrue(callable(getattr(c,'await_parent_admission',None)),'child admission handshake missing')
            args=SimpleNamespace(parent=os.getppid(),nonce=owner['nonce'],seed=20261109,scenario='s_curve_left_right',out=Path(d)/'child')
            header=cohort_header();header['parent_pid']=args.parent;c.write(Path(d)/'cohort.json',header)
            owner.update(parent_pid=os.getppid(),spawn_succeeded=None,pid=None);c.write(args.out/'owner.json',owner)
            with mock.patch.object(c,'HANDSHAKE_SECONDS',0):
                with self.assertRaises(ValueError):c.await_parent_admission(args)
                owner.update(spawn_succeeded=True,pid=os.getpid());c.write(args.out/'owner.json',owner)
                self.assertEqual(c.await_parent_admission(args)['pid'],os.getpid())

if __name__=='__main__':unittest.main()
