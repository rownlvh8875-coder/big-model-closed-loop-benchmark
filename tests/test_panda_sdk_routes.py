from pathlib import Path
import json,subprocess,tempfile,unittest
from scripts import panda_cache_adapter_cpu as cpu
from tests.panda_sdk_routes_cpu_support import compile_cpu,ROOT
class SevenRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='psd2-cpu-');cls.out=Path(cls.tmp.name)
        native=ROOT/'native/panda_sdk_routes_v2'
        # The legacy implementation is the real RED baseline; deleting v2 must fail positives.
        cls.profile=compile_cpu(cls.out/'normal',native if native.exists() else ROOT/'native')
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def run_case(self,mode,profile=None,safe=None):
        p=profile or self.profile;cmd=[p['routes'],mode]+([str(safe)] if safe else [])
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=10,env=cpu.cpu_environment());self.assertEqual((r.returncode,r.stderr),(0,''));data=json.loads(r.stdout)
        if mode!='cap257':self.assertEqual((data['args_ok'],data['errno_ok'],data['returns_ok']),(1,1,1))
        self.assertFalse(data['native_admitted']);return data
    def test_seven_signatures_and_unsigned64_returns_preserve_pack_state(self):
        for mode in ('all','preserve','compiled_origin','maxbits','paths'):
            with self.subTest(mode=mode):
                r=self.run_case(mode);self.assertEqual((r['finish'],r['source_error'],r['adapter_error'],r['snapshot'],r['calls'],r['before_pack'],r['after_pack'],r['forwarded']),(0,0,0,0,14,0,0,14));self.assertEqual(r['resolutions'],7)
                if mode=='paths':self.assertEqual(r['paths'],28)
    def test_null_resolutions_and_bound_slot_null_do_not_call_or_poison(self):
        a=self.run_case('nulls');self.assertEqual((a['finish'],a['calls'],a['forwarded'],a['resolutions']),(0,4,4,7))
        b=self.run_case('null_after_bound');self.assertEqual((b['finish'],b['calls'],b['forwarded'],b['resolutions']),(0,6,6,3))
    def test_invalid_indexed_target_forwards_then_poisoned_snapshot_is_zero(self):
        r=self.run_case('invalid_target');self.assertEqual((r['source_error'],r['forwarded'],r['stale']),(5,5,0));self.assertNotEqual(r['finish'],0);self.assertNotEqual(r['adapter_error'],0)
    def test_current_draw_read_and_failed_switch_destruction_rejects(self):
        for mode in ('destroy_current_draw','destroy_current_read','failed_switch'):
            with self.subTest(mode=mode):
                r=self.run_case(mode);self.assertEqual((r['source_error'],r['stale']),(5,0));self.assertNotEqual(r['finish'],0)
    def test_successful_switch_away_allows_other_drawable_destruction(self):
        r=self.run_case('switch_away');self.assertEqual((r['finish'],r['source_error'],r['snapshot']),(0,0,0))
    def test_foreign_display_rejects_after_original_forward(self):
        r=self.run_case('wrong_display');self.assertEqual((r['source_error'],r['stale'],r['calls']),(5,0,14));self.assertNotEqual(r['finish'],0)
    def test_rebound_original_and_unqualified_alias_stay_rejected(self):
        a=self.run_case('rebind');self.assertEqual((a['source_error'],a['forwarded'],a['calls']),(7,5,6))
        b=self.run_case('unknown');self.assertEqual((b['source_error'],b['forwarded'],b['calls']),(7,4,5))
    def test_default_off_forwards_without_recording_or_configuration(self):
        a=self.run_case('off');self.assertEqual((a['finish'],a['calls'],a['forwarded'],a['resolutions'],a['configured']),(0,14,0,0,0))
        r=subprocess.run([self.profile['off']],capture_output=True,text=True,timeout=10,env=cpu.cpu_environment());self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'CPU_DEFAULT_OFF_ORIGINAL_ONLY\n',''))
    def test_safe257_configuration_still_rejects(self):
        p=self.out/'safe257.txt';p.write_text(''.join('glSafe%d\n'%i for i in range(257)));r=self.run_case('cap257',safe=p);self.assertEqual((r['configure_result'],r['configured'],r['safe_count']),(-1,0,257))
    def test_old_fifty_cases_keep_expected_results(self):
        for mode in cpu.GOOD+cpu.BAD:
            r=subprocess.run([self.profile['legacy'],mode],capture_output=True,text=True,timeout=10,env=cpu.cpu_environment());self.assertEqual((r.returncode,r.stderr),(0,''));s=json.loads(r.stdout)
            with self.subTest(mode=mode):self.assertEqual((s['args_ok'],s['errno_ok'],s['reads'],s['regs_ok'],s['stale_output']),(1,1,1,1,0));self.assertEqual(s['finish']==0,mode in cpu.GOOD)
    def test_sanitized_new_routes_and_negative_lifetimes(self):
        native=ROOT/'native/panda_sdk_routes_v2';p=compile_cpu(self.out/'sanitized',native if native.exists() else ROOT/'native',True)
        for mode in ('all','preserve','maxbits','paths','null_after_bound','switch_away','invalid_target','destroy_current_draw','destroy_current_read','failed_switch','wrong_display'):
            with self.subTest(mode=mode):
                r=self.run_case(mode,p);self.assertEqual(r['finish']==0,mode in ('all','preserve','maxbits','paths','null_after_bound','switch_away'));self.assertEqual(r['source_error'],0 if r['finish']==0 else 5)
if __name__=='__main__':unittest.main()
