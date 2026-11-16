"""Synthetic material+geometry receipts; no Panda/SDK/model execution."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from scripts import run_sdk3_pixel_material as h,panda_sdk3_runtime as p
from tests import test_sdk3_pixel_geometry_budget_host as geometry
write=geometry.write

class MaterialAdmission(unittest.TestCase):
    def fixture(self,root):
        root=Path(root);dest,ref,nonce=geometry.GeometryAdmission().fixture(root);command=json.loads((dest/'command.json').read_text());i=command['argv'].index('/work/repo/scripts/sdk3_pixel_geometry_budget_native.py');command['argv'][i]='/work/repo/scripts/sdk3_pixel_material_native.py';write(dest/'command.json',command);g=json.loads((dest/'geometry-observer.json').read_text())['geometry'];matrix=[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]];raw=b'abc';file='material-001-ram.bin';(dest/file).write_bytes(raw)
        sampler=dict(wrap_u=1,wrap_v=1,wrap_w=1,minfilter=1,magfilter=1,effective_minfilter=1,effective_magfilter=1,anisotropic_degree=1,effective_anisotropic_degree=1,border_color=[0.,0.,0.,0.],min_lod=-1000.,max_lod=1000.,lod_bias=0.,text='synthetic-sampler')
        stage=dict(stage_id=0,name='default',sort=0,mode=0,texcoord_column='texcoord',texture_id=0,texture_matrix=matrix,effective_sampler=sampler,texture_default_sampler=sampler,differs_from_texture_default=False)
        mesh=dict(mesh_id=0,node_ordinal=0,path='synthetic/road',geom_index=0,geom_pointer=11,vertex_data_pointer=12,local_to_world=matrix,net_state_text='',net_state_text_truncated=False,net_state_pointer=13,stages=[stage],source_stage_count=1,material=dict(available=True,text='synthetic-material',name='synthetic',shininess=0.,**{key:dict(api_available=True,defined=(key=='diffuse'),value=[1.,1.,1.,1.] if key=='diffuse' else None) for key in ('ambient','diffuse','emission','specular','basecolor')}))
        # Old fixture omits optional actual pointers; bind the new synthetic values explicitly.
        g['meshes'][0].update(geom_pointer=11,vertex_data_pointer=12,net_state_text='',net_state_text_truncated=False,net_state_pointer=13,local_to_world=matrix);parent=json.loads((dest/'geometry-observer.json').read_text());parent['geometry']=g;write(dest/'geometry-observer.json',parent)
        triangle=dict(triangle_index=0,source_id=[0,0,0,0,1,2],positions_local=[[-1.,-1.,0.],[1.,-1.,0.],[0.,1.,0.]],normals=dict(status='CAPTURED',components=3,values=[[0.,0.,1.]]*3),texcoords={'texcoord':dict(status='CAPTURED',components=2,values=[[0.,0.],[1.,0.],[0.,1.]])})
        samples=[]
        for ray,hits in g['hits'].items():
            for hit in hits:
                b=hit['barycentric'];uv=[b[1],b[2]];samples.append(dict(ray=ray,triangle_index=0,barycentric=b,stages=[dict(stage_id=0,texture_id=0,column='texcoord',status='CAPTURED',uv=uv,transformed4=[*uv,0.,1.])]))
        journal=[json.loads(line) for line in (dest/'progress.jsonl').read_text().splitlines()];enter=next(r['elapsed_s'] for r in journal if r['event']=='checkpoint' and r['metadata'].get('stage')=='GEOMETRY_ENTER');exit=next(r['elapsed_s'] for r in journal if r['event']=='checkpoint' and r['metadata'].get('stage')=='GEOMETRY_RETURN')
        texture=dict(texture_id=0,pointer=14,name='color',filename='',fullpath='',x_size=1,y_size=1,z_size=1,num_components=3,component_width=1,component_type=0,format=7,texture_type=1,ram=dict(status='CAPTURED',file=file,nbytes=3,sha256=hashlib.sha256(raw).hexdigest(),resident_before=True,expected_nbytes=3,compression=1),asset=dict(status='UNAVAILABLE_NO_PATH'))
        m=dict(protocol='sdk3-pixel-material-v1',pid=11,nonce=nonce,status='MATERIAL_RECORDED',target_read_sha256=parent['target_read_sha256'],geometry_archive_sha256=g['triangle_archive']['sha256'],borrowed_parent_is_origin=True,clock='journal_elapsed_monotonic_seconds',material_enter_elapsed_s=enter+.0001,material_exit_elapsed_s=exit-.0001,cpu_seconds=.0008,limits=dict(max_hits_per_ray=8,max_triangles=40,max_stages=8,max_textures=16,max_file_bytes=8388608,max_total_bytes=16777216,max_cpu_seconds=20),selection_complete=True,truncation_reasons=[],selected_triangle_indices=[0],meshes=[mesh],triangles=[triangle],textures=[texture],samples=samples,bytes_captured=3,observer_finalized=True,shader_inputs_unenumerated=True,hardware_sampler_state_unobserved=True,gpu_material_result_proven=False,gpu_pixel_owner_proven=False,unique_cause_proven=False,repair_proven=False,stage7_complete=False)
        write(dest/'material.json',m);return dest,ref,nonce
    def test_raw_vertex_uv_and_texture_evidence_recompute_without_gpu_claim(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);r=h.validate_receipt(dest,ref,nonce);self.assertTrue(r['material_recorded']);self.assertEqual(r['material']['triangles'],1);self.assertEqual(r['material']['captured_bytes'],3);self.assertEqual(r['material']['samples'],5);self.assertFalse(r['gpu_material_result_proven']);self.assertFalse(r['original_matrix_gate_passed']);self.assertFalse(r['stage7_complete'])
    def test_wrong_identity_geometry_vertex_uv_transform_or_texture_link_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'material.json';raw=path.read_bytes();cases=[(('pid',),12),(('target_read_sha256',),'00'*32),(('geometry_archive_sha256',),'00'*32),(('triangles',0,'source_id'),[0,0,0,2,1,0]),(('triangles',0,'positions_local',0),[9.,9.,0.]),(('triangles',0,'texcoords','texcoord','values',0),[9.,9.]),(('samples',0,'stages',0,'texture_id'),1),(('meshes',0,'stages',0,'texture_matrix',3),[1.,0.,0.,1.]),(('gpu_material_result_proven',),True)]
            for keys,value in cases:
                m=json.loads(raw);node=m
                for key in keys[:-1]:node=node[key]
                node[keys[-1]]=value;write(path,m)
                with self.subTest(keys=keys),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
                path.write_bytes(raw)
    def test_tampered_raw_data_or_forged_budget_and_sampler_override_reject(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);p=dest/'material-001-ram.bin';p.write_bytes(b'bad')
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
            p.write_bytes(b'abc');path=dest/'material.json';raw=path.read_bytes()
            for keys,value in [(('bytes_captured',),0),(('limits','max_total_bytes'),999999999),(('meshes',0,'stages',0,'differs_from_texture_default'),True),(('material_enter_elapsed_s',),0.)]:
                m=json.loads(raw);node=m
                for key in keys[:-1]:node=node[key]
                node[keys[-1]]=value;write(path,m)
                with self.subTest(keys=keys),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
                path.write_bytes(raw)
    def test_unavailable_ram_and_partial_or_source_mismatch_remain_honest(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'material.json';m=json.loads(path.read_text());m['textures'][0]['ram']=dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=False);m['bytes_captured']=0;(dest/'material-001-ram.bin').unlink();write(path,m);r=h.validate_receipt(dest,ref,nonce);self.assertTrue(r['material_recorded']);self.assertEqual(r['material']['captured_bytes'],0);self.assertEqual(r['material']['textures_without_ram'],1);self.assertFalse(r['gpu_material_result_proven'])
            m.update(selection_complete=False,truncation_reasons=['time_budget']);write(path,m);r=h.validate_receipt(dest,ref,nonce);self.assertFalse(r['material_complete']);self.assertFalse(r['renderer_diagnostic_passed'])
            reference=json.loads(ref.read_text());reference['prefix_sha256'][0]['road']='00'*32;write(ref,reference);report=json.loads((dest/'report.json').read_text());report['reference_sha256']=p.digest(ref);write(dest/'report.json',report);r=h.validate_receipt(dest,ref,nonce);self.assertFalse(r['source_image_equivalence']);self.assertFalse(r['renderer_diagnostic_passed'])
