"""Validate inactive proposals and synthetic installed-identity metadata only.

No API, Docker, installed-tree collector or native admission is implemented.
Matching opaque hashes cannot authenticate the objects they purport to name.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

JSON_LIMIT = 128 * 1024
DIFFERENCE_LIMIT = 64
ASSETS_SHA256 = '4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9'
VERSIONS = {'python': '3.11.18', 'executable': '/opt/venv/bin/python', 'numpy': '2.4.6',
            'opencv_python_headless': '5.0.0.93', 'cv2': '5.0.0',
            'panda3d': '1.10.13', 'metadrive_simulator': '0.4.3'}
RENDER_ENV = {'LIBGL_ALWAYS_SOFTWARE': '1', 'PYOPENGL_PLATFORM': 'glx', 'OMP_NUM_THREADS': '2'}
CONFIGURATION = {'read_only_rootfs': True, 'source_mount_read_only': True,
                 'host_native_library_mounts': False, 'host_display_mounts': False,
                 'device_passthrough': False, 'imports_isolated': True,
                 'cache_policy': 'fresh-per-case-external-bounded'}
IMAGE_HASHES = {'artifact_zip_sha256', 'image_tar_sha256', 'installed_files_sha256',
                'build_recipe_sha256', 'lock_sha256', 'assets_zip_sha256'}
HOST_STRINGS = {'sysname', 'release', 'version', 'machine', 'byteorder', 'cpu_vendor', 'cpu_model'}
ENGINE_FIELDS = {'docker_client', 'docker_server', 'docker_api', 'oci_runtime', 'storage_driver'}
PREPARATION_FIELDS = {'base_image_platform_manifest_digest', 'artifact_id', 'run_id', 'workflow_id',
    'source_sha', 'artifact_zip_sha256', 'image_tar_sha256', 'config_digest', 'rootfs_diff_ids',
    'installed_files_sha256', 'build_recipe_sha256', 'lock_sha256', 'environment_profile_sha256',
    'launch_receipt_sha256', 'docker_compatibility_profile', 'observed_feasibility'}
ALLOWANCE_FIELDS = {'providers', 'capture_pairs', 'task_steps', 'ram_reads', 'clock_snapshots',
                    'texture_readings', 'extra_gpu_reads', 'official_model_calls', 'ort_sessions'}
LIMITS = {'image_tar_bytes': 2147483648, 'image_artifact_zip_bytes': 2147483648,
    'installed_content_bytes': 3221225472, 'inventory_read_bytes': 4294967296,
    'inventory_entries': 100000, 'inventory_json_bytes': 16777216, 'identity_json_bytes': 131072,
    'file_bytes': 536870912, 'path_utf8_bytes': 4096, 'log_bytes': 1048576,
    'inventory_seconds': 180, 'image_download_seconds': 300, 'download_chunk_bytes': 1048576,
    'minimum_free_storage_union_bytes': 17179869184, 'difference_records': 64}
PROPOSAL_LITERALS = {'schema': 'engine-clock-runtime-contract-proposal-v1',
    'status': 'INACTIVE_DESIGN_ONLY', 'scope': 'PROVIDER_FREE_DESIGN', 'execution_authorized': False,
    'pure_metadata_implementation_ready': True, 'image_preparation_ready': False,
    'native_admission_ready': False, 'selected_distribution': 'actions-docker-save-v1',
    'future_identity_schema': 'engine-clock-installed-identity-v1',
    'future_preflight_schema': 'engine-clock-runtime-preflight-v1',
    'scientific_strict': 'FAIL', 'expanded': 'NOT_RUN', 'geometry_optics_full_s': 'NOT_VALIDATED',
    'stage7': 'INCOMPLETE', 'cloud_configuration_changed': False, 'cloud_published': False,
    'main_merged': False}
PROPOSAL_TEXT = {'design_branch', 'spec', 'plan', 'assurance', 'legacy_runtime_policy'}
PRESERVED = {'producer_files': 70, 'workflow_files': 44, 'consumed_request_acceptance_files': 8,
             'protected': 13, 'baseline': 43, 'old_gates_unchanged': True, 'histories_retained': True}
ACTUAL_ZERO = {'provider_constructors', 'native_engine_runs', 'docker_build_pull_load_run',
              'registry_publications', 'official_weight_downloads', 'official_model_calls',
              'ort_sessions', 'new_gpu_reads', 'new_clock_getters'}
ACTUAL_NULL = {'image_artifact_id', 'native_run_id', 'native_artifact_id'}


def _fields(value, keys, path):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError('missing or unregistered fields at ' + path)


def _same(value, expected, path):
    if type(value) is not type(expected) or value != expected:
        raise ValueError('invalid declared value at ' + path)


def _text(value, path):
    if type(value) is not str or not value:
        raise ValueError('nonempty string required at ' + path)


def _hex(value, length, path):
    if type(value) is not str or len(value) != length or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('invalid lowercase digest encoding at ' + path)


def _digest(value, path):
    if type(value) is not str or not value.startswith('sha256:'):
        raise ValueError('sha256-prefixed digest required at ' + path)
    _hex(value[7:], 64, path)


def _positive(value, path):
    if type(value) is not int or value <= 0:
        raise ValueError('positive integer required at ' + path)


def _encode(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise ValueError('invalid bounded JSON metadata') from None
    if len(raw) > JSON_LIMIT:
        raise ValueError('metadata exceeds 128KiB')
    return raw


def _literals(value, expected, path):
    _fields(value, expected, path)
    for key, literal in expected.items():
        _same(value[key], literal, path + '.' + key)


def validate_identity(document: dict) -> dict:
    """Check metadata syntax/self-hash; authenticate no external object."""
    _encode(document)
    _fields(document, {'schema', 'core', 'core_sha256'}, 'identity')
    _same(document['schema'], 'engine-clock-installed-identity-v1', 'identity.schema')
    core = document['core']
    _fields(core, {'image', 'versions', 'host', 'engine', 'configuration'}, 'core')
    image = core['image']
    _fields(image, IMAGE_HASHES | {'distribution', 'artifact_id', 'config_digest',
                                 'rootfs_diff_ids', 'platform'}, 'core.image')
    _same(image['distribution'], 'actions-docker-save-v1', 'core.image.distribution')
    _same(image['platform'], 'linux/amd64', 'core.image.platform')
    _positive(image['artifact_id'], 'core.image.artifact_id')
    for key in IMAGE_HASHES:
        _hex(image[key], 64, 'core.image.' + key)
    _same(image['assets_zip_sha256'], ASSETS_SHA256, 'core.image.assets_zip_sha256')
    _digest(image['config_digest'], 'core.image.config_digest')
    layers = image['rootfs_diff_ids']
    if type(layers) is not list or not layers:
        raise ValueError('ordered nonempty rootfs diffID list required')
    for layer in layers:
        _digest(layer, 'core.image.rootfs_diff_ids')
    _literals(core['versions'], VERSIONS, 'core.versions')
    host = core['host']
    _fields(host, HOST_STRINGS | {'cpu_flags', 'logical_cpus', 'affinity_cpus'}, 'core.host')
    for key in HOST_STRINGS:
        _text(host[key], 'core.host.' + key)
    for key, value in {'sysname': 'Linux', 'machine': 'x86_64', 'byteorder': 'little'}.items():
        _same(host[key], value, 'core.host.' + key)
    for key in ('logical_cpus', 'affinity_cpus'):
        _positive(host[key], 'core.host.' + key)
    if host['affinity_cpus'] > host['logical_cpus']:
        raise ValueError('affinity count exceeds logical CPU count')
    flags = host['cpu_flags']
    if (type(flags) is not list or not flags or any(type(v) is not str or not v for v in flags)
            or flags != sorted(set(flags))):
        raise ValueError('nonempty sorted unique CPU flags required')
    _fields(core['engine'], ENGINE_FIELDS, 'core.engine')
    for key in ENGINE_FIELDS:
        _text(core['engine'][key], 'core.engine.' + key)
    config = core['configuration']
    _fields(config, set(CONFIGURATION) | {'render_env', 'environment_profile_sha256'}, 'core.configuration')
    for key, value in CONFIGURATION.items():
        _same(config[key], value, 'core.configuration.' + key)
    _literals(config['render_env'], RENDER_ENV, 'core.configuration.render_env')
    _hex(config['environment_profile_sha256'], 64, 'core.configuration.environment_profile_sha256')
    _hex(document['core_sha256'], 64, 'identity.core_sha256')
    if hashlib.sha256(_encode(core)).hexdigest() != document['core_sha256']:
        raise ValueError('identity core hash mismatch')
    return document


def validate_proposal(document: dict) -> dict:
    """Validate the inactive declaration, never historical or execution truth."""
    _encode(document)
    extra = {'base_sha', 'producer70_sha256', 'preserved', 'prior_observation',
             'required_preparation', 'native_allowance', 'future_limits', 'actual_current_increment'}
    _fields(document, set(PROPOSAL_LITERALS) | PROPOSAL_TEXT | extra, 'proposal')
    for key, value in PROPOSAL_LITERALS.items():
        _same(document[key], value, 'proposal.' + key)
    for key in PROPOSAL_TEXT:
        _text(document[key], 'proposal.' + key)
    _hex(document['base_sha'], 40, 'proposal.base_sha')
    _hex(document['producer70_sha256'], 64, 'proposal.producer70_sha256')
    _literals(document['preserved'], PRESERVED, 'proposal.preserved')
    _fields(document['required_preparation'], PREPARATION_FIELDS, 'proposal.required_preparation')
    if any(v is not None for v in document['required_preparation'].values()):
        raise ValueError('inactive proposal cannot carry preparation evidence')
    _literals(document['native_allowance'], dict.fromkeys(ALLOWANCE_FIELDS, 0), 'proposal.native_allowance')
    _literals(document['future_limits'], LIMITS, 'proposal.future_limits')
    actual = document['actual_current_increment']
    _fields(actual, ACTUAL_ZERO | ACTUAL_NULL, 'proposal.actual_current_increment')
    for key in ACTUAL_ZERO:
        _same(actual[key], 0, 'proposal.actual_current_increment.' + key)
    if any(actual[key] is not None for key in ACTUAL_NULL):
        raise ValueError('inactive proposal cannot carry new execution references')
    prior = document['prior_observation']
    ids = {phase + '_' + kind for phase in ('canary', 'activation') for kind in ('run_id', 'job_id', 'artifact_id')}
    _fields(prior, ids | {'canary_source', 'activation_source', 'canary_image_version',
            'activation_image_version', 'activation_verdict', 'failed_aggregates',
            'unexecuted_cases', 'allowance_reusable'}, 'proposal.prior_observation')
    for key in ids:
        _positive(prior[key], 'proposal.prior_observation.' + key)
    for phase in ('canary', 'activation'):
        _hex(prior[phase + '_source'], 40, 'proposal.prior_observation.source')
        _text(prior[phase + '_image_version'], 'proposal.prior_observation.image_version')
    for key, value in {'activation_verdict': 'ACCEPTED_AUTHENTIC_FAILURE',
                       'failed_aggregates': 'NULL_PRESERVED', 'unexecuted_cases': 4,
                       'allowance_reusable': False}.items():
        _same(prior[key], value, 'proposal.prior_observation.' + key)
    return {'status': 'INACTIVE_PROPOSAL_VALIDATED', 'execution_authorized': False}


def _differences(left, right, path):
    if type(left) is dict:
        for key in sorted(left):
            yield from _differences(left[key], right[key], path + '.' + key)
    elif type(left) is list:
        if len(left) != len(right):
            yield path + '.length'
        for index, (a, b) in enumerate(zip(left, right)):
            yield from _differences(a, b, path + '[' + str(index) + ']')
    elif left != right:
        yield path


def compare_identity(left: dict, right: dict) -> dict:
    """Report bounded field paths only; no object/content provenance is proved."""
    validate_identity(left)
    validate_identity(right)
    paths = sorted(_differences(left['core'], right['core'], 'core'))
    return {'status': 'INSTALLED_PROFILE_MISMATCH' if paths else 'INSTALLED_PROFILE_MATCH',
            'differences': paths[:DIFFERENCE_LIMIT], 'truncated': len(paths) > DIFFERENCE_LIMIT,
            'native_admission': False}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _nonfinite(_):
    raise ValueError('nonfinite JSON number')


def _read(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError('regular metadata file required')
    with path.open('rb') as stream:
        raw = stream.read(JSON_LIMIT + 1)
    if len(raw) > JSON_LIMIT:
        raise ValueError('metadata exceeds 128KiB')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_object, parse_constant=_nonfinite)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('invalid command line')


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    proposal = sub.add_parser('validate-proposal')
    proposal.add_argument('--proposal', required=True)
    compare = sub.add_parser('compare-identity')
    compare.add_argument('--left', required=True)
    compare.add_argument('--right', required=True)
    try:
        args = parser.parse_args(argv)
        if args.command == 'validate-proposal':
            result = validate_proposal(_read(args.proposal))
        else:
            result = compare_identity(_read(args.left), _read(args.right))
        code = int(result['status'] == 'INSTALLED_PROFILE_MISMATCH')
    except (ValueError, TypeError, RecursionError, OSError, UnicodeError) as exc:
        detail = str(exc)[:512] if isinstance(exc, ValueError) and not isinstance(exc, UnicodeError) else 'invalid bounded metadata input'
        result = {'status': 'INVALID_CONTRACT', 'native_admission': False,
                  'error': type(exc).__name__ + ': ' + detail}
        code = 1
    print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
