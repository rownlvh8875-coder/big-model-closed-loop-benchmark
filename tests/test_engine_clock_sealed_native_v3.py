"""Real recorded cv2 mutation at a fresh process boundary; no engine/Docker."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
try:from scripts import engine_clock_sealed_native_v3 as n
except ImportError:n=None
ROOT=Path(__file__).resolve().parents[1]

class NativeEnvironmentTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(n,'fresh process environment boundary missing')
    def actual(self):
        d=json.loads((ROOT/'docs/evidence/STAGE7_ENGINE_CLOCK_SEALED_NATIVE_02_RESULT.json').read_bytes())
        return d['records']['output/parent-admission.json']['environment']
    def test_initial_ld_rejects_but_exact_recorded_post_import_matches(self):
        actual=self.actual()
        with self.assertRaises(ValueError):n.check_environment(actual,'parent')
        self.assertEqual(n.environment_profile(),n.check_post_import_environment(actual,'parent'))
        for key,value in [('LD_LIBRARY_PATH','/host'),('GALLIUM_DRIVER','llvmpipe')]:
            bad=dict(actual);bad[key]=value
            with self.assertRaises(ValueError):n.check_post_import_environment(bad,'parent')
        with self.assertRaises(ValueError):n.check_post_import_environment(n.environment_profile(),'parent')
    def test_child_uses_validated_launch_snapshot_without_mutating_parent(self):
        from scripts import engine_clock_sealed_native_container_v3 as c
        actual=self.actual();proof=dict(launch_environment=n.environment_profile(),environment=actual)
        saved=copy.deepcopy(proof);child=c.build_child_environment(proof,10)
        self.assertNotIn('LD_LIBRARY_PATH',child)
        self.assertEqual('10',child['FIRST_DIVERGENCE_TRIAL_FD'])
        self.assertEqual('/work/cache/case_00',child['MESA_SHADER_CACHE_DIR'])
        self.assertEqual(saved,proof)
        proof['launch_environment']['LD_LIBRARY_PATH']=actual['LD_LIBRARY_PATH']
        with self.assertRaises(ValueError):c.build_child_environment(proof,10)
    def test_environment_identity_commits_to_both_profiles_and_snapshot_policy(self):
        receipt=json.loads((ROOT/(n.AUTH+'preparation.json')).read_bytes());actual=json.loads((ROOT/(n.AUTH+'root-acceptance.json')).read_bytes())
        identity=n.make_identity(receipt,n.image_evidence(ROOT)['expected'],actual['host'],actual['engine'])
        descriptor=dict(launch=n.environment_profile(),post_cv2=dict(n.environment_profile(),LD_LIBRARY_PATH='/opt/venv/lib/python3.11/site-packages/cv2/../../lib64:'),child_launch_policy='validated-preimport-snapshot-v1')
        digest=hashlib.sha256(json.dumps(descriptor,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()
        self.assertEqual(digest,identity['core']['configuration']['environment_profile_sha256'])
    def test_child_post_import_retains_and_validates_all_process_routes(self):
        env=dict(self.actual(),FIRST_DIVERGENCE_TRIAL_FD='10',MESA_SHADER_CACHE_DIR='/work/cache/case_00',DISPLAY=':99',XAUTHORITY='/tmp/xvfb-run.aA01bB/Xauthority',PWD='/work/repo')
        self.assertEqual(n.environment_profile(),n.check_post_import_environment(env,'child'))
        env['MESA_SHADER_CACHE_DIR']='/host'
        with self.assertRaises(ValueError):n.check_post_import_environment(env,'child')

if __name__=='__main__':unittest.main()
