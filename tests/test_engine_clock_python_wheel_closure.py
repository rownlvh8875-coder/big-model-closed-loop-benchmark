"""Generated wheel/graph fixtures only: no network, installs or package imports."""
import base64
import builtins
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile
try:
 from scripts import engine_clock_python_wheel_closure as w
except ImportError:w=None


def make_wheel(root,name='sample',version='1.0',requires=(),extras=(),python=None,tag='py3-none-any',extra_files=None):
 normalized=name.replace('-','_');dist=normalized+'-'+version+'.dist-info/'
 metadata='Metadata-Version: 2.1\nName: '+name+'\nVersion: '+version+'\n'
 if python:metadata+='Requires-Python: '+python+'\n'
 metadata+=''.join('Requires-Dist: '+r+'\n' for r in requires)+''.join('Provides-Extra: '+e+'\n' for e in extras)+'\n'
 files={normalized+'/__init__.py':b'raise RuntimeError("NEVER_IMPORT_FIXTURE")\n',dist+'METADATA':metadata.encode(),dist+'WHEEL':('Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: '+tag+'\n').encode(),**(extra_files or {})}
 rows=[]
 for p,data in files.items():rows.append([p,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('='),str(len(data))])
 rows.append([dist+'RECORD','','']);out=io.StringIO(newline='');csv.writer(out,lineterminator='\n').writerows(rows);files[dist+'RECORD']=out.getvalue().encode()
 path=root/(normalized+'-'+version+'-'+tag+'.whl')
 with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for p,data in files.items():z.writestr(p,data)
 return path


class WheelInputTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(w,'wheel-input verifier missing')
 def test_exact_archive_payload_record_and_metadata_without_import(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=make_wheel(root,requires=['dependency>=1; python_version >= "3.11"'],extras=['feature'],python='>=3.11,<3.12',extra_files={'sample/vendor/lib-1.dist-info/RECORD':b'original vendored RECORD','sample/hooks.pth':b'NEVER_EXECUTE'})
   original=builtins.__import__
   def guarded(name,*args,**kwargs):
    if name.split('.')[0] in ('sample','numpy','cv2','panda3d','metadrive','onnxruntime'):raise AssertionError('native/package import')
    return original(name,*args,**kwargs)
   with patch.object(builtins,'__import__',side_effect=guarded):row=w.inspect_wheel(path)
   self.assertEqual('sample',row['name']);self.assertEqual('1.0',row['version']);self.assertEqual(path.stat().st_size,row['nbytes']);self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),row['sha256']);self.assertEqual(6,row['member_count']);self.assertEqual(['sample/hooks.pth'],row['startup_hooks']);self.assertEqual(['feature'],row['provides_extra'])
 def test_wrong_python_and_platform_tag_reject(self):
  for python,tag in [('>=3.12','py3-none-any'),(None,'cp312-cp312-manylinux_2_28_x86_64'),(None,'cp311-cp311-manylinux_2_39_x86_64')]:
   with tempfile.TemporaryDirectory() as tmp:
    path=make_wheel(Path(tmp),python=python,tag=tag)
    with self.assertRaises(ValueError):w.inspect_wheel(path)
 def test_corrupt_record_duplicate_traversal_and_symlink_reject(self):
  for kind in ('changed','duplicate','traversal','symlink'):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);path=make_wheel(root)
    if kind=='changed':
     with zipfile.ZipFile(path) as z:items={i.filename:z.read(i) for i in z.infolist()}
     items['sample/__init__.py']=b'changed'
     with zipfile.ZipFile(path,'w') as z:
      for p,data in items.items():z.writestr(p,data)
    else:
     with zipfile.ZipFile(path,'a') as z:
      if kind=='duplicate':z.writestr('sample/__init__.py',b'bad')
      elif kind=='traversal':z.writestr('../SECRET_SENTINEL',b'bad')
      else:
       info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,b'/SECRET_SENTINEL')
    with self.assertRaisesRegex(ValueError,'^[A-Z_]+$') as caught:w.inspect_wheel(path)
    self.assertNotIn('SECRET',str(caught.exception))
 def test_publisher_exact_file_hash_size_origin_and_target(self):
  with tempfile.TemporaryDirectory() as tmp:
   row=w.inspect_wheel(make_wheel(Path(tmp)))
   file={'filename':row['filename'],'packagetype':'bdist_wheel','python_version':'py3','url':'https://files.pythonhosted.org/packages/x/'+row['filename'],'size':row['nbytes'],'digests':{'sha256':row['sha256']},'yanked':False,'requires_python':'>=3.11'}
   data={'info':{'name':'sample','version':'1.0'},'urls':[file]};origin=w.verify_publisher(row,data);self.assertEqual(file['url'],origin['url'])
   for key,bad in [('size',row['nbytes']+1),('digests',{'sha256':'0'*64}),('url','https://SECRET@files.pythonhosted.org/x.whl'),('url','https://evil.invalid/'+row['filename']),('yanked',True),('requires_python','>=3.12')]:
    altered=copy.deepcopy(data);altered['urls'][0][key]=bad
    with self.assertRaisesRegex(ValueError,'^PUBLISHER_WHEEL_MISMATCH$'):w.verify_publisher(row,altered)
 def test_file_directory_collision_and_missing_record_row_reject(self):
  for extra in ({'sample':b'file collision'},{'sample/../bad':b'bad'}):
   with tempfile.TemporaryDirectory() as tmp:
    with self.assertRaises(ValueError):w.inspect_wheel(make_wheel(Path(tmp),extra_files=extra))


class TargetGraphTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(w,'target graph verifier missing')
 def rows(self,root,items):return [w.inspect_wheel(make_wheel(root,**item)) for item in items]
 def test_target_patch_marker_is_evaluated_not_host_patch(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);rows=self.rows(root,[{'name':'root','requires':['child>=1; python_full_version > "3.11.17"']}])
   with self.assertRaisesRegex(ValueError,'^UNSATISFIED_TARGET_DEPENDENCY$'):w.validate_graph(rows,['root==1.0'])
   rows+=self.rows(root,[{'name':'child'}]);result=w.validate_graph(rows,['root==1.0']);self.assertEqual('3.11.18',result['environment']['python_full_version']);self.assertEqual(['child','root'],result['selected_names'])
 def test_extras_propagate_to_fixed_point(self):
  with tempfile.TemporaryDirectory() as tmp:
   rows=self.rows(Path(tmp),[{'name':'root','extras':['feature'],'requires':['middle[ssl]>=1; extra == "feature"']},{'name':'middle','extras':['ssl'],'requires':['leaf>=1; extra == "ssl"']},{'name':'leaf','requires':['root>=1']}])
   result=w.validate_graph(rows,['root[feature]==1.0']);self.assertEqual(['ssl'],result['requested_extras']['middle']);self.assertEqual(3,len(result['edges']))
 def test_missing_version_orphan_duplicate_and_unknown_extra_reject(self):
  cases=[([{'name':'root','requires':['child>=2']},{'name':'child'}],['root==1.0']),([{'name':'root'},{'name':'orphan'}],['root==1.0']),([{'name':'root'},{'name':'root','version':'2.0'}],['root>=1']),([{'name':'root'}],['root[missing]==1.0'])]
  for items,roots in cases:
   with tempfile.TemporaryDirectory() as tmp:
    rows=self.rows(Path(tmp),items)
    with self.assertRaises(ValueError):w.validate_graph(rows,roots)
 def test_unsupported_kernel_marker_and_direct_url_reject(self):
  for requirement,code in [('child; platform_release == "7.0"','UNSUPPORTED_TARGET_MARKER'),('child @ https://example.invalid/SECRET.whl','DIRECT_DEPENDENCY_URL_REJECTED')]:
   with tempfile.TemporaryDirectory() as tmp:
    rows=self.rows(Path(tmp),[{'name':'root','requires':[requirement]}])
    with self.assertRaisesRegex(ValueError,'^'+code+'$'):w.validate_graph(rows,['root==1.0'])
 def test_quoted_kernel_marker_name_is_data(self):
  with tempfile.TemporaryDirectory() as tmp:
   rows=self.rows(Path(tmp),[{'name':'root','requires':['child; extra == "platform_release"']}]);self.assertEqual(['root'],w.validate_graph(rows,['root==1.0'])['selected_names'])
 def test_graph_deadline_rejects_before_claiming_closure(self):
  with tempfile.TemporaryDirectory() as tmp:
   rows=self.rows(Path(tmp),[{'name':'root'}])
   with self.assertRaisesRegex(ValueError,'^TARGET_GRAPH_DEADLINE$'):w.validate_graph(rows,['root==1.0'],deadline=0)
 def test_multiple_cv2_distributions_reject(self):
  with tempfile.TemporaryDirectory() as tmp:
   rows=self.rows(Path(tmp),[{'name':'opencv-python'},{'name':'opencv-python-headless'}])
   with self.assertRaisesRegex(ValueError,'^MULTIPLE_CV2_PROVIDERS$'):w.validate_graph(rows,['opencv-python==1.0','opencv-python-headless==1.0'])

if __name__=='__main__':unittest.main()
