"""Separate Linux trial body and portable ownership checks; no native-run CLI.

The native body is called only after parent authorization/SDK bootstrap. This
module does not authorize a model job, start a display, or replace parent limits.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
from . import worker_ownership as ownership

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT/'scripts/full_s_recorded_worker.py'
CASE = (20261109, 's_curve_left_right')


def need(value, message):
    if not value:
        raise ValueError(message)


def _fresh(out):
    out = Path(out).absolute()
    need(not out.exists() and not out.is_symlink() and all(not p.is_symlink() for p in out.parents), 'fresh nonsymlink output required')
    out.mkdir(parents=True, mode=0o700)
    return out


def _write_receipt(path, value, *, replace=False):
    path = Path(path)
    raw = (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()
    need(len(raw) <= 4*1024**2 and not path.is_symlink(), 'bounded nonsymlink receipt required')
    if not replace:
        with path.open('xb') as stream:
            stream.write(raw)
        return
    need(path.is_file(), 'previous owned receipt required')
    temporary = path.with_name(path.name+'.tmp')
    created = False
    try:
        with temporary.open('xb') as stream:
            created = True
            stream.write(raw)
        temporary.replace(path)
    finally:
        if created and temporary.exists():
            temporary.unlink()


def preflight():
    from .full_s_failure_capture import recording_plan
    return dict(protocol='recorded-full-s-worker-preflight-v1', private_task_state='NOT_OBSERVED',
        execution_activated=False, native_run_command_available=False, max_steps=600,
        child_limit_s=9000, cohort_model_limit=8, cohort_inference_limit=4800,
        model_ram_gate_bytes=8*1024**3, recording=recording_plan(),
        official_model_processes=0, inferences=0, all_four_validation_tracks_passed=False,
        scope='Read-only preparation. Parent owns source/resource/PID admission, SDK bootstrap, Xvfb, container and timeout. Private task state unknown.')


def _read_receipt(path, limit=65536):
    from .full_s_failure_capture import _decode
    path = Path(path).absolute()
    need(not path.is_symlink() and all(not p.is_symlink() for p in path.parents), 'nonsymlink receipt path required')
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'bounded regular receipt required before open')
    with path.open('rb') as stream:
        raw = stream.read(limit+1)
    need(len(raw) == info.st_size and len(raw) <= limit, 'bounded stable receipt snapshot required')
    value = _decode(raw)
    need(isinstance(value, dict), 'receipt object required')
    return value


def worker_check(args):
    owner = ownership.await_parent_ack(args.out, parent=args.parent, nonce=args.nonce,
        seed=args.seed, scene=args.scene, read_owner=_read_receipt)
    need(owner.get('mode') == 'OWNERSHIP_ONLY', 'ownership-only admission mode required')
    snapshot = ownership.ownership_snapshot(owner, 'full-s-recorded-worker')
    _write_receipt(Path(args.out)/'worker.json', snapshot)
    return 0


def process_check(out):
    out = _fresh(out)
    nonce = secrets.token_hex(16)
    owner = dict(parent_pid=os.getpid(), nonce=nonce, seed=CASE[0], scenario=CASE[1],
        mode='OWNERSHIP_ONLY', pid=None, spawn_succeeded=None, child_reaped=False, returncode=None)
    _write_receipt(out/'owner.json', owner)
    executable, env = ownership.worker_launch()
    command = [executable, '-I', '-S', '-B', str(ENTRY), 'internal-check', '--out', str(out),
        '--parent', str(os.getpid()), '--nonce', nonce, '--seed', str(CASE[0]), '--scene', CASE[1]]
    child = None
    failure = None
    secondary = []
    result = None
    try:
        try:
            child = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except BaseException as exc:
            if ownership.confirmed_spawn_failure(exc):
                owner.update(spawn_succeeded=False, child_reaped=True)
            raise
        owner.update(pid=child.pid, spawn_succeeded=True)
        _write_receipt(out/'owner.json', owner, replace=True)
        owner['returncode'] = child.wait(timeout=20)
        owner['child_reaped'] = True
        need(owner['returncode'] == 0, 'actual ownership-only child failed')
        worker = _read_receipt(out/'worker.json')
        need(worker.get('protocol') == 'owned-worker-process-check-v1' and
             worker.get('process_id') == child.pid and worker.get('parent_process_id') == os.getpid() and
             worker.get('nonce') == nonce and (worker.get('seed'), worker.get('scenario')) == CASE and
             worker.get('backend') == 'full-s-recorded-worker' and worker.get('ownership_check_complete') is True and
             worker.get('site_hooks_disabled') is True and worker.get('native_modules_loaded') is False and
             worker.get('model_loaded') is False and worker.get('server_connection_attempted') is False and
             type(worker.get('official_model_processes')) is int and worker['official_model_processes'] == 0 and
             type(worker.get('inferences')) is int and worker['inferences'] == 0 and
             Path(worker.get('prefix', '')).resolve() == Path(ownership.logical_prefix()).resolve(), 'actual child identity/prefix and zero native activity required')
        result = dict(protocol='recorded-full-s-worker-process-check-v1', status='PROCESS_CHECK_PASS',
            worker=worker, execution_activated=False, official_model_processes=0, inferences=0,
            all_four_validation_tracks_passed=False, scope='Actual owned entrypoint/PID/venv only, no native model/camera run.')
    except BaseException as exc:
        failure = exc
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=10)
                owner.update(returncode=child.returncode, child_reaped=True)
            except BaseException as exc:
                if failure is None: failure = exc
                else: secondary.append(_error(exc))
        try:
            _write_receipt(out/'owner.json', owner, replace=True)
        except BaseException as exc:
            if failure is None: failure = exc
            else: secondary.append(_error(exc))
    if failure is not None:
        failure.owner, failure.secondary_errors = dict(owner), secondary
        raise failure
    _write_receipt(out/'process-check.json', result)
    return result


class TrialFailure(RuntimeError):
    def __init__(self, primary_error, report, inference_bounds, secondary_errors):
        super().__init__(primary_error)
        self.primary_error, self.report = primary_error, report
        self.inference_bounds, self.secondary_errors = inference_bounds, secondary_errors


def _error(exc):
    return type(exc).__name__+': '+str(exc)[:2048]


def _source_snapshot():
    from .full_s_failure_capture import SOURCES
    selected = set(SOURCES) | {'bigbench/full_s_recorded_worker.py', 'scripts/full_s_recorded_worker.py',
        'bigbench/onnx_contract.py', 'bigbench/lane_truth.py', 'scripts/sdk3_four_validation_trial.py'}
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(selected)}


def _runtime_context(parent):
    ort = sys.modules.get('onnxruntime')
    session = getattr(parent, 'session', None)
    session_type = getattr(ort, 'InferenceSession', None)
    return dict(version=getattr(ort, '__version__', None),
        real_session=isinstance(session_type, type) and isinstance(session, session_type),
        providers=session.get_providers() if session is not None and hasattr(session, 'get_providers') else None,
        session_class=type(session).__module__+'.'+type(session).__qualname__ if session is not None else None)


def _exception_chain(exc):
    chain, seen = [], set()
    while exc is not None and id(exc) not in seen and len(chain) < 16:
        seen.add(id(exc))
        chain.append(exc)
        exc = exc.__cause__ or (None if exc.__suppress_context__ else exc.__context__)
    return chain


def run_recorded_trial(args):
    """Linux body for an already admitted/bootstrapped private native worker.

    Caller supplies a fresh body output directory, separately from owner/Xvfb
    logs. Original parent authentication/timeouts are mandatory and external.
    This function is intentionally absent from the executable CLI modes.
    """
    return _run_trial(args, camera_canary=False)


def run_camera_canary_trial(args):
    """Same observed body, two captures and synthetic state/action, NO graph."""
    need((args.seed, args.scenario) == CASE, 'single registered camera canary case required')
    return _run_trial(args, camera_canary=True)


def _run_trial(args, *, camera_canary):
    need(sys.platform == 'linux', 'frozen SDK3 trial body requires Linux')
    max_steps = 2 if camera_canary else 600
    need(type(args.seed) is int and args.seed in (20261109, 20261110) and
         args.scenario in ('s_curve_left_right', 's_curve_right_left') and
         isinstance(args.nonce, str) and len(args.nonce) == 32 and
         all(c in '0123456789abcdef' for c in args.nonce), 'registered case and fresh parent nonce required')
    need(not os.environ.get('LD_PRELOAD'), 'uninstrumented original native runtime required')
    out = Path(args.out)
    need(out.parent.is_dir() and shutil.disk_usage(out.parent).free >= 384*1024**2,
         '384MiB output headroom required before constructors')
    out = _fresh(out)
    life = dict(protocol='recorded-full-s-worker-lifecycle-v1', pid=os.getpid(), parent_pid=os.getppid(),
        nonce=args.nonce, seed=args.seed, scenario=args.scenario, status='PRE_POLICY',
        policy_constructor_entered=False, policy_created=False, provider_created=False,
        provider_received=False, provider_close_attempted=False, body_provider_close_attempted=False,
        provider_closed=False, inference_bounds=[0,0])
    provider = parent = report = None
    primary = None
    secondary = []
    driver = verification = stats = None
    lifecycle_created = False
    recording_started = False
    def persist():
        nonlocal lifecycle_created
        _write_receipt(out/'recorded-trial-lifecycle.json', life, replace=lifecycle_created)
        lifecycle_created = True
    def progress(payload):
        life.update(payload)
        life['inference_bounds'] = list(payload['inference_bounds'])
        persist()
    try:
        persist()
        life['status'] = 'DEPENDENCIES_LOADING'
        persist()
        # Inside the error boundary, but unreachable from cold/check entrypoints.
        if camera_canary:
            from .recorded_worker_canary import NoGraphPolicy
        else:
            from scripts.native_mdv3_repeat_trial import AuditedOfficialOnnx
        from scripts.sdk3_four_validation_trial import _world, driver_info
        from scripts.sdk3_priority_model_native import source_stats_after
        from .native_model_campaign import NativeWorldCamera
        from .model_world_frame import WorldFramePolicyAdapter, SOURCE_ACTION_FRAME
        from .optical_calibration import intrinsics_from_panda_lens
        from .full_s_failure_capture import capture_full_s, verify_recording
        life.update(status='POLICY_LOADING', policy_constructor_entered=True)
        persist()
        parent = (NoGraphPolicy(ROOT/'model_specs/md-v3.json') if camera_canary else
                  AuditedOfficialOnnx(Path('/model.onnx'), ROOT/'model_specs/md-v3.json'))
        life.update(status='WORLD_LOADING', policy_created=True, provider_created=None,
                    provider_close_attempted=None, provider_closed=None)
        persist()
        provider, lanes, terrain = _world(args.seed, args.scenario)
        life.update(provider_created=True, provider_received=True, provider_close_attempted=False,
                    provider_closed=False)
        camera = NativeWorldCamera(provider)
        intrinsics = {role: intrinsics_from_panda_lens(provider.env.engine.sensors['bigbench_'+role].get_lens(), 964, 604)
                      for role in ('road', 'wide')}
        driver = driver_info(provider)
        policy = WorldFramePolicyAdapter(parent, source_action_frame=SOURCE_ACTION_FRAME)
        recording_started = True
        report = capture_full_s(policy, camera, lanes, intrinsics=intrinsics, out=out/'recording',
            seed=args.seed, scene=args.scenario, max_steps=max_steps, progress=progress)
        life['inference_bounds'] = list(report['actual_inference_bounds'])
        if report.get('trial_completed') is not True:
            primary = RuntimeError(report.get('error') or 'original full-S trial incomplete')
    except BaseException as exc:
        report = getattr(exc, 'report', report)
        if report is not None and report.get('trial_completed') is False and report.get('error'):
            primary = RuntimeError(report['error'])
            secondary.append(_error(exc))
        elif life['status'] == 'WORLD_LOADING' and not life['provider_received']:
            chain = _exception_chain(exc)
            primary = chain[-1]
            secondary.extend(_error(value) for value in reversed(chain[:-1]))
        else:
            primary = exc
        bounds = getattr(exc, 'inference_bounds', None)
        if bounds is not None:
            life['inference_bounds'] = list(bounds)
        elif report is not None:
            life['inference_bounds'] = list(report['actual_inference_bounds'])
        elif parent is not None:
            known = len(parent.audit_rows)
            life['inference_bounds'] = [known, max(known, life['inference_bounds'][1])]
    finally:
        if provider is not None:
            life['provider_close_attempted'] = True
            life['body_provider_close_attempted'] = True
            try:
                provider.close()
                life['provider_closed'] = True
            except BaseException as exc:
                if primary is None:
                    primary = exc
                else:
                    secondary.append(_error(exc))
        if parent is not None:
            try:
                stats = source_stats_after()
            except BaseException as exc:
                if primary is None:
                    primary = exc
                else:
                    secondary.append(_error(exc))
    manifest_present = None
    report_present = None
    source_evidence = None
    try:
        manifest_present = (out/'recording/manifest.json').is_file()
    except Exception as exc:
        if primary is None: primary = exc
        else: secondary.append(_error(exc))
    if manifest_present and not isinstance(primary, (KeyboardInterrupt, SystemExit)):
        try:
            verification = verify_recording(out/'recording')
            manifest = _read_receipt(out/'recording/manifest.json', 4*1024**2)
            source_evidence = any('source/road' in package['blobs'] or 'source/wide' in package['blobs']
                                  for package in manifest['packages'].values())
        except Exception as exc:
            if primary is None:
                primary = exc
            else:
                secondary.append(_error(exc))
    try:
        report_present = (out/'recording/report.json').exists()
    except Exception as exc:
        if primary is None: primary = exc
        else: secondary.append(_error(exc))
    source_context = None
    runtime_context = None
    try:
        source_context = _source_snapshot()
    except Exception as exc:
        if primary is None:
            primary = exc
        else:
            secondary.append(_error(exc))
    try:
        runtime_context = _runtime_context(parent)
    except Exception as exc:
        if primary is None:
            primary = exc
        else:
            secondary.append(_error(exc))
    receipt = dict(protocol='recorded-full-s-worker-trial-v1', seed=args.seed, scenario=args.scenario,
        nonce=args.nonce, pid=os.getpid(), parent_pid=os.getppid(), max_steps=max_steps,
        actual_inference_bounds=life['inference_bounds'], provider_closed=life['provider_closed'],
        raw_rgb_observer_requested=recording_started, raw_rgb_source_evidence_present=source_evidence,
        raw_rgb_observer_used=True if source_evidence else None if recording_started else False,
        model_test_double=getattr(parent, 'is_mock', None),
        injected_session=getattr(parent, '_injected_session', None), driver=driver,
        onnxruntime=runtime_context,
        source_stats_after=stats, recording_verification=verification,
        original_report_file='recording/report.json' if report_present else None,
        primary_error=_error(primary) if primary is not None else None, secondary_errors=secondary,
        source_context=source_context,
        fingerprint_scope='SELECTED_SOURCE_FILES_NOT_FULL_CLOSURE', parent_admission_checked_by_body=False,
        origin_authenticated=False, all_four_validation_tracks_passed=False,
        model_camera_qualified=False, physical_optics_validated=False, carla_validated=False,
        hardware_gpu_qualified=False, scope='Separate observed worker body. Parent owns admission/runtime/timeout. No baseline repeatability, model ranking or native qualification.')
    if camera_canary:
        from .recorded_worker_canary import MODE
        receipt.update(mode=MODE, fixture_policy_audit_bounds=life['inference_bounds'],
            official_inference_bounds=[0,0], official_model_processes=0,
            policy_data='SYNTHETIC_STATE_AND_ZERO_ACTION_NO_GRAPH',
            graph_feed_attested=False)
        life.update(mode=MODE, official_inference_bounds=[0,0],
            counter_scope='FIXTURE_POLICY_AUDITS_NOT_ONNX_INFERENCES')
    receipt_created = False
    try:
        _write_receipt(out/'recorded-trial.json', receipt)
        receipt_created = True
    except BaseException as exc:
        if primary is None:
            primary = exc
        else:
            secondary.append(_error(exc))
    life.update(status='RECORDED' if primary is None else 'FAILED_OR_INCOMPLETE',
        primary_error=_error(primary) if primary is not None else None, secondary_errors=secondary)
    try:
        persist()
    except BaseException as exc:
        if primary is None:
            primary = exc
        else:
            secondary.append(_error(exc))
    if primary is not None and receipt_created:
        receipt.update(primary_error=_error(primary), secondary_errors=secondary)
        try:
            _write_receipt(out/'recorded-trial.json', receipt, replace=True)
        except BaseException as exc:
            secondary.append(_error(exc))
    if primary is not None:
        if isinstance(primary, (KeyboardInterrupt, SystemExit)):
            raise primary
        raise TrialFailure(_error(primary), report, life['inference_bounds'], secondary) from primary
    return receipt
