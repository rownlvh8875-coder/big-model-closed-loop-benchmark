"""Host receipt admission using real synthetic files, never native targets."""
import copy,json,tempfile,unittest
from pathlib import Path
from scripts import run_sdk3_rgb_forensics as h
from tests import test_continue_panda_sdk3_models as fixtures


class RGBHostAdmission(unittest.TestCase):
    def fixture(self,root):
        folder=fixtures.CompleteMissingModelCondition().make_case(root,20261110,'s_curve_left_right')
        pair=folder/'pair';p=pair/'execution.json';value=json.loads(p.read_text());value['stopped_state']['ExitCode']=0;value['ownership_unresolved']=False;p.write_text(json.dumps(value))
        (pair/'command.json').write_text(json.dumps(dict(argv=['--model-pair'])))
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
            folder=self.fixture(d);pair=folder/'pair';path=pair/'command.json';path.write_text(json.dumps(dict(argv=['--model-pair','--full-rgb'])))
            with self.assertRaises(ValueError):h.validate_observed_pair(folder,'control')
            path.write_text(json.dumps(dict(argv=['--model-pair'])));path=pair/'pair-ledger.json';value=json.loads(path.read_text());value[1]['pid']=None;path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):h.validate_observed_pair(folder,'control')

    def test_source_delta_allows_only_declared_optional_dispatch_extensions(self):
        h.validate_source_delta(['M\tscripts/native_mdv3_repeat_trial.py','M\tscripts/panda_sdk3_diagnostic.py','A\tscripts/sdk3_rgb_forensics.py'])
        for rows in [[],['M\tbigbench/native_model_campaign.py'],['M\tscripts/compare_fresh_native_mdv3.py'],['D\tdocs/old.json']]:
            with self.assertRaises(ValueError):h.validate_source_delta(rows)

if __name__=='__main__':unittest.main()
