from pathlib import Path
from types import SimpleNamespace
import copy,json,subprocess,sys,tempfile,unittest
try:from scripts import sdk3_prepared_texture_native as native,run_sdk3_prepared_texture as h
except ImportError:native=h=None
from scripts import sdk3_terrain_attribute_native as oldnative,run_sdk3_terrain_attribute as oldhost
from tests.sdk3_prepared_texture_fixtures import fixture

def write(path,x):path.write_text(json.dumps(x,indent=2)+'\n')
class PreparedBoundary(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'prepared native/host boundary is missing')
    def test_real_snapshot_deduplicates_context_and_admits_sparse_mip(self):
        with tempfile.TemporaryDirectory() as d:
            f,ref,n,x=fixture(d,native);r=h.validate_receipt(f,ref,n);self.assertTrue(r['prepared_complete']);self.assertTrue(r['mip1_collection_complete']);self.assertEqual(r['mip1_window_count'],len(json.loads((f/'terrain.json').read_text())['samples']));self.assertEqual(len(x['contexts']),1);self.assertEqual(len(x['outputs']),3);self.assertEqual(len(x['textures']),3);self.assertEqual(x['textures'][0]['minimum_bias_by_context'],[1]);self.assertEqual(x['textures'][0]['mip1_windows'][0]['window']['texels'][0]['raw_hex'],'0000803e');self.assertFalse(r['hardware_texture_dimensions_proven']);self.assertFalse(r['stage7_complete'])
    def test_absent_mip_is_honest_optional_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            f,ref,n,x=fixture(d,native,mip_resident=False);r=h.validate_receipt(f,ref,n);self.assertTrue(r['prepared_complete']);self.assertFalse(r['mip1_collection_complete']);self.assertEqual(r['mip1_sample_bytes_captured'],0)
    def test_unknown_cap_does_not_invent_bias(self):
        for cap in (-1,0):
            with self.subTest(cap=cap),tempfile.TemporaryDirectory() as d:
                f,ref,n,x=fixture(d,native,cap=cap);self.assertEqual(x['textures'][0]['minimum_bias_by_context'],[None]);self.assertTrue(h.validate_receipt(f,ref,n)['prepared_complete'])
    def test_missing_output_and_interrupted_metadata_are_partial(self):
        for kw in (dict(missing_output=True),dict(fail=True)):
            with self.subTest(kw=kw),tempfile.TemporaryDirectory() as d:
                f,ref,n,x=fixture(d,native,**kw);r=h.validate_receipt(f,ref,n);self.assertFalse(r['prepared_complete']);self.assertFalse(r['renderer_diagnostic_passed'])
    def test_rss_boundary_and_forged_completion(self):
        for delta in (32768,32769):
            with self.subTest(delta=delta),tempfile.TemporaryDirectory() as d:
                f,ref,n,x=fixture(d,native,rss_delta=delta);r=h.validate_receipt(f,ref,n);self.assertEqual(r['prepared_complete'],delta==32768)
                if delta>32768:
                    x.update(selection_complete=True,status='PREPARED_RECORDED',truncation_reasons=[]);write(f/'prepared.json',x)
                    with self.assertRaises(ValueError):h.validate_receipt(f,ref,n)
    def test_absent_terrain_has_no_invented_texture_table(self):
        with tempfile.TemporaryDirectory() as d:
            f,ref,n,x=fixture(d,native,absent=True);r=h.validate_receipt(f,ref,n);self.assertEqual(x['textures'],[]);self.assertFalse(r['mip1_collection_complete']);self.assertFalse(r['renderer_diagnostic_passed'])
    def test_identity_policy_final_hashes_clock_and_claim_mutations_reject(self):
        with tempfile.TemporaryDirectory() as d:
            f,ref,n,x=fixture(d,native)
            for key,value in [('nonce','wrong'),('pid',99),('policy',{}),('reference_index_sha256','00'*32),('terrain_sha256','00'*32),('material_sha256','00'*32),('target_read_sha256','00'*32),('observer_finalized',False),('borrowed_parent_is_origin',False),('prepared_enter_elapsed_s',-1),('hardware_texture_dimensions_proven',True),('actual_upload_bias_proven',True),('gpu_pixel_owner_proven',True),('repair_proven',True),('mip1_sample_bytes_captured',True)]:
                y=copy.deepcopy(x);y[key]=value;write(f/'prepared.json',y)
                with self.subTest(key=key),self.assertRaises(ValueError):h.validate_receipt(f,ref,n)
    def test_texture_context_metadata_and_sparse_bindings_reject(self):
        with tempfile.TemporaryDirectory() as d:
            f,ref,n,x=fixture(d,native)
            for kind in ('owner','context','view','shape','bias','offset','uv','raw','sample','bytes','duplicate_gsg','unavailable_with_bytes'):
                y=copy.deepcopy(x);t=y['textures'][0];w=t['mip1_windows'][0]['window']
                if kind=='owner':t['pointer']+=1
                elif kind=='context':t['cache'][0]['context_index']=5
                elif kind=='view':t['mips']['num_views']=9
                elif kind=='shape':t['mips']['levels'][1]['size_xy'][0]+=1
                elif kind=='bias':t['minimum_bias_by_context']=[0]
                elif kind=='offset':w['texels'][0]['offset']+=4
                elif kind=='uv':w['uv'][0]+=.001
                elif kind=='raw':w['texels'][0]['raw_hex']='00'*4
                elif kind=='sample':t['mip1_windows'][0]['sample_index']=1
                elif kind=='bytes':y['mip1_sample_bytes_captured']+=4
                elif kind=='duplicate_gsg':y['contexts'].append(copy.deepcopy(y['contexts'][0]))
                else:w['status']='UNAVAILABLE_NOT_RESIDENT'
                write(f/'prepared.json',y)
                with self.subTest(kind=kind),self.assertRaises(ValueError):h.validate_receipt(f,ref,n)
    def test_exact_cold_help_and_private_lifecycle_entry(self):
        for entry,flags in ((native.__file__,['-I','-S','-B']),(h.__file__,['-I','-B'])):
            r=subprocess.run([sys.executable,*flags,entry,'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr)
        a=SimpleNamespace(out='/tmp/o',nonce='n');before=oldnative.owned_child_command(a,1);command=native.owned_child_command(a,1);self.assertEqual(command[:4]+command[5:],before[:4]+before[5:]);self.assertIn('sdk3_prepared_texture_native.py',command[4]);self.assertEqual(oldnative.owned_child_command(a,1),before);self.assertEqual(oldhost.ENTRY,'/work/repo/scripts/sdk3_terrain_attribute_native.py')
if __name__=='__main__':unittest.main()
