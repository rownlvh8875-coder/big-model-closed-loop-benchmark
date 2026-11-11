"""Synthetic cache/native receipts only; never native evidence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_native_shadow_sampler import fixture as sampler_fixture
from scripts.native_shader_cache_matrix import (
    ARMS, execution_order, inventory, validate_inventory, run_case, compare_case, aggregate_scenes,
)

SEED=20261109
SCENE='s_curve_left_right'


def native_fixture(seed,scene,label):
    d=sampler_fixture(seed,scene,'original_off',int(label[-1]))
    del d['shadow_sampler_diagnostic']
    d['process_uuid']=f'{seed}-{scene}-{label}'
    d['process_id']=40000+list(ARMS).index(label.rsplit('-',1)[0])*10+int(label[-1])
    return d


def fake_native(command, *, env, stdout, stderr):
    seed=int(command[command.index('--seed')+1]);scene=command[command.index('--scene')+1]
    out=Path(command[command.index('--out')+1]);label=out.stem
    assert command[command.index('--arm')+1]=='sequential_road_first'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(native_fixture(seed,scene,label)))
    cache=Path(env['MESA_SHADER_CACHE_DIR'])
    if env.get('MESA_SHADER_CACHE_DISABLE')!='true':
        (cache/'shader.bin').write_bytes(b'synthetic shader cache')
    return SimpleNamespace(returncode=0)


def build(root):
    with patch('scripts.native_shader_cache_matrix.subprocess.run',side_effect=fake_native):
        for seed in (20261109,20261110):
            for scene in ('s_curve_left_right','s_curve_right_left'):run_case(root,seed,scene)


class ShaderCacheMatrixTests(unittest.TestCase):
    def test_nested_inventory_uses_canonical_relative_path_order(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'a').mkdir();(p/'a/b').write_bytes(b'one');(p/'a-0').write_bytes(b'two')
            result=inventory(p)
            self.assertEqual([f['path'] for f in result['files']],['a-0','a/b'])
            validate_inventory(result)

    def test_order_balances_shared_outer_inner_and_disabled_first_last(self):
        orders=[execution_order(s,c) for s in (20261109,20261110)
                for c in ('s_curve_left_right','s_curve_right_left')]
        self.assertEqual(len(set(orders)),4)
        for order in orders:
            self.assertEqual(set(order),{f'{a}-{i}' for a in ARMS for i in (0,1)})
            self.assertLess(order.index('shared-0'),order.index('shared-1'))
        self.assertEqual(sum(o[0].startswith('disabled') for o in orders),2)
        non_disabled=[[x for x in o if not x.startswith('disabled')] for o in orders]
        self.assertEqual(sum(o[0]=='shared-0' and o[-1]=='shared-1' for o in non_disabled),2)

    def test_inventory_detects_same_size_content_changes_and_symlinks(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'shader').write_bytes(b'abc');before=inventory(p)
            (p/'shader').write_bytes(b'xyz');self.assertNotEqual(before,inventory(p))
            (p/'link').symlink_to(p/'shader')
            with self.assertRaises(ValueError):inventory(p)
            (p/'link').unlink()
            root_link=p.parent/(p.name+'-link');root_link.symlink_to(p,target_is_directory=True)
            try:
                with self.assertRaises(ValueError):inventory(root_link)
            finally:root_link.unlink()

    def test_disabled_flag_must_prevent_cache_writes_and_enabled_cache_must_populate(self):
        for mode in ('ignored_disable','no_enabled_cache'):
            with self.subTest(mode=mode), TemporaryDirectory() as tmp:
                def unverified(command,**kwargs):
                    if mode=='no_enabled_cache':kwargs['env']=dict(kwargs['env'],MESA_SHADER_CACHE_DISABLE='true')
                    result=fake_native(command,**kwargs)
                    if mode=='ignored_disable' and kwargs['env'].get('MESA_SHADER_CACHE_DISABLE')=='true':
                        (Path(kwargs['env']['MESA_SHADER_CACHE_DIR'])/'unexpected').write_bytes(b'cache')
                    return result
                with patch('scripts.native_shader_cache_matrix.subprocess.run',side_effect=unverified):
                    with self.assertRaisesRegex(ValueError,'intervention'):run_case(Path(tmp),SEED,SCENE)

    def test_six_fresh_native_processes_per_case_and_24_per_cohort(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root);r=aggregate_scenes(root)
            self.assertEqual(r['independent_process_count'],24)
            self.assertFalse(r['original_mdv3_repeatability_proven'])
            self.assertFalse(r['unique_renderer_cause_proven'])
            self.assertEqual(len(r['per_scene']),4)

    def test_existing_case_is_rejected_before_launch(self):
        with TemporaryDirectory() as tmp, patch('scripts.native_shader_cache_matrix.subprocess.run') as native:
            root=Path(tmp);(root/f'seed-{SEED}'/SCENE).mkdir(parents=True)
            with self.assertRaises(FileExistsError):run_case(root,SEED,SCENE)
            native.assert_not_called()

    def test_native_failure_preserves_partial_evidence_and_does_not_write_case_success(self):
        with TemporaryDirectory() as tmp, patch('scripts.native_shader_cache_matrix.subprocess.run',return_value=SimpleNamespace(returncode=7)):
            root=Path(tmp)
            with self.assertRaises(RuntimeError):run_case(root,SEED,SCENE)
            folder=root/f'seed-{SEED}'/SCENE
            self.assertTrue((folder/'execution.json').exists())
            self.assertFalse((folder/'case_comparison.json').exists())

    def test_modified_native_snapshot_cache_provenance_and_clock_are_rejected(self):
        for change in ('native_sha','snapshot','shared_before','disabled_after','env','clock'):
            with self.subTest(change=change), TemporaryDirectory() as tmp:
                root=Path(tmp)
                with patch('scripts.native_shader_cache_matrix.subprocess.run',side_effect=fake_native):run_case(root,SEED,SCENE)
                folder=root/f'seed-{SEED}'/SCENE
                record=folder/'shared-1.json';d=json.loads(record.read_text())
                if change=='native_sha':d['native_sha256']='e'*64
                elif change=='snapshot':(folder/'snapshots/shared-1/shader.bin').write_bytes(b'changed')
                elif change=='shared_before':d['cache_before']['file_count']=0
                elif change=='disabled_after':
                    record=folder/'disabled-0.json';d=json.loads(record.read_text());d['cache_after']['file_count']=1
                elif change=='env':d['cache_disable']='true'
                else:
                    p=folder/'native/shared-1.json';n=json.loads(p.read_text());n['clock_timeline'][0]['before']['dt_s']=float('nan');p.write_text(json.dumps(n))
                    import hashlib
                    d['native_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
                record.write_text(json.dumps(d))
                with self.assertRaises(ValueError):compare_case(root,SEED,SCENE)

    def test_process_reuse_and_modified_case_summary_fail(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root)
            folder=root/f'seed-{SEED}'/SCENE;p=folder/'case_comparison.json'
            d=json.loads(p.read_text());d['independent_process_count']=5;p.write_text(json.dumps(d))
            with self.assertRaises(ValueError):aggregate_scenes(root)
            n=folder/'native/isolated-0.json';d=json.loads(n.read_text());d['process_id']=40000;n.write_text(json.dumps(d))
            import hashlib
            p=folder/'isolated-0.json';d=json.loads(p.read_text());d['native_sha256']=hashlib.sha256(n.read_bytes()).hexdigest();p.write_text(json.dumps(d))
            with self.assertRaises(ValueError):compare_case(root,SEED,SCENE)

    def test_real_image_difference_is_reported_instead_of_relaxed(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            def different(command,**kwargs):
                result=fake_native(command,**kwargs)
                p=Path(command[command.index('--out')+1])
                if p.stem=='shared-1':
                    d=json.loads(p.read_text());d['onnx_i420']['all_frame_sha256'][1]='e'*64;p.write_text(json.dumps(d))
                return result
            with patch('scripts.native_shader_cache_matrix.subprocess.run',side_effect=different):r=run_case(root,SEED,SCENE)
            self.assertEqual(r['arms']['shared']['i420']['matched_full_timeline'],9)
            self.assertEqual(r['arms']['shared']['i420']['first_different_step_1_based'],2)
            self.assertEqual(r['cross_cache_image_comparisons']['shared_later_vs_isolated_cold']['i420']['matched_full_timeline'],9)

    def test_cohort_rejects_reused_uuid_even_with_regenerated_case_summary(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root)
            folder=root/'seed-20261110'/SCENE;n=folder/'native/shared-0.json'
            d=json.loads(n.read_text());d['process_uuid']=f'{SEED}-{SCENE}-shared-0';n.write_text(json.dumps(d))
            import hashlib
            p=folder/'shared-0.json';d=json.loads(p.read_text());d['native_sha256']=hashlib.sha256(n.read_bytes()).hexdigest();p.write_text(json.dumps(d))
            (folder/'case_comparison.json').write_text(json.dumps(compare_case(root,20261110,SCENE)))
            with self.assertRaisesRegex(ValueError,'UUID'):aggregate_scenes(root)


if __name__=='__main__':unittest.main()
