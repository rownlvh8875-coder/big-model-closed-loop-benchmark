"""Read-only fixtures; no live namespace or privileged process."""
import copy
import ctypes
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

try:
    from scripts import engine_clock_namespace_identity as obs
except ImportError:
    obs = None


class FakeSystem:
    def __init__(self, result=0, error=0): self.result, self.error, self.calls = result, error, []
    def snapshot(self):
        self.calls.append('snapshot')
        return {'namespace': None, 'index': len(self.calls), 'pid': 42}
    def invoke(self, flags):
        self.calls.append(flags)
        return {'returncode': self.result, 'errno': self.error, 'flags': flags}


class IdentityTests(unittest.TestCase):
    def setUp(self): self.assertIsNotNone(obs, 'post-unshare identity observer missing')

    def test_after_state_retained_when_namespace_unreadable_or_unchanged(self):
        backend = FakeSystem()
        value = obs.worker('RAW_USER_NET', backend)
        self.assertEqual(['snapshot', 1342177280, 'snapshot'], backend.calls)
        self.assertEqual(3, value['after']['index'])
        self.assertEqual(0, value['syscall']['returncode'])
        self.assertFalse(value['admission'])

    def test_failed_syscall_still_retains_after_and_numeric_errno(self):
        value = obs.worker('RAW_USER_NET', FakeSystem(-1, 1))
        self.assertEqual(1, value['syscall']['errno'])
        self.assertIn('after', value)
        self.assertFalse(value['admission'])

    def test_noop_and_snapshot_controls_do_not_request_new_namespaces(self):
        for case, calls in [('NOOP', ['snapshot', 0, 'snapshot']), ('SNAPSHOT', ['snapshot', 'snapshot'])]:
            backend=FakeSystem(); value=obs.worker(case,backend)
            self.assertEqual(calls,backend.calls)
            self.assertIn('after',value)
        backend=FakeSystem()
        with self.assertRaisesRegex(ValueError, '^INVALID_CASE$'): obs.worker('SECRET_SENTINEL',backend)
        self.assertEqual([],backend.calls)

    def test_typed_unshare_clears_stale_errno_and_uses_int_abi(self):
        class Function:
            def __call__(inner, flags):
                self.assertEqual(0,ctypes.get_errno())
                self.assertEqual(1342177280,flags)
                return 0
        class Lib: unshare=Function()
        ctypes.set_errno(99)
        value=obs.typed_unshare(Lib,1342177280)
        self.assertEqual({'flags':1342177280,'returncode':0,'errno':0},value)
        self.assertEqual([ctypes.c_int],Lib.unshare.argtypes)
        self.assertIs(ctypes.c_int,Lib.unshare.restype)

    def test_proc_snapshot_keeps_readlink_and_numeric_stat_open_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'self/ns').mkdir(parents=True);(p/'self/attr').mkdir()
            (p/'self/ns/user').symlink_to('user:[1234]')
            (p/'self/uid_map').write_text('0 1001 1\nSECRET_SENTINEL\n')
            (p/'self/gid_map').write_text('0 1001 1\n')
            (p/'self/attr/current').write_bytes(b'unconfined\xff')
            result=obs.snapshot(p)
            n=result['namespace_details']['self/user']
            self.assertEqual('user:[1234]',n['readlink'])
            self.assertEqual(2,n['stat_errno'])
            self.assertEqual(2,n['open_errno'])
            self.assertEqual([[0,1001,1]],result['maps']['uid_map'])
            self.assertIsNone(result['facts']['profile']['known'])
            self.assertNotIn('SECRET_SENTINEL',json.dumps(result))

    def test_unknown_namespace_link_is_hashed_not_echoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ns';p.symlink_to('SECRET_SENTINEL')
            value=obs.namespace_detail(p,'user')
            self.assertIsNone(value['readlink'])
            self.assertNotIn('SECRET_SENTINEL',json.dumps(value))
            self.assertEqual(hashlib.sha256(b'SECRET_SENTINEL').hexdigest(),value['readlink_sha256'])

    def test_journal_empty_and_malformed_remain_unknown(self):
        for raw in (b'',b'not json\n',b'{"MESSAGE":7}\n'):
            value=obs.parse_journal(raw,{42})
            self.assertEqual('UNKNOWN',value['availability'])
            self.assertEqual([],value['observations'])

    def test_journal_keeps_matching_userns_and_capability_fixed_fields_only(self):
        message='apparmor="DENIED" operation="userns_create" profile="unconfined" pid=42 comm="SECRET_SENTINEL"'
        raw=(json.dumps({'MESSAGE':message})+'\n'+json.dumps({'MESSAGE':message.replace('pid=42','pid=420')})+'\n').encode()
        value=obs.parse_journal(raw,{42})
        self.assertEqual('READ_COMPLETE_WITH_RECORDS',value['availability'])
        self.assertEqual(1,len(value['observations']))
        self.assertEqual('userns_create',value['observations'][0]['operation'])
        self.assertNotIn('SECRET_SENTINEL',json.dumps(value))

    def test_fixed_commands_use_installed_unshare_and_no_credentials(self):
        root=Path('/fixture')
        args=obs.commands(root)
        self.assertEqual(3,len(args))
        self.assertEqual('/usr/bin/unshare',args[2][1][0])
        self.assertEqual(['--user','--map-root-user','--net','--'],args[2][1][1:5])
        self.assertTrue(all('/usr/bin/python3' in argv for _,argv in args))

    def test_request_only_activation_and_old_request_rejection(self):
        value={'schema':'namespace-identity-request-v1','request_id':'namespace-diagnostic-20261113-02',
               'repository':'rownlvh8875-coder/big-model-closed-loop-benchmark','branch':'diagnose/engine-clock-namespace-20261113-02',
               'workflow_path':'.github/workflows/engine-clock-namespace-identity.yml','reviewed_source_sha':'1'*40,
               'budget':{'runs':1,'attempts':1,'workers':3},'source_closure':{p:'0'*64 for p in obs.CLOSURE}}
        self.assertEqual(value,obs.validate_request(value))
        for key,bad in [('request_id','namespace-diagnostic-20261113-01'),('budget',{'runs':2,'attempts':1,'workers':3}),('extra','SECRET_SENTINEL')]:
            d=copy.deepcopy(value);d[key]=bad
            with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'): obs.validate_request(d)
        prior={'truncated':False,'tree':[]};current={'sha':'3'*40,'truncated':False,'tree':[{'path':obs.REQUEST_PATH,'type':'blob','mode':'100644','sha':'4'*40}]}
        commit={'sha':'2'*40,'parents':[{'sha':'1'*40}],'tree':{'sha':'3'*40}}
        self.assertIsNone(obs.validate_activation(value,'2'*40,current,prior,commit))
        for mutation in ('merge','extra','existing','symlink'):
            a,b,c=copy.deepcopy(current),copy.deepcopy(prior),copy.deepcopy(commit)
            if mutation=='merge': c['parents'].append({'sha':'5'*40})
            elif mutation=='extra': a['tree'].append({'path':'other','type':'blob','mode':'100644','sha':'6'*40})
            elif mutation=='existing': b['tree']=copy.deepcopy(a['tree'])
            else: a['tree'][0]['mode']='120000'
            with self.assertRaisesRegex(ValueError,'^INVALID_ACTIVATION$'): obs.validate_activation(value,'2'*40,a,b,c)

if __name__=='__main__':unittest.main()
