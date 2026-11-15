import hashlib,io,tarfile,tempfile,unittest
from pathlib import Path
from scripts import panda_sdk_cg_inputs as cg

def archive(rows):
 out=io.BytesIO()
 with tarfile.open(fileobj=out,mode='w:gz') as t:
  for name,data,kind,target in rows:
   m=tarfile.TarInfo(name);m.type=kind;m.linkname=target;m.size=len(data);t.addfile(m,io.BytesIO(data) if kind==tarfile.REGTYPE else None)
 return out.getvalue()
def fixture():
 rows=[('usr/include/Cg/cg.h',b'#define CG_VERSION_NUM 3100\n',tarfile.REGTYPE,''),('usr/include/Cg/cgGL.h',b'#include <Cg/cg.h>\n',tarfile.REGTYPE,'')]
 pins={n:dict(nbytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b,_,_ in rows};return rows,pins
class InputsTests(unittest.TestCase):
 def test_exact_header_and_image_provider_selection(self):
  rows,pins=fixture();rows.append(('usr/lib64/libCg.so',b'not a provider',tarfile.REGTYPE,''));got=cg.extract_headers(archive(rows),pins);self.assertEqual(set(got),set(pins));self.assertEqual(got['usr/include/Cg/cg.h'],rows[0][1])
 def test_parser_stub_and_toolkit_or_trace_hash_reject(self):
  rows,pins=fixture();rows[0]=(rows[0][0],b'typedef enum {} CGprofile;',tarfile.REGTYPE,'')
  with self.assertRaises(ValueError):cg.extract_headers(archive(rows),pins)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'libCg.so';p.write_bytes(b'Trace');expected={'libCg.so':dict(nbytes=6,sha256=hashlib.sha256(b'image!').hexdigest())}
   with self.assertRaises(ValueError):cg.verify_providers({'libCg.so':p},expected)
 def test_unsafe_duplicate_and_selected_link_reject(self):
  rows,pins=fixture()
  for extra in [('../escape',b'',tarfile.REGTYPE,''),('/absolute',b'',tarfile.REGTYPE,''),rows[0],('usr/include/Cg/cg.h',b'',tarfile.SYMTYPE,'../../bad')]:
   with self.subTest(name=extra[0]),self.assertRaises(ValueError):cg.extract_headers(archive(rows+[extra]),pins)
 def test_missing_header_and_declared_oversize_reject(self):
  rows,pins=fixture()
  with self.assertRaises(ValueError):cg.extract_headers(archive(rows[:1]),pins)
  with self.assertRaises(ValueError):cg.extract_headers(archive(rows),{**pins,rows[0][0]:dict(nbytes=2**21,sha256='0'*64)})
 def test_regular_provider_only_and_exact_set(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'provider';p.write_bytes(b'original');pins={'libCg.so':dict(nbytes=8,sha256=hashlib.sha256(b'original').hexdigest())};self.assertEqual(cg.verify_providers({'libCg.so':p},pins)['libCg.so']['sha256'],pins['libCg.so']['sha256'])
   q=Path(d)/'alias';q.symlink_to(p)
   with self.assertRaises(ValueError):cg.verify_providers({'libCg.so':q},pins)
   with self.assertRaises(ValueError):cg.verify_providers({'libCg.so':p,'Trace':p},pins)
 def test_forged_authority_and_existing_output_never_write(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=p/'authority';a.write_text('{}');o=p/'out';o.mkdir();(o/'keep').write_text('unchanged')
   with self.assertRaises(ValueError):cg.qualify_inputs(p/'missing',a,{},o)
   self.assertEqual((o/'keep').read_text(),'unchanged')
if __name__=='__main__':unittest.main()
