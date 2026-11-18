"""Pure/fake orchestration only; never an actual Windows camera PASS."""
from pathlib import Path
from unittest import mock
import copy,json,subprocess,sys,tempfile,unittest
from tests.test_windows_camera_probe import RawCamera
from bigbench.full_s_receipts import RecordedLane
from bigbench.optical_calibration import reference_source
try:from scripts import probe_laptop_camera as c
except ImportError:c=None
ROOT=Path(__file__).resolve().parents[1]

class CameraCliContracts(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(c,'separate model-free Windows camera CLI missing')
        self.enterContext(mock.patch('numpy.__version__','2.4.6'));self.enterContext(mock.patch('cv2.__version__','5.0.0'))
    def cohort(self,folder):
        from bigbench.windows_camera_probe import RawFrames,capture_probe,CASES
        geometry=json.loads((ROOT/'docs/fixtures/sdk3-full-s-native-route-v1.json').read_text())['cases']
        driver=dict(renderer='NVIDIA GeForce RTX 3050 Ti Laptop GPU/UNIT',vendor='NVIDIA Corporation',version='4.6 unit')
        context=dict(system='Windows',python='3.11.9',panda='1.10.13',metadrive='0.4.3',numpy='2.4.6',opencv='5.0.0',renderer=driver['renderer'],vendor=driver['vendor'],driver_version=driver['version'],core_sha256='f'*64,panda_dll_sha256={'libpanda.dll':'d'*64},source_sha256=c.source_hashes(),camera_renderers={role:dict(driver) for role in ('road','wide')},linux_sdk3_qualified=False,physical_optics_validated=False)
        for index,(seed,scene) in enumerate(CASES):
            path=Path(folder)/f'{seed}-{scene}';path.mkdir()
            rows=next(row['geometry'] for row in geometry if (row['seed'],row['scenario'])==(seed,scene))
            lanes=[type(row['lane_class'].rsplit('.',1)[1],(RecordedLane,),{'__module__':row['lane_class'].rsplit('.',1)[0]})(row) for row in rows]
            raw=RawFrames();r=capture_probe(RawCamera(raw),raw,lanes,{role:reference_source(role) for role in ('road','wide')},path,seed,scene)
            r.update(context=copy.deepcopy(context),nonce=f'{index+1:032x}',process_id=100+index,provider_closed=True,original_camera_preserved=True,ort_module_loaded=False)
            c.write(path/'probe.json',r);c.write(path/'owner.json',dict(nonce=r['nonce'],pid=r['process_id'],spawn_attempted=True,spawn_succeeded=True,returncode=0,child_reaped=True))
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

if __name__=='__main__':unittest.main()
