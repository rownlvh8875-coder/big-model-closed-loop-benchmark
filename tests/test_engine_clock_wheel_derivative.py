"""Small in-memory wheels only; no MetaDrive payload is imported or downloaded."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
from time import perf_counter
import unittest
from unittest.mock import patch
import warnings
from zipfile import ZipFile, ZipInfo, ZIP_STORED, ZIP_DEFLATED

try:
    from scripts import engine_clock_wheel_derivative as derivative
except ImportError:
    derivative = None

DIST = 'metadrive_simulator-0.4.3.dist-info/'
META = DIST+'METADATA'
WHEEL = DIST+'WHEEL'
RECORD = DIST+'RECORD'
PROOF = DIST+'ENGINE_CLOCK_DERIVATION.json'
BASE_META = (b'Metadata-Version: 2.1\nName: metadrive-simulator\nVersion: 0.4.3\n'
             b'License: Apache 2.0\nRequires-Dist: numpy >=1.21.6\n'
             b'Requires-Dist: opencv-python\n\nRequires-Dist: opencv-python\nfixture body\n')
EXPECTED_META = (b'Metadata-Version: 2.1\nName: metadrive-simulator\nVersion: 0.4.3\n'
                 b'License: Apache 2.0\nRequires-Dist: numpy >=1.21.6\n'
                 b'Requires-Dist: opencv-python-headless==5.0.0.93\n\n'
                 b'Requires-Dist: opencv-python\nfixture body\n')
BASE_WHEEL = b'Wheel-Version: 1.0\nGenerator: fixture-builder\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fixture(*, metadata=BASE_META, wheel_metadata=BASE_WHEEL, changes=None,
            record_change=None, info_change=None, duplicate=None, compression=ZIP_STORED):
    files = {'metadrive/__init__.py': b"raise AssertionError('PACKAGE_MUST_NOT_EXECUTE')\n",
             'metadrive/assets/': b'', 'metadrive/assets/raw.bin': b'\x00\xff\x01\x00\x80',
             'metadrive/assets/한글.bin': b'unicode',
             DIST+'LICENSE.txt': b'fixture license bytes\n',
             DIST+'entry_points.txt': b'[console_scripts]\nfixture=metadrive:main\n',
             META: metadata, WHEEL: wheel_metadata}
    if changes:
        for name, value in changes.items():
            if value is None: files.pop(name, None)
            else: files[name] = value
    rows = []
    for name, data in files.items():
        if not name.endswith('/'):
            rows.append([name, 'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('='), str(len(data))])
    rows.append([RECORD, '', ''])
    if record_change: record_change(rows)
    text = io.StringIO(newline=''); csv.writer(text, lineterminator='\n').writerows(rows)
    files[RECORD] = text.getvalue().encode()
    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with ZipFile(buffer, 'w', compression=compression) as z:
            for name, data in list(files.items())+([] if duplicate is None else [(duplicate, files[duplicate])]):
                info = ZipInfo(name, (2020, 2, 3, 4, 5, 6)); info.create_system = 3
                info.external_attr = ((stat.S_IFDIR|0o755) if name.endswith('/') else (stat.S_IFREG|0o640)) << 16
                info.compress_type = compression
                if info_change: info_change(info)
                z.writestr(info, data)
    return buffer.getvalue(), metadata


class WheelDerivativeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(derivative, 'wheel metadata derivative implementation is missing')

    def run_fixture(self, pair=None, **kwargs):
        source, metadata = fixture() if pair is None else pair
        options = dict(expected_source_sha256=digest(source), expected_metadata_sha256=digest(metadata), deadline=perf_counter()+10)
        options.update(kwargs)
        return derivative.derive_wheel(source, **options)

    def assert_failed(self, output, receipt):
        self.assertIsNone(output)
        self.assertEqual(receipt['status'], 'FAILED_OR_INCOMPLETE')
        self.assertFalse(receipt['complete'])
        self.assertIsNone(receipt['derived_wheel_sha256'])
        self.assertIsNone(receipt['preserved_members_sha256'])
        for field in ['native_admission','execution_authorized','image_preparation_ready','official_distribution','source_origin_authenticated']:
            self.assertIs(receipt[field], False)
        self.assertLess(len(json.dumps(receipt)), 8192)

    def test_only_target_header_changes_and_payload_license_attributes_survive(self):
        source, metadata = fixture(); before = source
        output, r = self.run_fixture((source,metadata))
        self.assertEqual(r['status'], 'METADATA_DERIVATIVE_CREATED'); self.assertTrue(r['complete'])
        self.assertEqual(r['source_wheel_sha256'], digest(source)); self.assertEqual(r['derived_wheel_sha256'], digest(output))
        self.assertEqual(r['preserved_members'], 6); self.assertEqual(source, before)
        with ZipFile(io.BytesIO(source)) as old, ZipFile(io.BytesIO(output)) as new:
            self.assertEqual(new.read(META), EXPECTED_META)
            self.assertEqual(set(new.namelist()), set(old.namelist())|{PROOF})
            for name in set(old.namelist())-{META,WHEEL,RECORD}:
                self.assertEqual(new.read(name), old.read(name), name)
                self.assertEqual(new.getinfo(name).external_attr, old.getinfo(name).external_attr)
                self.assertEqual(new.getinfo(name).create_system, old.getinfo(name).create_system)

    def test_derivative_label_generator_and_provenance_never_grant_admission(self):
        source, metadata=fixture();output,r=self.run_fixture((source,metadata))
        self.assertEqual(r['derived_filename'],'metadrive_simulator-0.4.3-1headless-py3-none-any.whl')
        for field in ['native_admission','execution_authorized','image_preparation_ready','official_distribution','source_origin_authenticated']:
            self.assertIs(r[field],False)
        with ZipFile(io.BytesIO(output)) as z:
            wheel=z.read(WHEEL)
            self.assertEqual(wheel,b'Wheel-Version: 1.0\nGenerator: engine-clock-wheel-derivative (metadata-v1)\nRoot-Is-Purelib: true\nTag: py3-none-any\nBuild: 1headless\n\n')
            proof=json.loads(z.read(PROOF))
            self.assertEqual(proof['source_wheel_sha256'],digest(source))
            self.assertEqual(proof['source_metadata_sha256'],digest(metadata))
            self.assertEqual(proof['preserved_members_sha256'],r['preserved_members_sha256'])
            self.assertIs(proof['official_distribution'],False)
            self.assertNotIn('implementation_sha256',proof)

    def test_regenerated_record_covers_actual_written_files(self):
        output,r=self.run_fixture()
        with ZipFile(io.BytesIO(output)) as z:
            rows=list(csv.reader(io.StringIO(z.read(RECORD).decode(),newline='')))
            self.assertEqual(len(rows),len({x[0] for x in rows}))
            self.assertEqual({x[0] for x in rows},{n for n in z.namelist() if not n.endswith('/')})
            for name,hash_value,size in rows:
                if name==RECORD:self.assertEqual([hash_value,size],['','']);continue
                data=z.read(name)
                self.assertEqual(size,str(len(data)))
                self.assertEqual(hash_value,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('='))

    def test_identical_inputs_produce_identical_archive_bytes(self):
        pair=fixture();a,ra=self.run_fixture(pair);b,rb=self.run_fixture(pair)
        self.assertEqual(a,b);self.assertEqual(ra['derived_wheel_sha256'],rb['derived_wheel_sha256'])
        with ZipFile(io.BytesIO(a)) as z:
            self.assertTrue(all(x.date_time==(1980,1,1,0,0,0) and x.compress_type==ZIP_STORED for x in z.infolist()))

    def test_zero_source_attributes_are_not_replaced_by_zipfile_defaults(self):
        source,metadata=fixture();raw=bytearray(source)
        offset=struct.unpack_from('<L',raw,len(raw)-6)[0]
        while raw[offset:offset+4]==b'PK\x01\x02':
            struct.pack_into('<L',raw,offset+38,0)
            nlen,xlen,clen=struct.unpack_from('<3H',raw,offset+28)
            offset+=46+nlen+xlen+clen
        output,r=self.run_fixture((bytes(raw),metadata))
        self.assertTrue(r['complete'])
        with ZipFile(io.BytesIO(output)) as z:
            for info in z.infolist():
                if info.filename!=PROOF:self.assertEqual(info.external_attr,0,info.filename)

    def test_real_saved_metadata_in_synthetic_carrier_preserves_body(self):
        raw=Path('docs/evidence/engine-clock-image-inputs/metadrive-0.4.3.METADATA').read_bytes()
        output,r=self.run_fixture(fixture(metadata=raw))
        self.assertTrue(r['complete'])
        with ZipFile(io.BytesIO(output)) as z:
            old_head,_,body=raw.partition(b'\n\n');new_head,_,new_body=z.read(META).partition(b'\n\n')
            self.assertEqual(body,new_body)
            self.assertEqual(new_head.replace(b'opencv-python-headless==5.0.0.93',b'opencv-python'),old_head)
            self.assertEqual(r['source_metadata_sha256'],'4fb69fa54bb0e8118315aecdc482597af69798e17e47df3c57fbca50d4e7bcf6')
        self.assertIs(r['source_origin_authenticated'],False)

    def test_deflated_source_and_empty_payload_are_preserved(self):
        output,r=self.run_fixture(fixture(changes={'metadrive/empty':b''},compression=ZIP_DEFLATED))
        self.assertTrue(r['complete'])
        with ZipFile(io.BytesIO(output)) as z:self.assertEqual(z.read('metadrive/empty'),b'')

    def test_source_and_metadata_pin_mismatches_return_no_output(self):
        for changes in [dict(expected_source_sha256='0'*64),dict(expected_metadata_sha256='0'*64)]:
            with self.subTest(changes=changes):self.assert_failed(*self.run_fixture(**changes))

    def test_bad_input_and_digest_types_fail_closed(self):
        source,meta=fixture()
        for value in [None,True,bytearray(source),io.BytesIO(source)]:
            self.assert_failed(*derivative.derive_wheel(value,expected_source_sha256=digest(source),expected_metadata_sha256=digest(meta),deadline=perf_counter()+10))
        for key in ['expected_source_sha256','expected_metadata_sha256']:
            for value in [None,True,'A'*64,'sha256:'+'a'*64,'a'*63]:
                self.assert_failed(*self.run_fixture(**{key:value}))

    def test_wrong_distribution_version_or_missing_core_headers_reject(self):
        for raw in [BASE_META.replace(b'Name: metadrive-simulator',b'Name: other'),BASE_META.replace(b'Version: 0.4.3',b'Version: 0.4.4'),BASE_META.replace(b'Metadata-Version: 2.1\n',b''),BASE_META.replace(b'Name: metadrive-simulator\n',b''),BASE_META.replace(b'Version: 0.4.3\n',b'Version: 0.4.3\nVersion: 0.4.3\n')]:
            with self.subTest(raw=raw):self.assert_failed(*self.run_fixture(fixture(metadata=raw)))

    def test_conditional_duplicate_missing_or_preexisting_opencv_requirements_reject(self):
        replacements=[b'opencv-python; extra == "x"',b'opencv-python>=4',b'opencv-python\nRequires-Dist: opencv-python',b'opencv-python-headless==5.0.0.93',b'opencv-python\nRequires-Dist: opencv_contrib_python',b'\n opencv-python']
        for value in replacements:
            self.assert_failed(*self.run_fixture(fixture(metadata=BASE_META.replace(b'opencv-python',value,1))))
        self.assert_failed(*self.run_fixture(fixture(metadata=BASE_META.replace(b'Requires-Dist: opencv-python\n',b'',1))))

    def test_bad_wheel_headers_and_metadata_encodings_reject(self):
        for raw in [BASE_WHEEL.replace(b'1.0',b'2.0'),BASE_WHEEL.replace(b'py3-none-any',b'cp311-cp311-linux_x86_64'),BASE_WHEEL.replace(b'true',b'false'),BASE_WHEEL.replace(b'\n\n',b'\nBuild: 1headless\n\n'),BASE_WHEEL.replace(b'Generator: fixture-builder\n',b''),BASE_WHEEL+b'body']:
            self.assert_failed(*self.run_fixture(fixture(wheel_metadata=raw)))
        for raw in [BASE_META.replace(b'\n',b'\r\n'),BASE_META+b'\0',BASE_META+b'\xff']:
            self.assert_failed(*self.run_fixture(fixture(metadata=raw)))

    def test_signatures_foreign_metadata_and_preexisting_provenance_reject(self):
        for name in [DIST+'RECORD.jws',DIST+'RECORD.p7s',PROOF,'other-1.dist-info/METADATA']:
            self.assert_failed(*self.run_fixture(fixture(changes={name:b'fixture'})))

    def test_duplicate_archive_members_reject(self):
        self.assert_failed(*self.run_fixture(fixture(duplicate='metadrive/assets/raw.bin')))

    def test_hostile_paths_and_file_directory_ancestry_reject(self):
        for name in ['/tmp/secret','../secret','metadrive/../secret','metadrive//bad','metadrive/./bad','C:bad','metadrive\\bad','metadrive/line\nbad','metadrive/nul\0bad','metadrive/control\x7fbad','metadrive/'+'x'*4096]:
            self.assert_failed(*self.run_fixture(fixture(changes={name:b'fixture'})))
        self.assert_failed(*self.run_fixture(fixture(changes={'metadrive/assets':b'file'})))
        self.assert_failed(*self.run_fixture(fixture(changes={'metadrive/ancestor':b'file','metadrive/ancestor/child':b'child'})))

    def test_symlink_and_special_modes_reject(self):
        for kind in [stat.S_IFLNK,stat.S_IFIFO,stat.S_IFSOCK,stat.S_IFCHR,stat.S_IFBLK]:
            def change(info):
                if info.filename=='metadrive/assets/raw.bin':info.external_attr=(kind|0o640)<<16
            self.assert_failed(*self.run_fixture(fixture(info_change=change)))

    def test_missing_extra_duplicate_bad_hash_or_size_record_rows_reject(self):
        mutations=[lambda rows:rows.pop(0),lambda rows:rows.append(['metadrive/not-there','sha256='+'A'*43,'0']),lambda rows:rows.append(rows[0].copy()),lambda rows:rows[0].__setitem__(1,'sha256='+'A'*43),lambda rows:rows[0].__setitem__(2,'0001'),lambda rows:rows[-1].__setitem__(1,'sha256='+'A'*43),lambda rows:rows[0].append('extra')]
        for mutate in mutations:self.assert_failed(*self.run_fixture(fixture(record_change=mutate)))

    def test_crc_corruption_returns_no_partial_output(self):
        source,meta=fixture();source=source.replace(b'\x00\xff\x01\x00\x80',b'\x00\xfe\x01\x00\x80',1)
        self.assert_failed(*self.run_fixture((source,meta)))

    def test_local_central_name_or_size_mismatch_reject(self):
        source,meta=fixture()
        altered=bytearray(source);altered[30]=ord('x');self.assert_failed(*self.run_fixture((bytes(altered),meta)))
        altered=bytearray(source);struct.pack_into('<L',altered,22,999);self.assert_failed(*self.run_fixture((bytes(altered),meta)))

    def test_encryption_data_descriptors_and_unknown_flags_reject(self):
        source,meta=fixture();central=source.index(b'PK\x01\x02')
        for flag in [1,8,0x40]:
            altered=bytearray(source);struct.pack_into('<H',altered,6,flag);struct.pack_into('<H',altered,central+8,flag)
            self.assert_failed(*self.run_fixture((bytes(altered),meta)))

    def test_extra_fields_comments_preamble_trailing_and_hidden_gaps_reject(self):
        for field,value in [('extra',b'\xfe\xca\x00\x00'),('comment',b'comment')]:
            self.assert_failed(*self.run_fixture(fixture(info_change=lambda info:setattr(info,field,value))))
        source,meta=fixture()
        for altered in [b'prefix'+source,source+b'trailing']:
            self.assert_failed(*self.run_fixture((altered,meta)))
        central=struct.unpack_from('<L',source,len(source)-6)[0]
        altered=bytearray(source[:central]+b'GAP!'+source[central:]);struct.pack_into('<L',altered,len(altered)-6,central+4)
        self.assert_failed(*self.run_fixture((bytes(altered),meta)))
        b=io.BytesIO(source)
        with ZipFile(b,'a') as z:z.comment=b'comment'
        self.assert_failed(*self.run_fixture((b.getvalue(),meta)))

    def test_multidisk_zip64_count_and_truncated_archives_reject(self):
        source,meta=fixture()
        for offset,value in [(-18,1),(-12,65535),(-14,65535)]:
            altered=bytearray(source);struct.pack_into('<H',altered,len(source)+offset,value)
            self.assert_failed(*self.run_fixture((bytes(altered),meta)))
        for altered in [source[:-1],source[:30],b'not a zip']:
            self.assert_failed(*self.run_fixture((altered,meta)))

    def test_archive_expanded_member_metadata_and_node_caps_return_no_output(self):
        source,meta=fixture()
        with ZipFile(io.BytesIO(source)) as z:expanded=sum(i.file_size for i in z.infolist());nodes=len(z.infolist())
        for name,limit in [('MAX_SOURCE_BYTES',len(source)-1),('MAX_EXPANDED_BYTES',expanded-1),('MAX_MEMBER_BYTES',4),('MAX_METADATA_BYTES',len(meta)-1),('MAX_MEMBERS',nodes)]:
            with self.subTest(name=name),patch.object(derivative,name,limit):self.assert_failed(*self.run_fixture((source,meta)))

    def test_member_budget_is_enforced_before_central_parser_allocation(self):
        pair=fixture()
        # The stdlib constructor materializes the complete central directory.
        # A rejecting parser double exposes accidentally reaching that boundary.
        with patch.object(derivative,'MAX_MEMBERS',1),patch.object(derivative,'ZipFile',side_effect=MemoryError('unbounded central parser')):
            output,r=self.run_fixture(pair)
        self.assert_failed(output,r)
        self.assertEqual(r['error_code'],'MEMBER_LIMIT')

    def test_output_and_read_budgets_discard_partial_memory_output(self):
        for name,limit in [('MAX_OUTPUT_BYTES',100),('MAX_READ_BYTES',3)]:
            with patch.object(derivative,name,limit):self.assert_failed(*self.run_fixture())

    def test_invalid_expired_and_midwork_deadlines_return_no_output(self):
        for value in [None,True,float('nan'),float('inf'),-1]:
            self.assert_failed(*self.run_fixture(deadline=value))
        ticks=iter(range(10000))
        with patch.object(derivative,'perf_counter',side_effect=lambda:next(ticks)):
            self.assert_failed(*self.run_fixture(deadline=4.))

    def test_external_exception_text_is_sanitized_and_interrupt_propagates(self):
        pair=fixture()
        for error in [OSError('RAW_SECRET_SENTINEL'),ValueError('RAW_SECRET_SENTINEL'),RuntimeError('RAW_SECRET_SENTINEL')]:
            with patch.object(derivative.ZipFile,'open',side_effect=error):output,r=self.run_fixture(pair)
            self.assert_failed(output,r);self.assertNotIn('RAW_SECRET_SENTINEL',json.dumps(r))
        with patch.object(derivative.ZipFile,'open',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_fixture(pair)

    def test_pure_transform_does_not_read_or_write_files(self):
        pair=fixture()
        with patch('builtins.open',side_effect=AssertionError('filesystem IO')):output,r=self.run_fixture(pair)
        self.assertTrue(r['complete']);self.assertIsInstance(output,bytes)

    def test_fresh_import_and_transform_without_native_network_process_imports(self):
        source,meta=fixture()
        code='''import builtins,base64,json,sys,time
old=builtins.__import__
blocked={'numpy','cv2','panda3d','metadrive','onnxruntime','socket','requests','subprocess','ctypes'}
def guard(name,*a,**k):
 if name.split('.')[0] in blocked or name=='urllib.request':raise AssertionError('external/native import')
 return old(name,*a,**k)
builtins.__import__=guard
from scripts.engine_clock_wheel_derivative import derive_wheel
out,r=derive_wheel(base64.b64decode(sys.argv[1]),expected_source_sha256=sys.argv[2],expected_metadata_sha256=sys.argv[3],deadline=time.perf_counter()+10)
print(json.dumps({'status':r['status'],'native_admission':r['native_admission'],'origin':r['source_origin_authenticated']}))
'''
        p=subprocess.run([sys.executable,'-c',code,base64.b64encode(source).decode(),digest(source),digest(meta)],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),{'status':'METADATA_DERIVATIVE_CREATED','native_admission':False,'origin':False})


if __name__=='__main__':unittest.main()
