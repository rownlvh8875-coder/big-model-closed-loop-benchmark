from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,unittest
from scripts import run_sdk3_shader_cache as h,sdk3_shader_cache as cache,sdk3_shader_cache_native as native,panda_sdk3_runtime as p
from tests import sdk3_shader_cache_fixtures as fixtures

def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
def fixture(folder):
    dest,ref,nonce,x=fixtures.fixture(folder,native);command=json.loads((dest/'command.json').read_text());argv=command['argv'];argv[argv.index('/work/repo/scripts/sdk3_shader_path_native.py')]='/work/repo/scripts/sdk3_shader_cache_native.py';write(dest/'command.json',command);return dest,ref,nonce
class CacheAdmission(unittest.TestCase):
    def test_complete_pinned_cache_and_owner_arrays_pass_without_gpu_claim(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixture(d);r=h.validate_receipt(dest,ref,nonce);self.assertTrue(r['shader_complete']);self.assertTrue(r['shader_variants_matched']);self.assertTrue(r['pssm_owner_arrays_recorded']);self.assertEqual(r['shader_cache_policy_id'],cache.POLICY_ID);self.assertFalse(r['hardware_uniform_values_proven']);self.assertFalse(r['stage7_complete'])
    def test_rehashed_actual_crlf_or_code_change_is_not_normalized(self):
        for mode in ('crlf','code'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                dest,ref,nonce=fixture(d);path=dest/'shader.json';x=json.loads(path.read_text());desc=x['shaders'][0]['stages']['fragment']['text'];q=dest/desc['file'];old=q.read_bytes();new=old.replace(b'\n',b'\r\n') if mode=='crlf' else old.replace(b'void main()',b'void changed()',1);self.assertNotEqual(new,old);q.write_bytes(new);x['bytes_captured']+=len(new)-len(old);desc.update(nbytes=len(new),sha256=hashlib.sha256(new).hexdigest());write(path,x);r=h.validate_receipt(dest,ref,nonce);self.assertFalse(r['shader_variants_matched']);self.assertFalse(r['renderer_diagnostic_passed'])
    def test_complete_missing_or_nonfinite_owner_arrays_reject(self):
        for mode in ('missing','nan','shape'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                dest,ref,nonce=fixture(d);path=dest/'shader.json';x=json.loads(path.read_text())
                if mode=='missing':x['pssm_owner']=dict(available=False,input_values_bound_to_shader=False)
                elif mode=='nan':x['pssm_owner']['mvp_array'][0][0][0]=float('nan')
                else:x['pssm_owner']['nearfar_array']=[[1.,2.]]
                write(path,x)
                with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_partial_and_source_mismatch_remain_unqualified(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixture(d);path=dest/'shader.json';x=json.loads(path.read_text());x.update(status='SHADER_PARTIAL',selection_complete=False,truncation_reasons=['inspection_error'],pssm_owner=dict(available=False,input_values_bound_to_shader=False));write(path,x);r=h.validate_receipt(dest,ref,nonce);self.assertFalse(r['shader_complete']);self.assertFalse(r['pssm_owner_arrays_recorded']);self.assertFalse(r['renderer_diagnostic_passed'])
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixture(d);reference=json.loads(ref.read_text());reference['prefix_sha256'][0]['road']='00'*32;write(ref,reference);report=json.loads((dest/'report.json').read_text());report['reference_sha256']=p.digest(ref);write(dest/'report.json',report);r=h.validate_receipt(dest,ref,nonce);self.assertTrue(r['shader_variants_matched']);self.assertFalse(r['source_image_equivalence']);self.assertFalse(r['renderer_diagnostic_passed'])
    def test_target_material_state_and_owner_binding_forgery_reject(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixture(d);path=dest/'shader.json';raw=path.read_bytes()
            for keys,value in [(('target_read_sha256',),'00'*32),(('material_sha256',),'00'*32),(('meshes',0,'net_state_pointer'),999),(('pssm_owner','input_values_bound_to_shader'),True)]:
                x=json.loads(raw);node=x
                for key in keys[:-1]:node=node[key]
                node[keys[-1]]=value;write(path,x)
                with self.subTest(keys=keys),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_isolated_cli_help_needs_no_native_or_network(self):
        r=subprocess.run([sys.executable,'-I','-B',str(Path(h.__file__).resolve()),'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--run',r.stdout)
