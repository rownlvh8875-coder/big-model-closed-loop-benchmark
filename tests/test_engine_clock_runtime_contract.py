"""Pure metadata behavior; fixtures are synthetic, never runtime attestation."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from scripts import engine_clock_runtime_contract as contract
except ImportError:
    contract = None

PROPOSAL = Path(__file__).resolve().parents[1] / 'docs/evidence/STAGE7_ENGINE_CLOCK_RUNTIME_CONTRACT_PROPOSAL.json'
FIXTURE_SHA = '154d262b11ce9aa23819fe6bfec8e75c20aed94c4a77869f32e34a566108f3ff'
FIXTURE_CORE = {
    'image': {
        'distribution': 'actions-docker-save-v1', 'artifact_id': 123,
        'artifact_zip_sha256': 'a' * 64, 'image_tar_sha256': 'b' * 64,
        'config_digest': 'sha256:' + 'c' * 64,
        'rootfs_diff_ids': ['sha256:' + 'd' * 64, 'sha256:' + 'e' * 64],
        'platform': 'linux/amd64', 'installed_files_sha256': 'f' * 64,
        'build_recipe_sha256': '1' * 64, 'lock_sha256': '2' * 64,
        'assets_zip_sha256': '4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9',
    },
    'versions': {
        'python': '3.11.18', 'executable': '/opt/venv/bin/python',
        'numpy': '2.4.6', 'opencv_python_headless': '5.0.0.93', 'cv2': '5.0.0',
        'panda3d': '1.10.13', 'metadrive_simulator': '0.4.3',
    },
    'host': {
        'sysname': 'Linux', 'release': 'fixture-kernel', 'version': 'fixture-build',
        'machine': 'x86_64', 'byteorder': 'little', 'cpu_vendor': 'fixture-vendor',
        'cpu_model': 'fixture-model', 'cpu_flags': ['avx', 'sse2'],
        'logical_cpus': 4, 'affinity_cpus': 2,
    },
    'engine': {
        'docker_client': 'fixture-client', 'docker_server': 'fixture-server',
        'docker_api': 'fixture-api', 'oci_runtime': 'fixture-runc', 'storage_driver': 'fixture-overlay',
    },
    'configuration': {
        'read_only_rootfs': True, 'source_mount_read_only': True,
        'host_native_library_mounts': False, 'host_display_mounts': False,
        'device_passthrough': False, 'imports_isolated': True,
        'render_env': {'LIBGL_ALWAYS_SOFTWARE': '1', 'PYOPENGL_PLATFORM': 'glx', 'OMP_NUM_THREADS': '2'},
        'cache_policy': 'fresh-per-case-external-bounded', 'environment_profile_sha256': '3' * 64,
    },
}


def identity(core=None):
    core = copy.deepcopy(FIXTURE_CORE if core is None else core)
    raw = json.dumps(core, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    return {'schema': 'engine-clock-installed-identity-v1', 'core': core,
            'core_sha256': hashlib.sha256(raw).hexdigest()}


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(contract, 'pure metadata contract implementation is missing')

    def cli(self, command, *contents):
        with tempfile.TemporaryDirectory() as tmp:
            files = []
            for i, raw in enumerate(contents):
                p = Path(tmp) / str(i)
                p.write_bytes(raw if isinstance(raw, bytes) else raw.encode())
                files.append(str(p))
            args = ['validate-proposal', '--proposal', files[0]] if command == 'proposal' else [
                'compare-identity', '--left', files[0], '--right', files[1]]
            result = subprocess.run([sys.executable, '-m', 'scripts.engine_clock_runtime_contract', *args],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.stderr, '')
            self.assertLessEqual(len(result.stdout.encode()), 131072)
            return result.returncode, json.loads(result.stdout)

    def test_inactive_proposal_never_authorizes_execution(self):
        value = json.loads(PROPOSAL.read_text())
        result = contract.validate_proposal(value)
        self.assertEqual(result['status'], 'INACTIVE_PROPOSAL_VALIDATED')
        self.assertIs(result['execution_authorized'], False)
        self.assertEqual(value, json.loads(PROPOSAL.read_text()))
        code, data = self.cli('proposal', PROPOSAL.read_bytes())
        self.assertEqual(code, 0)
        self.assertIs(data['execution_authorized'], False)

    def test_active_ready_nonnull_or_extra_proposal_rejects(self):
        original = json.loads(PROPOSAL.read_text())
        changes = [lambda d: d.update(execution_authorized=True),
                   lambda d: d.update(image_preparation_ready=True),
                   lambda d: d.update(native_admission_ready=True),
                   lambda d: d.update(status='ACTIVE'),
                   lambda d: d.update(unregistered=True),
                   lambda d: d['native_allowance'].update(providers=1),
                   lambda d: d['native_allowance'].update(providers=False),
                   lambda d: d['required_preparation'].update(config_digest='sha256:' + 'c' * 64),
                   lambda d: d['required_preparation'].clear()]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                data = copy.deepcopy(original); change(data)
                with self.assertRaises(ValueError): contract.validate_proposal(data)

    def test_canonical_fixture_hash_and_no_input_mutation(self):
        data = identity()
        self.assertEqual(data['core_sha256'], FIXTURE_SHA)
        before = copy.deepcopy(data)
        self.assertEqual(contract.validate_identity(data), before)
        self.assertEqual(data, before)
        reversed_keys = dict(reversed(list(data.items())))
        self.assertEqual(contract.validate_identity(reversed_keys), before)

    def test_matching_synthetic_identity_is_metadata_only(self):
        result = contract.compare_identity(identity(), identity())
        self.assertEqual(result, {'status': 'INSTALLED_PROFILE_MATCH', 'differences': [],
                                  'truncated': False, 'native_admission': False})
        code, result = self.cli('compare', json.dumps(identity()), json.dumps(identity()))
        self.assertEqual(code, 0)
        self.assertIs(result['native_admission'], False)

    def test_same_shaped_digest_substitution_is_not_authenticated(self):
        other = identity(); other['core']['image']['config_digest'] = 'sha256:' + '9' * 64
        other = identity(other['core'])
        self.assertEqual(contract.validate_identity(other), other)
        result = contract.compare_identity(identity(), other)
        self.assertEqual(result['status'], 'INSTALLED_PROFILE_MISMATCH')
        self.assertEqual(result['differences'], ['core.image.config_digest'])
        self.assertIs(result['native_admission'], False)
        self.assertIs(contract.compare_identity(other, other)['native_admission'], False)

    def test_host_kernel_cpu_engine_and_installed_fields_are_binding(self):
        for group, key, replacement in [
                ('host', 'release', 'different-kernel'), ('host', 'version', 'different-build'),
                ('host', 'cpu_vendor', 'other-vendor'), ('host', 'cpu_model', 'other-model'),
                ('host', 'logical_cpus', 8), ('host', 'affinity_cpus', 3),
                ('host', 'cpu_flags', ['avx', 'sse3']),
                ('engine', 'docker_server', 'other-server'), ('engine', 'oci_runtime', 'other-runc'),
                ('image', 'artifact_id', 124), ('image', 'image_tar_sha256', '9' * 64),
                ('image', 'installed_files_sha256', '8' * 64),
                ('configuration', 'environment_profile_sha256', '7' * 64)]:
            with self.subTest(group=group, key=key):
                core = copy.deepcopy(FIXTURE_CORE); core[group][key] = replacement
                result = contract.compare_identity(identity(), identity(core))
                self.assertEqual(result['status'], 'INSTALLED_PROFILE_MISMATCH')
                self.assertTrue(result['differences'])
                self.assertIs(result['native_admission'], False)

    def test_every_core_leaf_is_bound_or_rejected(self):
        def paths(value, prefix=()):
            if isinstance(value, dict):
                for key, val in value.items():yield from paths(val, prefix + (key,))
            elif isinstance(value, list):
                for key, val in enumerate(value):yield from paths(val, prefix + (key,))
            else:yield prefix, value
        for path, old in paths(FIXTURE_CORE):
            core = copy.deepcopy(FIXTURE_CORE); node = core
            for key in path[:-1]:node = node[key]
            if type(old) is bool:new = not old
            elif type(old) is int:new = old + 1
            else:new = old + 'changed'
            node[path[-1]] = new
            with self.subTest(path=path):
                try:result = contract.compare_identity(identity(), identity(core))
                except ValueError:continue
                self.assertEqual(result['status'], 'INSTALLED_PROFILE_MISMATCH')
                self.assertTrue(result['differences'])

    def test_diff_id_order_is_not_sorted_away(self):
        core = copy.deepcopy(FIXTURE_CORE); core['image']['rootfs_diff_ids'].reverse()
        result = contract.compare_identity(identity(), identity(core))
        self.assertEqual(result['differences'], ['core.image.rootfs_diff_ids[0]', 'core.image.rootfs_diff_ids[1]'])

    def test_unsorted_duplicate_empty_cpu_flags_reject(self):
        for flags in [['sse2', 'avx'], ['avx', 'avx'], [], [''], [True]]:
            core = copy.deepcopy(FIXTURE_CORE); core['host']['cpu_flags'] = flags
            with self.subTest(flags=flags), self.assertRaises(ValueError):contract.validate_identity(identity(core))

    def test_missing_extra_legacy_and_provenance_fields_reject(self):
        valid = identity()
        bad = [{'python': '3.11.18', 'ImageVersion': '20261111.370.1'}, {}, [], None,
               {**valid, 'provenance': {'ImageVersion': 'other', 'pid': 1}},
               {**valid, 'schema': 'engine-clock-runtime-preflight-v1'},
               {k:v for k,v in valid.items() if k!='core_sha256'}]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):contract.validate_identity(data)
        core = copy.deepcopy(FIXTURE_CORE); core['host']['ImageVersion'] = 'other'
        with self.assertRaises(ValueError):contract.validate_identity(identity(core))

    def test_null_boolean_wrong_type_and_incompatible_pins_reject(self):
        for group, key, value in [('image','artifact_id',True), ('image','artifact_id',0),
                ('image','config_digest',None), ('host','affinity_cpus',5),
                ('host','logical_cpus',4.0), ('host','sysname','Darwin'),
                ('versions','numpy','1.26.4'), ('versions','python','3.12.0'),
                ('configuration','read_only_rootfs',1), ('configuration','device_passthrough',True),
                ('image','assets_zip_sha256','0'*64)]:
            core = copy.deepcopy(FIXTURE_CORE); core[group][key] = value
            with self.subTest(group=group,key=key), self.assertRaises(ValueError):contract.validate_identity(identity(core))

    def test_invalid_digest_placement_tag_case_and_self_hash_reject(self):
        for value in ['image:latest', 'c'*64, 'sha512:'+'c'*64, 'sha256:'+'C'*64, 'sha256:'+'c'*63]:
            core=copy.deepcopy(FIXTURE_CORE);core['image']['config_digest']=value
            with self.subTest(value=value), self.assertRaises(ValueError):contract.validate_identity(identity(core))
        core=copy.deepcopy(FIXTURE_CORE);core['image']['image_tar_sha256']='sha256:'+'c'*64
        with self.assertRaises(ValueError):contract.validate_identity(identity(core))
        wrong=identity();wrong['core_sha256']='0'*64
        with self.assertRaises(ValueError):contract.validate_identity(wrong)

    def test_more_than_64_differences_truncate_in_sorted_path_order(self):
        a=copy.deepcopy(FIXTURE_CORE);b=copy.deepcopy(FIXTURE_CORE)
        a['host']['cpu_flags']=[f'a{i:03}' for i in range(80)]
        b['host']['cpu_flags']=[f'b{i:03}' for i in range(80)]
        result=contract.compare_identity(identity(a),identity(b))
        expected=sorted(f'core.host.cpu_flags[{i}]' for i in range(80))[:64]
        self.assertEqual(result['differences'],expected)
        self.assertIs(result['truncated'],True)

    def test_duplicate_nan_invalid_utf8_oversize_cli_rejects_without_echo(self):
        value=json.dumps(identity())
        cases=['{"schema":"one","schema":"two"}', value.replace('"artifact_id": 123','"artifact_id": NaN'),
               '{"secret":"RAW_SECRET_SENTINEL"}', b'\xff', ' ' * 131073]
        for raw in cases:
            with self.subTest(kind=type(raw).__name__):
                code,data=self.cli('compare',raw,value)
                self.assertEqual(code,1);self.assertIs(data['native_admission'],False)
                self.assertNotIn('RAW_SECRET_SENTINEL',json.dumps(data))
        core=copy.deepcopy(FIXTURE_CORE);core['host']['cpu_model']='x'*131073
        with self.assertRaises(ValueError):contract.validate_identity(identity(core))

    def test_cli_mismatch_reports_paths_and_never_raw_values(self):
        core=copy.deepcopy(FIXTURE_CORE);core['host']['cpu_model']='RAW_SECRET_SENTINEL'
        code,data=self.cli('compare',json.dumps(identity()),json.dumps(identity(core)))
        self.assertEqual(code,1);self.assertEqual(data['differences'],['core.host.cpu_model'])
        self.assertNotIn('RAW_SECRET_SENTINEL',json.dumps(data))

    def test_cli_file_error_is_bounded_and_invalid(self):
        result=subprocess.run([sys.executable,'-m','scripts.engine_clock_runtime_contract',
            'validate-proposal','--proposal','/NO_SUCH_METADATA_FILE'],capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertEqual(result.stderr,'')
        data=json.loads(result.stdout);self.assertIs(data['native_admission'],False)
        self.assertLess(len(result.stdout),1024)

    def test_fresh_import_and_validation_forbid_external_operations(self):
        code='''import builtins,json,sys
old=builtins.__import__
blocked={'numpy','cv2','panda3d','metadrive','onnxruntime','socket','requests','subprocess'}
def guard(name,*args,**kwargs):
    if name.split('.')[0] in blocked or name=='urllib.request':raise AssertionError('external/native import prohibited')
    return old(name,*args,**kwargs)
builtins.__import__=guard
from scripts import engine_clock_runtime_contract as c
with open(sys.argv[1]) as stream:r=c.validate_proposal(json.load(stream))
print(json.dumps(r))
'''
        result=subprocess.run([sys.executable,'-c',code,str(PROPOSAL)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIs(json.loads(result.stdout)['execution_authorized'],False)


if __name__=='__main__':unittest.main()
