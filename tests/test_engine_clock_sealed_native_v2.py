"""Safe pre-native diagnostic fixtures only; no real engine or Docker."""
import copy
import json
from pathlib import Path
import unittest
try:
    from scripts import engine_clock_sealed_native_v2 as n
except ImportError:n=None

ROOT=Path(__file__).resolve().parents[1]

class LaunchDiagnosticTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(n,'safe actual launch diagnostics missing')
    def fixture(self):
        from test_engine_clock_sealed_native import SealedNativeTests
        raw=SealedNativeTests('runTest').launch()
        raw['Config']['Labels']['stage7.request']=n.ID;raw['Config']['Cmd']=n.CONTAINER_COMMAND
        routes=dict(repo='/host/repo',binding='/host/binding',output='/host/output',cache='/host/cache')
        expected=dict(config_digest='sha256:'+'c'*64,source_sha='1'*40,nonce='a'*32)
        return raw,routes,expected
    def test_accepted_shape_has_no_failed_predicates(self):
        raw,routes,expected=self.fixture();d=n.launch_diagnostics(raw,routes,expected)
        self.assertEqual([],d['failed']);self.assertTrue(n.validate_launch(raw,routes,expected)['validated'])
    def test_exact_safe_failure_codes_and_no_unvalidated_values(self):
        raw,routes,expected=self.fixture()
        raw['HostConfig']['ReadonlyRootfs']=False
        raw['Mounts'][0].update(Source='https://secret:proxy-password@host/token',Propagation='')
        raw['Config']['Env']+=['GH_TOKEN=super-secret-token','HTTP_PROXY=https://secret:proxy-password@host/token']
        raw['Config']['Cmd']=['arbitrary-secret-argv']
        raw['Config']['Labels']['unknown-secret-label']='arbitrary-secret-label-value'
        d=n.launch_diagnostics(raw,routes,expected);encoded=json.dumps(d)
        for value in ('proxy-password','super-secret-token','arbitrary-secret-argv','arbitrary-secret-label-value','unknown-secret-label'):
            self.assertNotIn(value,encoded)
        for code in ('host.ReadonlyRootfs','environment','config.Cmd','labels','mounts'):
            self.assertIn(code,d['failed'])
        self.assertLess(len(encoded),65536)
        with self.assertRaises(ValueError):n.validate_launch(raw,routes,expected)
    def test_mount_propagation_is_observed_without_acceptance_relaxation(self):
        raw,routes,expected=self.fixture();raw['Mounts'][0]['Propagation']=''
        d=n.launch_diagnostics(raw,routes,expected)
        self.assertEqual('',d['mounts']['/work/repo']['propagation'])
        self.assertIn('mounts',d['failed'])
        with self.assertRaises(ValueError):n.validate_launch(raw,routes,expected)
    def test_new_request_identity_and_actual_closure(self):
        from test_engine_clock_sealed_native import SealedNativeTests
        old=SealedNativeTests('runTest').request()
        with self.assertRaises(ValueError):n.validate_request(old,ROOT)
        paths=n.source_paths(ROOT)
        self.assertTrue({'scripts/engine_clock_sealed_native.py','scripts/engine_clock_sealed_native_v2.py',
            'scripts/engine_clock_sealed_native_run_v2.py','scripts/engine_clock_sealed_native_container_v2.py',
            'docs/evidence/STAGE7_ENGINE_CLOCK_SEALED_NATIVE_01_RESULT.json',n.WORKFLOW}<=paths)

    def test_genuine_docker28_tmpfs_hostconfig_only_is_complete(self):
        actual=json.loads((ROOT/(n.AUTH+'preflight.json')).read_bytes())['collector']['launch']
        self.assertEqual([],actual['mounts'])
        self.assertEqual({'/tmp':'rw,nosuid,nodev,noexec,size=67108864,mode=0700'},actual['tmpfs'])
        raw,routes,expected=self.fixture()
        raw['Mounts']=raw['Mounts'][:-1]+actual['mounts']
        raw['HostConfig']['Tmpfs']=actual['tmpfs']
        self.assertTrue(n.validate_launch(raw,routes,expected)['validated'])
        self.assertEqual([],n.launch_diagnostics(raw,routes,expected)['failed'])
        bad=copy.deepcopy(raw);bad['HostConfig']['Tmpfs']={}
        with self.assertRaises(ValueError):n.validate_launch(bad,routes,expected)
        bad=copy.deepcopy(raw);bad['Mounts'].append(dict(Type='tmpfs',Source='',Destination='/unregistered',RW=True))
        with self.assertRaises(ValueError):n.validate_launch(bad,routes,expected)

if __name__=='__main__':unittest.main()
