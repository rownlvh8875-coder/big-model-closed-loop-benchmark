"""Real CPU-only pipe transport regressions; no graphics/model receiver runs."""
import errno
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from bigbench import first_divergence_model as model


# Copies only the released wrapper's descriptor clobber/command-close contract.
SHELL = 'exec 3>/dev/null\n"$@" 3>&-\n'
RECEIVER = r'''
import json, os, sys, time
mode = sys.argv[1]
fd = int(os.environ['FIRST_DIVERGENCE_TRIAL_FD'])
if mode == 'exit':
    os.write(2, b'EARLY_EXIT_73\n'); sys.exit(73)
if mode == 'silent_stall':
    os.close(1); os.close(2); time.sleep(30)
if mode == 'stall':
    os.write(2, b'NONREADING\n'); time.sleep(30)
if mode in ('verbose', 'overflow'):
    os.write(2, b'PRE_READ\n' + b'v'*200000)
with os.fdopen(fd, 'rb') as stream:
    if mode == 'partial_exit':
        stream.read(32); os.write(2,b'PARTIAL_EXIT_73\n'); sys.exit(73)
    payload = stream.read()
permit = json.loads(payload)
assert permit['nonce'] == 'a'*64
assert permit['parent_pid'] == int(sys.argv[2])
assert permit['process_group'] == os.getpgrp()
assert permit['schedule_index'] == 0
assert permit['parent_uuid'] == 'b'*32
assert permit['arm'] == 'original' and permit['repeat'] == 0
assert permit['source_snapshot'] == {'padding':'s'*128000}
assert permit['runtime'] == {'fixture':'stdlib'}
os.write(1, json.dumps({'received':len(payload), 'fd':fd, 'pid':os.getpid(), 'group':os.getpgrp()}).encode()+b'\n')
'''


class LaunchTransportTests(unittest.TestCase):
    def setUp(self):
        model._enable_subreaper()
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp)
        self.wrapper = self.root/'wrapper.sh'
        self.wrapper.write_text(SHELL)
        self.row = {'launched':False, 'launcher_pid':None, 'process_group':None,
                    'cleanup_errors':[], 'exit_code':None,
                    'storage':dict(payload_limit_bytes=1000000, trial_ledger_limit_bytes=4096,
                                   log_limit_bytes=300000, log_bytes=0, limit_error=None)}
        self.processes = []
        self.real_popen = subprocess.Popen
        self.enterContext(patch.object(model.capture, 'source_snapshot', return_value={'padding':'s'*128000}))
        self.enterContext(patch.object(model, '_runtime_identity', return_value={'fixture':'stdlib'}))
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for process in self.processes:
            if process.poll() is None:
                model._terminate_group(process)
            if process.stdout is not None and not process.stdout.closed:
                process.stdout.close()

    def boundary(self, mode='normal', synchronize=False):
        def popen(command, **kwargs):
            self.assertEqual(command[:2], ['xvfb-run','-a'])
            self.assertEqual(command[2:6], [sys.executable,'-m','scripts.first_divergence_audit','native-trial'])
            self.assertEqual(kwargs['stdout'], subprocess.PIPE)
            self.assertEqual(kwargs['stderr'], subprocess.STDOUT)
            self.assertTrue(kwargs['start_new_session'])
            self.assertEqual(len(kwargs['pass_fds']), 1)
            self.assertFalse(os.get_inheritable(kwargs['pass_fds'][0]))
            self.assertEqual(str(kwargs['pass_fds'][0]), kwargs['env']['FIRST_DIVERGENCE_TRIAL_FD'])
            process = self.real_popen(['/bin/sh',str(self.wrapper),sys.executable,'-c',RECEIVER,mode,str(os.getpid())], **kwargs)
            self.processes.append(process)
            if synchronize:
                process.wait(timeout=3)
            return process
        return patch.object(model.subprocess, 'Popen', side_effect=popen)

    def launch(self, *, timeout=3):
        self.assertIn('timeout', inspect.signature(model._launch_trial).parameters,
                      'launcher must bound permit delivery with the caller deadline')
        return model._launch_trial('missing-model','missing-spec',self.root/'trial','original',0,
                                   'a'*64,'b'*32,0,self.row,timeout=timeout)

    def assert_reaped(self):
        for process in self.processes:
            self.assertIsNotNone(process.poll())
            self.assertTrue(process.stdout.closed)
            with self.assertRaises(ProcessLookupError):
                os.killpg(process.pid, 0)

    def test_known_wrapper_contract_destroys_fd3_but_keeps_high_fd(self):
        # Run in an isolated stdlib interpreter so descriptor 3 is deterministic.
        source = r'''
import os, subprocess, sys
low, writer = os.pipe()
fd = int(sys.argv[1])
if fd != low:
    os.dup2(low, fd); os.close(low)
process = subprocess.Popen(['/bin/sh', sys.argv[2], sys.executable, '-c',
    'import os,sys; print(os.read(int(sys.argv[1]),16).decode())',str(fd)],
    pass_fds=(fd,),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
os.close(fd)
try: os.write(writer,b'permit')
except BrokenPipeError: pass
os.close(writer)
out,err=process.communicate(timeout=3)
assert (process.returncode != 0 and b'Bad file descriptor' in err) if fd==3 else (process.returncode==0 and out==b'permit\n')
'''
        for fd in (3,10):
            result = self.real_popen([sys.executable,'-c',source,str(fd),str(self.wrapper)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err = result.communicate(timeout=5)
            self.assertEqual(result.returncode, 0, err.decode())

    def test_default_positional_call_retains_early_exit_diagnostics(self):
        with self.boundary('exit',synchronize=True),self.assertRaises(BrokenPipeError):
            model._launch_trial('missing-model','missing-spec',self.root/'trial','original',0,
                                'a'*64,'b'*32,0,self.row)
        path=self.root/'trial/process.log'
        self.assertTrue(path.exists(),'early output log must exist before permit delivery')
        self.assertIn(b'EARLY_EXIT_73',path.read_bytes())
        self.assert_reaped()

    def test_high_fd_permit_eof_and_early_verbose_output_are_delivered(self):
        before = len(os.listdir('/proc/self/fd'))
        with self.boundary('verbose'):
            child = self.launch()
        self.assertEqual(child.wait(timeout=3),0)
        self.assertEqual(model._terminate_group(child.process),[])
        log = (self.root/'trial/process.log').read_bytes()
        self.assertIn(b'PRE_READ\n'+b'v'*200000, log)
        receipt = json.loads(log.splitlines()[-1])
        self.assertGreaterEqual(receipt['fd'],10)
        self.assertGreater(receipt['received'],128000)
        self.assertIn(f'authorization_fd={receipt["fd"]}'.encode(),log)
        self.assertIn(b'phase=permit',log)
        self.assertNotIn(b'ssssssssssss',log)
        self.assertTrue(self.row['launched'])
        self.assertEqual(self.row['launcher_pid'],child.pid)
        self.assertEqual(self.row['storage']['log_bytes'],len(log))
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)
        self.assert_reaped()

    def test_nonblocking_partial_writes_retry_eintr_and_eagain(self):
        real_write=os.write; calls=[]
        def short_write(fd,data):
            if not calls:
                calls.append('eintr');raise InterruptedError(errno.EINTR,'interrupted')
            if len(calls)==1:
                calls.append('eagain');raise BlockingIOError(errno.EAGAIN,'full')
            count=real_write(fd,data[:31]);calls.append(count);return count
        with self.boundary(),patch.object(model.os,'write',side_effect=short_write):
            child=self.launch()
        self.assertEqual(child.wait(timeout=3),0)
        self.assertGreater(len(calls),100)
        self.assertEqual(model._terminate_group(child.process),[])
        self.assert_reaped()

    def test_nonreading_child_times_out_with_marker_and_no_leaks(self):
        before=len(os.listdir('/proc/self/fd'));start=time.monotonic()
        with self.boundary('stall'),self.assertRaises(subprocess.TimeoutExpired):
            self.launch(timeout=.2)
        self.assertLess(time.monotonic()-start,3)
        self.assertIn(b'NONREADING', (self.root/'trial/process.log').read_bytes())
        self.assertTrue(self.row['launched']);self.assertIsNotNone(self.row['exit_code'])
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)
        self.assert_reaped()

    def test_output_eof_does_not_end_nonreading_permit_deadline(self):
        before=len(os.listdir('/proc/self/fd'))
        with self.boundary('silent_stall'),self.assertRaises(subprocess.TimeoutExpired):
            self.launch(timeout=.2)
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)
        self.assert_reaped()

    def test_partial_delivery_then_exit_retains_output_and_breaks_pipe(self):
        with self.boundary('partial_exit'),self.assertRaises(BrokenPipeError):
            self.launch()
        self.assertIn(b'PARTIAL_EXIT_73',(self.root/'trial/process.log').read_bytes())
        self.assert_reaped()

    def test_early_exit_keeps_primary_broken_pipe_marker_and_real_exit(self):
        before=len(os.listdir('/proc/self/fd'))
        with self.boundary('exit',synchronize=True),self.assertRaises(BrokenPipeError):
            self.launch()
        self.assertIn(b'EARLY_EXIT_73', (self.root/'trial/process.log').read_bytes())
        self.assertEqual(self.row['exit_code'],73)
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)
        self.assert_reaped()

    def test_log_cap_is_exact_and_raw_group_is_reaped(self):
        self.row['storage']['log_limit_bytes']=1024
        with self.boundary('overflow'),self.assertRaisesRegex(ValueError,'log storage budget'):
            self.launch()
        self.assertEqual((self.root/'trial/process.log').stat().st_size,1024)
        self.assertEqual(self.row['storage']['log_bytes'],1024)
        self.assertIn('log storage budget',self.row['storage']['limit_error'])
        self.assert_reaped()

    def test_invalid_timeout_or_limits_allocate_and_spawn_nothing(self):
        for timeout in (True,False,0,-1,float('nan'),float('inf'),481,10**1000,'1'):
            with self.subTest(timeout=timeout),patch.object(model.os,'pipe') as pipe,patch.object(model.subprocess,'Popen') as popen:
                with self.assertRaises(ValueError):self.launch(timeout=timeout)
                pipe.assert_not_called();popen.assert_not_called()
        self.row['storage']['log_limit_bytes']=-1
        with patch.object(model.os,'pipe') as pipe,patch.object(model.subprocess,'Popen') as popen:
            with self.assertRaises(ValueError):self.launch()
            pipe.assert_not_called();popen.assert_not_called()

    def test_log_open_failure_allocates_no_unowned_fds_or_process(self):
        out=self.root/'trial';out.mkdir();(out/'process.log').write_bytes(b'existing')
        before=len(os.listdir('/proc/self/fd'))
        with patch.object(model.subprocess,'Popen') as popen,self.assertRaises(FileExistsError):self.launch()
        popen.assert_not_called()
        self.assertEqual((out/'process.log').read_bytes(),b'existing')
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_popen_and_source_failure_keep_primary_and_close_handles(self):
        for mode in ('popen','source'):
            with self.subTest(mode=mode):
                self.row['storage']['log_bytes']=0
                self.root.joinpath('trial/process.log').unlink(missing_ok=True)
                before=len(os.listdir('/proc/self/fd'))
                boundary=self.boundary('stall') if mode=='source' else patch.object(model.subprocess,'Popen',side_effect=RuntimeError('spawn-primary'))
                source=patch.object(model.capture,'source_snapshot',side_effect=RuntimeError('source-primary')) if mode=='source' else patch.object(model,'_runtime_identity',return_value={})
                with boundary,source,self.assertRaisesRegex(RuntimeError,mode+'-primary' if mode=='source' else 'spawn-primary'):
                    self.launch()
                self.assertTrue((self.root/'trial/process.log').exists())
                self.assertEqual(len(os.listdir('/proc/self/fd')),before)
                self.assert_reaped()

    def test_pipe_reservation_failures_close_log_and_all_descriptors(self):
        for boundary in ('pipe','duplicate'):
            with self.subTest(boundary=boundary):
                self.root.joinpath('trial/process.log').unlink(missing_ok=True)
                before=len(os.listdir('/proc/self/fd'))
                target=model.os if boundary=='pipe' else model.fcntl
                attribute='pipe' if boundary=='pipe' else 'fcntl'
                with patch.object(target,attribute,side_effect=OSError('allocation-primary')),self.assertRaisesRegex(OSError,'allocation-primary'):
                    self.launch()
                self.assertEqual(len(os.listdir('/proc/self/fd')),before)
                self.assertEqual(self.processes,[])

    def test_group_cleanup_exception_is_secondary_to_delivery_error(self):
        terminate=model._terminate_group
        def raising_cleanup(process):
            terminate(process)
            raise OSError('secondary-reaper')
        with self.boundary('exit',synchronize=True),patch.object(model,'_terminate_group',side_effect=raising_cleanup),self.assertRaises(BrokenPipeError):
            self.launch()
        self.assertTrue(any('secondary-reaper' in e for e in self.row['cleanup_errors']))
        self.assert_reaped()

    def test_cleanup_errors_do_not_replace_primary_or_skip_raw_reaping(self):
        real_close=model._LogSink.close;real_terminate=model._terminate_group;reaped=[]
        def bad_close(sink):real_close(sink);raise OSError('secondary-log-close')
        def terminate(process):
            self.assertIsInstance(process,self.real_popen)
            reaped.append(process.pid)
            return real_terminate(process)+['secondary-cleanup']
        with self.boundary('exit',synchronize=True),patch.object(model._LogSink,'close',bad_close),patch.object(model,'_terminate_group',side_effect=terminate),self.assertRaises(BrokenPipeError):
            self.launch()
        self.assertEqual(reaped,[self.processes[0].pid])
        self.assertTrue(any('secondary-log-close' in e for e in self.row['cleanup_errors']))
        self.assertIn('secondary-cleanup',self.row['cleanup_errors'])
        self.assertIn(b'EARLY_EXIT_73',(self.root/'trial/process.log').read_bytes())
        self.assert_reaped()


class StudyLaunchDeadlineTests(unittest.TestCase):
    def test_study_deducts_launch_time_and_marks_launch_or_wait_expiry(self):
        for launch_timeout in (False,True):
            with self.subTest(launch_timeout=launch_timeout),tempfile.TemporaryDirectory() as temp:
                clock=[0.];budgets=[];waits=[];cleaned=[]
                class Process:
                    pid=12345;returncode=-9
                    def wait(self,timeout):
                        waits.append(timeout)
                        raise subprocess.TimeoutExpired('wait-fixture',timeout)
                def launch(*args,timeout):
                    budgets.append(timeout)
                    args[-1].update(launched=True,launcher_pid=12345,process_group=12345)
                    clock[0]+=2.
                    if launch_timeout:raise subprocess.TimeoutExpired('launch-fixture',timeout)
                    return Process()
                def accepted():clock[0]=2395.;return {}
                with patch.object(model,'_require_model_acceptance',side_effect=accepted),patch.object(model,'retention_preflight'),patch.object(model,'_require_official_model'),patch.object(model,'_enable_subreaper'),patch.object(model.capture,'_require_ephemeral_ci'),patch.object(model.capture,'source_snapshot',return_value={}),patch.object(model,'_runtime_identity',return_value={}),patch.object(model,'_launch_trial',side_effect=launch),patch.object(model,'_terminate_group',side_effect=lambda p:cleaned.append(p.pid) or []),patch.object(model,'perf_counter',side_effect=lambda:clock[0]):
                    result=model.run_study('missing-model','missing-spec',Path(temp)/'study')
                self.assertEqual(budgets,[5.])
                self.assertEqual(waits,[] if launch_timeout else [3.])
                self.assertEqual(cleaned,[] if launch_timeout else [12345])
                self.assertTrue(result['launch_ledger'][0]['timed_out'])
                self.assertEqual(result['status'],'FAILED_OR_INCOMPLETE')
                self.assertIsNone(result['model_calls'])
                self.assertEqual(result['model_calls_lower_bound'],0)
                self.assertEqual(result['model_calls_upper_bound'],4)


class ProbeTests(unittest.TestCase):
    """The only fake is xvfb-run: real launcher, shell, FIFO and fixed receiver."""
    def run(self, result=None):
        # Whole discovery can import the existing tiny ORT test before this
        # class runs. Execute only this method once in a clean CPU interpreter.
        if any(n == p or n.startswith(p+'.') for n in sys.modules
               for p in ('onnxruntime','panda3d','direct','metadrive')):
            result = result or self.defaultTestResult()
            result.startTest(self)
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parent))
            completed=subprocess.run([sys.executable,'-m','unittest',
                'test_first_divergence_transport.ProbeTests.'+self._testMethodName,'-v'],
                cwd=model.capture.REPO_ROOT,env=env,capture_output=True,timeout=30)
            if completed.returncode:
                try:self.fail(completed.stdout.decode()+completed.stderr.decode())
                except self.failureException:result.addFailure(self,sys.exc_info())
            else:result.addSuccess(self)
            result.stopTest(self)
            return result
        return super().run(result)

    def setUp(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('scripts.first_divergence_transport_probe'),
                             'the guarded fixed transport probe is not implemented')
        from scripts import first_divergence_transport_probe as probe
        self.probe = probe
        model._enable_subreaper()
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp)
        self.wrapper = self.root/'wrapper.sh'
        self.wrapper.write_text(SHELL)
        self.calls = []
        self.real_popen = subprocess.Popen
        self.head = 'a'*40
        env = dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='rownlvh8875-coder/big-model-closed-loop-benchmark',
                   GITHUB_SHA=self.head,GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1',GITHUB_EVENT_NAME='push',
                   GITHUB_REF_NAME='fix/first-divergence-launch-transport',RUNNER_TEMP=self.temp,
                   GITHUB_WORKFLOW_REF='rownlvh8875-coder/big-model-closed-loop-benchmark/.github/workflows/stage7-first-divergence-transport.yml@refs/heads/fix/first-divergence-launch-transport',
                   ImageOS='ubuntu24',ImageVersion='fixture-image',FIRST_DIVERGENCE_ACCEPTANCE='must-be-cleared')
        self.enterContext(patch.dict(os.environ,env))
        self.enterContext(patch.object(probe,'_git',side_effect=self.git))
        self.enterContext(patch.object(probe,'_tools',return_value={
            'wrapper_path':'/usr/bin/xvfb-run','wrapper_sha256':'b'*64,'wrapper_version':'fixture-xvfb',
            'xauth_path':'/usr/bin/xauth','xauth_version':'fixture-xauth'}))

    def git(self,*args,**kwargs):
        if args == ('rev-parse','HEAD'):return (self.head+'\n').encode()
        if args[0] == 'show':
            head,name=args[1].split(':',1)
            self.assertEqual(head,self.head)
            return (model.capture.REPO_ROOT/name).read_bytes()
        self.fail(f'unexpected Git plumbing: {args}')

    def boundary(self, *, mutate=None, prefix=b''):
        def popen(command,**kwargs):
            self.assertEqual(command[:3],['xvfb-run',sys.executable,str(self.probe.SCRIPT)])
            self.assertEqual(command[3],'_receive')
            self.assertEqual(set(kwargs),{'cwd','env','stdout','stderr','start_new_session','pass_fds'})
            self.assertEqual(kwargs['cwd'],model.capture.REPO_ROOT)
            self.assertEqual(kwargs['stdout'],subprocess.PIPE)
            self.assertEqual(kwargs['stderr'],subprocess.STDOUT)
            self.assertIs(kwargs['start_new_session'],True)
            fd,=kwargs['pass_fds'];self.assertGreaterEqual(fd,10)
            self.assertEqual(kwargs['env']['FIRST_DIVERGENCE_TRIAL_FD'],str(fd))
            self.assertNotIn('FIRST_DIVERGENCE_ACCEPTANCE',kwargs['env'])
            receiver=command[1:]
            if mutate:receiver=mutate(receiver)
            actual=['/bin/sh',str(self.wrapper),*receiver]
            if prefix:
                actual=['/bin/sh','-c','printf "%s" "$1"; shift; exec "$@"','fixture',prefix.decode(),*actual]
            process=self.real_popen(actual,**kwargs);self.calls.append(process)
            return process
        return patch.object(subprocess,'Popen',side_effect=popen)

    def run_ok(self):
        with self.boundary():result=self.probe.run_probe(self.root/'out')
        self.assertEqual(result['status'],'TRANSPORT_ASSOCIATION_VALIDATED')
        self.assertEqual(self.probe.validate_probe(self.root/'out'),result)
        return result

    def rewrite(self,result):
        (self.root/'out/probe.json').write_text(json.dumps(result,allow_nan=False))

    def test_real_launcher_two_sequential_cases_and_actual_receipts(self):
        result=self.run_ok()
        self.assertEqual([r['case'] for r in result['cases']],['normal','early_exit'])
        self.assertEqual(len(self.calls),2)
        self.assertEqual([p.returncode for p in self.calls],[0,73])
        for row,p in zip(result['cases'],self.calls):
            self.assertEqual(row['launcher_pid'],p.pid)
            self.assertEqual(row['process_group'],p.pid)
            self.assertGreaterEqual(row['receiver']['fd'],10)
            self.assertEqual(row['receiver']['pgid'],p.pid)
            self.assertNotEqual(row['receiver']['pid'],os.getpid())
            self.assertTrue(p.stdout.closed)
            with self.assertRaises(ProcessLookupError):os.killpg(p.pid,0)
        self.assertEqual(result['claims']['official_model_calls'],0)
        self.assertEqual(result['claims']['ort_sessions'],0)
        self.assertEqual(result['claims']['metadrive_providers'],0)
        self.assertEqual(len(result['source_snapshot']),61)
        self.assertEqual(os.environ['FIRST_DIVERGENCE_ACCEPTANCE'],'must-be-cleared')
        self.assertEqual(sorted(str(p.relative_to(self.root/'out')) for p in (self.root/'out').rglob('*') if p.is_file()),
                         ['early_exit/process.log','normal/process.log','probe.json'])

    def test_guard_rejects_actual_context_before_any_launch(self):
        for key,value in [('GITHUB_ACTIONS','false'),('GITHUB_EVENT_NAME','workflow_dispatch'),
                          ('GITHUB_REF_NAME','main'),('GITHUB_RUN_ATTEMPT','2'),('GITHUB_SHA','b'*40),
                          ('GITHUB_WORKFLOW_REF','wrong'),('GITHUB_RUN_ID','0'),('ImageVersion','')]:
            with self.subTest(key=key),patch.dict(os.environ,{key:value}),self.boundary():
                with self.assertRaises(ValueError):self.probe.run_probe(self.root/'out')
            self.assertFalse((self.root/'out').exists())
        self.assertEqual(self.calls,[])

    def test_source_git_blob_mismatch_blocks_before_launch(self):
        with patch.object(self.probe,'_git',side_effect=lambda *a,**kw: b'not-current' if a[0]=='show' else (self.head+'\n').encode()),self.boundary():
            with self.assertRaises(ValueError):self.probe.run_probe(self.root/'out')
        self.assertEqual(self.calls,[])

    def test_outside_existing_and_symlink_outputs_rejected(self):
        existing=self.root/'existing';existing.mkdir()
        link=self.root/'link';link.symlink_to(self.root,target_is_directory=True)
        for out in (self.root,self.root.parent/'outside-probe',existing,link/'output'):
            with self.subTest(out=out),self.boundary():
                with self.assertRaises(ValueError):self.probe.run_probe(out)
        self.assertEqual(self.calls,[])

    def test_failed_normal_stops_without_retry_and_keeps_failure_ledger(self):
        def corrupt(argv):
            result=list(argv);result[result.index('--nonce')+1]='c'*64;return result
        with self.boundary(mutate=corrupt):result=self.probe.run_probe(self.root/'out')
        self.assertEqual(result['status'],'FAILED_OR_INCOMPLETE')
        self.assertEqual(len(self.calls),1)
        self.assertIn('error',result)
        self.assertTrue((self.root/'out/normal/process.log').exists())
        with self.assertRaises(ValueError):self.probe.validate_probe(self.root/'out')

    def test_log_overflow_is_bounded_and_stops(self):
        with self.boundary(prefix=b'v'*70000):result=self.probe.run_probe(self.root/'out')
        self.assertEqual(result['status'],'FAILED_OR_INCOMPLETE')
        self.assertEqual(len(self.calls),1)
        self.assertEqual((self.root/'out/normal/process.log').stat().st_size,65536)
        self.assertLessEqual(sum(p.stat().st_size for p in (self.root/'out').rglob('*') if p.is_file()),2097152)
        for p in self.calls:
            self.assertIsNotNone(p.poll())
            with self.assertRaises(ProcessLookupError):os.killpg(p.pid,0)

    def test_validator_rejects_tampered_identity_source_claims_limits_and_substitutions(self):
        import copy
        original=self.run_ok()
        changes=[lambda x:x['cases'][0]['receiver'].__setitem__('pid',1),
                 lambda x:x['cases'][0].__setitem__('exit_code',73),
                 lambda x:x['cases'][0].__setitem__('group_gone',False),
                 lambda x:x['cases'][0].__setitem__('elapsed_s',121),
                 lambda x:x['claims'].__setitem__('original_strict_pass',True),
                 lambda x:x['claims'].__setitem__('official_model_calls',False),
                 lambda x:x['substitutions'].append('bypass'),
                 lambda x:x['source_snapshot'].__setitem__('bigbench/first_divergence.py','0'*64),
                 lambda x:x['cases'][0]['log'].__setitem__('path','../outside'),
                 lambda x:x['cases'][0]['log'].__setitem__('bytes',65537),
                 lambda x:x['cases'][0]['receiver'].__setitem__('fd',3),
                 lambda x:x.__setitem__('extra',True)]
        for change in changes:
            candidate=copy.deepcopy(original);change(candidate);self.rewrite(candidate)
            with self.subTest(change=change),self.assertRaises(ValueError):self.probe.validate_probe(self.root/'out')

    def test_validator_rejects_missing_extra_symlink_and_modified_logs(self):
        result=self.run_ok();log=self.root/'out/normal/process.log';raw=log.read_bytes()
        log.write_bytes(raw+b'tamper')
        with self.assertRaises(ValueError):self.probe.validate_probe(self.root/'out')
        log.write_bytes(raw);log.unlink()
        with self.assertRaises(ValueError):self.probe.validate_probe(self.root/'out')
        target=self.root/'outside';target.write_bytes(raw);log.symlink_to(target)
        with self.assertRaises(ValueError):self.probe.validate_probe(self.root/'out')
        log.unlink();log.write_bytes(raw)
        extra=self.root/'out/extra';extra.write_text('extra')
        with self.assertRaises(ValueError):self.probe.validate_probe(self.root/'out')

    def test_validator_duplicate_nonfinite_and_cli_are_pure(self):
        self.run_ok();path=self.root/'out/probe.json';original=path.read_text()
        for data in ('{"schema":1,"schema":2}',original.replace('"attempt": 1','"attempt": NaN')):
            path.write_text(data)
            with self.assertRaises(ValueError):self.probe.validate_probe(self.root/'out')
        path.write_text(original)
        # CLI validation of an invalid artifact is stdlib-only and launches nothing.
        path.write_text('{"x":NaN}')
        process=self.real_popen([sys.executable,str(self.probe.SCRIPT),'validate','--root',str(self.root/'out')],
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=process.communicate(timeout=5)
        self.assertNotEqual(process.returncode,0)

    def test_workflow_parsed_contract_and_bash_syntax(self):
        workflow=json.loads((model.capture.REPO_ROOT/'.github/workflows/stage7-first-divergence-transport.yml').read_text())
        self.assertEqual(set(workflow['on']),{'push'})
        self.assertEqual(workflow['on']['push']['branches'],['fix/first-divergence-launch-transport'])
        self.assertEqual(workflow['permissions'],{'contents':'read'})
        job,=workflow['jobs'].values();self.assertEqual(job['timeout-minutes'],15)
        self.assertNotIn('env',job)
        steps=job['steps'];runs=[s['run'] for s in steps if 'run' in s]
        self.assertTrue(any('numpy==2.4.6 opencv-python-headless==5.0.0.93' in r for r in runs))
        from hashlib import sha256
        bootstrap=next(s['run'] for s in steps if s.get('name')=='Provided native system bootstrap')
        self.assertEqual(sha256(bootstrap.encode()).hexdigest(),'432772a69fe7b888b80fe5842708653b85253ba4d036d939889f20fa8cbb2175')
        for run in runs:
            for forbidden in ('onnxruntime','panda3d','metadrive','hf_models','[inference]','huggingface'):
                self.assertNotIn(forbidden,run.lower())
        for run in runs:
            completed=subprocess.run(['bash','-n'],input=run.encode(),capture_output=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
        paths=workflow['on']['push']['paths']
        self.assertEqual(set(paths),{'scripts/first_divergence_transport_probe.py','tests/test_first_divergence_transport.py',
                                    '.github/workflows/stage7-first-divergence-transport.yml','bigbench/first_divergence_model.py',
                                    'bigbench/first_divergence.py','tests/test_first_divergence_model.py'})
        upload=steps[-1]
        self.assertEqual(upload['if'],'always()')
        self.assertEqual(upload['with']['name'],'stage7-first-divergence-transport')
        self.assertEqual(upload['with']['path'],'${{ runner.temp }}/first-divergence-transport')


    def test_fixed_receiver_rejects_private_permit_type_fields_and_association(self):
        import fcntl
        from hashlib import sha256
        source={'registered':'a'*64};runtime={'python':'fixture'}
        digest=lambda x:sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        mutations=[lambda p:p.__setitem__('repeat',False),lambda p:p.__setitem__('schedule_index',True),
                   lambda p:p.__setitem__('parent_pid',True),lambda p:p.__setitem__('parent_uuid','bad'),
                   lambda p:p.__setitem__('nonce','b'*64),lambda p:p.__setitem__('process_group',1),
                   lambda p:p.__setitem__('source_snapshot',{'wrong':'a'*64}),
                   lambda p:p.__setitem__('runtime',{'wrong':'fixture'}),
                   lambda p:p.__setitem__('extra',1),lambda p:p['storage_limits'].__setitem__('log_limit_bytes',True)]
        for mutation in mutations:
            low,writer=os.pipe();fd=fcntl.fcntl(low,fcntl.F_DUPFD_CLOEXEC,10);os.close(low)
            env=dict(os.environ,FIRST_DIVERGENCE_TRIAL_FD=str(fd));env.pop('FIRST_DIVERGENCE_ACCEPTANCE',None)
            argv=[sys.executable,str(self.probe.SCRIPT),'_receive','--case','normal','--parent-pid',str(os.getpid()),
                  '--parent-uuid','b'*32,'--nonce','a'*64,'--source-sha256',digest(source),
                  '--runtime-sha256',digest(runtime),'--model',str(self.root/'missing.onnx'),'--timeout','2']
            process=self.real_popen(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                    pass_fds=(fd,),start_new_session=True)
            os.close(fd)
            permit=dict(parent_pid=os.getpid(),parent_uuid='b'*32,process_group=process.pid,
                        nonce='a'*64,arm='original',repeat=0,schedule_index=0,source_snapshot=source,runtime=runtime,
                        storage_limits=dict(payload_limit_bytes=0,trial_ledger_limit_bytes=4096,log_limit_bytes=65536))
            mutation(permit)
            try:os.write(writer,json.dumps(permit).encode())
            finally:os.close(writer)
            out,err=process.communicate(timeout=4)
            with self.subTest(mutation=mutation):
                self.assertNotEqual(process.returncode,0,(out,err))
                self.assertNotIn(b'PROBE_PERMIT_RECEIVED',out)

    def test_case_deadline_kills_stalled_wrapper_with_raw_handle(self):
        # This fixture runs the fixed receiver, then keeps the whole wrapper
        # alive. The early adapter must own cleanup until Popen returns.
        self.wrapper.write_text('exec 3>/dev/null\n"$@" 3>&-\nsleep 30\n')
        started=time.monotonic()
        with self.boundary(),patch.object(self.probe,'CASE_CAP',6.15),self.probe._without_acceptance():
            result=self.probe._case(self.root/'early_exit','early_exit','b'*32,'a'*64,'c'*64,time.monotonic()+20)
        self.assertIn('TimeoutExpired',result['error'])
        self.assertLess(time.monotonic()-started,6.15)
        self.assertEqual(len(self.calls),1)
        self.assertTrue(result['group_gone']);self.assertTrue(result['reaped'])
        self.assertTrue(self.calls[0].stdout.closed)
        with self.assertRaises(ProcessLookupError):os.killpg(self.calls[0].pid,0)

    def test_missing_early_stderr_fails_with_real_exit_and_no_retry(self):
        self.wrapper.write_text('exec 3>/dev/null\n"$@" 3>&- 2>/dev/null\n')
        with self.boundary():result=self.probe.run_probe(self.root/'out')
        self.assertEqual(result['status'],'FAILED_OR_INCOMPLETE')
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.calls[1].returncode,73)
        self.assertIn('missing early stderr',result['error'])

    def test_serialization_failure_preserves_initiating_error_and_bounded_ledger(self):
        def corrupt(argv):
            result=list(argv);result[result.index('--nonce')+1]='c'*64;return result
        with self.boundary(mutate=corrupt),patch.object(self.probe,'_encode',side_effect=TypeError('serialization fixture')):
            result=self.probe.run_probe(self.root/'out')
        self.assertEqual(result['status'],'FAILED_OR_INCOMPLETE')
        self.assertIn('ValueError',result['error'])
        self.assertIn('TypeError',result['publication_error'])
        self.assertEqual(len(self.calls),1)
        self.assertEqual(json.loads((self.root/'out/probe.json').read_text()),result)
        self.assertLessEqual(sum(p.stat().st_size for p in (self.root/'out').rglob('*') if p.is_file()),2097152)

    def test_parent_forbidden_import_guard_fails_before_context_or_launch(self):
        with patch.dict(sys.modules,{'onnxruntime.fixture':object()}),self.boundary():
            with self.assertRaisesRegex(ValueError,'runtime module'):
                self.probe.run_probe(self.root/'out')
        self.assertEqual(self.calls,[])
        self.assertFalse((self.root/'out').exists())


    def test_source_preflight_respects_total_deadline_before_any_launch(self):
        clock=[0.]
        def slow_git(*args,**kwargs):
            if args[0]=='show':clock[0]+=20.
            return self.git(*args,**kwargs)
        with patch.object(self.probe.time,'monotonic',side_effect=lambda:clock[0]), \
             patch.object(self.probe,'_git',side_effect=slow_git),self.boundary():
            with self.assertRaises(subprocess.TimeoutExpired):self.probe.run_probe(self.root/'out')
        self.assertEqual(self.calls,[])
        self.assertFalse((self.root/'out').exists())


    def test_changed_production_command_cannot_cross_substitution_boundary(self):
        launch=model._launch_trial
        def changed(*args,**kwargs):
            values=list(args);values[3]='proxy'
            return launch(*values,**kwargs)
        with self.boundary(),patch.object(model,'_launch_trial',side_effect=changed):
            result=self.probe.run_probe(self.root/'out')
        self.assertEqual(result['status'],'FAILED_OR_INCOMPLETE')
        self.assertIn('unexpected production command/kwargs',result['error'])
        self.assertEqual(self.calls,[])


    def test_validator_rejects_enormous_numeric_deadline_as_value_error(self):
        result=self.run_ok();result['elapsed_s']=10**1000;self.rewrite(result)
        try:self.probe.validate_probe(self.root/'out')
        except Exception as exc:self.assertIsInstance(exc,ValueError)
        else:self.fail('unbounded deadline accepted')

    def retained_reader_wrapper(self, delay):
        # Model the released wrapper's asynchronous TERM-without-wait teardown.
        # The helper inherits the actual permit FD and never reads it.
        helper=self.root/'retained-reader.py'
        helper.write_text('''import os, signal, sys, time
from pathlib import Path
def stop(signum, frame):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(float(sys.argv[1]))
    Path(sys.argv[3]).write_text('TERM_COMPLETED')
    os._exit(0)
signal.signal(signal.SIGTERM, stop)
Path(sys.argv[2]).write_text(str(os.getpid()))
while True: signal.pause()
''')
        # Fixture paths come from TemporaryDirectory and contain no shell chars.
        self.wrapper.write_text(
            'exec 3>/dev/null\n'
            f'ready="{self.root}/$5.ready"\ndone="{self.root}/$5.done"\n'
            f'"$1" "{helper}" "{delay}" "$ready" "$done" &\n'
            'reader=$!\n'
            'while [ ! -f "$ready" ]; do sleep 0.01; done\n'
            '"$@" 3>&-\nstatus=$?\n'
            'kill -TERM "$reader"\nexit "$status"\n')

    def test_early_exit_passively_reaps_retained_reader_before_delivery(self):
        self.retained_reader_wrapper(.5)
        cleanup=model._terminate_group;cleanup_after_completion=[]
        def raw_cleanup(process):
            case='normal' if process is self.calls[0] else 'early_exit'
            cleanup_after_completion.append((case,(self.root/(case+'.done')).exists()))
            return cleanup(process)
        with self.boundary(),patch.object(model,'_terminate_group',side_effect=raw_cleanup):
            result=self.probe.run_probe(self.root/'out')
        early=result['cases'][1]
        log=(self.root/'out/early_exit/process.log').read_bytes()
        with self.subTest(check='actual EPIPE'):
            self.assertEqual(early['delivery_error'],'BrokenPipeError')
        with self.subTest(check='no successful delivery'):
            self.assertNotIn(b'phase=permit_sent',log)
        with self.subTest(check='passive completion before production cleanup'):
            self.assertEqual(cleanup_after_completion,[('normal',True),('early_exit',True)])
        self.assertEqual(result['status'],'TRANSPORT_ASSOCIATION_VALIDATED')
        self.assertEqual(self.probe.validate_probe(self.root/'out'),result)
        self.assertEqual(early['exit_code'],73)
        self.assertIn(b'FIRST_DIVERGENCE_PROBE_EARLY_EXIT_73',log)
        self.assertEqual(len(self.calls),2)
        for row,process in zip(result['cases'],self.calls):
            self.assertTrue(row['group_gone']);self.assertTrue(row['reaped'])
            self.assertTrue(process.stdout.closed)
            reader=int((self.root/(row['case']+'.ready')).read_text())
            with self.assertRaises(ProcessLookupError):os.kill(reader,0)
            with self.assertRaises(ChildProcessError):os.waitpid(reader,os.WNOHANG)
            with self.assertRaises(ProcessLookupError):os.killpg(process.pid,0)

    def test_retained_reader_deadline_fails_before_handle_transfer_and_reaps(self):
        self.retained_reader_wrapper(30)
        started=time.monotonic()
        with self.boundary(),patch.object(self.probe,'CASE_CAP',6.4),self.probe._without_acceptance():
            result=self.probe._case(self.root/'early_exit','early_exit','b'*32,'a'*64,'c'*64,time.monotonic()+20)
        self.assertIn('TimeoutExpired',result['error'])
        self.assertIsNone(result['wait_timeout_s'],'adapter still owns the handle at passive-wait expiry')
        self.assertIsNone(result['delivery_error'])
        self.assertEqual(result['exit_code'],73)
        self.assertLess(time.monotonic()-started,6.4)
        self.assertEqual(len(self.calls),1)
        self.assertFalse((self.root/'early_exit.done').exists())
        self.assertTrue(result['group_gone']);self.assertTrue(result['reaped'])
        self.assertTrue(self.calls[0].stdout.closed)
        reader=int((self.root/'early_exit.ready').read_text())
        with self.assertRaises(ProcessLookupError):os.kill(reader,0)
        with self.assertRaises(ChildProcessError):os.waitpid(reader,os.WNOHANG)
        with self.assertRaises(ProcessLookupError):os.killpg(self.calls[0].pid,0)


if __name__ == '__main__':
    unittest.main()
