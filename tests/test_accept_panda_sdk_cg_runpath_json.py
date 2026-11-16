import copy,json,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from scripts import accept_panda_sdk_cg_runpath_json as receiver
from scripts import panda_sdk_cg_runpath_json as j
from scripts import panda_sdk_cg_runpath_carrier as carrier
from tests import test_panda_sdk_link_image as image_fixtures

API=j.ROOT/'docs/evidence/panda-sdk-cg-runpath-candidate-03/actual/acceptance/api'

class MemoryClient:
    def __init__(self,mutate=None):self.mutate=mutate;self.calls=[]
    def get_json(self,path,name):
        self.calls.append(path);value=json.loads((API/name).read_text())
        if self.mutate:self.mutate(name,value)
        return value

def toy_carrier(root):
    candidate=root/'candidate';candidate.mkdir();archive=root/'toy.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for name in sorted(carrier.FILES):
            raw=b'x'*128 if name=='candidate/layout-descriptor.data' else b'{}' if name.startswith('reports/') else b'toy DATA'
            path=candidate/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);z.writestr(name,raw)
    pin=dict(artifact_zip_nbytes=archive.stat().st_size,artifact_zip_sha256=j.sha(archive.read_bytes()))
    return archive,candidate,pin

class ReceiverTests(unittest.TestCase):
    def child(self, code, out):
        process=subprocess.run([sys.executable,'-B','-c',code,str(out)],cwd=j.ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(process.returncode,0,process.stdout+process.stderr)
        saved=json.loads((out/'acceptance.json').read_text())
        self.assertEqual(saved['status'],'FAILED');self.assertFalse(saved['actions_output_origin_authenticated']);self.assertFalse(saved['selected_static_accepted'])
    def test_fresh_process_import_failure_still_has_negative_receipt(self):
        code="""
import os,sys
from pathlib import Path
original=os.open
def blocked(path,*args,**kwargs):
    if str(path).endswith('docs/evidence/panda-sdk-cg-residual-01/contract.json'):
        raise OSError('fixture frozen-contract import unavailable')
    return original(path,*args,**kwargs)
os.open=blocked
from scripts import accept_panda_sdk_cg_runpath_json as receiver
result=receiver.audit('f'*40,[],Path(sys.argv[1]))
assert result['status']=='FAILED' and not result['actions_output_origin_authenticated']
"""
        with tempfile.TemporaryDirectory() as d:self.child(code,Path(d)/'audit')
    def test_final_write_failure_retains_parseable_negative_receipt(self):
        code="""
import json,resource,signal,sys
from pathlib import Path
from unittest.mock import patch
from scripts import accept_panda_sdk_cg_runpath_json as receiver
signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
def block_final_write(source):
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,resource.getrlimit(resource.RLIMIT_FSIZE)[1]))
    raise ValueError('fixture failure after initial receipt')
with patch.object(receiver,'verify_audit_source',side_effect=block_final_write):
    result=receiver.audit('a'*40,[],Path(sys.argv[1]))
saved=json.loads((Path(sys.argv[1])/'acceptance.json').read_text())
assert result==saved and saved['status']=='FAILED' and not saved['selected_static_accepted']
assert sorted(p.name for p in Path(sys.argv[1]).iterdir())==['acceptance.json']
"""
        with tempfile.TemporaryDirectory() as d:self.child(code,Path(d)/'audit')
    def test_exact_existing_origin_metadata_no_network_mutation(self):
        client=MemoryClient();result=receiver.authenticate_producer(client);self.assertEqual(result['run']['id'],43786081196);self.assertEqual(result['artifact']['id'],14191115165);self.assertEqual(result['job']['id'],133033912459);self.assertTrue(client.calls);self.assertTrue(all(not path.startswith('dispatch') for path in client.calls))
    def test_wrong_original_origin_cannot_substitute(self):
        mutations=[('live-run.json',lambda x:x.update(run_attempt=2)),('live-run.json',lambda x:x.update(head_sha='f'*40)),('build-jobs.json',lambda x:x['jobs'][0].update(id=1)),('artifacts.json',lambda x:x['artifacts'][0].update(digest='sha256:'+'f'*64)),('source-push-run.json',lambda x:x.update(conclusion='failure')),('activation-compare.json',lambda x:x['files'].append(dict(filename='forged',status='added',sha='1'*40)))]
        for filename,change in mutations:
            def mutate(name,value):
                if name==filename:change(value)
            with self.subTest(filename=filename),self.assertRaises(ValueError):receiver.authenticate_producer(MemoryClient(mutate))
    def test_exact_cached_zip_and_retained_files_without_extraction(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive,candidate,pin=toy_carrier(root);result=receiver.verify_zip_files(archive,candidate,pin);self.assertEqual(set(result['files']),carrier.FILES);self.assertFalse(result['native_admitted']);self.assertEqual(sorted(p.name for p in root.iterdir()),['candidate','toy.zip'])
            with self.assertRaises(ValueError):receiver.verify_cached_carrier(archive,candidate)
    def test_same_size_cache_poison_extra_member_and_symlinks_reject(self):
        for mode in ['file','zip','extra','file-link','parent-link']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=Path(d);archive,candidate,pin=toy_carrier(root);path=candidate/'candidate/libpandagl.so.data'
                if mode=='file':path.write_bytes(b'bad DATA')
                if mode=='zip':
                    raw=bytearray(archive.read_bytes());raw[50]^=1;archive.write_bytes(raw)
                if mode=='extra':(candidate/'extra').write_bytes(b'bad')
                if mode=='file-link':path.rename(root/'saved');path.symlink_to(root/'saved')
                if mode=='parent-link':(candidate/'candidate').rename(root/'saved-dir');(candidate/'candidate').symlink_to(root/'saved-dir',target_is_directory=True)
                with self.assertRaises(ValueError):receiver.verify_zip_files(archive,candidate,pin)
    def test_missing_cache_and_wrong_zip_digest_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(ValueError):receiver.verify_cached_carrier(root/'absent',root/'absent-dir')
            archive,candidate,pin=toy_carrier(root);pin['artifact_zip_sha256']='0'*64
            with self.assertRaises(ValueError):receiver.verify_zip_files(archive,candidate,pin)
    def test_provider_cache_binds_inventory_digest_and_no_host_alias(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw=b'CPU provider DATA';inventory=image_fixtures.SelectedImageTests().inventory(raw);path=root/(j.sha(raw)+'.elf.data');path.write_bytes(raw);result=receiver.provider_paths(inventory,root);self.assertEqual(result['/usr/lib/target'],path)
            path.write_bytes(b'x'*len(raw))
            with self.assertRaises(ValueError):receiver.provider_paths(inventory,root)
            path.unlink();path.symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):receiver.provider_paths(inventory,root)
    def test_frozen_source314_and_original_failure_are_bound(self):
        snapshot=receiver.frozen_state();self.assertEqual(len(snapshot['source_closure']),314);self.assertEqual(snapshot['old_failure_sha256'],j.contract()['old_failure_sha256'])
        original=j.read
        def changed(path,limit):return b'changed failure' if Path(path)==j.ROOT/j.contract()['old_failure_path'] else original(path,limit)
        # Avoid recursive contract reads in the injected reader.
        target=j.ROOT/j.contract()['old_failure_path']
        def changed(path,limit):return b'changed failure' if Path(path)==target else original(path,limit)
        with patch.object(j,'read',side_effect=changed),self.assertRaises(ValueError):receiver.frozen_state()
    def test_wrong_own_source_and_bootstrap_failure_leave_negative_receipt(self):
        with self.assertRaises(ValueError):receiver.verify_audit_source('f'*40)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'audit';result=receiver.audit('f'*40,[dict(event='push',run_id=1),dict(event='pull_request',run_id=2)],out);saved=json.loads((out/'acceptance.json').read_text());self.assertEqual(result,saved);self.assertEqual(saved['status'],'FAILED');self.assertFalse(saved['actions_output_origin_authenticated']);self.assertFalse(saved['selected_static_accepted']);self.assertEqual(saved['new_sdk_builds'],0);self.assertEqual(saved['new_workflow_activations'],0)
    def test_new_audit_result_never_overwrites_closed_verdict(self):
        original=j.read(j.ROOT/j.contract()['old_failure_path'],1024**2)
        with tempfile.TemporaryDirectory() as d:
            with patch.object(receiver,'verify_audit_source',side_effect=ValueError('fixture bootstrap failure')):
                result=receiver.audit('a'*40,[],Path(d)/'audit')
            self.assertFalse(result['old_receiver_verdict_changed']);self.assertEqual(j.read(j.ROOT/j.contract()['old_failure_path'],1024**2),original)

if __name__=='__main__':unittest.main()
