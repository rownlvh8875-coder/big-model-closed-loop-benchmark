"""Synthetic complete inherited receipts, actual pinned source data, no Panda."""
from pathlib import Path
import copy,json,tempfile,unittest
from scripts import run_sdk3_shader_path as h,sdk3_shader_path as s,panda_sdk3_runtime as p
from tests import test_sdk3_pixel_material_host as material
write=material.write
ROOT=Path(__file__).resolve().parents[1]
class ShaderAdmission(unittest.TestCase):
    def fixture(self,root):
        dest,ref,nonce=material.MaterialAdmission().fixture(root);command=json.loads((dest/'command.json').read_text());i=command['argv'].index('/work/repo/scripts/sdk3_pixel_material_native.py');command['argv'][i]='/work/repo/scripts/sdk3_shader_path_native.py';write(dest/'command.json',command)
        m=json.loads((dest/'material.json').read_text());store=s.TextStore(dest);sources=[];raw={}
        for name in h.SOURCE_PINS:
            text=(ROOT/'docs/evidence/sdk3-shader-path-01/frozen-source'/(name+'.data')).read_bytes().decode('utf-8');sources.append(dict(name=name,**store.save(text,'source')));raw[name]=text
        config=dict(max_lights=8,use_normal_maps=False,use_emission_maps=True,enable_fog=False,use_occlusion_maps=False,use_330=False,enable_hardware_skinning=True,exposure=1.)
        shaders=[]
        for role,files,defines in [('scene',('simplepbr.vert','simplepbr.frag'),s.pipeline_defines(config)),('tonemap',('post.vert','tonemap.frag'),{})]:
            stages={}
            for stage,name in zip(('vertex','fragment'),files):stages[stage]=dict(filename='',text=store.save(s.variant(raw['third_party/simplepbr/shaders/'+name+'.glsl'],defines,stage),role+'-'+stage))
            shaders.append(dict(shader_id=len(shaders),pointer=100+len(shaders),language=2,error_flag=False,stages=stages))
        inputs=[dict(name=name,status='UNAVAILABLE_NUMERIC_ARRAY',value_type=4,priority=0) for name in s.INPUT_NAMES]
        texture=dict(pointer=300,name='scene',x_size=964,y_size=604,z_size=1,num_components=4,component_width=4,component_type=2,format=21,texture_type=1)
        x=dict(protocol='sdk3-shader-path-v1',pid=11,nonce=nonce,status='SHADER_RECORDED',limits=dict(h.LIMITS),clock='journal_elapsed_monotonic_seconds',shader_enter_elapsed_s=m['material_exit_elapsed_s'],shader_exit_elapsed_s=m['material_exit_elapsed_s'],elapsed_wall_seconds=0.,target_read_sha256=m['target_read_sha256'],geometry_archive_sha256=m['geometry_archive_sha256'],material_sha256=p.digest(dest/'material.json'),borrowed_parent_is_origin=True,observer_finalized=True,selection_complete=True,truncation_reasons=[],sources=sources,bytes_captured=store.used,pipeline=config,shaders=shaders,meshes=[dict(mesh_id=0,net_state_pointer=13,shader_attrib_pointer=101,shader_id=0,known_inputs=inputs)],camera=dict(initial_state_text='',tag_state_key='rgb'),tonemap=dict(shader_id=1,net_state_pointer=500,shader_attrib_pointer=501,quad_path='synthetic/quad',scene_texture=texture,copy_texture_pointer=301,tex_input=dict(name='tex',status='AVAILABLE_TEXTURE',value_type=1,priority=0,texture=copy.deepcopy(texture)),exposure_input=dict(name='exposure',status='AVAILABLE_VECTOR',value_type=3,priority=0,vector=[1.,0.,0.,1.])),pssm_owner=dict(available=False,input_values_bound_to_shader=False),known_input_scope='KNOWN_EIGHT_PSSM_NAMES_ONLY',all_inputs_enumerated=False,gpu_program_execution_proven=False,hardware_uniform_values_proven=False,gpu_pixel_owner_proven=False,unique_cause_proven=False,repair_proven=False,stage7_complete=False)
        write(dest/'shader.json',x);return dest,ref,nonce
    def test_bound_scene_tonemap_variants_and_unavailable_arrays_are_honest(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);x=h.validate_receipt(dest,ref,nonce);self.assertTrue(x['shader_recorded']);self.assertTrue(x['shader_complete']);self.assertTrue(x['shader_variants_matched']);self.assertEqual(x['shader']['known_inputs'],8);self.assertFalse(x['gpu_program_execution_proven']);self.assertFalse(x['hardware_uniform_values_proven']);self.assertFalse(x['stage7_complete'])
    def test_forged_target_material_state_texture_and_gpu_flags_reject(self):
        cases=[(('target_read_sha256',),'00'*32),(('material_sha256',),'00'*32),(('meshes',0,'net_state_pointer'),999),(('tonemap','tex_input','texture','pointer'),999),(('hardware_uniform_values_proven',),True),(('pssm_owner','input_values_bound_to_shader'),True),(('shader_enter_elapsed_s',),-1)]
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);raw=(dest/'shader.json').read_bytes()
            for keys,value in cases:
                x=json.loads(raw);row=x
                for key in keys[:-1]:row=row[key]
                row[keys[-1]]=value;write(dest/'shader.json',x)
                with self.subTest(keys=keys),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_modified_source_or_shader_bytes_reject(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);x=json.loads((dest/'shader.json').read_text())
            for desc in (x['sources'][0],x['shaders'][0]['stages']['fragment']['text']):
                file=dest/desc['file'];original=file.read_bytes();file.write_bytes(b'wrong')
                with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
                file.write_bytes(original)
    def test_changed_actual_variant_is_retained_as_unqualified_observation(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'shader.json';x=json.loads(path.read_text());x['pipeline']['use_normal_maps']=True;write(path,x);r=h.validate_receipt(dest,ref,nonce);self.assertTrue(r['shader_recorded']);self.assertFalse(r['shader_variants_matched']);self.assertFalse(r['renderer_diagnostic_passed'])
    def test_unknown_numeric_arrays_cannot_forge_values_or_duplicate_names(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'shader.json';raw=path.read_bytes()
            for duplicate in (False,True):
                x=json.loads(raw)
                if duplicate:x['meshes'][0]['known_inputs'][1]['name']=s.INPUT_NAMES[0]
                else:x['meshes'][0]['known_inputs'][0]['vector']=[0.,0.,0.,0.]
                write(path,x)
                with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_partial_and_source_mismatch_do_not_promote_gate(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'shader.json';x=json.loads(path.read_text());x.update(status='SHADER_PARTIAL',selection_complete=False,truncation_reasons=['time_budget']);write(path,x);r=h.validate_receipt(dest,ref,nonce);self.assertFalse(r['shader_complete']);self.assertFalse(r['renderer_diagnostic_passed'])

    def test_native_entry_boot_and_owned_child_command_keep_zero_model_scope(self):
        from types import SimpleNamespace
        from scripts import sdk3_shader_path_native as native
        from scripts import sdk3_pixel_material_native as original
        before=original.owned_child_command(SimpleNamespace(out='/tmp/o',nonce='n'),123)
        cmd=native.owned_child_command(SimpleNamespace(out='/tmp/o',nonce='n'),123)
        self.assertIn('sdk3_shader_path_native.py',cmd[4]);self.assertIn('--owned-child',cmd);self.assertEqual(cmd[cmd.index('--server-owner')+1],'123');self.assertNotIn('--model-trial',cmd);self.assertEqual(original.owned_child_command(SimpleNamespace(out='/tmp/o',nonce='n'),123),before)
