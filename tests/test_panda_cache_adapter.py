from pathlib import Path
import json,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
GOOD=('bootstrap','live','preserve','aliases','delete_mutate','unrelated_delete','zero_delete','empty_delete','two_contexts','failed_switch','failed_create','new','attribs','sgix','pending_destroy','pending_release','draw_delete','after_finish','install_twice','truthy_current','observe')
BAD=('no_attach','dirty_cache','double_attach','shared','display','unknown_context','livecap','lifetimes','pending_rebind','double_destroy','fbo_deleted','fbo_mutate','source_error','source_reentry','source_thread','adapter_thread','eventcap','delete_bad','delete_negative','forged','original_snapshot','identity','downstream','double_finish','overlap','external_finish','nonzero_error','pending_known','pending_unknown')

def compile_adapter(out,sanitize=False):
    flags=['-O1' if sanitize else '-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'native')]
    san=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie'] if sanitize else []
    obj=Path(str(out)+'.o');caller=Path(str(out)+'.S');caller.write_text((ROOT/'tests/fixtures/panda_readback_caller.S').read_text().replace('pb_entry','psd_read_pixels'))
    commands=[['/usr/bin/gcc','-std=c11',*flags,*san,'-c',str(ROOT/'native/readback_command_state.c'),'-o',str(obj)],
              ['/usr/bin/g++','-std=c++11',*flags,*san,'-Dpb_fixture_call=pca_fixture_call','-Dpb_fixture_return=pca_fixture_return',str(ROOT/'native/panda_source_activity.cxx'),str(ROOT/'native/panda_cache_adapter.cxx'),str(ROOT/'tests/fixtures/panda_cache_adapter_fixture.cxx'),str(caller),str(obj),'-o',str(out)]]
    for command in commands:
        p=subprocess.run(command,capture_output=True,text=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)
    return commands

class PandaCacheAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=None;cls.exe=None
        if (ROOT/'native/panda_cache_adapter.cxx').exists():
            cls.temp=tempfile.TemporaryDirectory(prefix='pca-test-');cls.exe=Path(cls.temp.name)/'cpu';compile_adapter(cls.exe)
    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()
    def setUp(self):self.assertIsNotNone(self.exe,'source-event cache adapter required')
    def sample(self,mode):
        p=subprocess.run([str(self.exe),mode],capture_output=True,text=True,timeout=10)
        self.assertEqual((p.returncode,p.stderr),(0,''));return json.loads(p.stdout)
    def test_bootstrap_replay_matches_live_without_repeating_originals(self):
        a,b=self.sample('bootstrap'),self.sample('live')
        self.assertEqual((a['originals'],b['originals']),(8,8))
        self.assertEqual((a['replayed'],b['replayed']),(5,0))
        for s in (a,b):self.assertEqual((s['finish'],s['pack_buffer'],s['read_fbo'],s['context_tag'],s['resets']),(0,0,9,1,1))
    def test_buffer_deletion_uses_pre_original_names_before_any_fbo_is_ready(self):
        for mode,want in (('delete_mutate',0),('unrelated_delete',7),('zero_delete',7),('empty_delete',7),('two_contexts',7),('failed_switch',7)):
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual((s['finish'],s['pack_buffer'],s['args_ok']),(0,want,1))
    def test_context_creation_forms_pending_destroy_and_handle_reuse(self):
        for mode,tag,created,pending in (('failed_create',1,1,0),('new',1,1,0),('attribs',1,1,0),('sgix',1,1,0),('pending_destroy',1,1,1),('pending_release',2,2,0)):
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual((s['finish'],s['context_tag'],s['created'],s['pending']),(0,tag,created,pending))
    def test_aliases_and_paths_deliver_once_and_draw_delete_keeps_read_state(self):
        s=self.sample('aliases');self.assertEqual((s['finish'],s['source_resolutions'],s['source_paths']),(0,2,4))
        s=self.sample('draw_delete');self.assertEqual((s['finish'],s['read_fbo'],s['draw_fbo']),(0,9,0))
    def test_fail_closed_shapes_contexts_threads_limits_identity_and_finish(self):
        for mode in BAD:
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertNotEqual(s['finish'],0);self.assertNotEqual(s['adapter_error'],0)
    def test_originals_errno_and_read_tail_survive_every_rejection(self):
        for mode in GOOD+BAD:
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual((s['args_ok'],s['errno_ok'],s['reads'],s['regs_ok']),(1,1,1,1));self.assertFalse(s['native_admitted'])
    def test_observe_install_once_and_truthy_glx_results_remain_healthy(self):
        for mode in ('observe','install_twice','truthy_current','preserve','after_finish'):
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual((s['finish'],s['adapter_error'],s['source_error']),(0,0,0))
    def test_pending_supported_and_unknown_lookups_reject_observe_and_snapshot(self):
        for mode in ('pending_known','pending_unknown'):
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual((s['args_ok'],s['stale_output']),(1,0));self.assertNotEqual(s['finish'],0)
    def test_failed_observation_clears_stale_output(self):
        for mode in ('no_attach','fbo_deleted','source_error','original_snapshot','identity'):
            s=self.sample(mode)
            with self.subTest(mode=mode):self.assertEqual(s['stale_output'],0)
    def test_sanitized_delete_shape_and_thread_failure_forward_originals(self):
        with tempfile.TemporaryDirectory(prefix='pca-san-') as folder:
            exe=Path(folder)/'cpu';compile_adapter(exe,True)
            for mode in ('bootstrap','delete_mutate','delete_bad','delete_negative','forged','adapter_thread'):
                p=subprocess.run([str(exe),mode],capture_output=True,text=True,timeout=10)
                self.assertEqual((p.returncode,p.stderr),(0,''));s=json.loads(p.stdout);self.assertEqual((s['args_ok'],s['errno_ok']),(1,1))

if __name__=='__main__':unittest.main()
