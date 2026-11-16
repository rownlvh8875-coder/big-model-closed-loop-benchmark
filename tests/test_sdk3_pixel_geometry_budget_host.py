"""Synthetic complete progress+geometry protocol fixtures, no native target."""
import copy,json,shutil,tempfile,unittest
from pathlib import Path
from scripts import run_sdk3_pixel_geometry_budget as h,panda_sdk3_runtime as p
from tests import test_sdk3_capture_progress_host as progress,test_sdk3_pixel_geometry_host as geometry
write=progress.write

class GeometryAdmission(unittest.TestCase):
    def fixture(self,root):
        root=Path(root);dest,ref,nonce=progress.Admission().complete_fixture(root);aux=root/'geometry-fixture';aux.mkdir();gd,_,_=geometry.ZeroModelAdmission().fixture(aux);gr=json.loads((gd/'report.json').read_text())['geometry'];shutil.copyfile(gd/'geometry.npz',dest/'geometry.npz');gr.update(lens_projection_inverse=[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]],lens_inverse_dtype='float32',lens_far_limit=1e-7);gr['meshes'][0].update(node_ordinal=0,geom_index=0);gr['counts']['nontriangle_primitives']=0;r=json.loads((dest/'report.json').read_text());image=dict(r['captures'][6]['images'][0]);shutil.copyfile(dest/image['file'],dest/'target-road.rgb.zlib');image['file']='target-road.rgb.zlib'
        manifest=dict(protocol='sdk3-pixel-geometry-budget-v1',pid=11,nonce=nonce,status='GEOMETRY_RECORDED',child_timeout_seconds=600,container_timeout_seconds=630,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False,target_step=7,target_pixel_xy=[596,494],target_pixel_rgb=[100,100,100],target_read_sha256=image['sha256'],target_image=image,observer=dict(read_attempts=7,reads=7,inspection_attempts=1,inspections=1),observers_restored=True,geometry=gr);write(dest/'geometry-observer.json',manifest)
        w=json.loads((dest/'watchdog.json').read_text());w['timeout_seconds']=600;write(dest/'watchdog.json',w);c=json.loads((dest/'command.json').read_text());i=c['argv'].index('/work/repo/scripts/sdk3_capture_progress_native.py');c['argv'][i]='/work/repo/scripts/sdk3_pixel_geometry_budget_native.py';write(dest/'command.json',c)
        path=dest/'progress.jsonl';rows=[json.loads(line) for line in path.read_text().splitlines()];result=[]
        for row in rows:
            result.append(row)
            if row['event']=='get_rgb.return' and row['step']==7 and row['camera']=='road':
                for stage in ['GEOMETRY_ENTER','GEOMETRY_RETURN']:result.append(dict(row,event='checkpoint',metadata=dict(stage=stage,**({'target_sha256':image['sha256']} if stage=='GEOMETRY_ENTER' else {}))))
        path.write_text(''.join(json.dumps(dict(row,seq=i+1,elapsed_s=i*.001,cpu_s=i*.001),separators=(',',':'))+'\n' for i,row in enumerate(result)));return dest,ref,nonce
    def test_complete_source_qualified_geometry_recomputes_hits_without_gpu_claim(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);r=h.validate_receipt(dest,ref,nonce);self.assertTrue(r['native_completed']);self.assertTrue(r['source_image_equivalence']);self.assertTrue(r['geometry_recorded']);self.assertTrue(r['geometry_scan_finished']);self.assertEqual(r['geometry']['hits']['center'][0]['distance'],1.);self.assertEqual(r['verified_source_images'],14);self.assertFalse(r['gpu_pixel_owner_proven']);self.assertFalse(r['original_matrix_gate_passed']);self.assertFalse(r['stage7_complete'])
    def test_old_timeout_wrong_target_identity_observer_or_gpu_claim_reject(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d)
            cases=[('watchdog.json',('timeout_seconds',),160),('geometry-observer.json',('pid',),12),('geometry-observer.json',('nonce',),'00'*16),('geometry-observer.json',('target_pixel_xy',),[494,596]),('geometry-observer.json',('observer','reads'),8),('geometry-observer.json',('observers_restored',),False),('geometry-observer.json',('target_read_sha256',),'00'*32),('geometry-observer.json',('geometry','gpu_pixel_owner_proven'),True),('geometry-observer.json',('geometry','hits','center'),[])]
            for name,keys,value in cases:
                path=dest/name;raw=path.read_bytes();r=json.loads(raw);node=r
                for key in keys[:-1]:node=node[key]
                node[keys[-1]]=value;write(path,r)
                with self.subTest(keys=keys),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
                path.write_bytes(raw)
    def test_geometry_outside_borrowed_road_boundary_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'progress.jsonl';rows=[json.loads(line) for line in path.read_text().splitlines()]
            for row in rows:
                if row['event']=='checkpoint':row['camera']='wide'
            path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_partial_scan_or_source_mismatch_does_not_promote_diagnostic(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'geometry-observer.json';m=json.loads(path.read_text());m['geometry'].update(scan_finished_within_budget=False,truncation_reasons=['time_budget'],cpu_scan_seconds=46.);write(path,m);r=h.validate_receipt(dest,ref,nonce);self.assertFalse(r['geometry_scan_finished']);self.assertFalse(r['renderer_diagnostic_passed']);self.assertFalse(r['repair_proven'])
            reference=json.loads(ref.read_text());reference['prefix_sha256'][0]['road']='00'*32;write(ref,reference);report=json.loads((dest/'report.json').read_text());report['reference_sha256']=p.digest(ref);write(dest/'report.json',report);r=h.validate_receipt(dest,ref,nonce);self.assertFalse(r['source_image_equivalence']);self.assertFalse(r['renderer_diagnostic_passed']);self.assertTrue(r['geometry_recorded'])
    def test_target_raw_bytes_and_geometry_counter_cannot_be_forged(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'target-road.rgb.zlib';raw=path.read_bytes();path.write_bytes(b'bad')
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
            path.write_bytes(raw);path=dest/'geometry-observer.json';m=json.loads(path.read_text());m['geometry']['counts']['triangles_tested']=9;write(path,m)
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
