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


if __name__ == '__main__':
    unittest.main()
