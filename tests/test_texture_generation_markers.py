"""CPU-only protocol tests; fake camera/native/API boundaries never run Panda."""
import contextlib
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np
from scripts import texture_generation_markers as m


class Texture:
    def __init__(self, values, events): self.values=iter(values);self.events=events
    def get_image_modified(self): self.events.append('marker');return self
    def get_seq(self): return next(self.values)


class Camera:
    def __init__(self, events, values=(0,0)):
        self.events=events;self.array=np.zeros((604,964,3),np.uint8)
        self.copy_texture=Texture(values,events)
    def get_rgb_array_cpu(self): self.events.append('copy');return self.array


def provider(cameras):
    return types.SimpleNamespace(env=types.SimpleNamespace(engine=types.SimpleNamespace(
        sensors={'bigbench_'+k:v for k,v in zip(m.CAMERAS,cameras)})))


class MarkerTests(unittest.TestCase):
    def test_off_returns_original_object_without_marker_access_and_restores_inheritance(self):
        events=[];cams=[Camera(events),Camera(events)];p=provider(cams);rows=[]
        with m.marker_scope(p,False,rows):
            for cam in cams:self.assertIs(cam.get_rgb_array_cpu(),cam.array)
        self.assertEqual(events,['copy','copy']);self.assertEqual([r['camera'] for r in rows],['road','wide'])
        self.assertTrue(all('get_rgb_array_cpu' not in c.__dict__ for c in cams))
        self.assertEqual([(r['before'],r['after']) for r in rows],[(None,None)]*2)
        self.assertEqual(rows[0]['raw_sha256'],m._sha(cams[0].array.tobytes()))

    def test_signed_wrap_and_equal_markers_preserve_exact_order_and_instance_ownership(self):
        events=[];cams=[Camera(events,(-2147483648,2147483647)),Camera(events,(-1,-1))]
        original=cams[0].get_rgb_array_cpu;cams[0].get_rgb_array_cpu=original;rows=[]
        with m.marker_scope(provider(cams),True,rows):
            for cam in cams:self.assertIs(cam.get_rgb_array_cpu(),cam.array)
        self.assertIs(cams[0].__dict__['get_rgb_array_cpu'],original)
        self.assertEqual(events,['marker','copy','marker']*2)
        self.assertEqual([(r['before'],r['after']) for r in rows],[(-2147483648,2147483647),(-1,-1)])
        self.assertEqual([r['equal'] for r in rows],[False,True])

    def test_errors_restore_all_and_reject_nested_wrappers(self):
        for failure in ('body','before','copy','after'):
            events=[];cams=[Camera(events),Camera(events)];p=provider(cams);rows=[]
            def fail():raise RuntimeError(failure)
            if failure=='copy':cams[0].get_rgb_array_cpu=fail
            if failure=='before':cams[0].copy_texture.get_image_modified=fail
            if failure=='after':cams[0].copy_texture=Texture((0,),events)
            prior=[dict(c.__dict__) for c in cams]
            with self.assertRaises((RuntimeError,StopIteration)):
                with m.marker_scope(p,True,rows):
                    if failure=='body':raise RuntimeError('body')
                    cams[0].get_rgb_array_cpu()
            for c,attrs in zip(cams,prior):self.assertEqual(c.__dict__,attrs)
        with m.marker_scope(p,False,[]):
            with self.assertRaisesRegex(ValueError,'nested'):
                with m.marker_scope(p,True,[]):pass

    def test_invalid_marker_type_does_not_call_copy(self):
        events=[];cams=[Camera(events,(True,0)),Camera(events)]
        with self.assertRaises(ValueError):
            with m.marker_scope(provider(cams),True,[]):cams[0].get_rgb_array_cpu()
        self.assertEqual(events,['marker'])


class AdmissionTests(unittest.TestCase):
    def test_source_closure_exactly_65(self):
        snapshot=m.source_snapshot();self.assertEqual(len(snapshot),65)
        self.assertNotIn(m.REQUEST,snapshot);self.assertIn(m.WORKFLOW,snapshot)

    def test_request_strict_fields(self):
        self.assertEqual(m._request_data(dict(schema=m.REQUEST_SCHEMA,mode='canary',acceptance=None))['mode'],'canary')
        for data in (dict(schema=m.REQUEST_SCHEMA,mode='abba',acceptance=None),
                     dict(schema=m.REQUEST_SCHEMA,mode='canary',acceptance={},extra=1)):
            with self.assertRaises(ValueError):m._request_data(data)

    def test_native_runtime_requires_pins_and_absent_ort(self):
        valid=dict(python='3.11.9',executable='/usr/bin/python',numpy='2.4.6',
                   **{'opencv-python-headless':'5.0.0.93','panda3d':'1.10.13','metadrive-simulator':'0.4.3'},
                   onnxruntime=None,cv2='5.0.0',ImageOS='ubuntu24',ImageVersion='2026')
        m._check_runtime(valid)
        for key,value in [('onnxruntime','1.31.1'),('numpy','1.0'),('cv2',''),('python','3.12.1')]:
            bad=dict(valid);bad[key]=value
            with self.assertRaises(ValueError):m._check_runtime(bad)

    def test_cache_inventory_is_bounded_and_symlink_free(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.assertEqual(m._cache_inventory(root)['files'],0)
            (root/'one').write_bytes(b'abc');self.assertEqual(m._cache_inventory(root)['bytes'],3)
            (root/'link').symlink_to(root/'one')
            with self.assertRaises(ValueError):m._cache_inventory(root)

    def test_json_rejects_duplicates_nonfinite_and_budget(self):
        for data in (b'{"x":1,"x":2}',b'{"x":NaN}',b' '*(m.JSON_CAP+1)):
            with self.assertRaises(ValueError):m._json(data)

    def test_output_must_be_fixed_and_fresh(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'RUNNER_TEMP':d,'GITHUB_ACTIONS':'true'}):
            expected=Path(d)/'texture-marker-canary'
            self.assertEqual(m._output(expected,'canary'),expected)
            for path in (Path(d)/'other',Path(d),Path(d)/'texture-marker-abba'):
                with self.assertRaises(ValueError):m._output(path,'canary')
            expected.mkdir()
            with self.assertRaises(ValueError):m._output(expected,'canary')

    def test_missing_or_low_authorization_rejected_before_context(self):
        for value in ('','3','notfd'):
            with patch.dict(os.environ,{'FIRST_DIVERGENCE_TRIAL_FD':value}):
                with self.assertRaises(ValueError):m._consume('canary',0,'a'*64,Path('/tmp/x'))
                self.assertNotIn('FIRST_DIVERGENCE_TRIAL_FD',os.environ)

    def test_comparisons_include_both_repeats_and_all_cross_pairs(self):
        cases=[]
        for index,enabled in enumerate((False,True,True,False)):
            rows=[dict(raw={k:dict(rgb_sha256=str(index)) for k in m.CAMERAS},
                       canvas={k:dict(rgb_sha256='same') for k in m.CAMERAS},packed=dict(sha256='same'))]*6
            cases.append(dict(enabled=enabled,accepted=rows,markers=[dict(before=0,after=0,equal=True)]*12))
        result=m._comparisons(cases)
        self.assertEqual(len(result),6);self.assertEqual({r['kind'] for r in result},{'OFF/OFF','ON/ON','OFF/ON'})
        self.assertTrue(all(r['first_raw_difference']==dict(capture=1,camera='road') for r in result))


class WorkflowTests(unittest.TestCase):
    def test_parsed_workflow_exact_scope_bootstrap_and_no_models(self):
        workflow=json.loads((m.REPO/m.WORKFLOW).read_text())
        self.assertEqual(set(workflow['on']),{'push'})
        self.assertEqual(workflow['on']['push'],dict(branches=[m.BRANCH],paths=[m.SCRIPT_PATH,m.TEST_PATH,m.WORKFLOW,m.REQUEST]))
        self.assertEqual(workflow['permissions'],dict(contents='read',actions='read'))
        steps=workflow['jobs']['diagnostic']['steps']
        old=json.loads((m.REPO/'.github/workflows/stage7-first-divergence-post-transport.yml').read_text())
        oldsteps=old['jobs']['diagnostic']['steps']
        bootstrap=next(s for s in oldsteps if s.get('name')=='Install provided native system route')
        self.assertIn(bootstrap,steps)
        self.assertIn(next(s for s in oldsteps if s.get('name')=='Prepare exact official MetaDrive assets'),steps)
        commands='\n'.join(s.get('run','') for s in steps)
        self.assertNotIn('onnxruntime==',commands);self.assertNotIn('[inference]',commands);self.assertNotIn('hf_models',commands)
        self.assertEqual(commands.count('scripts.texture_generation_markers run'),1)
        for step in steps:
            if 'run' in step:
                result=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)


class DatasetTests(unittest.TestCase):
    """Real six-pair raw/canvas/I420 fixtures; no native library or engine."""
    def fixture(self,root,phase='canary'):
        from bigbench.camera import RGBFrame
        from bigbench.optical_calibration import PinholeRectifier, reference_source
        runtime=dict(python='3.11.9',executable='/usr/bin/python',numpy='2.4.6',
                     **{'opencv-python-headless':'5.0.0.93','panda3d':'1.10.13','metadrive-simulator':'0.4.3'},
                     onnxruntime=None,cv2='5.0.0',ImageOS='ubuntu24',ImageVersion='2026')
        context=dict(repository=m.REPOSITORY,workflow_path=m.WORKFLOW,workflow_id=1,head_sha='a'*40,
                     run_id=1,attempt=1,event='push',branch=m.BRANCH)
        request=dict(schema=m.REQUEST_SCHEMA,mode=phase,acceptance=None)
        if phase=='abba':
            request['acceptance']=dict(source_sha='b'*40,run_id=2,run_attempt=1,workflow_id=1,artifact_id=3,
                artifact_name='stage7-texture-marker-canary',artifact_size_bytes=100,artifact_sha256='c'*64,
                root_raw_accepted=True,fresh_raw_review_accepted=True)
        raw={k:np.full(m.capture.RAW_SHAPE,i*23+15,np.uint8) for i,k in enumerate(m.CAMERAS)}
        intrinsics={k:reference_source(k,964,604) for k in m.CAMERAS}
        pair,_=PinholeRectifier().rectify_pair(raw['road'],raw['wide'],road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
        from dataclasses import asdict
        blob=json.dumps(request);count=len(m.SCHEDULES[phase])
        data=dict(schema=m.SCHEMA,status='MARKER_DATASET_VALIDATED',phase=phase,parent_pid=100,parent_uuid='1'*32,
            context=context,source_snapshot=m.source_snapshot(),runtime=runtime,request_blob=blob,request_sha256=m._sha(blob.encode()),
            protocol=m.PROTOCOL,claims=m.CLAIMS,limitation=m.LIMITATION,acceptance=None,launches=[],comparisons=[],
            providers=count,accepted_pairs=6*count,observed_reads=12*count,marker_reads=24 if phase=='canary' else 48,
            elapsed_s=.1,error=None,cleanup_errors=[])
        if phase=='abba':data['acceptance']=dict(schema='texture-marker-acceptance-v1',accepted_context={**context,'head_sha':'b'*40,'run_id':2},acceptance=request['acceptance'],accepted_dataset_status='MARKER_DATASET_VALIDATED',source_snapshot=data['source_snapshot'],runtime=runtime)
        cases=[]
        for index,(enabled,repeat) in enumerate(m.SCHEDULES[phase]):
            case_root=root/f'case_{index:02d}';case_root.mkdir(parents=True)
            case=dict(schema=m.CASE_SCHEMA,status='CAMERA_REPLAY_RECORDED',phase=phase,index=index,enabled=enabled,repeat=repeat,
                nonce=str(index+4)*64,parent_pid=100,parent_uuid='1'*32,process_id=102+index*2,process_uuid=str(index+5)*32,
                process_group=101+index*2,context=context,source_snapshot=data['source_snapshot'],runtime=runtime,
                request_sha256=data['request_sha256'],protocol=m.PROTOCOL,claims=m.CLAIMS,limitation=m.LIMITATION,
                provider_attempted=True,provider_constructed=True,provider_closed=True,provider_lower_bound=1,provider_upper_bound=1,
                markers=[],capture_rows=[],accepted=[],capture_count=6,observed_reads=12,marker_reads=24 if enabled else 0,
                retained_payload_bytes=6*(m.capture.RAW_PAIR_BYTES+m.capture.CANVAS_PAIR_BYTES+m.capture.PACKED_BYTES),
                payload_charged_bytes=38171904,error=None,cleanup_errors=[])
            for i,pose in enumerate(m.POSES,1):
                accepted=dict(accepted_index=i,capture_index=i,observation=dict(speed_mps=8.,time_s=pose['t']),
                    intrinsics={k:asdict(v) for k,v in intrinsics.items()},raw={},canvas={})
                rawsha={};canvassha={}
                for camera in m.CAMERAS:
                    rawsha[camera]=m._sha(raw[camera].tobytes());canvassha[camera]=getattr(pair,camera).sha256
                    case['markers'].append(dict(call=len(case['markers'])+1,camera=camera,before=-1 if enabled else None,
                        after=-1 if enabled else None,equal=True if enabled else None,raw_sha256=rawsha[camera],
                        status='RETURNED',copy_attempted=True,copy_returned=True,copy_wall_s=0.,wrapper_wall_s=0.))
                    for boundary,frame in (('raw',RGBFrame(964,604,raw[camera].tobytes())),('canvas',getattr(pair,camera))):
                        name=f'capture_{i:02d}/{boundary}_{camera}.png';frame.save_png(case_root/name)
                        payload=(case_root/name).read_bytes()
                        accepted[boundary][camera]=dict(path=name,nbytes=len(payload),sha256=m._sha(payload),rgb_sha256=frame.sha256)
                packed=m.capture.camera_pair_to_model(pair.road,pair.wide).tobytes();name=f'capture_{i:02d}/packed_i420.bin'
                (case_root/name).write_bytes(packed)
                accepted['packed']=dict(path=name,nbytes=len(packed),sha256=m._sha(packed),actual_input_sha256=None,association='DERIVED_ONLY_NO_MODEL_CALL')
                case['accepted'].append(accepted)
                case['capture_rows'].append(dict(capture_index=i,status='RETURNED',pose=pose,raw_sha256=rawsha,canvas_sha256=canvassha,
                    capture_wrapper_wall_s=0.,capture_inclusive_wall_s=0.,wrapper_observer_arithmetic_wall_s=0.,raw_callback_nested_wall_s=0.,accept_observation_wall_s=0.))
            log=f'authorization_fd=10 phase=prepared\nphase=permit launcher_pid={case["process_group"]}\nphase=permit_sent\n'.encode()
            (case_root/'process.log').write_bytes(log);m._write(case_root/'case.json',case)
            cache=m._cache_inventory(case_root/'nonexistent')
            after=copy.deepcopy(cache);after.update(files=1,bytes=3,entries=[dict(path='mesa/cache',nbytes=3)])
            data['launches'].append(dict(index=index,enabled=enabled,nonce=case['nonce'],attempted=True,launched=True,
                launcher_pid=case['process_group'],process_group=case['process_group'],exit_code=0,cleanup_errors=[],error=None,
                group_gone=True,reaped=True,provider_lower_bound=1,provider_upper_bound=1,provider_attempted=True,
                provider_constructed=True,provider_closed=True,storage=dict(m.LIMITS,log_bytes=len(log),limit_error=None),
                cache_path='/runner/tmp/texture-marker-cache-'+data['parent_uuid']+f'-{index:02d}',cache_before=cache,cache_after=after,
                launch_s=.01,wait_s=.01,elapsed_s=.03,log=dict(path='process.log',nbytes=len(log),sha256=m._sha(log))))
            cases.append(case)
        data['comparisons']=m._comparisons(cases);m._write(root/'phase.json',data)
        return data,cases

    def rewrite(self,path,value):path.write_text(json.dumps(value))

    def test_real_fixture_canary_and_abba_exact_counts_and_comparisons(self):
        for phase,count in (('canary',33),('abba',129)):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);self.fixture(root,phase)
                result=m.validate_dataset(root)
                self.assertEqual(result['phase'],phase);self.assertEqual(len(m._members(root)[0]),count)
                if phase=='abba':self.assertEqual(len(result['comparisons']),6)

    def test_tampered_markers_pose_counter_source_runtime_raw_and_extra_members_rejected(self):
        changes=[('phase',lambda d:d['source_snapshot'].__setitem__(m.SCRIPT_PATH,'0'*64)),
                 ('phase',lambda d:d['runtime'].__setitem__('onnxruntime','1')),
                 ('phase',lambda d:d.__setitem__('providers',True)),
                 ('phase',lambda d:d.__setitem__('comparisons',[{}])),
                 ('case',lambda d:d['markers'][0].__setitem__('raw_sha256','0'*64)),
                 ('case',lambda d:d['markers'][0].__setitem__('before',True)),
                 ('case',lambda d:d['markers'][0].__setitem__('equal',False)),
                 ('case',lambda d:d['capture_rows'][0]['pose'].__setitem__('x',0.)),
                 ('case',lambda d:d['accepted'][0]['raw']['road'].__setitem__('rgb_sha256','0'*64)),
                 ('case',lambda d:d.__setitem__('capture_count',5)),
                 ('case',lambda d:d.__setitem__('provider_closed',False)),
                 ('case',lambda d:d['accepted'][0]['packed'].__setitem__('actual_input_sha256','0'*64))]
        # Each mutation exercises actual saved evidence; source must remain stable.
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            phase_original=(root/'phase.json').read_bytes();case_original=(root/'case_00/case.json').read_bytes()
            for target,mutate in changes:
                path=root/('phase.json' if target=='phase' else 'case_00/case.json')
                original=phase_original if target=='phase' else case_original
                data=json.loads(original);mutate(data);self.rewrite(path,data)
                with self.subTest(target=target,mutate=mutate):
                    with self.assertRaises(ValueError):m.validate_dataset(root)
                path.write_bytes(original)
            (root/'extra').write_bytes(b'x')
            with self.assertRaises(ValueError):m.validate_dataset(root)

    def test_disk_and_memory_caps_are_distinct_and_frozen_reservation_fits(self):
        self.assertEqual(m.RETENTION_CAP,32*1024*1024);self.assertEqual(m.PAYLOAD_CAP,40*1024*1024)
        estimate=6*(2*(964*604*4+65536+512*256*4+65536)+m.capture.PACKED_BYTES)
        self.assertEqual(estimate,38171904)
        budget=m.oldmodel._StorageBudget(m.PAYLOAD_CAP);budget.reserve(estimate)
        self.assertLess(m.capture.capture_payload_estimate(6),m.RETENTION_CAP)
        with self.assertRaises(ValueError):budget.reserve(m.PAYLOAD_CAP)


class BoundaryTests(unittest.TestCase):
    def test_real_pipe_invalid_permits_are_consumed_once_with_bounded_eof(self):
        import fcntl
        for payload in (b'{}',b'{"parent_pid":1,"parent_pid":2}',b'[]'):
            readfd,writefd=os.pipe();fd=fcntl.fcntl(readfd,fcntl.F_DUPFD_CLOEXEC,10);os.close(readfd)
            os.write(writefd,payload);os.close(writefd)
            with patch.dict(os.environ,{'FIRST_DIVERGENCE_TRIAL_FD':str(fd)}):
                with self.assertRaises(ValueError):m._consume('canary',0,'a'*64,Path('/tmp/x'))
                self.assertNotIn('FIRST_DIVERGENCE_TRIAL_FD',os.environ)
            with self.assertRaises(OSError):os.fstat(fd)

    def test_context_rejects_api_completed_branch_attempt_head_and_source_before_native(self):
        run=dict(id=1,workflow_id=2,event='push',head_branch=m.BRANCH,path=m.WORKFLOW,
                 repository=dict(full_name=m.REPOSITORY),run_attempt=1,head_sha='a'*40,status='in_progress')
        env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=m.REPOSITORY,GITHUB_SHA='a'*40,
                 GITHUB_RUN_ID='1',GITHUB_RUN_ATTEMPT='1',GITHUB_EVENT_NAME='push',GITHUB_REF_NAME=m.BRANCH)
        request=(m.REPO/m.REQUEST).read_bytes()
        snapshot=m.source_snapshot()
        def git(*args,**kwargs):
            if args==('rev-parse','HEAD'):return b'a'*40
            if args[0]=='show':return (m.REPO/args[1].split(':',1)[1]).read_bytes()
            return b''
        class API:
            def json(self,path):return run if '/runs/' in path else dict(id=2,path=m.WORKFLOW,state='active')
        with patch.dict(os.environ,env),patch.object(m,'_git',side_effect=git):
            self.assertEqual(m._context(API(),m.perf_counter()+200)[0]['run_id'],1)
            for key,bad in (('status','completed'),('head_branch','main'),('run_attempt',2),('head_sha','b'*40)):
                old=run[key];run[key]=bad
                with self.assertRaises(ValueError):m._context(API(),m.perf_counter()+200)
                run[key]=old
            with patch.object(m,'_git',return_value=b'drift'):
                with self.assertRaises(ValueError):m._context(API(),m.perf_counter()+200)

    def test_case_launch_failure_keeps_prefix_and_unknown_provider_bounds(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'RUNNER_TEMP':temp}):
            out=Path(temp)/'phase/case_00';out.parent.mkdir()
            def launch(*args,**kwargs):
                target=args[2];target.mkdir();(target/'process.log').write_bytes(b'early prefix')
                raise BrokenPipeError('permit')
            with patch.object(m.oldmodel,'_launch_trial',side_effect=launch):
                row=m._case(out,'canary',0,'a'*32,{},m.perf_counter()+500)
            self.assertIn('BrokenPipeError',row['error']);self.assertEqual((row['provider_lower_bound'],row['provider_upper_bound']),(0,1))
            self.assertIsNone(row['provider_attempted']);self.assertEqual((out/'process.log').read_bytes(),b'early prefix')
            self.assertEqual(row['log']['nbytes'],12)

    def test_case_factory_failure_is_a_returned_failure_ledger(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'RUNNER_TEMP':temp}):
            out=Path(temp)/'phase/case_00';out.parent.mkdir()
            with patch.object(Path,'mkdir',side_effect=OSError('cache mkdir')):
                row=m._case(out,'canary',0,'a'*32,{},m.perf_counter()+500)
            self.assertIn('cache mkdir',row['error']);self.assertFalse(row['launched'])
            self.assertEqual((row['provider_lower_bound'],row['provider_upper_bound']),(0,1))

    def test_case_wait_deducts_launch_and_cleans_group_on_timeout(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'RUNNER_TEMP':temp}):
            out=Path(temp)/'phase/case_00';out.parent.mkdir();seen=[]
            process=types.SimpleNamespace(pid=321,returncode=-9,poll=lambda:-9)
            child=types.SimpleNamespace(process=process,output_cleanup_errors=[],
                wait=lambda timeout:seen.append(timeout) or (_ for _ in ()).throw(subprocess.TimeoutExpired('fake',timeout)),
                drain_available=lambda:None,close_output=lambda:None)
            def launch(*args,**kwargs):
                seen.append(kwargs['timeout']);return child
            with patch.object(m.oldmodel,'_launch_trial',side_effect=launch),patch.object(m.oldmodel,'_terminate_group',return_value=[]) as cleanup:
                row=m._case(out,'canary',0,'a'*32,{},m.perf_counter()+500)
            self.assertLessEqual(seen[1],seen[0]);cleanup.assert_called_once_with(process)
            self.assertIn('TimeoutExpired',row['error'])

    def test_original_zip_rejects_duplicates_symlinks_traversal_and_member_budget(self):
        import zipfile
        import io
        archives=[]
        for name,mode in (('../evil',0),('link',0o120777)):
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w') as z:
                entry=zipfile.ZipInfo(name);entry.external_attr=mode<<16;z.writestr(entry,b'x')
            archives.append(data.getvalue())
        with tempfile.TemporaryDirectory() as temp:
            for index,archive in enumerate(archives):
                with self.assertRaises(ValueError):m._extract(archive,Path(temp)/str(index))

    def test_marker_sensor_setup_failure_restores_first_camera(self):
        events=[];camera=Camera(events);p=provider([camera,Camera(events)])
        del p.env.engine.sensors['bigbench_wide']
        with self.assertRaises(KeyError):
            with m.marker_scope(p,False,[]):pass
        self.assertNotIn('get_rgb_array_cpu',camera.__dict__)

    def test_fresh_cache_route_must_be_empty_bounded_and_no_disable_setting(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'entry').write_bytes(b'x')
            with patch.object(m,'CACHE_CAP',0):
                with self.assertRaises(ValueError):m._cache_inventory(root)
            value=dict(files=1,bytes=1,entries=[dict(path='../evil',nbytes=1)],byte_limit=m.CACHE_CAP,file_limit=m.CACHE_FILES,
                       scope='bounded post-process metadata inventory; no per-read hit proof')
            with self.assertRaises(ValueError):m._cache_record(value,empty=False)


class LifecycleTests(unittest.TestCase):
    def test_child_closes_once_and_preserves_primary_and_close_failures(self):
        from bigbench import native_model_campaign as campaign
        from bigbench import metadrive_camera as native
        permit=dict(parent_pid=100,parent_uuid='1'*32)
        binding=dict(context={},source_snapshot={},runtime={},request_sha256='a'*64)
        fake=provider([Camera([]),Camera([])]);closed=[]
        def close():closed.append(1);raise RuntimeError('close-secondary')
        fake.close=close
        class FailCamera:
            def __init__(self,*args,**kwargs):pass
            def capture(self,pose):raise RuntimeError('capture-primary')
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'_consume',return_value=(permit,binding)),patch.object(native,'NativeMetaDriveProvider',return_value=fake),patch.object(campaign,'NativeWorldCamera',FailCamera):
            data=m.run_child(Path(temp),'canary',0,'a'*64)
        self.assertEqual(closed,[1]);self.assertIn('capture-primary',data['error'])
        self.assertIn('close-secondary',data['cleanup_errors'][0]);self.assertFalse(data['provider_closed'])
        self.assertEqual(data['status'],'FAILED_OR_INCOMPLETE')

    def test_constructor_failure_reports_unknown_allocation_bounds_and_no_close(self):
        from bigbench import metadrive_camera as native
        permit=dict(parent_pid=100,parent_uuid='1'*32);binding=dict(context={},source_snapshot={},runtime={},request_sha256='a'*64)
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'_consume',return_value=(permit,binding)),patch.object(native,'NativeMetaDriveProvider',side_effect=RuntimeError('constructor')):
            data=m.run_child(Path(temp),'canary',0,'a'*64)
        self.assertTrue(data['provider_attempted']);self.assertFalse(data['provider_constructed']);self.assertFalse(data['provider_closed'])
        self.assertEqual((data['provider_lower_bound'],data['provider_upper_bound']),(0,1))

    def test_phase_stops_after_first_failed_case_and_retains_failure_ledger(self):
        context={};snapshot={};request=dict(schema=m.REQUEST_SCHEMA,mode='canary',acceptance=None)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'output'
            with patch.object(m.oldmodel,'_github'),patch.object(m,'_context',return_value=(context,snapshot,request,'a'*64)),patch.object(m,'_output',return_value=out),patch.object(m,'_runtime',return_value={}),patch.object(m,'_unique_run'),patch.object(m.oldmodel,'_enable_subreaper'),patch.object(m,'_case',return_value=dict(error='stop',provider_lower_bound=0,provider_upper_bound=1)) as launch:
                data=m.run_phase(out)
            self.assertEqual(launch.call_count,1);self.assertEqual(data['status'],'FAILED_OR_INCOMPLETE')
            self.assertTrue((out/'phase.json').is_file());self.assertIsNone(data['providers'])

    def test_invalid_candidate_is_published_as_failure(self):
        context={};snapshot={};request=dict(schema=m.REQUEST_SCHEMA,mode='canary',acceptance=None)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'output'
            def case(*args):
                target=args[0];target.mkdir();m._write(target/'case.json',dict(accepted=[],markers=[],enabled=True))
                return dict(error=None)
            with patch.object(m.oldmodel,'_github'),patch.object(m,'_context',return_value=(context,snapshot,request,'a'*64)),patch.object(m,'_output',return_value=out),patch.object(m,'_runtime',return_value={}),patch.object(m,'_unique_run'),patch.object(m.oldmodel,'_enable_subreaper'),patch.object(m,'_case',side_effect=case):
                data=m.run_phase(out)
            self.assertEqual(data['status'],'FAILED_OR_INCOMPLETE')
            self.assertEqual(m._read(out/'phase.json')['status'],'FAILED_OR_INCOMPLETE')


class GateTests(unittest.TestCase):
    def fixture(self,temp):
        import io,zipfile
        acceptedroot=Path(temp)/'accepted';acceptedroot.mkdir()
        canary,_=DatasetTests().fixture(acceptedroot)
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for path in acceptedroot.rglob('*'):
                if path.is_file():z.write(path,path.relative_to(acceptedroot).as_posix())
        raw=archive.getvalue();accepted=canary['context'];current={**accepted,'head_sha':'b'*40,'run_id':10}
        a=dict(source_sha=accepted['head_sha'],run_id=accepted['run_id'],run_attempt=1,workflow_id=accepted['workflow_id'],
               artifact_id=20,artifact_name='stage7-texture-marker-canary',artifact_size_bytes=len(raw),artifact_sha256=m._sha(raw),
               root_raw_accepted=True,fresh_raw_review_accepted=True)
        request=dict(schema=m.REQUEST_SCHEMA,mode='abba',acceptance=a)
        run=dict(id=accepted['run_id'],workflow_id=accepted['workflow_id'],event='push',head_branch=m.BRANCH,path=m.WORKFLOW,
                 repository=dict(full_name=m.REPOSITORY,id=123),run_attempt=1,head_sha=accepted['head_sha'],status='completed',conclusion='success')
        currentrun={**run,'id':10,'head_sha':'b'*40,'status':'in_progress','conclusion':None}
        artifact=dict(id=20,name=a['artifact_name'],expired=False,size_in_bytes=len(raw),digest='sha256:'+m._sha(raw),
                      workflow_run=dict(id=run['id'],head_sha=run['head_sha'],head_branch=m.BRANCH,repository_id=123))
        commit=dict(sha='b'*40,parents=[dict(sha='a'*40)],files=[dict(filename=m.REQUEST,status='modified')])
        class API:
            def json(self,path):
                if '/runs?' in path:return dict(total_count=1,workflow_runs=[currentrun])
                if '/actions/runs/' in path:return run
                if '/commits/' in path:return commit
                if '/artifacts/' in path:return artifact
                raise AssertionError(path)
            def download(self,path,limit):return raw
        def git(*args,**kwargs):
            if args[0]=='rev-list':return b'b'*40+b' '+b'a'*40
            if args[0]=='diff-tree':return m.REQUEST.encode()
            if args[0]=='show':
                name=args[1].split(':',1)[1]
                if name==m.REQUEST:return json.dumps(dict(schema=m.REQUEST_SCHEMA,mode='canary',acceptance=None)).encode()
                return (m.REPO/name).read_bytes()
            raise AssertionError(args)
        return API(),git,current,canary['source_snapshot'],canary['runtime'],request,run,artifact,commit

    def test_actual_original_zip_gate_and_api_artifact_direct_parent_rejections(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'RUNNER_TEMP':temp}):
            api,git,current,snapshot,runtime,request,run,artifact,commit=self.fixture(temp)
            with patch.object(m,'_git',side_effect=git):
                receipt=m._gate(api,current,snapshot,runtime,request,m.perf_counter()+300)
                self.assertEqual(receipt['schema'],'texture-marker-acceptance-v1')
                cases=[(run,'conclusion','failure'),(artifact,'digest','sha256:'+'0'*64),
                       (artifact,'name','other'),(artifact,'expired',True),(artifact,'size_in_bytes',1),
                       (artifact['workflow_run'],'id',99),(artifact['workflow_run'],'head_branch','main'),
                       (commit,'parents',[dict(sha='0'*40)]),(commit,'files',[dict(filename=m.SCRIPT_PATH,status='modified')])]
                for target,key,value in cases:
                    old=target[key];target[key]=value
                    with self.subTest(key=key):
                        with self.assertRaises(ValueError):m._gate(api,current,snapshot,runtime,request,m.perf_counter()+300)
                    target[key]=old
                original=api.download
                api.download=lambda path,limit:b'notzip'
                with self.assertRaises(ValueError):m._gate(api,current,snapshot,runtime,request,m.perf_counter()+300)
                api.download=original
                bad=dict(runtime);bad['ImageVersion']='different'
                with self.assertRaises(ValueError):m._gate(api,current,snapshot,bad,request,m.perf_counter()+300)

    def test_duplicate_head_runs_are_rejected_before_acceptance(self):
        class API:
            def json(self,path):return dict(total_count=2,workflow_runs=[])
        with self.assertRaises(ValueError):m._unique_run(API(),dict(workflow_id=1,head_sha='a'*40))

    def test_api_transport_reserves_time_for_its_fixed_timeout(self):
        api=types.SimpleNamespace(json=lambda p:{},download=lambda p,limit:b'')
        bounded=m._DeadlineAPI(api,m.perf_counter()+.01)
        with self.assertRaises(ValueError):bounded.json('/anything')
        with self.assertRaises(ValueError):bounded.download('/anything',100)

    def test_request_whitespace_cannot_exhaust_failure_ledger(self):
        data=b' '*65536+(m.REPO/m.REQUEST).read_bytes()
        with self.assertRaises(ValueError):m._request_bytes(data)


class TransportTests(unittest.TestCase):
    def test_actual_frozen_launcher_pipe_uses_fixed_child_command_and_preserves_popen_contract(self):
        """The replacement process is stdlib only; xvfb/Panda are never started."""
        real_popen=subprocess.Popen;seen=[]
        receiver="import json,os,pathlib; fd=int(os.environ['FIRST_DIVERGENCE_TRIAL_FD']); data=b''\nwhile True:\n b=os.read(fd,65536)\n if not b: break\n data+=b\nos.close(fd); pathlib.Path(os.environ['TEST_RECEIPT_PATH']).write_bytes(data); pathlib.Path(os.environ['MESA_SHADER_CACHE_DIR'],'cache').write_bytes(b'x'); print('stdlib fixture only')"
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'RUNNER_TEMP':temp,'FIRST_DIVERGENCE_ACCEPTANCE':'must-clear',
            'MESA_SHADER_CACHE_DISABLE':'true','TEST_RECEIPT_PATH':str(Path(temp)/'permit.json')}):
            out=Path(temp)/'phase/case_00';out.parent.mkdir()
            def popen(command,**kwargs):
                seen.append((command,dict(kwargs)))
                return real_popen([m.sys.executable,'-c',receiver],**kwargs)
            with patch.object(subprocess,'Popen',side_effect=popen),patch.object(m.oldmodel,'_runtime_identity',return_value={'fixture':'only'}):
                row=m._case(out,'canary',0,'a'*32,{},m.perf_counter()+500)
            self.assertEqual(len(seen),1);command,kwargs=seen[0]
            self.assertEqual(command[:5],['xvfb-run',m.sys.executable,'-m','scripts.texture_generation_markers','child'])
            self.assertNotIn('-a',command);self.assertNotIn('FIRST_DIVERGENCE_ACCEPTANCE',kwargs['env'])
            self.assertNotIn('MESA_SHADER_CACHE_DISABLE',kwargs['env']);self.assertTrue(kwargs['start_new_session'])
            self.assertEqual(kwargs['cwd'],m.REPO);self.assertEqual(kwargs['stdout'],subprocess.PIPE)
            self.assertEqual(kwargs['stderr'],subprocess.STDOUT);self.assertGreaterEqual(kwargs['pass_fds'][0],10)
            permit=json.loads((Path(temp)/'permit.json').read_text())
            self.assertEqual(len(permit['source_snapshot']),62);self.assertEqual(permit['arm'],'retention')
            self.assertEqual(permit['schedule_index'],0);self.assertEqual(permit['storage_limits'],m.LIMITS)
            self.assertTrue(row['group_gone']);self.assertTrue(row['reaped'])
            self.assertIsNotNone(row['error']) # fixture deliberately supplies no scientific case ledger


class SemanticsTests(unittest.TestCase):
    def test_off_markers_are_unobserved_and_on_absolute_values_separate_from_patterns(self):
        accepted=[dict(raw={k:dict(rgb_sha256='same') for k in m.CAMERAS},canvas={k:dict(rgb_sha256='same') for k in m.CAMERAS},packed=dict(sha256='same'))]*6
        off=dict(enabled=False,accepted=accepted,markers=[dict(before=None,after=None,equal=None)]*12)
        on0=dict(enabled=True,accepted=accepted,markers=[dict(before=0,after=0,equal=True)]*12)
        on1=dict(enabled=True,accepted=accepted,markers=[dict(before=-1,after=-1,equal=True)]*12)
        comparisons=m._comparisons([off,on0,on1,off])
        for row in comparisons:
            if row['kind']=='ON/ON':
                self.assertTrue(row['marker_patterns_equal']);self.assertFalse(row['marker_values_equal'])
            else:
                self.assertIsNone(row['marker_patterns_equal']);self.assertIsNone(row['marker_values_equal'])

    def test_subreaper_failure_after_output_creation_is_recorded(self):
        request=dict(schema=m.REQUEST_SCHEMA,mode='canary',acceptance=None)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'output'
            with patch.object(m.oldmodel,'_github'),patch.object(m,'_context',return_value=({}, {},request,'a'*64)),patch.object(m,'_output',return_value=out),patch.object(m,'_runtime',return_value={}),patch.object(m,'_unique_run'),patch.object(m.oldmodel,'_enable_subreaper',side_effect=ValueError('subreaper unavailable')):
                data=m.run_phase(out)
            self.assertEqual(data['status'],'FAILED_OR_INCOMPLETE');self.assertIn('subreaper',data['error'])
            self.assertTrue((out/'phase.json').is_file())


class AuthorizationTests(unittest.TestCase):
    def test_live_root_pipe_binding_and_nonce_schedule_source_runtime_output_rejections(self):
        import fcntl
        oldsource={'old62-fixture':'a'*64};runtime={'runtime-fixture':'only'}
        context={'fixture':'context'};ownsource={'own65-fixture':'b'*64}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'texture-marker-canary';root.mkdir();cache=Path(temp)/'cache';cache.mkdir()
            binding=dict(phase='canary',parent_pid=os.getppid(),parent_uuid='c'*32,root=str(root),context=context,
                         source_snapshot=ownsource,runtime=runtime,request_sha256='d'*64)
            base=dict(parent_pid=os.getppid(),parent_uuid='c'*32,process_group=os.getpgid(0),nonce='e'*64,
                      arm='retention',repeat=0,schedule_index=0,source_snapshot=oldsource,runtime=runtime,storage_limits=m.LIMITS)
            def consume(value,out=None):
                readfd,writefd=os.pipe();fd=fcntl.fcntl(readfd,fcntl.F_DUPFD_CLOEXEC,10);os.close(readfd)
                os.write(writefd,json.dumps(value).encode());os.close(writefd)
                env=dict(RUNNER_TEMP=temp,GITHUB_ACTIONS='true',MESA_SHADER_CACHE_DIR=str(cache),
                         TEXTURE_MARKER_BINDING=json.dumps(binding),FIRST_DIVERGENCE_TRIAL_FD=str(fd))
                with patch.dict(os.environ,env),patch.object(m.capture,'source_snapshot',return_value=oldsource),patch.object(m.oldmodel,'_runtime_identity',return_value=runtime),patch.object(m.oldmodel,'_github'),patch.object(m,'_context',return_value=(context,ownsource,dict(mode='canary'),'d'*64)),patch.object(m,'_runtime',return_value=runtime):
                    os.environ.pop('FIRST_DIVERGENCE_ACCEPTANCE',None)
                    return m._consume('canary',0,'e'*64,out or root/'case_00')
            permit,_=consume(base);self.assertEqual(permit['parent_pid'],os.getppid())
            for key,value in [('nonce','0'*64),('schedule_index',1),('source_snapshot',{}),('runtime',{}),('process_group',-1),('parent_pid',os.getpid()),('arm','original')]:
                bad=copy.deepcopy(base);bad[key]=value
                with self.subTest(key=key):
                    with self.assertRaises((ValueError,ProcessLookupError)):consume(bad)
            with self.assertRaises(ValueError):consume(base,root/'wrong')
            (cache/'already-used').write_bytes(b'x')
            with self.assertRaises(ValueError):consume(base)

    def test_native_boundary_rejects_imported_ort_even_with_allowed_distribution_metadata(self):
        valid=dict(python='3.11.9',executable='/usr/bin/python',numpy='2.4.6',
                   **{'opencv-python-headless':'5.0.0.93','panda3d':'1.10.13','metadrive-simulator':'0.4.3'},onnxruntime=None)
        with patch.object(m.capture,'runtime_versions',return_value=valid),patch.dict(os.environ,{'ImageOS':'ubuntu24','ImageVersion':'2026'}),patch.dict(m.sys.modules,{'onnxruntime':types.ModuleType('onnxruntime')}):
            with self.assertRaisesRegex(ValueError,'imported ORT'):m._runtime()

    def test_empty_cache_files_do_not_attest_populated_driver_route(self):
        record=dict(files=1,bytes=0,entries=[dict(path='empty',nbytes=0)],byte_limit=m.CACHE_CAP,file_limit=m.CACHE_FILES,
                    scope='bounded post-process metadata inventory; no per-read hit proof')
        with self.assertRaises(ValueError):m._cache_record(record,empty=False)

    def test_extra_empty_artifact_directory_is_unregistered(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);DatasetTests().fixture(root);(root/'unregistered-directory').mkdir()
            with self.assertRaises(ValueError):m.validate_dataset(root)


class FailureCountTests(unittest.TestCase):
    def test_incomplete_phase_does_not_assert_actual_zero_activity(self):
        request=dict(schema=m.REQUEST_SCHEMA,mode='canary',acceptance=None)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'output'
            with patch.object(m.oldmodel,'_github'),patch.object(m,'_context',return_value=({}, {},request,'a'*64)),patch.object(m,'_output',return_value=out),patch.object(m,'_runtime',return_value={}),patch.object(m,'_unique_run'),patch.object(m.oldmodel,'_enable_subreaper'),patch.object(m,'_case',return_value=dict(error='child missing')):
                data=m.run_phase(out)
            for key in ('providers','accepted_pairs','observed_reads','marker_reads'):self.assertIsNone(data[key])

    def test_failed_child_retains_rows_and_leaves_actual_observed_counts_unknown(self):
        from bigbench import native_model_campaign as campaign
        from bigbench import metadrive_camera as native
        camera=Camera([],(-1,));fake=provider([camera,Camera([])]);fake.close=lambda:None
        permit=dict(parent_pid=100,parent_uuid='1'*32);binding=dict(context={},source_snapshot={},runtime={},request_sha256='a'*64)
        class FailCamera:
            def __init__(self,*args,**kwargs):pass
            def capture(self,pose):camera.get_rgb_array_cpu()
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'_consume',return_value=(permit,binding)),patch.object(native,'NativeMetaDriveProvider',return_value=fake),patch.object(campaign,'NativeWorldCamera',FailCamera):
            data=m.run_child(Path(temp),'canary',0,'a'*64)
        self.assertTrue(data['provider_closed']);self.assertEqual(len(data['markers']),1)
        self.assertIsNone(data['observed_reads']);self.assertIsNone(data['marker_reads'])
        self.assertTrue(data['markers'][0]['copy_attempted']);self.assertTrue(data['markers'][0]['copy_returned'])


class ClosureUnconfirmedTests(unittest.TestCase):
    """Real frozen camera/collector CPU copies survive a fake provider close error."""
    def run_accepted_then_close_error(self,out,accepted_pairs=6,disk=None):
        from bigbench import metadrive_camera as native
        from bigbench.optical_calibration import reference_source
        events=[];cams=[]
        for index,kind in enumerate(m.CAMERAS):
            cam=Camera(events,[-1]*12);cam.array.fill(23+index*61)
            intrinsic=reference_source(kind,964,604)
            lens=types.SimpleNamespace(getFilmSize=lambda k=intrinsic:(964/k.fx,604/k.fy),
                                       getFilmOffset=lambda:(0.,0.),getFocalLength=lambda:1.)
            cam.get_lens=lambda lens=lens:lens
            cam.perceive_calls=0
            def perceive(*args,_cam=cam,**kwargs):
                _cam.perceive_calls+=1
                if _cam.perceive_calls>accepted_pairs:raise RuntimeError('capture-after-prefix')
                return _cam.get_rgb_array_cpu()
            cam.perceive=perceive;cams.append(cam)
        fake=provider(cams);fake.env.engine.origin=object()
        fake.source_width=964;fake.source_height=604;fake.height_m=1.2
        close_calls=[]
        def close():close_calls.append(1);raise RuntimeError('close-unconfirmed')
        fake.close=close
        collector=m.capture.CaptureCollector('retention',payload_cap_bytes=m.RETENTION_CAP,max_captures=6)
        permit=dict(parent_pid=100,parent_uuid='1'*32)
        binding=dict(context={},source_snapshot={},runtime={},request_sha256='a'*64)
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(m,'_consume',return_value=(permit,binding)))
            stack.enter_context(patch.object(native,'NativeMetaDriveProvider',return_value=fake))
            stack.enter_context(patch.object(m.capture,'CaptureCollector',return_value=collector))
            if disk is not None:stack.enter_context(patch.object(m.oldmodel,'_StorageBudget',return_value=disk))
            data=m.run_child(out,'canary',0,'a'*64)
        self.assertEqual(close_calls,[1]);self.assertFalse(collector._closed)
        # The frozen serializer must still require actual confirmed closure.
        with self.assertRaisesRegex(ValueError,'provider closure'):collector.serialize_captures(out/'forbidden')
        return data,collector,events

    def test_all_six_accepted_pairs_survive_close_failure_as_unconfirmed_raw_canvas(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,collector,events=self.run_accepted_then_close_error(root)
            self.assertEqual(data['status'],'FAILED_OR_INCOMPLETE');self.assertFalse(data['provider_closed'])
            self.assertIn('close-unconfirmed',data['error']);self.assertEqual(len(collector.records),6)
            self.assertEqual(data['accepted'],[])
            evidence=data.get('closure_unconfirmed_snapshots')
            self.assertIsNotNone(evidence,'accepted CPU payloads must be persisted despite unconfirmed closure')
            self.assertEqual(evidence['schema'],'texture-marker-closure-unconfirmed-v1')
            self.assertEqual(evidence['status'],'CLOSURE_UNCONFIRMED_CPU_SNAPSHOTS')
            self.assertFalse(evidence['provider_closed']);self.assertTrue(evidence['complete'])
            self.assertEqual(len(evidence['rows']),6);self.assertIsNone(evidence['error'])
            self.assertEqual(events.count('copy'),12);self.assertEqual(events.count('marker'),24)
            self.assertLessEqual(data['payload_charged_bytes'],m.PAYLOAD_CAP)
            self.assertLessEqual(sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),m.PAYLOAD_CAP+m.JSON_CAP)
            for index,(row,record) in enumerate(zip(evidence['rows'],collector.records),1):
                self.assertEqual(row['accepted_index'],index);self.assertEqual(row['capture_index'],record.capture_index)
                self.assertEqual(row['raw_sha256'],record.raw_sha256)
                self.assertNotIn('packed',row)
                for kind in m.CAMERAS:
                    for boundary,width,height,expected in (
                        ('raw',964,604,record.raw_rgb[kind].tobytes()),
                        ('canvas',512,256,getattr(record.pair,kind).rgb)):
                        desc=row[boundary][kind];path=root/desc['path']
                        self.assertIn('closure_unconfirmed/',desc['path'])
                        self.assertEqual(m.capture._read_png(path,width,height).rgb,expected)
                        self.assertEqual(m._sha(path.read_bytes()),desc['sha256'])
            self.assertFalse(list(root.rglob('packed_i420.bin')))
            self.assertEqual(m._read(root/'case.json')['closure_unconfirmed_snapshots'],evidence)

    def test_partial_snapshot_budget_error_retains_prefix_and_primary_close_errors(self):
        budget=m.oldmodel._StorageBudget(964*604*4+65536)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,collector,events=self.run_accepted_then_close_error(root,accepted_pairs=1,disk=budget)
            self.assertEqual(data['status'],'FAILED_OR_INCOMPLETE');self.assertFalse(data['provider_closed'])
            self.assertIn('capture-after-prefix',data['error'])
            self.assertIn('close-unconfirmed',data['cleanup_errors'][0])
            evidence=data.get('closure_unconfirmed_snapshots')
            self.assertIsNotNone(evidence,'bounded failed persistence must retain its prefix ledger')
            self.assertFalse(evidence['complete']);self.assertIn('budget',evidence['error'])
            self.assertIn('budget',data['cleanup_errors'][1]);self.assertEqual(len(evidence['rows']),1)
            desc=evidence['rows'][0]['raw']['road'];self.assertTrue((root/desc['path']).is_file())
            self.assertEqual(evidence['rows'][0]['canvas'],{})
            self.assertEqual(len(list(root.rglob('*.png'))),1)
            self.assertEqual(data['payload_charged_bytes'],budget.charged)
            self.assertLessEqual(budget.charged,budget.limit)
            self.assertLessEqual(collector.payload_bytes,m.RETENTION_CAP)
