"""Synthetic file evidence for an outcome-independent continuation, no native execution."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from tests.test_aggregate_original_mdv3_current_recheck import mock_trial
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
from scripts import continue_panda_sdk3_models as c
from scripts import panda_sdk3_runtime as p


class CompleteMissingModelCondition(unittest.TestCase):
    def make_case(self,root,seed,scene,bad=False):
        folder=Path(root)/'models'/f'seed-{seed}'/scene;pair=folder/'pair';pair.mkdir(parents=True)
        rows=[mock_trial(seed,scene,pid) for pid in (11,24)]
        for row in rows:row.update(selected_sdk_sha256=p.SDK_SHA,sdk_load_order='core-first',trial_evidence='UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC')
        if bad:rows[1]['frames'][6]['source_road_rgb_sha256']='different-original-road-at-step7'
        cid=hashlib.sha256(f'{seed}-{scene}'.encode()).hexdigest()
        execution=dict(returncode=0,failure=None,owned_container_removed=True,container_id=cid,stopped_state=dict(Running=False,Pid=0,OOMKilled=False))
        profile=dict(Memory=10737418240,MemorySwap=10737418240,NanoCpus=2000000000,PidsLimit=128,ReadonlyRootfs=True,NetworkMode='none',IpcMode='private')
        (pair/'execution.json').write_text(json.dumps(execution));(pair/'container.json').write_text(json.dumps(dict(id=cid,image=p.IMAGE,effective_limits=profile)))
        for index,row in enumerate(rows):
            d=pair/f'run-{index}';d.mkdir();raw=json.dumps(row,indent=1).encode();(d/'run.json').write_bytes(raw);(folder/f'run_{index}.json').write_bytes(raw)
            (d/'native-child.json').write_text(json.dumps(dict(spawn_attempted=True,pid=row['process_id'],returncode=0,server_returncode=0)))
        (folder/'strict_native_repeat_verdict.json').write_text(json.dumps(compare_fresh_trials(*rows)))
        return folder

    def prior(self,root):
        root=Path(root)
        for seed,scene in [(20261109,'s_curve_left_right'),(20261109,'s_curve_right_left'),(20261110,'s_curve_left_right')]:self.make_case(root,seed,scene,bad=seed==20261110)
        (root/'summary.json').write_text(json.dumps(dict(source_sha='f3bb85b6e692ecfd1efb54e2af3aabb93beb3c3e',sdk_sha256=p.SDK_SHA,image=p.IMAGE,official_model_processes=6)))
        incomplete=root/'models/seed-20261110/s_curve_right_left/pair/run-0';incomplete.mkdir(parents=True);(incomplete/'run.json').write_text('{}')
        return root

    def test_copies_all_completed_raw_bytes_including_the_failed_pair(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);prior=self.prior(d/'prior');target=d/'selected'
            result=c.copy_completed_cases(prior,target)
            self.assertEqual(len(result),3);self.assertEqual([r['verdict']['exact_repeated_execution_gate_passed'] for r in result],[True,True,False])
            for row in result:
                relative=Path(f"seed-{row['seed']}")/row['scenario']
                for i in (0,1):self.assertEqual((prior/'models'/relative/f'run_{i}.json').read_bytes(),(target/relative/f'run_{i}.json').read_bytes())
            self.assertFalse((target/'seed-20261110/s_curve_right_left').exists())

    def test_prior_unknown_native_exit_cannot_be_admitted_by_a_success_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            folder=self.make_case(d,20261109,'s_curve_left_right');path=folder/'pair/run-1/native-child.json';v=json.loads(path.read_text());v['returncode']=None;path.write_text(json.dumps(v))
            with self.assertRaises(ValueError):c.validate_case(folder,20261109,'s_curve_left_right')

    def test_wrong_model_resource_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder=self.make_case(d,20261109,'s_curve_left_right');path=folder/'pair/container.json';v=json.loads(path.read_text());v['effective_limits']['Memory']=4294967296;path.write_text(json.dumps(v))
            with self.assertRaises(ValueError):c.validate_case(folder,20261109,'s_curve_left_right')

    def test_final_matrix_preserves_failure_after_last_case_passes(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);prior=self.prior(d/'prior');target=d/'selected';c.copy_completed_cases(prior,target)
            self.make_case(d,20261110,'s_curve_right_left')
            import shutil
            shutil.copytree(d/'models/seed-20261110/s_curve_right_left',target/'seed-20261110/s_curve_right_left')
            result=c.finalize_matrix(target)
            self.assertEqual(result['strict_gate_pass_count'],3);self.assertFalse(result['all_four_cases_strict_native_gate_passed'])

    def test_changed_existing_native_or_other_base_file_is_rejected(self):
        c.validate_source_delta(['A\tscripts/continue_panda_sdk3_models.py'])
        for rows in [[],['M\tbigbench/onnx_policy.py'],['D\tscripts/panda_sdk3_diagnostic.py'],['M\tdocs/old.json']]:
            with self.assertRaises(ValueError):c.validate_source_delta(rows)


if __name__=='__main__':unittest.main()
