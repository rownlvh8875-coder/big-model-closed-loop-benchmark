from pathlib import Path
from types import SimpleNamespace
import copy,json,subprocess,sys,tempfile,unittest
from scripts import sdk3_terrain_attribute_native as native,run_sdk3_terrain_attribute as h,run_sdk3_terrain_state as previous,sdk3_terrain_state_native as oldnative
from tests.sdk3_terrain_attribute_fixtures import fixture

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

class AttributeAdmission(unittest.TestCase):
    def test_real_large_attribute_snapshot_is_admitted_with_exact_sparse_counter(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native);r=h.validate_receipt(folder,ref,nonce)
            self.assertTrue(r['attribute_collection_complete']);self.assertGreater(r['attribute_window_count'],0);self.assertEqual(r['sparse_sample_bytes_captured'],x['sparse_sample_bytes_captured']);self.assertLessEqual(r['sparse_sample_bytes_captured'],960)
            row=x['textures'][0];self.assertEqual(row['texture']['x_size'],22528);self.assertEqual(row['windows'][0]['window']['expected_nbytes'],2030043136)
            self.assertFalse(r['gpu_pixel_owner_proven']);self.assertFalse(r['repair_proven']);self.assertFalse(r['stage7_complete'])
    def test_real_snapshot_reports_and_binds_sparse_rss_highwater(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native);self.assertIn('sparse_rss_peak_kib',x);before,after=x['sparse_rss_peak_kib'];self.assertGreaterEqual(after,before);self.assertLessEqual(after-before,32768)
            r=h.validate_receipt(folder,ref,nonce);self.assertEqual(r['sparse_rss_delta_kib'],after-before)
            for pair in ([before,-1],[before+.5,after],[before]):
                y=copy.deepcopy(x);y['sparse_rss_peak_kib']=pair;write(folder/'terrain.json',y)
                with self.subTest(pair=pair),self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
    def test_original_host_keeps_1gib_admission(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native);row=x['textures'][0];window=row['windows'][0]['window']
            with self.assertRaises(ValueError):previous._window(window,row['texture'],row['default_sampler'],x['samples'][0]['attribute_uv'])
    def test_wrong_policy_counter_type_or_count_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native)
            for key,value in [('sparse_policy',{}),('sparse_policy',dict(x['sparse_policy'],max_logical_buffer_bytes=2**33)),('sparse_sample_bytes_captured',True),('sparse_sample_bytes_captured',x['sparse_sample_bytes_captured']+1)]:
                y=copy.deepcopy(x);y[key]=value;write(folder/'terrain.json',y)
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
    def test_offset_uv_rawhash_and_owner_binding_mutations_reject(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native)
            for key in ('offset','uv','raw_hex','pointer'):
                y=copy.deepcopy(x);window=y['textures'][0]['windows'][0]['window']
                if key=='offset':window['texels'][0]['offset']+=4
                elif key=='uv':window['uv'][0]+=.01
                elif key=='raw_hex':window['texels'][0]['raw_hex']='ff'*4
                else:y['textures'][0]['texture']['pointer']+=1
                write(folder/'terrain.json',y)
                with self.subTest(key=key),self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
    def test_identity_and_gpu_claim_mutations_reject(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native)
            for key,value in [('nonce','wrong'),('shader_sha256','00'*32),('target_read_sha256','00'*32),('observer_finalized',False),('gpu_program_execution_proven',True),('cpu_candidates_are_terrain_intersections',True)]:
                y=copy.deepcopy(x);y[key]=value;write(folder/'terrain.json',y)
                with self.subTest(key=key),self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
    def test_real_producer_interruption_stays_inconclusive(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native,interrupt=True);r=h.validate_receipt(folder,ref,nonce);self.assertEqual(x['status'],'TERRAIN_PARTIAL');self.assertFalse(r['attribute_collection_complete']);self.assertFalse(r['renderer_diagnostic_passed']);self.assertEqual(r['sparse_sample_bytes_captured'],0)
    def test_absent_or_nonresident_attribute_cannot_claim_complete_collection(self):
        for kwargs in [dict(absent=True),dict(resident=False)]:
            with self.subTest(kwargs=kwargs),tempfile.TemporaryDirectory() as d:
                folder,ref,nonce,x=fixture(d,native,**kwargs);r=h.validate_receipt(folder,ref,nonce);self.assertFalse(r['attribute_collection_complete']);self.assertEqual(r['attribute_window_count'],0);self.assertFalse(r['renderer_diagnostic_passed'])
    def test_exact_cold_native_help_and_host_help_boot(self):
        for entry,flags,expected in [(native.__file__,['-I','-S','-B'],'--out'),(h.__file__,['-I','-B'],'--run')]:
            r=subprocess.run([sys.executable,*flags,str(Path(entry).resolve()),'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr);self.assertIn(expected,r.stdout)
    def test_private_entry_changes_only_script_and_preserves_old_globals(self):
        args=SimpleNamespace(out='/tmp/o',nonce='n');before=oldnative.owned_child_command(args,1);cmd=native.owned_child_command(args,1);self.assertIn('sdk3_terrain_attribute_native.py',cmd[4]);self.assertEqual(before[:4]+before[5:],cmd[:4]+cmd[5:]);self.assertEqual(oldnative.owned_child_command(args,1),before);self.assertEqual(previous.TERRAIN_LIMITS['max_resident_bytes'],2**30)

if __name__=='__main__':unittest.main()
