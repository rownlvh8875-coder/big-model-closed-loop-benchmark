"""Host receipt admission using real synthetic files, never native targets."""
import copy,json,tempfile,unittest
from pathlib import Path
from scripts import run_sdk3_rgb_forensics as h
from scripts import panda_sdk3_runtime as runtime
from tests import test_continue_panda_sdk3_models as fixtures


class RGBHostAdmission(unittest.TestCase):
    def fixture(self,root):
        folder=fixtures.CompleteMissingModelCondition().make_case(root,20261110,'s_curve_left_right')
        pair=folder/'pair';p=pair/'execution.json';value=json.loads(p.read_text());value['stopped_state']['ExitCode']=0;value['ownership_unresolved']=False;p.write_text(json.dumps(value))
        container_path=pair/'container.json';container=json.loads(container_path.read_text());container.update(name='test-owned',ownership_label='ab'*16);container_path.write_text(json.dumps(container))
        (pair/'command.json').write_text(json.dumps(dict(argv=runtime.container_command('test-owned',Path(root),Path(root)/'sdk',pair,['--model-pair','--seed','20261110','--scenario','s_curve_left_right'],model=Path(root)/'model.onnx',deps=Path(root)/'deps',owner='ab'*16),ownership_label='ab'*16)))
        ledger=[dict(index=i,launcher_spawn_attempted=True,launcher_pid=10+i,spawn_attempted=True,pid=pid,returncode=0) for i,pid in enumerate((11,24))]
        (pair/'pair-ledger.json').write_text(json.dumps(ledger));return folder

    def test_matching_control_still_keeps_original_three_of_four_failure(self):
        with tempfile.TemporaryDirectory() as d:
            result=h.validate_observed_pair(self.fixture(d),'control')
            self.assertTrue(result['strict_pair_pass']);self.assertFalse(result['repair_proven']);self.assertFalse(result['original_matrix_gate_passed'])

    def test_nonzero_unknown_exit_oom_cleanup_or_wrong_profile_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder=self.fixture(d);pair=folder/'pair'
            cases=[('execution.json',('returncode',),1),('execution.json',('owned_container_removed',),False),('execution.json',('ownership_unresolved',),True),('execution.json',('stopped_state','OOMKilled'),True),('execution.json',('stopped_state','Running'),True),('execution.json',('stopped_state','ExitCode'),9),('container.json',('image',),'wrong-image'),('container.json',('effective_limits','Memory'),4294967296),('run-1/native-child.json',('returncode',),None),('run-1/native-child.json',('returncode',),1),('run-1/native-child.json',('server_returncode',),1),('run-1/native-child.json',('pid',),11),('run-1/run.json',('selected_sdk_sha256',),'00'*32),('run-1/run.json',('model_sha256',),'00'*32),('run-1/run.json',('seed',),20261109)]
            for name,keys,bad in cases:
                path=pair/name;original=path.read_bytes();value=json.loads(original);target=value
                for k in keys[:-1]:target=target[k]
                target[keys[-1]]=bad;path.write_text(json.dumps(value))
                with self.subTest(name=name,keys=keys,bad=bad),self.assertRaises(ValueError):h.validate_observed_pair(folder,'control')
                path.write_bytes(original)

    def test_probe_flag_and_actual_spawn_ledger_must_match_arm(self):
        with tempfile.TemporaryDirectory() as d:
            folder=self.fixture(d);pair=folder/'pair';path=pair/'command.json';command=path.read_bytes();value=json.loads(command);value['argv'].append('--full-rgb');path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):h.validate_observed_pair(folder,'control')
            path.write_bytes(command);path=pair/'pair-ledger.json';value=json.loads(path.read_text());value[1]['pid']=None;path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):h.validate_observed_pair(folder,'control')

    def test_source_delta_allows_only_declared_optional_dispatch_extensions(self):
        h.validate_source_delta(['M\tscripts/panda_sdk3_diagnostic.py','A\tscripts/sdk3_rgb_forensics.py'])
        for rows in [[],['M\tscripts/native_mdv3_repeat_trial.py'],['M\tbigbench/native_model_campaign.py'],['M\tscripts/compare_fresh_native_mdv3.py'],['D\tdocs/old.json']]:
            with self.assertRaises(ValueError):h.validate_source_delta(rows)

    def test_missing_null_empty_or_malformed_container_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder=self.fixture(d);paths=[folder/'pair/execution.json',folder/'pair/container.json'];original=[p.read_bytes() for p in paths]
            for value in (None,'','not-an-id','missing'):
                for path,raw,key in zip(paths,original,('container_id','id')):
                    row=json.loads(raw)
                    if value=='missing':row.pop(key)
                    else:row[key]=value
                    path.write_text(json.dumps(row))
                with self.subTest(value=value),self.assertRaises(ValueError):h.validate_observed_pair(folder,'control')
            for path,raw in zip(paths,original):path.write_bytes(raw)

    def test_wrong_or_missing_capture_mode_cannot_be_certified_by_matching_trials(self):
        with tempfile.TemporaryDirectory() as d:
            folder=self.fixture(d);paths=[folder/f'pair/run-{i}/run.json' for i in (0,1)];original=[p.read_bytes() for p in paths]
            for mode in (None,'replayed_frames'):
                for path,raw in zip(paths,original):
                    row=json.loads(raw)
                    if mode is None:row.pop('camera_capture_mode')
                    else:row['camera_capture_mode']=mode
                    path.write_text(json.dumps(row))
                with self.subTest(mode=mode),self.assertRaises(ValueError):h.validate_observed_pair(folder,'control')

    def test_wrong_user_driver_duplicate_env_or_extra_capability_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder=self.fixture(d);path=folder/'pair/command.json';original=path.read_bytes()
            for change in ('root_user','wrong_driver','duplicate_env','privileged'):
                row=json.loads(original);argv=row['argv']
                if change=='root_user':argv[argv.index('--user')+1]='0:0'
                if change=='wrong_driver':argv[argv.index('GALLIUM_DRIVER=softpipe')]='GALLIUM_DRIVER=llvmpipe'
                if change=='duplicate_env':argv[2:2]=['--env','GALLIUM_DRIVER=llvmpipe']
                if change=='privileged':argv.insert(2,'--privileged')
                path.write_text(json.dumps(row))
                with self.subTest(change=change),self.assertRaises(ValueError):h.validate_observed_pair(folder,'control')

if __name__=='__main__':unittest.main()
