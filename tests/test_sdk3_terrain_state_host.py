from pathlib import Path
from types import SimpleNamespace
import copy,hashlib,json,subprocess,sys,tempfile,unittest
from scripts import sdk3_terrain_state_native as native,run_sdk3_terrain_state as h,sdk3_shader_cache_native as oldnative
from tests.sdk3_terrain_state_fixtures import fixture

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

class TerrainAdmission(unittest.TestCase):
    def test_real_snapshot_records_tag_sources_and_candidate_windows(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native);r=h.validate_receipt(folder,ref,nonce)
            self.assertEqual(x['status'],'TERRAIN_RECORDED');self.assertTrue(r['terrain_complete']);self.assertTrue(r['terrain_present']);self.assertTrue(r['terrain_tag_shader_matched']);self.assertGreater(r['cpu_candidate_windows_captured'],0)
            self.assertEqual([row['role'] for row in x['states']],['node_net','camera_initial','camera_tag','cpu_net_then_tag']);self.assertIsNone(x['states'][0]['shader_id']);self.assertEqual(x['states'][2]['shader_id'],x['states'][3]['shader_id'])
            self.assertEqual(x['states'][2]['shader_override'],7);self.assertFalse(r['gpu_pixel_owner_proven']);self.assertFalse(r['stage7_complete'])
    def test_absent_terrain_is_explicit_and_unqualified(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native,absent=True);r=h.validate_receipt(folder,ref,nonce);self.assertFalse(r['terrain_present']);self.assertFalse(r['terrain_tag_shader_matched']);self.assertFalse(r['renderer_diagnostic_passed'])
    def test_unavailable_cpu_ram_never_fabricates_texels(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native,resident=False);r=h.validate_receipt(folder,ref,nonce);self.assertEqual(r['cpu_candidate_windows_captured'],0);self.assertTrue(r['terrain_complete'])
            for row in x['textures']:
                for window in row['windows']:self.assertEqual(window['window'],dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=False))
    def test_identity_binding_interval_and_false_claim_mutations_reject(self):
        cases=[(('nonce',),'forged'),(('target_read_sha256',),'00'*32),(('shader_sha256',),'00'*32),(('geometry_archive_sha256',),'00'*32),(('observer_finalized',),False),(('borrowed_parent_is_origin',),False),(('terrain_enter_elapsed_s',),-1.),(('gpu_program_execution_proven',),True),(('gpu_pixel_owner_proven',),True),(('cpu_candidates_are_terrain_intersections',),True),(('states_are_actual_cull_state',),True)]
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native)
            for keys,value in cases:
                v=copy.deepcopy(x);row=v
                for k in keys[:-1]:row=row[k]
                row[keys[-1]]=value;write(folder/'terrain.json',v)
                with self.subTest(keys=keys),self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
    def test_owner_texture_binding_mismatch_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native);x['textures'][0]['texture']['pointer']=999;write(folder/'terrain.json',x)
            with self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
    def test_forged_candidate_uv_or_world_position_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native)
            for key in ('attribute_uv','world_point','local_point'):
                v=copy.deepcopy(x);v['samples'][0][key][0]+=.1;write(folder/'terrain.json',v)
                with self.subTest(key=key),self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
    def test_offset_coordinate_and_byte_hash_mutations_reject(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native)
            for key in ('offset','xy','raw_hex'):
                v=copy.deepcopy(x);row=v['textures'][0]['windows'][0]['window']['texels'][0]
                if key=='offset':row[key]+=4
                elif key=='xy':row[key][0]+=1
                else:row[key]='ff'*row['nbytes']
                write(folder/'terrain.json',v)
                with self.subTest(key=key),self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
    def test_changed_source_and_actual_shader_bytes_reject(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native)
            for desc in (x['sources'][0],x['shaders'][0]['stages']['fragment']['text']):
                p=folder/desc['file'];raw=p.read_bytes();p.write_bytes(b'changed')
                with self.subTest(file=desc['file']),self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
                p.write_bytes(raw)
    def test_rehashed_changed_cache_is_retained_as_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native);desc=x['shaders'][0]['stages']['fragment']['text'];p=folder/desc['file'];raw=p.read_bytes().replace(b'void main()',b'void changed()',1);delta=len(raw)-desc['nbytes'];p.write_bytes(raw);desc.update(nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());x['bytes_captured']+=delta;write(folder/'terrain.json',x);r=h.validate_receipt(folder,ref,nonce);self.assertFalse(r['terrain_tag_shader_matched']);self.assertFalse(r['renderer_diagnostic_passed'])
    def test_partial_observation_cannot_promote_gate(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native);x.update(status='TERRAIN_PARTIAL',selection_complete=False,truncation_reasons=['time_budget']);write(folder/'terrain.json',x);r=h.validate_receipt(folder,ref,nonce);self.assertFalse(r['terrain_complete']);self.assertFalse(r['renderer_diagnostic_passed'])
    def test_duplicate_known_input_or_forged_unavailable_data_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            folder,ref,nonce,x=fixture(d,native)
            for duplicate in (True,False):
                v=copy.deepcopy(x);inputs=v['states'][1]['known_inputs']
                if duplicate:inputs[1]['name']=inputs[0]['name']
                else:inputs[0]['vector']=[1.,0.,0.,0.]
                write(folder/'terrain.json',v)
                with self.subTest(duplicate=duplicate),self.assertRaises(ValueError):h.validate_receipt(folder,ref,nonce)
    def test_private_entry_does_not_change_prior_globals(self):
        args=SimpleNamespace(out='/tmp/out',nonce='n');before=oldnative.owned_child_command(args,1);cmd=native.owned_child_command(args,1)
        self.assertIn('sdk3_terrain_state_native.py',cmd[4]);self.assertEqual(oldnative.owned_child_command(args,1),before);self.assertNotIn('--model-trial',cmd)
        for entry in (native.__file__,h.__file__):
            r=subprocess.run([sys.executable,'-I','-B',str(Path(entry).resolve()),'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr)
            if entry==h.__file__:self.assertIn('--run',r.stdout)

if __name__=='__main__':unittest.main()
