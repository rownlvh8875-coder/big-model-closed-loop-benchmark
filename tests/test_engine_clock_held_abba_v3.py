"""New phase authority and honest producer/control metadata, CPU-only."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
try:
    from scripts import engine_clock_held_abba_v3 as n
except ImportError:n=None
ROOT=Path(__file__).resolve().parents[1]


def approval():
    return dict(canary_head_sha='2'*40,source_sha='1'*40,run_id=21,workflow_id=31,job_id=41,
        artifact_id=51,artifact_name=n.artifact('canary'),artifact_size_bytes=1234,artifact_sha256='a'*64,
        attestor_job_id=42,attestor_artifact_id=52,attestor_artifact_name=n.artifact('attestation'),
        attestor_artifact_size_bytes=987,attestor_artifact_sha256='b'*64,lease_sha256='c'*64,
        root_raw_accepted=True,fresh_raw_review_accepted=True)


def request(mode='canary'):
    return dict(schema=n.REQUEST_SCHEMA,mode=mode,acceptance=None if mode=='canary' else approval(),
        request_id=n.ID,repository=n.REPOSITORY,branch=n.BRANCH,workflow_path=n.WORKFLOW,
        reviewed_source_branch=n.SOURCE_BRANCH,reviewed_source_sha='1'*40,
        source_closure={p:'0'*64 for p in n.source_paths(ROOT)},
        source_ci=[dict(event='push',run_id=11),dict(event='pull_request',run_id=12)],
        budget=copy.deepcopy(n.BUDGET),lifecycle=copy.deepcopy(n.LIFECYCLE),native_budget=n.native_budget(mode),
        image_evidence=n.image_evidence(ROOT),official_model_calls=0,ort_sessions=0)


def context(mode='canary'):
    return dict(repository=n.REPOSITORY,event='push',attempt=1,run_id=21,workflow_id=31,job_id=41,
        head_sha='2'*40,producer_head_sha='2'*40,control_head_sha='2'*40 if mode=='canary' else '3'*40,
        source_sha='1'*40,producer_request_sha256=n.sha(n.canonical(request())),
        request_sha256=n.sha(n.canonical(request(mode))),lease_sha256='c'*64,
        source_closure_verified=True,authenticated_api_origin='https://api.github.com',mode=mode)


def completion():
    a=approval()
    run=dict(id=21,head_sha='2'*40,head_branch=n.BRANCH,workflow_id=31,path=n.WORKFLOW,
        event='push',run_attempt=1,status='in_progress',conclusion=None,repository=dict(id=7,full_name=n.REPOSITORY))
    def job(jid,name,status,conclusion):
        return dict(id=jid,name=name,run_id=21,head_sha='2'*40,run_attempt=1,status=status,conclusion=conclusion,steps=[])
    host=job(41,'native-host','in_progress',None)
    host['steps']=[dict(name=name,number=i,status='completed',conclusion='success') for i,name in enumerate((n.C_STEP,n.C_UPLOAD),1)]
    attest=job(42,'canary-attestor','completed','success')
    jobs=dict(total_count=2,jobs=[host,attest])
    def artifact(aid,name,size,sha):
        return dict(id=aid,name=name,size_in_bytes=size,digest='sha256:'+sha,expired=False,
            workflow_run=dict(id=21,head_sha='2'*40,head_branch=n.BRANCH,repository_id=7))
    return a,run,jobs,artifact(51,n.artifact('canary'),1234,'a'*64),artifact(52,n.artifact('attestation'),987,'b'*64)


class HeldProtocolTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(n,'retained-host phase authority missing')

    def test_direct_parent_separate_control_addition_preserves_producer(self):
        c=request();a=request('abba')
        n.validate_activation(c,'2'*40,['1'*40],b'A\0'+n.C_REQUEST.encode()+b'\0','100644',n.BRANCH)
        n.validate_activation(a,'3'*40,['2'*40],b'A\0'+n.A_REQUEST.encode()+b'\0','100644',n.BRANCH)
        for delta in (b'M\0'+n.C_REQUEST.encode()+b'\0',b'A\0'+n.A_REQUEST.encode()+b'\0A\0other\0'):
            with self.assertRaises(ValueError):n.validate_activation(a,'3'*40,['2'*40],delta,'100644',n.BRANCH)
        with self.assertRaises(ValueError):n.validate_activation(a,'3'*40,['4'*40],b'A\0'+n.A_REQUEST.encode()+b'\0','100644',n.BRANCH)

    def test_request_counts_and_old_or_false_authority_reject(self):
        for mode,count,getters in [('canary',1,144),('abba',4,384)]:
            r=request(mode);n.validate_request(r,ROOT)
            self.assertEqual((count,getters),(r['native_budget']['providers'],r['native_budget']['observer_getters']))
        for key,value in [('fresh_raw_review_accepted',1),('root_raw_accepted',False),('attestor_job_id',41),('artifact_name','engine-clock-sealed-abba-20261114-02'),('lease_sha256','invalid')]:
            bad=request('abba');bad['acceptance'][key]=value
            with self.assertRaises(ValueError):n.validate_request(bad,ROOT)
        bad=request();bad['lifecycle']['control_seconds']+=1
        with self.assertRaises(ValueError):n.validate_request(bad,ROOT)

    def test_completed_attestor_and_native_upload_steps_required_while_host_held(self):
        proof=completion();n.validate_completion_api(*proof,workflow_id=31)
        for index,key,value in [(1,'status','completed'),(1,'head_sha','3'*40),(3,'expired',True),(4,'digest','sha256:'+'9'*64)]:
            bad=copy.deepcopy(proof);bad[index][key]=value
            with self.assertRaises(ValueError):n.validate_completion_api(*bad,workflow_id=31)
        for status,conclusion in [('in_progress',None),('completed','failure')]:
            bad=copy.deepcopy(proof);bad[2]['jobs'][1].update(status=status,conclusion=conclusion)
            with self.assertRaises(ValueError):n.validate_completion_api(*bad,workflow_id=31)
        for i in (0,1):
            bad=copy.deepcopy(proof);bad[2]['jobs'][0]['steps'][i].update(status='in_progress',conclusion=None)
            with self.assertRaises(ValueError):n.validate_completion_api(*bad,workflow_id=31)

    def test_effective_A_request_never_relabels_actual_C_checkout(self):
        producer=n.canonical(request())
        for mode in ('canary','abba'):
            binding=dict(request=request(mode),producer_request=request(),context=context(mode))
            n.validate_binding_requests(binding,producer,ROOT)
            bad=copy.deepcopy(binding);bad['context']['head_sha']='3'*40
            with self.assertRaises(ValueError):n.validate_binding_requests(bad,producer,ROOT)
        with self.assertRaises(ValueError):n.validate_binding_requests(binding,n.canonical(request('abba')),ROOT)

    def test_control_tree_and_blob_must_add_only_A_request(self):
        raw=n.canonical(request('abba'));blob=n.git_blob_sha(raw)
        tree=dict(sha='7'*40,truncated=False,tree=[dict(path=n.A_REQUEST,mode='100644',type='blob',sha=blob)])
        n.validate_control_tree(tree,'7'*40,blob)
        for key,value in [('mode','120000'),('type','tree'),('sha','8'*40)]:
            bad=copy.deepcopy(tree);bad['tree'][0][key]=value
            with self.assertRaises(ValueError):n.validate_control_tree(bad,'7'*40,blob)
        bad=copy.deepcopy(tree);bad['truncated']=True
        with self.assertRaises(ValueError):n.validate_control_tree(bad,'7'*40,blob)
        commit=dict(sha='3'*40,parents=[dict(sha='2'*40)])
        compare=dict(status='ahead',ahead_by=1,behind_by=0,total_commits=1,base_commit=dict(sha='2'*40),merge_base_commit=dict(sha='2'*40),commits=[dict(sha='3'*40)],files=[dict(filename=n.A_REQUEST,status='added',sha=blob)])
        n.validate_control_delta(request(),request('abba'),'3'*40,commit,compare,blob,raw)
        for field,value in [('filename','scripts/injected.py'),('status','modified'),('sha','8'*40)]:
            bad=copy.deepcopy(compare);bad['files'][0][field]=value
            with self.assertRaises(ValueError):n.validate_control_delta(request(),request('abba'),'3'*40,commit,bad,blob,raw)
        with self.assertRaises(ValueError):n.validate_control_delta(request(),request('abba'),'3'*40,commit,compare,blob,raw+b' ')




class PhaseTreeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(n is not None and callable(getattr(n,'audit_phase_members',None)),'mode-specific phase member auditor missing')

    def recorded_tree(self,root):
        p=ROOT/'docs/evidence/engine-clock-held-abba-02/abba/engine-clock-held-abba-20261114-02-abba.members.json'
        rows=[r for r in json.loads(p.read_bytes())['entries'] if r['path'].startswith('output/')]
        for row in rows:
            path=root/row['path'][7:];path.parent.mkdir(parents=True,exist_ok=True)
            # Deliberately sparse stat fixtures: no claim of actual capture bytes.
            with path.open('wb') as f:f.truncate(row['nbytes'])

    def test_real_170_file_shape_fits_A_while_frozen_guard_still_rejects(self):
        from scripts import engine_clock_native as legacy
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.recorded_tree(root)
            with self.assertRaisesRegex(ValueError,'dataset byte/member cap'):legacy._members(root,192*1024**2)
            result=n.audit_phase_members(root,'abba')
            self.assertEqual(170,result['files']);self.assertEqual(65433113,result['nbytes_before_final_phase_ledger'])
            self.assertEqual(198,result['entries']);self.assertTrue(result['before_final_phase_ledger'])

    def test_C_retains_129_file_cap(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.recorded_tree(root)
            with self.assertRaisesRegex(ValueError,'files'):n.audit_phase_members(root,'canary')

    def test_A_257th_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'phase.json').write_bytes(b'{}')
            for i in range(256):(root/('record-%03d'%i)).write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'files'):n.audit_phase_members(root,'abba')

    def test_byte_overflow_rejected_without_reading_sparse_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'phase.json').write_bytes(b'{}')
            with (root/'oversize').open('wb') as f:f.truncate(201326593)
            with self.assertRaisesRegex(ValueError,'bytes'):n.audit_phase_members(root,'abba')

    def test_traversal_limit_precedes_empty_directory_registration(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'phase.json').write_bytes(b'{}')
            for i in range(512):(root/('empty-%03d'%i)).mkdir()
            with self.assertRaisesRegex(ValueError,'entries'):n.audit_phase_members(root,'abba')

    def test_symlink_and_hardlink_are_rejected(self):
        for kind in ('symlink','hardlink'):
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);(root/'phase.json').write_bytes(b'{}')
                if kind=='symlink':(root/'alias').symlink_to(root/'phase.json')
                else:os.link(root/'phase.json',root/'alias')
                with self.assertRaisesRegex(ValueError,'entry-type'):n.audit_phase_members(root,'abba')

    def test_empty_directory_and_unknown_mode_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'phase.json').write_bytes(b'{}');(root/'empty').mkdir()
            with self.assertRaisesRegex(ValueError,'directories'):n.audit_phase_members(root,'abba')
            with self.assertRaises(ValueError):n.audit_phase_members(root,'unknown')

if __name__=='__main__':unittest.main()
