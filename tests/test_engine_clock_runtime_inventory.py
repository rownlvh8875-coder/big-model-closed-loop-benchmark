"""Caller-root filesystem fixtures, never an installed native image scan."""
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
from time import perf_counter, sleep
import unittest
from unittest.mock import patch

try:
    from scripts import engine_clock_runtime_inventory as inventory
except ImportError:
    inventory = None

ROOTS = ['/etc', '/lib', '/lib64', '/opt/python', '/opt/venv', '/usr']
EXCLUSIONS = ['/etc/hostname', '/etc/hosts', '/etc/mtab', '/etc/resolv.conf']
ABC_SHA = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
EMPTY_SHA = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'


def manifest(entries=(), roots=None):
    return {'schema': 'installed-files-v1', 'roots': ROOTS.copy() if roots is None else roots,
            'runtime_exclusions': EXCLUSIONS.copy(),
            'entries': sorted(copy.deepcopy(list(entries)), key=lambda entry: entry['path'])}


def file_record(path, data=b'abc', mode=0o640):
    digest = ABC_SHA if data == b'abc' else EMPTY_SHA if not data else hashlib.sha256(data).hexdigest()
    return {'path': path, 'kind': 'file', 'mode': mode, 'nbytes': len(data), 'sha256': digest}


def link_record(path, target):
    return {'path': path, 'kind': 'symlink', 'target': target}


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(inventory, 'bounded file inventory implementation is missing')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'root'
        self.root.mkdir()
        for name in ROOTS:
            (self.root / name.lstrip('/')).mkdir(parents=True)

    def put(self, path, data=b'abc', mode=0o640):
        target = self.root / path.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(mode)
        return file_record(path, data, mode)

    def link(self, path, target):
        location = self.root / path.lstrip('/')
        location.parent.mkdir(parents=True, exist_ok=True)
        location.symlink_to(target)
        return link_record(path, target)

    def collect(self, expected, **kwargs):
        return inventory.collect_inventory(self.root, expected, deadline=perf_counter() + 10, **kwargs)

    def assert_failure(self, result):
        self.assertEqual(result['status'], 'FAILED_OR_INCOMPLETE')
        self.assertIs(result['complete'], False)
        self.assertIs(result['native_admission'], False)
        self.assertIsNone(result['inventory'])
        self.assertIsNone(result['canonical_manifest_sha256'])
        self.assertTrue(result['failure_stage'])
        self.assertLessEqual(len(result['matched_prefix']), 64)
        self.assertLess(len(result['error']), 1024)

    def test_exact_bytes_modes_empty_files_and_canonical_hash(self):
        expected = manifest([self.put('/usr/a.so'), self.put('/usr/empty', b'')])
        original = copy.deepcopy(expected)
        result = self.collect(expected)
        self.assertEqual(result['status'], 'INSTALLED_FILES_MATCH')
        self.assertIs(result['complete'], True)
        self.assertIs(result['native_admission'], False)
        self.assertEqual(result['inventory'], expected)
        self.assertEqual(expected, original)
        self.assertEqual(result['bytes_read'], 3)
        self.assertEqual(result['matched_entries'], 2)
        raw = json.dumps(expected, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        self.assertEqual(result['canonical_manifest_sha256'], hashlib.sha256(raw).hexdigest())

    def test_empty_declared_tree_can_match_without_installation_claim(self):
        result = self.collect(manifest())
        self.assertEqual(result['status'], 'INSTALLED_FILES_MATCH')
        self.assertEqual(result['bytes_read'], 0)
        self.assertEqual(result['matched_entries'], 0)
        self.assertIs(result['native_admission'], False)

    def test_changed_content_rejects_and_retains_only_matched_prefix(self):
        a = self.put('/usr/a.so'); z = self.put('/usr/z.so')
        (self.root/'usr/z.so').write_bytes(b'xyz')
        result = self.collect(manifest([a, z]))
        self.assert_failure(result)
        self.assertEqual(result['bytes_read'], 6)
        self.assertEqual([v['path'] for v in result['matched_prefix']], ['/usr/a.so'])
        self.assertNotIn('xyz', result['error'])

    def test_missing_extra_size_and_mode_changes_reject(self):
        expected = manifest([self.put('/usr/a')])
        for change in ['missing', 'extra', 'size', 'mode']:
            with self.subTest(change=change):
                (self.root/'usr/a').write_bytes(b'abc'); (self.root/'usr/a').chmod(0o640)
                extra = self.root/'usr/extra'
                if extra.exists(): extra.unlink()
                if change=='missing': (self.root/'usr/a').unlink()
                elif change=='extra': extra.write_bytes(b'UNEXPECTED_CONTENT')
                elif change=='size': (self.root/'usr/a').write_bytes(b'longer')
                else: (self.root/'usr/a').chmod(0o600)
                result = self.collect(expected)
                self.assert_failure(result)
                if change in ('size', 'mode'): self.assertEqual(result['bytes_read'], 0)

    def test_overlapping_roots_do_not_duplicate_payload_reads(self):
        expected = manifest([self.put('/usr/lib/a')], sorted(ROOTS+['/usr/lib']))
        result = self.collect(expected)
        self.assertEqual(result['status'], 'INSTALLED_FILES_MATCH')
        self.assertEqual(result['bytes_read'], 3)
        self.assertEqual(result['matched_entries'], 1)

    def test_root_and_cross_root_aliases_are_descriptors_not_duplicate_files(self):
        file = self.put('/usr/lib/a')
        (self.root/'lib').rmdir()
        root_link = self.link('/lib', 'usr/lib')
        cross = self.link('/opt/venv/a', '/usr/lib/a')
        result = self.collect(manifest([file, root_link, cross]))
        self.assertEqual(result['status'], 'INSTALLED_FILES_MATCH')
        self.assertEqual(result['bytes_read'], 3)
        self.assertEqual(result['matched_entries'], 3)

    def test_dangling_in_scope_link_is_recorded_without_loadability_claim(self):
        link = self.link('/usr/optional', 'not-installed')
        result = self.collect(manifest([link]))
        self.assertEqual(result['status'], 'INSTALLED_FILES_MATCH')
        self.assertEqual(result['bytes_read'], 0)
        self.assertIs(result['native_admission'], False)

    def test_required_root_cannot_cancel_a_missing_component_with_dotdot(self):
        (self.root/'lib').rmdir()
        root_link = self.link('/lib', 'usr/missing/..')
        expected = manifest([root_link])
        self.assertFalse((self.root/'lib').is_dir())
        self.assert_failure(self.collect(expected))
        # An existing empty directory is traversable even though manifests
        # contain no directory payload entries; the same target is now valid.
        (self.root/'usr/missing').mkdir()
        result = self.collect(expected)
        self.assertEqual(result['status'], 'INSTALLED_FILES_MATCH')
        self.assertEqual(result['bytes_read'], 0)
        self.assertIs(result['native_admission'], False)
        (self.root/'usr/missing').rmdir()
        (self.root/'lib').unlink()
        root_link = self.link('/lib', 'usr/bridge')
        bridge = self.link('/usr/bridge', 'missing/..')
        self.assert_failure(self.collect(manifest([root_link, bridge])))

    def test_symlink_cycle_and_escape_are_rejected_before_payload_reads(self):
        bads = [manifest([link_record('/usr/a', 'b'), link_record('/usr/b', 'a')]),
                manifest([link_record('/usr/a', '/tmp/secret')]),
                manifest([link_record('/usr/a', '../../tmp/secret')]),
                manifest([link_record('/usr/a', '/etc/hosts')])]
        for value in bads:
            with self.subTest(value=value):
                with self.assertRaises(ValueError): inventory.validate_inventory(value)
                result = self.collect(value)
                self.assert_failure(result)
                self.assertEqual(result['bytes_read'], 0)

    def test_dotdot_is_resolved_after_symlink_components(self):
        value = manifest([link_record('/usr/jump', '/tmp'),
                          link_record('/usr/use', 'jump/../safe')])
        with self.assertRaises(ValueError): inventory.validate_inventory(value)
        self.assert_failure(self.collect(value))

    def test_runtime_exclusions_never_read_payload_and_only_mtab_proc_link_allowed(self):
        self.put('/etc/hosts', b'PRIVATE_RUNTIME_CONTENT')
        self.link('/etc/mtab', '/proc/self/mounts')
        with patch.object(inventory.os, 'read', side_effect=AssertionError('excluded payload read')):
            result = self.collect(manifest())
        self.assertEqual(result['status'], 'INSTALLED_FILES_MATCH')
        self.assertEqual(result['bytes_read'], 0)
        (self.root/'etc/mtab').unlink(); self.link('/etc/mtab', '/usr/malicious')
        self.assert_failure(self.collect(manifest()))

    def test_excluded_directory_symlink_or_fifo_cannot_hide_a_subtree(self):
        path = self.root/'etc/hosts'
        for kind in ['directory','link','fifo']:
            with self.subTest(kind=kind):
                if kind=='directory': path.mkdir()
                elif kind=='link': path.symlink_to('/tmp/secret')
                else: os.mkfifo(path)
                self.assert_failure(self.collect(manifest()))
                if kind=='directory': path.rmdir()
                else: path.unlink()

    def test_fifo_and_socket_are_rejected_without_opening_payload(self):
        fifo=self.root/'usr/pipe'; os.mkfifo(fifo)
        self.assert_failure(self.collect(manifest()))
        fifo.unlink()
        with socket.socket(socket.AF_UNIX) as sock:
            sock.bind(str(self.root/'usr/socket'))
            self.assert_failure(self.collect(manifest()))

    def test_special_device_record_and_broad_or_payload_exclusions_reject(self):
        cases=[manifest([{'path':'/usr/device','kind':'device'}]),
               {**manifest(), 'runtime_exclusions':['/etc']},
               manifest([file_record('/etc/hosts')]),
               manifest([file_record('/etc/hosts/hidden')])]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):inventory.validate_inventory(case)

    def test_noncanonical_unknown_duplicate_types_and_alias_descendants_reject(self):
        values=[{**manifest(),'unregistered':True}, {**manifest(),'roots':['/usr']},
                {**manifest(),'roots':ROOTS+['/tmp']},
                manifest([file_record('/usr/a'),file_record('/usr/a')]),
                manifest([file_record('/usr/../a')]), manifest([file_record('/usr//a')]),
                manifest([file_record('/usr/a/')]),manifest([file_record('/usr/\x00a')]),
                manifest([link_record('/usr/link','/usr/target'),file_record('/usr/link/a')])]
        for key,value in [('mode',True),('nbytes',False),('mode',-1),('mode',0o10000),('sha256','A'*64)]:
            record=file_record('/usr/a');record[key]=value;values.append(manifest([record]))
        for value in values:
            with self.subTest(value=value),self.assertRaises(ValueError):inventory.validate_inventory(value)

    def test_root_symlink_and_missing_required_directory_reject(self):
        alias=Path(self.tmp.name)/'alias';alias.symlink_to(self.root, target_is_directory=True)
        self.assert_failure(inventory.collect_inventory(alias,manifest(),deadline=perf_counter()+10))
        (self.root/'lib').rmdir()
        self.assert_failure(self.collect(manifest()))

    def test_byte_budget_retains_real_prefix_without_exceeding_read_cap(self):
        a=self.put('/usr/a');b=self.put('/usr/b')
        with patch.object(inventory,'MAX_READ_BYTES',4): result=self.collect(manifest([a,b]))
        self.assert_failure(result)
        self.assertLessEqual(result['bytes_read'],4)
        self.assertEqual(result['matched_entries'],1)
        self.assertEqual(result['matched_prefix'],[a])

    def test_file_size_content_and_metadata_node_caps_fail_closed(self):
        a=self.put('/usr/a')
        with patch.object(inventory,'MAX_FILE_BYTES',2):
            result=self.collect(manifest([a]))
        self.assert_failure(result);self.assertEqual(result['bytes_read'],0)
        with patch.object(inventory,'MAX_INSTALLED_BYTES',2):
            self.assert_failure(self.collect(manifest([a])))
        with patch.object(inventory,'MAX_NODES',2):
            self.assert_failure(self.collect(manifest([a])))
        with patch.object(inventory,'MAX_JSON_BYTES',16):
            self.assert_failure(self.collect(manifest([a])))

    def test_empty_directory_enumeration_and_depth_are_bounded(self):
        for i in range(20):(self.root/f'usr/d{i:03}').mkdir()
        with patch.object(inventory,'MAX_NODES',12):
            self.assert_failure(self.collect(manifest()))
        (self.root/'usr/deep/a/b/c').mkdir(parents=True)
        with patch.object(inventory,'MAX_DEPTH',2):
            self.assert_failure(self.collect(manifest()))

    def test_invalid_or_expired_deadline_fails_before_payload_reads(self):
        expected=manifest([self.put('/usr/a')])
        for deadline in [True,float('nan'),float('inf'),perf_counter()-1]:
            with self.subTest(deadline=deadline):
                result=inventory.collect_inventory(self.root,expected,deadline=deadline)
                self.assert_failure(result);self.assertEqual(result['bytes_read'],0)

    def test_prefix_is_bounded_while_total_matches_remain_truthful(self):
        records=[self.put(f'/usr/f{i:03}',b'') for i in range(70)]
        result=self.collect(manifest(records))
        self.assertEqual(result['status'],'INSTALLED_FILES_MATCH')
        self.assertEqual(result['matched_entries'],70)
        self.assertEqual(len(result['matched_prefix']),64)
        self.assertEqual(result['bytes_read'],0)
        with patch.object(inventory,'MAX_PREFIX_BYTES',2): result=self.collect(manifest(records))
        self.assertEqual(result['status'],'INSTALLED_FILES_MATCH')
        self.assertEqual(result['matched_entries'],70)
        self.assertEqual(result['matched_prefix'],[])

    def test_in_place_mutation_is_not_accepted_as_a_snapshot(self):
        record=self.put('/usr/a',b'abcdef');real_read=os.read;changed=False
        def read(fd,n):
            nonlocal changed
            data=real_read(fd,n)
            if not changed:
                changed=True;(self.root/'usr/a').write_bytes(b'uvwxyz')
            return data
        with patch.object(inventory,'READ_CHUNK',2),patch.object(inventory.os,'read',side_effect=read):
            result=self.collect(manifest([record]))
        self.assert_failure(result)

    def test_directory_mutation_during_hashing_rejects(self):
        record=self.put('/usr/a');real_read=os.read;changed=False
        def read(fd,n):
            nonlocal changed
            data=real_read(fd,n)
            if not changed:changed=True;(self.root/'usr/new-file').write_bytes(b'new')
            return data
        with patch.object(inventory.os,'read',side_effect=read):result=self.collect(manifest([record]))
        self.assert_failure(result)

    def test_late_sibling_change_is_caught_by_metadata_only_second_pass(self):
        a=self.put('/usr/a/file');z=self.put('/usr/z/file');real_read=os.read;calls=0
        def read(fd,n):
            nonlocal calls
            data=real_read(fd,n);calls+=1
            if calls==2:(self.root/'usr/a/file').write_bytes(b'xyz')
            return data
        with patch.object(inventory.os,'read',side_effect=read):result=self.collect(manifest([a,z]))
        self.assert_failure(result)
        self.assertEqual(result['bytes_read'],6)
        self.assertEqual(result['matched_entries'],2)
        self.assertIn('metadata',result['error'])

    def test_blocked_regular_read_is_interrupted_by_absolute_deadline(self):
        record=self.put('/usr/a');real_read=os.read;returned=False
        def slow(fd,n):
            nonlocal returned
            sleep(1);returned=True;return real_read(fd,n)
        with patch.object(inventory.os,'read',side_effect=slow):
            result=inventory.collect_inventory(self.root,manifest([record]),deadline=perf_counter()+.2)
        self.assert_failure(result)
        self.assertFalse(returned)
        self.assertEqual(result['bytes_read'],0)

    def test_nonmain_thread_rejects_before_filesystem_reads(self):
        expected=manifest([self.put('/usr/a')]);results=[]
        thread=threading.Thread(target=lambda:results.append(self.collect(expected)))
        thread.start();thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assert_failure(results[0]);self.assertEqual(results[0]['bytes_read'],0)

    def test_existing_alarm_is_not_overwritten_and_prior_handler_restores(self):
        previous=signal.getsignal(signal.SIGALRM)
        def sentinel(signum,frame):raise AssertionError('unrelated alarm fired')
        signal.signal(signal.SIGALRM,sentinel)
        try:
            signal.setitimer(signal.ITIMER_REAL,5)
            result=self.collect(manifest())
            self.assert_failure(result);self.assertEqual(result['bytes_read'],0)
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0],0)
            signal.setitimer(signal.ITIMER_REAL,0)
            self.assertEqual(self.collect(manifest())['status'],'INSTALLED_FILES_MATCH')
            self.assertIs(signal.getsignal(signal.SIGALRM),sentinel)
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

    def test_owned_descriptors_close_on_failure_and_interrupt(self):
        record=self.put('/usr/a');real_open=os.open;opened=[]
        def track(*args,**kwargs):
            fd=real_open(*args,**kwargs);opened.append(fd);return fd
        with patch.object(inventory.os,'open',side_effect=track),patch.object(inventory.os,'read',side_effect=OSError('RAW_SECRET_SENTINEL')):
            result=self.collect(manifest([record]))
        self.assert_failure(result);self.assertNotIn('RAW_SECRET_SENTINEL',json.dumps(result))
        for fd in opened:
            with self.assertRaises(OSError):os.fstat(fd)
        opened.clear()
        with patch.object(inventory.os,'open',side_effect=track),patch.object(inventory.os,'read',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.collect(manifest([record]))
        for fd in opened:
            with self.assertRaises(OSError):os.fstat(fd)

    def test_uncontrolled_io_exception_text_is_not_persisted(self):
        record=self.put('/usr/a')
        for error in [ValueError('RAW_SECRET_SENTINEL'), TimeoutError('RAW_SECRET_SENTINEL')]:
            with self.subTest(error=type(error).__name__):
                with patch.object(inventory.os,'read',side_effect=error):
                    result=self.collect(manifest([record]))
                self.assert_failure(result)
                self.assertNotIn('RAW_SECRET_SENTINEL',json.dumps(result))

    def test_validate_inventory_is_metadata_only(self):
        value=manifest([file_record('/usr/a')]);before=copy.deepcopy(value)
        with patch.object(inventory.os,'open',side_effect=AssertionError('filesystem IO')):
            result=inventory.validate_inventory(value)
        self.assertEqual(result,before);self.assertEqual(value,before)

    def test_import_and_fixture_collection_do_not_use_native_network_or_process_modules(self):
        code='''import builtins,json,sys
old=builtins.__import__
blocked={'numpy','cv2','panda3d','metadrive','onnxruntime','socket','requests','subprocess','ctypes'}
def guard(name,*args,**kw):
    if name.split('.')[0] in blocked or name=='urllib.request':raise AssertionError('external/native import')
    return old(name,*args,**kw)
builtins.__import__=guard
from pathlib import Path
from time import perf_counter
from scripts import engine_clock_runtime_inventory as m
with open(sys.argv[2]) as stream:expected=json.load(stream)
r=m.collect_inventory(Path(sys.argv[1]),expected,deadline=perf_counter()+10)
print(json.dumps({'status':r['status'],'native_admission':r['native_admission']}))
'''
        p=Path(self.tmp.name)/'expected.json';p.write_text(json.dumps(manifest()))
        result=subprocess.run([sys.executable,'-c',code,str(self.root),str(p)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'status':'INSTALLED_FILES_MATCH','native_admission':False})


if __name__=='__main__':unittest.main()
