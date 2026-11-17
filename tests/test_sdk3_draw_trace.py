"""ABI/state contracts execute only fake GL/SDK shared libraries, never Panda."""
from pathlib import Path
import functools,json,os,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
CHILD=r'''
import ctypes as C,json,os,sys
from pathlib import Path
class Stats(C.Structure):_fields_=[(k,C.c_uint32) for k in ('version','error','active','restored')]+[(k,C.c_uint64) for k in ('lookups','forwards','draws','queries','readbacks','blits')]
sdk=C.CDLL(os.environ['SDK3_DRAW_TRACE_SDK'],use_errno=True);gl=C.CDLL(os.environ['SDK3_DRAW_TRACE_GL']);trace=C.CDLL(None);trace.dt_configure.argtypes=[C.c_char_p,C.c_uint];trace.dt_begin.argtypes=[C.c_int,C.c_int,C.c_int];trace.dt_get_stats.argtypes=[C.POINTER(Stats)]
case=sys.argv[1];path=Path(sys.argv[2]);gl.fake_setup(4 if case=='msaa' else 0,case=='error');assert trace.dt_configure(str(path).encode(),1 if case=='cap' else 512)==0
if case!='off':assert trace.dt_begin(1,3,3)==0
kinds=list(range(9)) if case in ('off','abi') else [4,4] if case=='cap' else [4]
returns=[sdk.fake_invoke(k,1 if case=='nested' else 0) for k in kinds]
trace.dt_end();trace.dt_close();s=Stats();trace.dt_get_stats(C.byref(s));rows=[json.loads(v) for v in path.read_text().splitlines()];print(json.dumps(dict(stats={k:getattr(s,k) for k,_ in s._fields_},calls=gl.fake_calls(),args_ok=gl.fake_args_ok(),restored=gl.fake_restored(),returns=returns,rows=rows)))
'''
@functools.lru_cache(None)
def build(folder):
    folder=Path(folder);fixture=ROOT/'tests/sdk3_draw_trace_fakes';common=['gcc','-std=c11','-fPIC','-shared','-O2','-Wall','-Wextra','-Werror']
    for name,source,extra in [('fakegl',fixture/'gl.c',[]),('fakesdk',fixture/'sdk.c',['-L'+str(folder),'-lfakegl','-Wl,-rpath,$ORIGIN']),('trace',ROOT/'native/sdk3_draw_trace/trace.c',['-ldl','-lm'])]:
        r=subprocess.run([*common,str(source),'-o',str(folder/('lib'+name+'.so')),*extra],capture_output=True,text=True,timeout=60)
        if r.returncode:raise AssertionError(r.stderr)
    return folder
class DrawTraceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def run_case(self,case):
        self.assertTrue((ROOT/'native/sdk3_draw_trace/trace.c').is_file(),'actual draw routing/state observer is missing');folder=build(str(self.folder));path=folder/(case+'.jsonl');env=dict(os.environ,LD_PRELOAD=str(folder/'libtrace.so'),SDK3_DRAW_TRACE_SDK=str(folder/'libfakesdk.so'),SDK3_DRAW_TRACE_GL=str(folder/'libfakegl.so'));r=subprocess.run([sys.executable,'-I','-B','-c',CHILD,case,str(path)],env=env,capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
    def test_off_routes_exact_arguments_and_errno_without_gpu_calls(self):
        x=self.run_case('off');self.assertEqual(x['calls'],9);self.assertEqual(x['args_ok'],1);self.assertTrue(all(v==34 for v in x['returns']));self.assertEqual(x['stats']['queries'],0);self.assertEqual(x['stats']['draws'],0)
    def test_active_direct_extension_alias_and_indirect_calls_still_forward(self):
        x=self.run_case('abi');self.assertEqual(x['calls'],9);self.assertEqual(x['args_ok'],1);self.assertEqual(x['stats']['draws'],9);self.assertTrue(all(v==34 for v in x['returns']))
    def test_nested_lookup_names_do_not_lose_outer_instanced_draw(self):
        x=self.run_case('nested');self.assertEqual(x['calls'],1);self.assertEqual(x['stats']['draws'],1);self.assertEqual(x['args_ok'],1)
    def test_single_sample_reads_restore_nondefault_fbo_and_all_pack_state(self):
        x=self.run_case('single');self.assertEqual(x['restored'],1);self.assertEqual(x['stats']['error'],0);self.assertEqual(x['stats']['blits'],0);self.assertGreater(x['stats']['readbacks'],0);self.assertTrue(all(r['restored'] for r in x['rows'] if r.get('event')=='draw'))
    def test_multisample_path_resolves_one_pixel_and_restores_bindings(self):
        x=self.run_case('msaa');self.assertEqual(x['restored'],1);self.assertEqual(x['stats']['error'],0);self.assertGreater(x['stats']['blits'],0);self.assertEqual(x['calls'],1)
    def test_requested_msaa_is_not_promoted_over_observed_sample_storage(self):
        x=self.run_case('sample_storage');draw=next(r for r in x['rows'] if r.get('event')=='draw');self.assertEqual(draw['after']['sample_buffers'],0);self.assertEqual(draw['after']['max_samples'],4);self.assertEqual(draw['after']['samples'],0)
    def run_depth_case(self,case,enabled,exhaust=False):
        folder=build(str(self.folder));path=folder/(case+'.jsonl');program=CHILD.replace("gl.fake_setup(4 if case=='msaa' else 0,case=='error');", "gl.fake_setup(0,False);gl.fake_terrain_scene();trace.dt_enable_depth_probe("+str(int(enabled))+");")
        program=program.replace("returns=[sdk.fake_invoke", "returns=[sdk.fake_invoke").replace("rows=rows)))", "rows=rows,changed_pixels=gl.fake_changed_pixels())))")
        if case=='skinning_table':program=program.replace('gl.fake_terrain_scene();','gl.fake_skinning_scene();')
        if case in ('depth_error','bad_row'):program=program.replace("gl.fake_terrain_scene();","gl.fake_terrain_scene();gl."+("fake_clear_error" if case=='depth_error' else "fake_bad_row")+"();")
        if exhaust:program=program.replace("returns=[sdk.fake_invoke(k,1 if case=='nested' else 0) for k in kinds]","returns=[sdk.fake_invoke(4,0) for _ in range(2)];gl.fake_plain_program();returns += [sdk.fake_invoke(4,0) for _ in range(510)]")
        env=dict(os.environ,LD_PRELOAD=str(folder/'libtrace.so'),SDK3_DRAW_TRACE_SDK=str(folder/'libfakesdk.so'),SDK3_DRAW_TRACE_GL=str(folder/'libfakegl.so'))
        r=subprocess.run([sys.executable,'-I','-B','-c',program,case,str(path)],env=env,capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
    def test_depth_probe_exposes_occluded_terrain_only_at_one_pixel(self):
        x=self.run_depth_case('depth_probe',True);self.assertEqual(x['changed_pixels'],1);self.assertEqual(x['calls'],1);self.assertEqual(x['args_ok'],1);self.assertEqual(x['restored'],1);self.assertEqual(x['stats']['error'],0)
        draw=next(r for r in x['rows'] if r.get('event')=='draw');self.assertEqual(draw['depth_probe']['cleared_pixels'],1);self.assertTrue(draw['depth_probe']['state_restored']);self.assertEqual(draw['before']['scissor'],draw['after']['scissor']);self.assertEqual(draw['before']['scissor_test'],draw['after']['scissor_test']);self.assertLess(draw['before']['depth'],draw['after']['depth'])
    def test_default_trace_does_not_clear_depth(self):
        x=self.run_depth_case('depth_control',False);self.assertEqual(x['changed_pixels'],0);self.assertEqual(x['stats']['error'],0);draw=next(r for r in x['rows'] if r.get('event')=='draw');self.assertIsNone(draw['depth_probe']);self.assertEqual(draw['before']['depth_bits32'],draw['after']['depth_bits32'])
    def test_terrain_row_is_bound_to_exact_gpu_view_and_restores_pack_and_fbo(self):
        x=self.run_depth_case('terrain_row',False);draw=next(r for r in x['rows'] if r.get('event')=='draw');row=draw['terrain_data_row'];self.assertEqual(row['view_index'],2);self.assertEqual(row['width'],7);self.assertEqual(row['nbytes'],112);self.assertTrue(row['restored']);self.assertEqual(row['values'][:4],[0.,2.,1.,.5]);self.assertEqual(row['values'][-4:],[6.,2.,1.,.5]);self.assertEqual(x['restored'],1)
    def test_row_reads_cannot_exceed_existing_readback_budget(self):
        x=self.run_depth_case('row_budget',False,exhaust=True);self.assertEqual(x['calls'],512);self.assertEqual(x['args_ok'],1);self.assertLessEqual(x['stats']['readbacks'],2048);self.assertNotEqual(x['stats']['error'],0)
    def test_failed_clear_retains_attempted_pixel_mutation_and_forwards_original(self):
        x=self.run_depth_case('depth_error',True);self.assertEqual(x['calls'],1);self.assertEqual(x['args_ok'],1);self.assertEqual(x['restored'],1);self.assertNotEqual(x['stats']['error'],0);draw=next(r for r in x['rows'] if r.get('event')=='draw');self.assertIsNotNone(draw['depth_probe']);self.assertFalse(draw['depth_probe']['state_restored'])
    def test_nonfinite_terrain_row_is_partial_with_retained_bits(self):
        x=self.run_depth_case('bad_row',False);self.assertEqual(x['calls'],1);self.assertEqual(x['restored'],1);self.assertNotEqual(x['stats']['error'],0);draw=next(r for r in x['rows'] if r.get('event')=='draw');self.assertEqual(draw['terrain_data_row']['status'],'ROW_PARTIAL');self.assertIsNone(draw['terrain_data_row']['values'][0]);self.assertIsInstance(draw['terrain_data_row']['float_bits'][0],int)
    def test_skinning_array_uses_each_indexed_matrix_and_retains_exact_bits(self):
        x=self.run_depth_case('skinning_table',False);draw=next(r for r in x['rows'] if r.get('event')=='draw');table=draw['transform_table'];self.assertEqual(table['count'],2);self.assertEqual(table['nbytes'],128);self.assertEqual(len(table['float_bits']),32);self.assertEqual(table['float_bits'][12],1067450368);self.assertEqual(table['float_bits'][28],1074790400);self.assertEqual(x['stats']['error'],0);self.assertEqual(x['calls'],1)
    def test_cap_marks_partial_but_never_suppresses_original_draw(self):
        x=self.run_case('cap');self.assertEqual(x['calls'],2);self.assertEqual(x['stats']['draws'],1);self.assertNotEqual(x['stats']['error'],0);self.assertEqual(x['restored'],1)
    def test_read_error_remains_failure_with_original_draw_and_state_restored(self):
        x=self.run_case('error');self.assertEqual(x['calls'],1);self.assertNotEqual(x['stats']['error'],0);self.assertEqual(x['restored'],1);self.assertEqual(x['args_ok'],1)
if __name__=='__main__':unittest.main()
