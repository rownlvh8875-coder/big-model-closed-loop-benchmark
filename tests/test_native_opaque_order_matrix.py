"""Synthetic receipt and CPU bin contracts, never native-rendering evidence."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import uuid

from test_native_shadow_feedback_matrix import fixture as feedback_fixture

CONDITIONS=('original_state_sorted','original_unsorted','both_state_sorted','both_unsorted')
SEEDS=(20261109,20261110)
SCENES=('s_curve_left_right','s_curve_right_left')


def module(test):
    test.assertIsNotNone(importlib.util.find_spec('scripts.native_opaque_order_matrix'),
                         'opaque order matrix is not implemented')
    return importlib.import_module('scripts.native_opaque_order_matrix')


def snapshot(typ=2):
    return dict(index=2,name='opaque',type=typ,sort=20,active=True)


class BinManager:
    def __init__(self,typ=2,index=2):
        self.typ=typ;self.index=index;self.sort=20;self.active=True;self.changes=[]
    def findBin(self,name):return self.index
    def getBinName(self,index):return 'opaque'
    def getBinType(self,index):return self.typ
    def getBinSort(self,index):return self.sort
    def getBinActive(self,index):return self.active
    def setBinType(self,index,typ):
        if index!=self.index:raise AssertionError('wrong opaque bin')
        self.changes.append((index,typ));self.typ=typ


def fixture(seed,scene,condition,repeat):
    feedback='both' if condition.startswith('both_') else 'baseline'
    d=feedback_fixture(seed,scene,feedback,False,repeat)
    name=f'{seed}-{scene}-{condition}-{repeat}'
    nonce=uuid.uuid5(uuid.NAMESPACE_URL,name).hex
    typ=1 if condition.endswith('_unsorted') else 2
    d.update(process_uuid=uuid.uuid5(uuid.NAMESPACE_DNS,name).hex,
        process_id=50000+CONDITIONS.index(condition)*10+repeat,
        renderer_equivalence_proven=False,original_mdv3_repeatability_proven=False,
        unique_renderer_cause_proven=False)
    d['shadow_feedback_trial']['request_uuid']=nonce
    d['opaque_order_trial']=dict(condition=condition,repeat=repeat,request_uuid=nonce)
    d['opaque_bin_diagnostic']=dict(before=snapshot(),configured=snapshot(typ),
        after_capture=snapshot(typ),restored=snapshot(),requested_type=typ,
        setup_cpu_checks=True,before_provider=True,type_only_policy=True,
        type_change_may_apply_next_frame=True,extra_render_ticks=0,
        observer_enabled=False,gpu_queries_used=False,actual_draw_trace=False,
        setup_overhead_free=False)
    return d


def build(root,m):
    for seed in SEEDS:
        for scene in SCENES:
            folder=root/f'seed-{seed}'/scene;folder.mkdir(parents=True)
            offset=SEEDS.index(seed)*2+SCENES.index(scene)
            order=CONDITIONS[offset:]+CONDITIONS[:offset];entries=[]
            for condition in order:
                for repeat in (0,1):
                    d=fixture(seed,scene,condition,repeat)
                    filename=f'{condition}-run_{repeat}.json'
                    (folder/filename).write_text(json.dumps(d))
                    entries.append(dict(sequence_index=len(entries),condition=condition,repeat=repeat,
                        filename=filename,request_uuid=d['opaque_order_trial']['request_uuid'],
                        process_uuid=d['process_uuid'],process_id=d['process_id'],
                        started_ns=100+10*len(entries),finished_ns=105+10*len(entries),
                        native_exit_status=0,accepted_exit_status=0))
            (folder/'execution_ledger.json').write_text(json.dumps(dict(seed=seed,scenario=scene,
                condition_order=list(order),entries=entries)))
            (folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,seed,scene)))


class OpaqueBinPolicyTests(unittest.TestCase):
    def test_only_unsorted_changes_type_and_both_policies_restore_on_capture_error(self):
        m=module(self)
        for typ in (2,1):
            for fail in (False,True):
                manager=BinManager()
                try:
                    with m.opaque_bin_policy(typ,manager=manager) as receipt:
                        self.assertEqual(manager.typ,typ)
                        self.assertEqual((manager.index,manager.sort,manager.active),(2,20,True))
                        if fail:raise RuntimeError('capture failed')
                except RuntimeError:
                    if not fail:raise
                self.assertEqual(manager.typ,2)
                self.assertEqual(manager.changes,[(2,1),(2,2)] if typ==1 else [])
                self.assertEqual(receipt['restored'],snapshot())

    def test_unknown_bin_or_original_type_rejected_before_mutation(self):
        m=module(self)
        for manager in (BinManager(index=-1),BinManager(typ=1),BinManager(typ=3)):
            with self.assertRaises(RuntimeError):
                with m.opaque_bin_policy(1,manager=manager):self.fail('unexpected setup')
            self.assertEqual(manager.changes,[])

    def test_type_must_survive_capture_and_policy_error_restores_original(self):
        m=module(self);manager=BinManager()
        with self.assertRaisesRegex(RuntimeError,'capture'):
            with m.opaque_bin_policy(1,manager=manager) as receipt:
                manager.typ=2
        self.assertEqual(receipt['after_capture']['type'],2)
        self.assertEqual(receipt['restored'],snapshot())

    @unittest.skipUnless(importlib.util.find_spec('panda3d'),'Panda CPU contract runs in native CI')
    def test_actual_panda_global_bin_is_restored_without_any_graphics_engine(self):
        m=module(self)
        from panda3d.core import CullBinManager
        manager=CullBinManager.getGlobalPtr();index=manager.findBin('opaque')
        self.assertEqual(int(manager.getBinType(index)),2)
        with m.opaque_bin_policy(1,manager=manager) as receipt:
            self.assertEqual(int(manager.getBinType(index)),1)
            self.assertEqual(receipt['before'],snapshot())
        self.assertEqual(int(manager.getBinType(index)),2)


class OpaqueMatrixTests(unittest.TestCase):
    def test_snapshot_numeric_and_boolean_fields_keep_their_wire_types(self):
        m=module(self)
        for stage,key,value in (('configured','type',True),('after_capture','index',2.),
                                ('restored','sort',20.),('configured','active',1)):
            d=fixture(SEEDS[0],SCENES[0],'both_unsorted',0)
            d['opaque_bin_diagnostic'][stage][key]=value
            with self.subTest(stage=stage,key=key):
                with self.assertRaises(ValueError):m.validate_trial(d,SEEDS[0],SCENES[0],'both_unsorted',0)

    def test_import_and_fixture_aggregation_do_not_initialize_panda_or_gl(self):
        m=module(self)
        result=subprocess.run([sys.executable,'-c',
            "import sys; import scripts.native_opaque_order_matrix; assert 'panda3d.core' not in sys.modules; assert 'metadrive' not in sys.modules"],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(m,'get_bin_manager',side_effect=AssertionError('Panda must remain lazy')):
                build(root,m);self.assertEqual(m.aggregate_cases(root)['independent_process_count'],32)

    def test_run_case_ledger_retains_all_success_failure_and_validation_outcomes(self):
        m=module(self)
        for outcome in ('success','failure','invalid'):
            with TemporaryDirectory() as tmp:
                root=Path(tmp)/'matrix';calls=[]
                def native(command,**kwargs):
                    calls.append(command);arg=lambda key:command[command.index(key)+1]
                    d=fixture(int(arg('--seed')),arg('--scene'),arg('--condition'),int(arg('--repeat')))
                    for key in ('opaque_order_trial','shadow_feedback_trial'):d[key]['request_uuid']=arg('--request-uuid')
                    if outcome=='invalid':d['opaque_bin_diagnostic']['after_capture']['sort']=99
                    Path(arg('--out')).write_text(json.dumps(d))
                    return SimpleNamespace(returncode=7 if outcome=='failure' else 5 if len(calls)==1 else 0)
                with patch.object(m.subprocess,'run',side_effect=native):
                    if outcome=='invalid':
                        with self.assertRaises(ValueError):m.run_case(root=root,seed=SEEDS[0],scene=SCENES[0])
                    else:self.assertEqual(m.run_case(root=root,seed=SEEDS[0],scene=SCENES[0]),7 if outcome=='failure' else 0)
                folder=root/f'seed-{SEEDS[0]}'/SCENES[0]
                ledger=json.loads((folder/'execution_ledger.json').read_text())
                self.assertEqual(len(calls),8 if outcome=='success' else 1)
                entry=ledger['entries'][0]
                self.assertEqual(entry['native_exit_status'],7 if outcome=='failure' else 5)
                self.assertEqual(entry['accepted_exit_status'],0 if outcome=='success' else 7 if outcome=='failure' else None)
                self.assertEqual('error' in entry,outcome=='invalid')
                self.assertTrue((folder/entry['filename']).exists())
                self.assertEqual((folder/'case_comparison.json').exists(),outcome=='success')
                with self.assertRaises(ValueError):m.run_case(root=root,seed=SEEDS[0],scene=SCENES[0])

    def test_policy_failure_after_capture_preserves_full_raw_fields_and_restored_state(self):
        m=module(self);manager=BinManager()
        def native(**kwargs):
            manager.typ=2
            d=fixture(SEEDS[0],SCENES[0],'both_unsorted',0)
            d['shadow_feedback_trial']['request_uuid']=kwargs['request_uuid']
            return d
        with patch.object(m,'get_bin_manager',return_value=manager),patch.object(m,'feedback_native_trial',side_effect=native):
            d=m.native_trial(seed=SEEDS[0],scene=SCENES[0],condition='both_unsorted',repeat=0,request_uuid='a'*32)
        self.assertEqual(d['status'],'ERROR')
        self.assertIn('source_rgb',d)
        self.assertEqual(d['native_capture_status_before_policy_error'],'OBSERVED_NATIVE_PIXEL_CLOCK')
        self.assertEqual(d['opaque_bin_diagnostic']['restored'],snapshot())

    def test_latin_orders_and_all_eight_condition_repeat_identities(self):
        m=module(self)
        orders=[m.condition_order(seed,scene) for seed in SEEDS for scene in SCENES]
        self.assertEqual(orders,[list(CONDITIONS),list(CONDITIONS[1:]+CONDITIONS[:1]),
            list(CONDITIONS[2:]+CONDITIONS[:2]),list(CONDITIONS[3:]+CONDITIONS[:3])])
        for condition in CONDITIONS:
            for repeat in (0,1):m.validate_trial(fixture(SEEDS[0],SCENES[0],condition,repeat),SEEDS[0],SCENES[0],condition,repeat)

    def test_wrong_bin_or_native_controls_and_claims_are_rejected(self):
        m=module(self)
        for mutation in ('condition','feedback','requested','before','configured','after','restored',
                         'sort','active','index','cpu','trace','queries','ticks','nonce','clock','tasks',
                         'pose','source','warp','i420','positive','readback','probe','shader','equivalence','gate'):
            d=fixture(SEEDS[0],SCENES[0],'both_unsorted',0);bin=d['opaque_bin_diagnostic']
            if mutation=='condition':d['opaque_order_trial']['condition']='original_unsorted'
            elif mutation=='feedback':d['shadow_feedback_trial']['condition']='baseline'
            elif mutation=='requested':bin['requested_type']=2
            elif mutation in ('before','configured','restored'):bin[mutation]['type']=3
            elif mutation=='after':bin['after_capture']['type']=2
            elif mutation=='sort':bin['after_capture']['sort']=21
            elif mutation=='active':bin['configured']['active']=False
            elif mutation=='index':bin['restored']['index']=4
            elif mutation=='cpu':bin['setup_cpu_checks']=False
            elif mutation=='trace':bin['actual_draw_trace']=True
            elif mutation=='queries':bin['gpu_queries_used']=True
            elif mutation=='ticks':bin['extra_render_ticks']=1
            elif mutation=='nonce':d['shadow_feedback_trial']['request_uuid']='f'*32
            elif mutation=='clock':d['clock_timeline'][1]['before']['frame_time_s']+=1
            elif mutation=='tasks':d['registered_tasks_after'].remove('PSSM.update')
            elif mutation=='pose':d['camera_pose'][0]=[float('nan'),0,0]
            elif mutation=='source':d['raw_sensor_rgb_dims']=[512,256]
            elif mutation=='warp':d['model_rgb']['road']['all_frame_sha256'][0]='bad'
            elif mutation=='i420':d['onnx_i420']['all_frame_sha256'].pop()
            elif mutation=='positive':d['camera_plus_2m_positive']['wide']=False
            elif mutation=='readback':d['cpu_readbacks_bit_exact_without_new_render']=False
            elif mutation=='probe':d['shadow_sampler_diagnostic']['terminal_probe']['records']=[{}]
            elif mutation=='shader':d['shadow_sampler_diagnostic']['configuration']['shader_edited']=True
            elif mutation=='equivalence':d['renderer_equivalence_proven']=True
            else:d['original_mdv3_repeatability_proven']=True
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):m.validate_trial(d,SEEDS[0],SCENES[0],'both_unsorted',0)

    def test_aggregate_recomputes_32_and_actual_mismatches_not_alternate_gate(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m);r=m.aggregate_cases(root)
            self.assertEqual(r['independent_process_count'],32)
            self.assertEqual(len(r['per_scene']),4)
            self.assertFalse(r['renderer_equivalence_proven'])
            folder=root/f'seed-{SEEDS[0]}'/SCENES[0];p=folder/'both_unsorted-run_1.json'
            d=json.loads(p.read_text());d['onnx_i420']['all_frame_sha256'][6]='e'*64;p.write_text(json.dumps(d))
            r=m.compare_case(root,SEEDS[0],SCENES[0]);comparison=r['conditions']['both_unsorted']['repeat_comparison']['i420']
            self.assertEqual(comparison['matched_full_timeline'],9)
            self.assertEqual(comparison['first_different_step_1_based'],7)
            with self.assertRaisesRegex(ValueError,'stale'):m.aggregate_cases(root)

    def test_existing_final_summary_and_cross_case_uuid_must_verify_exactly(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m);result=m.aggregate_cases(root)
            path=root/'aggregate_summary.json';path.write_text(json.dumps(result))
            self.assertEqual(m.aggregate_cases(root),result)
            altered=copy.deepcopy(result);altered['independent_process_count']=31
            path.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError,'stale'):m.aggregate_cases(root)
            path.unlink()
            folder=root/f'seed-{SEEDS[1]}'/SCENES[1];trial=folder/'original_state_sorted-run_0.json'
            d=json.loads(trial.read_text());d['process_uuid']=fixture(SEEDS[0],SCENES[0],'original_state_sorted',0)['process_uuid']
            trial.write_text(json.dumps(d));ledgerpath=folder/'execution_ledger.json';ledger=json.loads(ledgerpath.read_text())
            next(e for e in ledger['entries'] if e['filename']==trial.name)['process_uuid']=d['process_uuid']
            ledgerpath.write_text(json.dumps(ledger));(folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,SEEDS[1],SCENES[1])))
            with self.assertRaisesRegex(ValueError,'UUID reused'):m.aggregate_cases(root)

    def test_process_reuse_incomplete_or_reordered_ledger_rejected(self):
        m=module(self)
        for mutation in ('pid','uuid','missing','order','nonce','status','timestamp'):
            with TemporaryDirectory() as tmp:
                root=Path(tmp);build(root,m);folder=root/f'seed-{SEEDS[0]}'/SCENES[0]
                path=folder/'execution_ledger.json';ledger=json.loads(path.read_text());entries=ledger['entries']
                if mutation in ('pid','uuid'):
                    key='process_id' if mutation=='pid' else 'process_uuid';p=folder/entries[1]['filename']
                    d=json.loads(p.read_text());d[key]=entries[0][key];entries[1][key]=d[key];p.write_text(json.dumps(d))
                elif mutation=='missing':entries.pop()
                elif mutation=='order':entries[0],entries[2]=entries[2],entries[0]
                elif mutation=='nonce':entries[0]['request_uuid']='f'*32
                elif mutation=='status':entries[0]['native_exit_status']=2
                else:entries[1]['started_ns']=1
                path.write_text(json.dumps(ledger))
                with self.subTest(mutation=mutation):
                    with self.assertRaises(ValueError):m.compare_case(root,SEEDS[0],SCENES[0])

    def test_native_calls_existing_feedback_only_after_bin_setup_and_restores(self):
        m=module(self);manager=BinManager()
        def feedback(**kwargs):
            self.assertEqual(manager.typ,1)
            self.assertEqual(kwargs,dict(seed=SEEDS[0],scene=SCENES[0],condition='both',probe=False,repeat=1,request_uuid='a'*32))
            result=fixture(SEEDS[0],SCENES[0],'both_unsorted',1)
            result['shadow_feedback_trial']['request_uuid']=kwargs['request_uuid']
            return result
        with patch.object(m,'get_bin_manager',return_value=manager),patch.object(m,'feedback_native_trial',side_effect=feedback):
            d=m.native_trial(seed=SEEDS[0],scene=SCENES[0],condition='both_unsorted',repeat=1,request_uuid='a'*32)
        self.assertEqual(manager.typ,2)
        m.validate_trial(json.loads(json.dumps(d)),SEEDS[0],SCENES[0],'both_unsorted',1)

    def test_child_serializes_tuple_pose_before_strict_wire_validation_and_keeps_invalid_raw(self):
        m=module(self)
        for invalid in (False,True):
            d=fixture(SEEDS[0],SCENES[0],'original_state_sorted',0)
            d['camera_pose']=tuple(tuple(x) for x in d['camera_pose'])
            if invalid:d['registered_tasks_after'].remove('PSSM.update')
            with TemporaryDirectory() as tmp:
                out=Path(tmp)/'raw.json'
                with patch.object(m,'native_trial',return_value=d):
                    status=m.main(['--mode','native','--seed',str(SEEDS[0]),'--scene',SCENES[0],
                        '--condition','original_state_sorted','--repeat','0','--request-uuid',d['opaque_order_trial']['request_uuid'],'--out',str(out)])
                self.assertEqual(status,2 if invalid else 0)
                saved=json.loads(out.read_text())
                self.assertEqual(saved['source_rgb'],d['source_rgb'])
                self.assertEqual(saved['registered_tasks_after'],d['registered_tasks_after'])


class OpaqueLauncherTests(unittest.TestCase):
    def invoke(self,status,*,write=True,invalid=False,nonce=False,stale=False):
        m=module(self)
        with TemporaryDirectory() as tmp:
            out=Path(tmp)/'trial.json'
            if stale:out.write_text('{}')
            def native(command,**kwargs):
                self.assertEqual(command[:2],['xvfb-run','-a'])
                self.assertIn('scripts.native_opaque_order_matrix',command)
                if write:
                    d=fixture(SEEDS[0],SCENES[0],'both_unsorted',0)
                    request=command[command.index('--request-uuid')+1]
                    for key in ('opaque_order_trial','shadow_feedback_trial'):d[key]['request_uuid']='f'*32 if nonce else request
                    if invalid:d['opaque_bin_diagnostic']['after_capture']['type']=2
                    out.write_text(json.dumps(d))
                return SimpleNamespace(returncode=status)
            with patch.object(m.subprocess,'run',side_effect=native):
                return m.launch_trial(seed=SEEDS[0],scene=SCENES[0],condition='both_unsorted',repeat=0,out=out)

    def test_zero_and_cleanup_five_require_fresh_complete_matching_nonce(self):
        for status in (0,5):
            self.assertEqual(self.invoke(status),0)
            with self.assertRaises(ValueError):self.invoke(status,invalid=True)
            with self.assertRaises(ValueError):self.invoke(status,nonce=True)
            with self.assertRaises(FileNotFoundError):self.invoke(status,write=False)
        with self.assertRaises(ValueError):self.invoke(5,stale=True)

    def test_other_statuses_never_relabel_success(self):
        for status in (1,2,7,-9):self.assertEqual(self.invoke(status),status)
