"""Synthetic protocol fixtures; no real SDK/renderer/model invocation."""
import copy,hashlib,json,tempfile,unittest,zlib
from pathlib import Path
import numpy as np
from scripts import run_sdk3_capture_progress as h,sdk3_pixel_geometry as g,panda_sdk3_runtime as p
from scripts.sdk3_capture_progress import Journal,observe
from scripts.continue_panda_sdk3_models import PROFILE
from tests.test_sdk3_capture_progress import Camera
from tests.test_aggregate_original_mdv3_current_recheck import mock_trial

def write(path,row):path.write_text(json.dumps(row))

class Admission(unittest.TestCase):
    def fixture(self,root):
        root=Path(root);dest=root/'renderer';dest.mkdir();nonce='ab'*16;owner='ef'*16;cid='cd'*32;identity=dict(pid=11,nonce=nonce,protocol='sdk3-capture-progress-v1')
        raw=np.full((604,964,3),100,np.uint8).tobytes();sha=hashlib.sha256(raw).hexdigest();a=mock_trial(20261110,'s_curve_left_right',11);b=copy.deepcopy(a);b['process_id']=24
        for r in (a,b):
            r['selected_sdk_sha256']=p.SDK_SHA
            for f in r['frames']:f['source_road_rgb_sha256']=sha;f['source_wide_rgb_sha256']=sha
        b['frames'][6]['source_road_rgb_sha256']='01'*32;ref=g.reference_from_reports(a,b);refpath=root/'reference.json';write(refpath,ref)
        images=[]
        for camera in ('road','wide'):
            name='step1-'+camera+'.rgb.zlib';compressed=zlib.compress(raw);(dest/name).write_bytes(compressed);images.append(dict(camera=camera,file=name,shape=[604,964,3],sha256=sha,raw_bytes=len(raw),compressed_bytes=len(compressed)))
        report=dict(protocol='sdk3-capture-progress-v1',status='INCOMPLETE',pid=11,process_uuid='12'*16,nonce=nonce,repeat=0,seed=20261110,scenario='s_curve_left_right',core_sha256=p.CORE_SHA,sdk_sha256=p.SDK_SHA,panda_version='1.10.13',base_camera_sha256='23d90c3d12894f855ae64d4607c03f3bf34e31e28dd7f5ce82bd0ddc7b37faf5',reference_sha256=p.digest(refpath),official_model_processes=0,onnx_inferences=0,model_weights_used=False,repair_proven=False,stage7_complete=False,provider_closed=False,checkpoint='CAPTURE_ENTER',active_step=2,driver=dict(renderer='softpipe'),tasks_before=['igLoop','PSSM.update','update main chase camera'],captures=[dict(step=1,pose=dict(t=0.,x=0.,y=0.,heading=0.,speed=8.),road_sha256=sha,wide_sha256=sha,images=images)])
        write(dest/'report.json',report);write(dest/'native-child.json',dict(spawn_attempted=True,pid=11,returncode=-9,server_returncode=0));write(dest/'watchdog.json',dict(pid=11,timeout_seconds=160,timed_out=True,child_returncode=-9,server_returncode=0,elapsed_s=160.1,proc_before_kill={'stat':'11 '+Path('/proc/self/stat').read_text().split(' ',1)[1],'status':'Name:\tpython\nPid:\t11\n','wchan':'0'}))
        write(dest/'execution.json',dict(returncode=1,failure=None,ownership_unresolved=False,owned_container_removed=True,container_id=cid,stopped_state=dict(Running=False,Pid=0,OOMKilled=False,ExitCode=1)))
        write(dest/'container.json',dict(id=cid,name='test-progress',image=p.IMAGE,ownership_label=owner,effective_limits=PROFILE));cmd=h.native_command('test-progress',root,root/'sdk',dest,['--repeat','0','--nonce',nonce],reference=refpath,owner=owner);write(dest/'command.json',dict(argv=cmd,ownership_label=owner))
        j=Journal(dest,identity);c=Camera()
        with observe(c,j):c.capture(None)
        j.emit('capture.enter',step=2);j.emit('perceive.enter',step=2,camera='road');j.emit('task_step.enter',step=2,camera='road');j.close();(dest/'stacks.log').write_text('Timeout (0:00:30)!\nThread 0x123:\n  File "camera.py", line 7 in capture\n')
        return dest,refpath,nonce
    def test_timeout_is_observation_only_and_active_boundary_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);r=h.validate_receipt(dest,ref,nonce);self.assertEqual(r['status'],'TRACE_RECORDED_NATIVE_TIMEOUT');self.assertFalse(r['native_completed']);self.assertFalse(r['renderer_diagnostic_passed']);self.assertFalse(r['stage7_complete']);self.assertEqual(r['active_boundaries'][-1],dict(operation='task_step',step=2,camera='road'));self.assertEqual(r['completed_capture_returns'],1);self.assertIsNone(r['source_image_equivalence']);self.assertTrue(r['completed_prefix_matches_reference']);self.assertEqual(r['onnx_inferences'],0)
    def test_unknown_exit_wrong_pid_oom_cleanup_or_model_claim_cannot_be_admitted(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d)
            for name,keys,value in [('native-child.json',('returncode',),None),('watchdog.json',('pid',),12),('watchdog.json',('timed_out',),False),('execution.json',('owned_container_removed',),False),('execution.json',('stopped_state','OOMKilled'),True),('report.json',('onnx_inferences',),1),('report.json',('sdk_sha256',),'00'*32)]:
                path=dest/name;raw=path.read_bytes();row=json.loads(raw);target=row
                for k in keys[:-1]:target=target[k]
                target[keys[-1]]=value;write(path,row)
                with self.subTest(name=name,keys=keys),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
                path.write_bytes(raw)
    def test_extra_model_mount_and_false_native_entry_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'command.json';raw=path.read_bytes();row=json.loads(raw);i=row['argv'].index(p.IMAGE);row['argv'][i:i]=['--mount','type=bind,src=/tmp/model,dst=/model.onnx,readonly'];write(path,row)
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
            path.write_bytes(raw);row=json.loads(raw);i=row['argv'].index('/work/repo/scripts/sdk3_capture_progress_native.py');row['argv'][i]='/work/repo/scripts/panda_sdk3_diagnostic.py';write(path,row)
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_missing_timeout_stacks_or_forged_source_bytes_reject(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);path=dest/'stacks.log';raw=path.read_bytes();path.write_bytes(b'')
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
            path.write_bytes(raw);(dest/'step1-road.rgb.zlib').write_bytes(zlib.compress(b'wrong'))
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)

    def complete_fixture(self,d):
        dest,ref,nonce=self.fixture(d);r=json.loads((dest/'report.json').read_text());reference=json.loads(ref.read_text());first=r['captures'][0];captures=[]
        for step in range(1,8):
            c=copy.deepcopy(first);c['step']=step
            if step>1:c['pose']=reference['previous_states'][step-2]
            for image in c['images']:
                old=dest/image['file'];image['file']=f"step{step}-{image['camera']}.rgb.zlib";(dest/image['file']).write_bytes(old.read_bytes())
            captures.append(c)
        r.update(captures=captures,status='CAPTURE_REPLAY_RECORDED',provider_closed=True,observers_restored=True,ort_module_loaded=False,extra_gpu_queries=0,extra_render_tasks=0,tasks_after=r['tasks_before'],task_frame_count_delta=14);write(dest/'report.json',r)
        n=json.loads((dest/'native-child.json').read_text());n['returncode']=0;write(dest/'native-child.json',n);w=json.loads((dest/'watchdog.json').read_text());w.update(timed_out=False,child_returncode=0,elapsed_s=2.,proc_before_kill={});write(dest/'watchdog.json',w);e=json.loads((dest/'execution.json').read_text());e['returncode']=0;e['stopped_state']['ExitCode']=0;write(dest/'execution.json',e)
        (dest/'progress.jsonl').unlink();j=Journal(dest,dict(pid=11,nonce=nonce,protocol='sdk3-capture-progress-v1'));c=Camera()
        with observe(c,j):
            for _ in range(7):c.capture(None)
        j.close()
        return dest,ref,nonce
    def test_complete_seven_pose_source_match_is_still_not_original_gate(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.complete_fixture(d);result=h.validate_receipt(dest,ref,nonce);self.assertTrue(result['native_completed']);self.assertTrue(result['source_image_equivalence']);self.assertEqual(result['verified_source_images'],14);self.assertFalse(result['original_matrix_gate_passed']);self.assertFalse(result['repair_proven'])
    def test_retained_source_mismatch_remains_inconclusive(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=self.fixture(d);reference=json.loads(ref.read_text());reference['prefix_sha256'][0]['road']='00'*32;write(ref,reference);r=json.loads((dest/'report.json').read_text());r['reference_sha256']=p.digest(ref);write(dest/'report.json',r);result=h.validate_receipt(dest,ref,nonce);self.assertFalse(result['completed_prefix_matches_reference']);self.assertFalse(result['source_image_equivalence']);self.assertFalse(result['repair_proven'])
