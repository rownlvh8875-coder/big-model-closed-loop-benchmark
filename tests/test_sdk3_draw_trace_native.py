from pathlib import Path
from types import SimpleNamespace
import subprocess,sys,unittest
try:from scripts import sdk3_draw_trace as h,sdk3_draw_trace_native as native
except ImportError:h=native=None
class Region:
    def __init__(self,callback=None):self.callback=callback
    def getDrawCallback(self):return self.callback
    def setDrawCallback(self,value):self.callback=value
    def clearDrawCallback(self):self.callback=None
class Tracer:
    def __init__(self,fail=False):self.calls=[];self.fail=fail
    def begin(self,phase,x,y):
        self.calls.append(('begin',phase,x,y))
        if self.fail:raise ValueError('begin-failed')
    def end(self):self.calls.append(('end',))
class CallbackData:
    def __init__(self,error=False):self.calls=0;self.error=error
    def upcall(self):
        self.calls+=1
        if self.error:raise RuntimeError('original-render-error')
class NativeTraceContracts(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'native trace binding/callback boundary is missing')
    def test_target_pixel_converts_top_left_to_actual_gl_row(self):
        self.assertEqual(h.pixel_gl(964,604,596,494),(596,109));self.assertEqual(h.pixel_gl(8,8,3,3),(3,4))
    def test_gpu_column_major_unprojection_is_a_conditional_envelope(self):
        identity=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.];r=h.unproject_depth(identity,[0,0,2,2],[0,0],.25);self.assertEqual(r['local_point'],[-.5,-.5,-.5]);self.assertFalse(r['actual_coordinates_proven']);r=h.unproject_depth(identity,[0,0,2,2],[0,0],.25,depth_range=[1.,0.]);self.assertEqual(r['local_point'][2],.5)
    def test_singular_matrix_or_invalid_depth_is_never_invented(self):
        for matrix,depth in [([0.]*16,.5),([1.]*16,2.)]:
            with self.subTest(depth=depth),self.assertRaises(ValueError):h.unproject_depth(matrix,[0,0,2,2],[0,0],depth)
    def test_callbacks_scope_only_seventh_road_and_preserve_one_upcall(self):
        regions=[(1,Region()),(2,Region())];journal=SimpleNamespace(step=6,camera='road');tracer=Tracer();receipt={}
        with h.scoped_callbacks(regions,journal,tracer,(596,109),make_callback=lambda f:f,receipt=receipt):
            data=CallbackData();regions[0][1].callback(data);journal.step=7;journal.camera='wide';regions[0][1].callback(data);journal.camera='road';regions[0][1].callback(data);regions[1][1].callback(data);self.assertEqual(data.calls,4)
        self.assertEqual(tracer.calls,[('begin',1,596,109),('end',),('begin',2,596,109),('end',)]);self.assertTrue(receipt['callbacks_restored']);self.assertTrue(all(r.callback is None for _,r in regions));self.assertEqual(receipt['target_region_returns'],2)
    def test_probe_begin_failure_never_suppresses_original_draw(self):
        r=Region();data=CallbackData();receipt={}
        with h.scoped_callbacks([(1,r)],SimpleNamespace(step=7,camera='road'),Tracer(True),(3,3),make_callback=lambda f:f,receipt=receipt):r.callback(data)
        self.assertEqual(data.calls,1);self.assertTrue(receipt['errors']);self.assertFalse(receipt['trace_complete'])
    def test_original_render_exception_keeps_cleanup_and_exception(self):
        r=Region();tracer=Tracer();receipt={}
        with self.assertRaisesRegex(RuntimeError,'original-render-error'):
            with h.scoped_callbacks([(1,r)],SimpleNamespace(step=7,camera='road'),tracer,(3,3),make_callback=lambda f:f,receipt=receipt):r.callback(CallbackData(True))
        self.assertEqual(tracer.calls[-1],('end',));self.assertIsNone(r.callback);self.assertTrue(receipt['callbacks_restored'])
    def test_existing_callback_is_rejected_before_installing_anything(self):
        one,two=Region(),Region(object());saved=two.callback
        with self.assertRaises(ValueError):
            with h.scoped_callbacks([(1,one),(2,two)],SimpleNamespace(step=7,camera='road'),Tracer(),(3,3),make_callback=lambda f:f,receipt={}):pass
        self.assertIsNone(one.callback);self.assertIs(two.callback,saved)
    def test_off_observer_does_not_inspect_regions_or_load_a_library(self):
        receipt={}
        with h.scoped_callbacks([(1,object())],None,None,(3,3),make_callback=None,receipt=receipt,enabled=False):pass
        self.assertTrue(receipt['callbacks_restored']);self.assertEqual(receipt['target_region_returns'],0);self.assertEqual(receipt['status'],'OFF')
    def test_callback_scene_evidence_survives_main_thread_camera_change(self):
        r=Region();data=CallbackData();receipt={};captured={'camera_transform':[1.]*16,'camera_node':42}
        with h.scoped_callbacks([(1,r)],SimpleNamespace(step=7,camera='road'),Tracer(),(3,3),make_callback=lambda f:f,receipt=receipt,scene_metadata=lambda phase,data:dict(captured)):
            r.callback(data);captured['camera_node']=43
        self.assertEqual(data.calls,1);self.assertEqual(receipt['scene_observations'][0]['camera_node'],42)
        self.assertFalse(receipt['scene_observations'][0]['cpu_capture_label_proves_gpu_pose'])
    def test_scene_observation_failure_does_not_skip_original_upcall(self):
        r=Region();data=CallbackData();receipt={}
        def broken(phase,data):raise ValueError('missing scene')
        with h.scoped_callbacks([(1,r)],SimpleNamespace(step=7,camera='road'),Tracer(),(3,3),make_callback=lambda f:f,receipt=receipt,scene_metadata=broken):r.callback(data)
        self.assertEqual(data.calls,1);self.assertFalse(receipt['trace_complete']);self.assertIn('scene',receipt['errors'][0])
    def test_exact_cold_native_help_bootstraps_without_panda_or_numpy(self):
        r=subprocess.run([sys.executable,'-I','-S','-B',str(Path(native.__file__).resolve()),'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--mode',r.stdout)
    def test_owned_command_is_versioned_and_keeps_mode_and_nonce(self):
        a=SimpleNamespace(out='/tmp/new-owned',nonce='ab'*16,mode='trace');cmd=native.owned_child_command(a,123);self.assertIn('--owned-child',cmd);self.assertEqual(cmd[cmd.index('--mode')+1],'trace');self.assertEqual(cmd[cmd.index('--nonce')+1],a.nonce);self.assertTrue(cmd[4].endswith('sdk3_draw_trace_native.py'))
if __name__=='__main__':unittest.main()
