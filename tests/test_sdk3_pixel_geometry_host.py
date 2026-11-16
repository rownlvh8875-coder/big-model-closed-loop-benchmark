"""Synthetic wire data only; no Panda, SDK, model or Docker invocation."""
import copy,hashlib,json,tempfile,unittest,uuid,zlib
from pathlib import Path
import numpy as np
from scripts import run_sdk3_pixel_geometry as h
from scripts import sdk3_pixel_geometry as g,panda_sdk3_runtime as p
from scripts.continue_panda_sdk3_models import PROFILE
from tests.test_aggregate_original_mdv3_current_recheck import mock_trial


def write(path,value):path.write_text(json.dumps(value,allow_nan=False))

class ZeroModelAdmission(unittest.TestCase):
    def fixture(self,root):
        root=Path(root);dest=root/'renderer';dest.mkdir();nonce='ab'*16;identity='cd'*32;owner='ef'*16
        raw_road=np.full((604,964,3),100,np.uint8).tobytes();raw_wide=np.full((604,964,3),120,np.uint8).tobytes();road=hashlib.sha256(raw_road).hexdigest();wide=hashlib.sha256(raw_wide).hexdigest()
        a=mock_trial(20261110,'s_curve_left_right',11);b=copy.deepcopy(a);b['process_id']=24
        for row in (a,b):
            row['selected_sdk_sha256']=p.SDK_SHA
            for frame in row['frames']:frame['source_road_rgb_sha256']=road;frame['source_wide_rgb_sha256']=wide
        b['frames'][6]['source_road_rgb_sha256']='01'*32;reference=g.reference_from_reports(a,b);refpath=root/'reference.json';write(refpath,reference)
        captures=[dict(step=i+1,pose=reference['previous_states'][i-1] if i else dict(t=0.,x=0.,y=0.,heading=0.,speed=8.),road_sha256=road,wide_sha256=wide) for i in range(7)]
        rays=[dict(**sample,origin=[*sample['ndc'],-1.],direction=[0.,0.,1.],max_distance=2.) for sample in g.pixel_samples(964,604,596,494)]
        triangles=np.array([[[-1,-1,0],[1,-1,0],[0,1,0]]],dtype='<f8');ids=np.array([[0,0,0,0,1,2]],dtype='<i8');archive=g.save_geometry_archive(dest/'geometry.npz',triangles,ids)
        geometry=dict(stage='AFTER_ORIGINAL_ROAD_CPU_READ_BEFORE_CAMERA_RESTORE',borrowed_parent_is_origin=True,source_viewport=[0.,1.,0.,1.],source_buffer_size=[964,604],camera_to_world=np.eye(4).tolist(),lens_projection=np.eye(4).tolist(),rays=rays,meshes=[dict(mesh_id=0,path='synthetic/road',vertex_count=3,source_primitive_count=1,primitive_triangle_counts=[1],triangle_start=0,triangle_end=1)],counts=dict(triangles_tested=1),triangle_archive=archive,hits=g.all_ray_hits(triangles,rays),scan_finished_within_budget=True,cpu_scene_coverage_proven=False,gpu_pixel_owner_proven=False,depth_tie_proven=False,unique_cause_proven=False,cpu_sample_rays_not_msaa_positions=True,cpu_net_state_not_actual_cull_draw_state=True)
        images=[]
        for camera,raw in [('road',raw_road),('wide',raw_wide)]:
            name='step7-'+camera+'.rgb.zlib';compressed=zlib.compress(raw);(dest/name).write_bytes(compressed);images.append(dict(camera=camera,file=name,shape=[604,964,3],raw_bytes=len(raw),compressed_bytes=len(compressed),sha256=hashlib.sha256(raw).hexdigest()))
        report=dict(protocol='sdk3-pixel-geometry-v1',status='ZERO_MODEL_REPLAY_RECORDED',pid=11,process_uuid=uuid.uuid4().hex,nonce=nonce,repeat=0,seed=20261110,scenario='s_curve_left_right',base_camera_sha256='23d90c3d12894f855ae64d4607c03f3bf34e31e28dd7f5ce82bd0ddc7b37faf5',official_model_processes=0,onnx_inferences=0,ort_used=False,ort_module_loaded=False,model_weights_used=False,repair_proven=False,stage7_complete=False,provider_closed=True,getter_restored=True,extra_gpu_queries=0,extra_render_tasks=0,core_sha256=p.CORE_SHA,sdk_sha256=p.SDK_SHA,panda_version='1.10.13',reference_sha256=hashlib.sha256(refpath.read_bytes()).hexdigest(),captures=captures,geometry=geometry,replay=g.qualify_replay(captures,reference),target_images=images,target_read_sha256=road,target_road_rgb=[100,100,100],observer=dict(read_attempts=7,reads=7,inspection_attempts=1,inspections=1),tasks_before=['igLoop','PSSM.update','update main chase camera'],tasks_after=['igLoop','PSSM.update','update main chase camera'],task_frame_count_delta=14,driver=dict(renderer='softpipe'),child_finalized_before_server_stop=True,server_returncode=0)
        write(dest/'report.json',report);write(dest/'native-child.json',dict(spawn_attempted=True,pid=11,returncode=0,server_returncode=0))
        write(dest/'execution.json',dict(returncode=0,failure=None,ownership_unresolved=False,owned_container_removed=True,container_id=identity,stopped_state=dict(Running=False,Pid=0,OOMKilled=False,ExitCode=0)))
        write(dest/'container.json',dict(id=identity,name='test-geometry',image=p.IMAGE,ownership_label=owner,effective_limits=PROFILE))
        cmd=h.native_command('test-geometry',root,root/'sdk',dest,['--repeat','0','--nonce',nonce],reference=refpath,owner=owner)
        write(dest/'command.json',dict(argv=cmd,ownership_label=owner));return dest,refpath,nonce

    def test_valid_zero_model_replay_recomputes_numeric_hits_without_gpu_claim(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);result=h.validate_receipt(dest,ref,0,nonce)
            self.assertTrue(result['replay']['source_images_match_reference']);self.assertEqual(result['hits']['center'][0]['distance'],1.)
            self.assertFalse(result['gpu_pixel_owner_proven']);self.assertFalse(result['original_matrix_gate_passed']);self.assertEqual(result['onnx_inferences'],0)

    def test_wrong_lifecycle_profile_id_runtime_or_model_claim_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d)
            cases=[('native-child.json',('returncode',),None),('native-child.json',('server_returncode',),1),('execution.json',('stopped_state','OOMKilled'),True),('execution.json',('owned_container_removed',),False),('execution.json',('container_id',),None),('container.json',('effective_limits','NanoCpus'),1000000000),('report.json',('official_model_processes',),1),('report.json',('onnx_inferences',),1),('report.json',('ort_module_loaded',),True),('report.json',('sdk_sha256',),'00'*32),('report.json',('getter_restored',),False),('report.json',('target_read_sha256',),'00'*32),('report.json',('geometry','gpu_pixel_owner_proven'),True)]
            for name,keys,value in cases:
                path=dest/name;raw=path.read_bytes();row=json.loads(raw);target=row
                for key in keys[:-1]:target=target[key]
                target[keys[-1]]=value;write(path,row)
                with self.subTest(name=name,keys=keys),self.assertRaises(ValueError):h.validate_receipt(dest,ref,0,nonce)
                path.write_bytes(raw)

    def test_source_mismatch_and_truncated_scan_are_honestly_inconclusive(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'report.json';row=json.loads(path.read_text());reference=json.loads(ref.read_text());row['captures'][0]['road_sha256']='00'*32;row['replay']=g.qualify_replay(row['captures'],reference);row['geometry']['scan_finished_within_budget']=False;write(path,row)
            result=h.validate_receipt(dest,ref,0,nonce);self.assertFalse(result['replay']['source_images_match_reference']);self.assertFalse(result['geometry_scan_finished']);self.assertFalse(result['gpu_pixel_owner_proven'])

    def test_forged_geometry_hit_or_extra_model_mount_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'report.json';raw=path.read_bytes();row=json.loads(raw);row['geometry']['hits']['center'][0]['distance']=99;write(path,row)
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,0,nonce)
            path.write_bytes(raw);path=dest/'command.json';row=json.loads(path.read_text());i=row['argv'].index(p.IMAGE);row['argv'][i:i]=['--mount','type=bind,src=/tmp/model,dst=/model.onnx,readonly'];write(path,row)
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,0,nonce)

if __name__=='__main__':unittest.main()
