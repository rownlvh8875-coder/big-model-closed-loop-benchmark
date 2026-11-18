"""Portable admission/archive regressions; fixtures are never native evidence."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from bigbench import recorded_official_execution as c
from scripts import run_recorded_official as host


class AdmissionTests(unittest.TestCase):
    def test_unattested_current_run_and_unapproved_source_are_not_admitted(self):
        request,context,manifest,ci=self.good()
        with self.assertRaises(ValueError):host.validate_admission(request,context,manifest=manifest,ci=ci)
    def good(self):
        source='a'*40;head='b'*40
        manifest={'scripts/example.py':'c'*64}
        request=dict(schema='recorded-official-request-v1',active=True,mode=c.MODE,
            limits=dict(c.LIMITS),case=dict(seed=c.CASE[0],scenario=c.CASE[1]),source=source,
            push_ci=12,pr_ci=13,aux_ci=dict(windows_push=14,windows_pr=15,software_api_pr=16),source_map=manifest,approval_sha='e'*40)
        context=dict(attempt=1,event='push',branch=c.BRANCH,env_head=head,head=head,
            parents=[source],delta=['M\t'+c.REQUEST],repository='rownlvh8875-coder/big-model-closed-loop-benchmark',run_id='987')
        ci={}
        for event,runid in (('push',12),('pull_request',13)):
            ci[event]=dict(run=dict(id=runid,head_sha=source,head_branch=host.FEATURE,event=event,workflow_id=411705464,
                run_attempt=1,conclusion='success',status='completed',head_repository=dict(full_name=context['repository'])),
                jobs=dict(total_count=2,jobs=[dict(name=n,conclusion='success',status='completed') for n in ('synthetic-unit','onnx-interface-test')]),
                artifacts=dict(total_count=0,artifacts=[]))
        for role,workflow,event in (('windows_push',421897387,'push'),('windows_pr',421897387,'pull_request'),('software_api_pr',422015100,'pull_request')):
            ci[role]=dict(run=dict(id=request['aux_ci'][role],head_sha=source,head_branch=host.FEATURE,event=event,workflow_id=workflow,run_attempt=1,status='completed',conclusion='success',head_repository=dict(full_name=context['repository'])),jobs=dict(total_count=1,jobs=[dict(status='completed',conclusion='success')]),artifacts=dict(total_count=0,artifacts=[]))
        return request,context,manifest,ci

    def external(self,r,x,m,ci):
        authority=dict(ref=dict(ref='refs/heads/'+c.APPROVAL_BRANCH,object=dict(type='commit',sha=r['approval_sha'])),
            commit=dict(sha=r['approval_sha'],parents=[dict(sha=r['source'])],files=[dict(filename=c.APPROVAL_PATH,status='added')]),
            document=dict(schema='recorded-official-reviewed-source-approval-v1',source=r['source'],source_map=m,
                push_ci=r['push_ci'],pr_ci=r['pr_ci'],request_path=c.REQUEST,mode=c.MODE,limits=c.LIMITS,aux_ci=r['aux_ci']))
        current=dict(id=int(x['run_id']),workflow_id=98765,path=c.WORKFLOW,head_sha=x['head'],head_branch=c.BRANCH,
            event='push',run_attempt=1,head_repository=dict(full_name=x['repository']))
        history=dict(total_count=1,workflow_runs=[current])
        return dict(authority=authority,current=current,history=history)

    def test_only_exact_request_source_and_four_ci_jobs_are_admitted(self):
        r,x,m,ci=self.good()
        external=self.external(r,x,m,ci)
        self.assertEqual(host.validate_admission(r,x,manifest=m,ci=ci,**external)['source'],r['source'])
        for changes in ({'attempt':2},{'event':'workflow_dispatch'},{'branch':host.FEATURE},{'env_head':'c'*40},
                        {'parents':[]},{'parents':[r['source'],'d'*40]},{'delta':['M\tbigbench/image_adapter.py']},
                        {'run_id':None},{'head':'g'*40}):
            bad=dict(x,**changes)
            with self.subTest(context=changes),self.assertRaises(ValueError):host.validate_admission(r,bad,manifest=m,ci=ci,**external)
        for changes in ({'mode':'CAMERA_ONLY_NO_GRAPH'},{'active':False},{'limits':dict(c.LIMITS,official_models=2)},
                        {'limits':dict(c.LIMITS,official_models=False)},{'source_map':{}},{'source':'z'*40}):
            with self.subTest(request=changes),self.assertRaises(ValueError):host.validate_admission(dict(r,**changes),x,manifest=m,ci=ci,**external)
        for mutate in (lambda d:d['push']['run'].update(head_sha='d'*40),
                       lambda d:d['pull_request']['run'].update(run_attempt=2),
                       lambda d:d['push']['run'].update(workflow_id=123),
                       lambda d:d['push']['run']['head_repository'].update(full_name='fork/repo'),
                       lambda d:d['push']['jobs']['jobs'][0].update(conclusion='failure'),
                       lambda d:d['pull_request']['artifacts'].update(total_count=1)):
            bad=copy.deepcopy(ci);mutate(bad)
            with self.assertRaises(ValueError):host.validate_admission(r,x,manifest=m,ci=bad,**external)
        for mutate in (lambda d:d['current'].update(id=123),lambda d:d['current'].update(path='.github/workflows/ci.yml'),
                       lambda d:d['current'].update(head_sha='f'*40),lambda d:d['history'].update(total_count=2),
                       lambda d:d['authority']['document'].update(source_map={}),
                       lambda d:d['authority']['ref']['object'].update(sha='f'*40)):
            bad=copy.deepcopy(external);mutate(bad)
            with self.assertRaises(ValueError):host.validate_admission(r,x,manifest=m,ci=ci,**bad)

    def test_mounted_source_map_cannot_omit_change_or_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'source.py';path.write_bytes(b'original')
            mapping={'source.py':hashlib.sha256(b'original').hexdigest()}
            c.check_source_map(root,mapping)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):c.check_source_map(root,mapping)
            for name in ('../source.py','/source.py','C:/source.py','a\\b.py'):
                with self.assertRaises(ValueError):c.check_source_map(root,{name:'a'*64})
            if os.name!='nt':
                path.unlink();outside=root/'outside';outside.write_bytes(b'original');path.symlink_to(outside)
                with self.assertRaises(ValueError):c.check_source_map(root,mapping)

    def test_inactive_workflow_is_branch_path_scoped_and_has_no_model_phase(self):
        text=(host.ROOT/c.WORKFLOW).read_text()
        self.assertIn("branches: ['"+c.BRANCH+"']",text)
        self.assertIn("paths: ['"+c.REQUEST+"']",text)
        self.assertNotIn('workflow_dispatch',text)
        self.assertIn('recorded_official.py run',text)
        self.assertIn('if: always()',text)
        request=json.loads((host.ROOT/c.REQUEST).read_text())
        # On feature/source CI this placeholder must never be active.
        if os.environ.get('GITHUB_REF_NAME')!=c.BRANCH:self.assertIs(request['active'],False)


class ActiveRunTests(unittest.TestCase):
    def test_unknown_active_run_and_incomplete_or_duplicate_pages_fail_closed(self):
        rows=[dict(id=987,workflow_id=411705464,status='in_progress'),dict(id=2,workflow_id=123,status='in_progress')]
        for pages in ([dict(total_count=2,workflow_runs=rows)], [dict(total_count=3,workflow_runs=rows)],
                      [dict(total_count=2,workflow_runs=[rows[0],rows[0]])]):
            with self.assertRaises(ValueError):c.validate_public_activity(pages,current_id=987)
        rows[1]['status']='completed'
        self.assertEqual(c.validate_public_activity([dict(total_count=2,workflow_runs=rows)],current_id=987)['unknown_active_runs'],[])
        for status in ('queued','in_progress','waiting','pending','requested',None,'surprise'):
            rows[1]['status']=status
            with self.subTest(status=status),self.assertRaises(ValueError):c.validate_public_activity([dict(total_count=2,workflow_runs=rows)],current_id=987)
    def test_only_current_and_three_standard_workflows_are_allowed_active(self):
        rows=[dict(id=987,workflow_id=9,status='in_progress')]+[dict(id=n,workflow_id=n,status='queued') for n in (411705464,421897387,422015100)]
        result=c.validate_public_activity([dict(total_count=4,workflow_runs=rows)],current_id=987)
        self.assertFalse(result['private_task_observable'])

class BoundsTests(unittest.TestCase):
    def test_absent_lifecycle_is_unknown_and_pending_constructor_is_not_zero(self):
        self.assertEqual(c.activity_bounds(None),dict(official_model_process_bounds=[0,1],official_inference_bounds=[0,600]))
        self.assertEqual(c.activity_bounds(dict(policy_constructor_entered=True,policy_created=False,inference_bounds=[0,0])),dict(official_model_process_bounds=[0,1],official_inference_bounds=[0,0]))
        self.assertEqual(c.activity_bounds(dict(policy_constructor_entered=True,policy_created=True,inference_bounds=[3,4])),dict(official_model_process_bounds=[1,1],official_inference_bounds=[3,4]))
        for life in (dict(policy_constructor_entered=False,policy_created=True,inference_bounds=[0,0]),dict(policy_constructor_entered=True,policy_created=True,inference_bounds=[0,601]),dict(policy_constructor_entered=1,policy_created=True,inference_bounds=[0,0])):
            with self.assertRaises(ValueError):c.activity_bounds(life)
    def test_cold_plan_never_imports_native_or_model_runtime(self):
        import subprocess
        proc=subprocess.run([sys.executable,'-I','-S','-B',str(host.ROOT/'scripts/run_recorded_official.py'),'plan'],capture_output=True,text=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stderr)
        value=json.loads(proc.stdout);self.assertEqual(value['heavy_modules_loaded'],[]);self.assertFalse(value['execution_activated'])
        self.assertEqual(value['limits']['official_models'],1)

if __name__=='__main__':unittest.main()
