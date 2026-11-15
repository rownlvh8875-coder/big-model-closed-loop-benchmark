"""Owned tiny tar/inventory fixtures only; no Docker, host links or ELF loading."""
import hashlib,io,json,tarfile,tempfile,time,unittest
from unittest.mock import patch
from pathlib import Path
from tests.test_engine_clock_image_archive import make_save,tarbytes,TAG
from scripts.engine_clock_runtime_inventory import BASE_ROOTS,RUNTIME_EXCLUSIONS
from scripts import panda_sdk_image_archive as archive
try:from scripts import panda_sdk_link_image as image
except ImportError:image=None
class SelectedImageTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(image,'authenticated selected-provider reader missing')
 def inventory(self,data=b'new'):
  return dict(schema='installed-files-v1',roots=list(BASE_ROOTS),runtime_exclusions=list(RUNTIME_EXCLUSIONS),entries=[dict(path='/usr/lib/alias',kind='symlink',target='target'),dict(path='/usr/lib/target',kind='file',mode=0o644,nbytes=len(data),sha256=hashlib.sha256(data).hexdigest())])
 def layer(self,rows):
  b=io.BytesIO()
  with tarfile.open(fileobj=b,mode='w') as t:
   for name,kind,data in rows:
    m=tarfile.TarInfo(name);m.mode=0o644
    if kind=='file':m.size=len(data);t.addfile(m,io.BytesIO(data))
    elif kind=='dir':m.type=tarfile.DIRTYPE;t.addfile(m)
    else:m.type=tarfile.SYMTYPE if kind=='symlink' else tarfile.LNKTYPE;m.linkname=data;t.addfile(m)
  return b.getvalue()
 def reader(self,root,layers,doc=None):
  path,_,_=make_save(root,layers=layers);check=archive.inspect_save_archive(path,expected_tag=TAG,deadline=time.perf_counter()+10);return image.SelectedImage(path,image.Inventory(doc or self.inventory()),check,root/'out',deadline=time.monotonic()+20)
 def test_final_layer_bytes_are_bound_and_saved_as_nonexecutable_data(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);r=self.reader(p,[tarbytes([('usr/lib/target',b'old')]),tarbytes([('usr/lib/target',b'new')])]);rows=r.collect(['/usr/lib/target']);row=rows['/usr/lib/target'];self.assertEqual(Path(row['data_path']).read_bytes(),b'new');self.assertEqual(Path(row['data_path']).stat().st_mode&0o777,0o600);self.assertFalse(row['native_admitted'])
 def test_inventory_aliases_resolve_without_host_filesystem_following(self):
  r=image.Inventory(self.inventory());self.assertEqual(r.resolve('/usr/lib/alias'),'/usr/lib/target')
  for name in ('/usr/lib/../../../../etc/passwd','relative','/usr/lib/missing'):
   with self.assertRaises(ValueError):r.resolve(name)
  m=self.inventory();m['entries'][0]['target']='alias'
  with self.assertRaises(ValueError):image.Inventory(m).resolve('/usr/lib/alias')
 def test_whiteout_opaque_and_ancestor_replacement_remove_lower_payload(self):
  cases=[[('usr/lib/.wh.target','file',b'')],[('usr/lib/.wh..wh..opq','file',b'')],[('usr/lib','symlink','elsewhere')],[('usr/lib/target','hardlink','usr/elsewhere')]]
  for rows in cases:
   with self.subTest(rows=rows),tempfile.TemporaryDirectory() as t:
    p=Path(t);r=self.reader(p,[tarbytes([('usr/lib/target',b'new')]),self.layer(rows)])
    with self.assertRaises(ValueError):r.collect(['/usr/lib/target'])
 def test_same_layer_opaque_marker_does_not_delete_its_new_file(self):
  with tempfile.TemporaryDirectory() as t:
   r=self.reader(Path(t),[tarbytes([('usr/lib/target',b'old')]),self.layer([('usr/lib/target','file',b'new'),('usr/lib/.wh..wh..opq','file',b'')])]);self.assertEqual(Path(r.collect(['/usr/lib/target'])['/usr/lib/target']['data_path']).read_bytes(),b'new')
 def test_same_layer_nondirectory_ancestor_and_descendant_reject_in_both_orders(self):
  for kind,data in [('symlink','elsewhere'),('file',b'ancestor'),('hardlink','usr/elsewhere')]:
   for reverse in (False,True):
    with self.subTest(kind=kind,reverse=reverse),tempfile.TemporaryDirectory() as t:
     rows=[('usr/lib/target','file',b'new'),('usr/lib',kind,data)];rows=rows[::-1] if reverse else rows;r=self.reader(Path(t),[self.layer(rows)])
     with self.assertRaisesRegex(ValueError,'same-layer ancestor'):r.collect(['/usr/lib/target'])
 def test_opaque_before_new_file_and_sibling_prefix_remain_valid(self):
  with tempfile.TemporaryDirectory() as t:
   rows=[('usr/lib/.wh..wh..opq','file',b''),('usr/lib-other','file',b'sibling'),('usr/lib/target','file',b'new')];r=self.reader(Path(t),[self.layer(rows)]);self.assertEqual(Path(r.collect(['/usr/lib/target'])['/usr/lib/target']['data_path']).read_bytes(),b'new')
 def test_hash_mode_archive_drift_and_existing_output_reject(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);r=self.reader(p,[tarbytes([('usr/lib/target',b'bad')])])
   with self.assertRaises(ValueError):r.collect(['/usr/lib/target'])
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);r=self.reader(p,[tarbytes([('usr/lib/target',b'new')])]);r.path.write_bytes(b'changed')
   with self.assertRaises(ValueError):r.collect(['/usr/lib/target'])
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);r=self.reader(p,[tarbytes([('usr/lib/target',b'new')])]);check=r.check
   with self.assertRaises(ValueError):image.SelectedImage(r.path,r.inventory,check,p/'out',deadline=time.monotonic()+5)
 def test_provider_policy_is_deterministic_and_rejects_unknown_tokens(self):
  m=self.inventory();row=dict(m['entries'][1]);row['path']='/usr/lib/x86_64-linux-gnu/libsample.so';m['entries'].append(row);row=dict(row);row['path']=image.PANDA+'/libsample.so';m['entries'].append(row);m['entries'].sort(key=lambda r:r['path']);r=image.Inventory(m)
  self.assertEqual(r.select(image.PANDA+'/other.so','libsample.so',dict(rpath='$ORIGIN')),image.PANDA+'/libsample.so')
  self.assertEqual(r.select(image.PANDA+'/other.so','libsample.so',dict(rpath='$ORIGIN',runpath='/usr/lib/x86_64-linux-gnu')),'/usr/lib/x86_64-linux-gnu/libsample.so')
  for value in ('$LIB','relative',':$ORIGIN'):
   with self.assertRaises(ValueError):r.select(image.LIB,'libsample.so',dict(rpath=value))
 def test_selection_count_and_deadline_are_bounded(self):
  with tempfile.TemporaryDirectory() as t:
   r=self.reader(Path(t),[tarbytes([('usr/lib/target',b'new')])])
   with self.assertRaises(ValueError):r.collect(['/usr/lib/f'+str(n) for n in range(65)])
   r.stop=time.monotonic()-1
   with self.assertRaises(ValueError):r.collect(['/usr/lib/target'])
 def test_selected_mode_and_aggregate_bytes_reject(self):
  with tempfile.TemporaryDirectory() as t:
   m=self.inventory();m['entries'][1]['mode']=0o755;r=self.reader(Path(t),[tarbytes([('usr/lib/target',b'new')])],m)
   with self.assertRaisesRegex(ValueError,'bytes/mode mismatch'):r.collect(['/usr/lib/target'])
  with tempfile.TemporaryDirectory() as t:
   m=self.inventory();m['entries']=[dict(path='/usr/lib/f'+str(n),kind='file',mode=0o644,nbytes=64*1024**2,sha256='0'*64) for n in range(5)];r=self.reader(Path(t),[tarbytes([('irrelevant',b'x')])],m)
   with self.assertRaisesRegex(ValueError,'total byte budget'):r.collect([r['path'] for r in m['entries']])
 def test_metadata_output_budget_accounts_for_existing_provider_data(self):
  from scripts import audit_panda_sdk_link as audit
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'owned.data').write_bytes(b'x'*80)
   with self.assertRaisesRegex(ValueError,'audit output budget'):audit.write_json(p/'report.json',{'large':'x'*100},p,limit=128)
   self.assertLessEqual(sum(x.stat().st_size for x in p.iterdir()),128)
 def test_failed_positive_report_write_cannot_leave_positive_status(self):
  from scripts import audit_panda_sdk_link as audit
  from types import SimpleNamespace
  authority=json.loads((image.ROOT/image.AUTH).read_text());real=audit.write_json;raised=[]
  def writer(path,value,root,**kw):
   if value.get('status')=='STATIC_SYMBOLS_AVAILABLE_NOT_RUNTIME' and not raised:raised.append(True);raise ValueError('injected write failure')
   return real(path,value,root,**kw)
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);candidate=p/'candidate.data';candidate.write_bytes(b'CPU DATA')
   with patch.object(audit.archive,'inspect_save_archive',return_value=authority['archive']),patch.object(image,'SelectedImage',return_value=SimpleNamespace(cache={})),patch.object(image,'provider_graph',return_value=({'root_strong_symbols_available':True},{})),patch.object(audit,'write_json',side_effect=writer):
    with self.assertRaisesRegex(ValueError,'injected write failure'):audit.audit(p/'unused-image',candidate,p/'out')
   self.assertEqual(json.loads((p/'out/audit.json').read_text())['status'],'FAILED')
if __name__=='__main__':unittest.main()
