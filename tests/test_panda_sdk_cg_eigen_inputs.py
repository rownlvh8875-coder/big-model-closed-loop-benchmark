import io,json,lzma,tarfile,tempfile,unittest
from pathlib import Path
from scripts import panda_sdk_cg_eigen_inputs as e

def package(rows):
 out=io.BytesIO()
 with tarfile.open(fileobj=out,mode='w') as t:
  for name,body,kind in rows:
   m=tarfile.TarInfo(name);m.type=kind;m.size=len(body) if kind==tarfile.REGTYPE else 0;m.linkname='Core' if kind in (tarfile.SYMTYPE,tarfile.LNKTYPE) else '';t.addfile(m,io.BytesIO(body))
 payload=lzma.compress(out.getvalue());raw=b'!<arch>\n'
 for name,body in [('debian-binary',b'2.0\n'),('control.tar.xz',lzma.compress(b'')),('data.tar.xz',payload)]:
  header=(name+'/').ljust(16)+'0'.ljust(12)+'0'.ljust(6)+'0'.ljust(6)+'100644'.ljust(8)+str(len(body)).ljust(10)+'`\n';raw+=header.encode()+body+(b'\n' if len(body)%2 else b'')
 return raw
class EigenTests(unittest.TestCase):
 def test_exact_pinned_eigen_headers(self):
  c=e.contract();p=e.ROOT/c['eigen_package_path']
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);r=e.qualify_eigen(p,root);self.assertEqual(r['status'],'EIGEN_HEADERS_QUALIFIED_DATA_ONLY');self.assertEqual(r['header_files'],530);self.assertEqual(r['header_nbytes'],8669561);self.assertEqual((root/'usr/include/eigen3/Eigen/src/misc/lapacke.h').stat().st_size,1058369);self.assertFalse(r['target_execution']);self.assertFalse(list(root.rglob('*.so*')));self.assertFalse(list(root.rglob('*.cmake')))
   with self.assertRaises(ValueError):e.qualify_eigen(p,root)
 def test_selected_path_link_duplicate_missing_and_digest_reject(self):
  name='usr/include/eigen3/Eigen/Core';body=b'fixture';pins={name:dict(nbytes=len(body),sha256=e.sha(body))};data=package([(name,body,tarfile.REGTYPE)]);self.assertEqual(e.parse_package(data,pins)[name],body)
  for rows in [[('../escape',body,tarfile.REGTYPE)],[(name,body,tarfile.SYMTYPE)],[(name,body,tarfile.LNKTYPE)],[(name,body,tarfile.REGTYPE)]*2,[(name,b'changed',tarfile.REGTYPE)],[]]:
   with self.assertRaises(ValueError):e.parse_package(package(rows),pins)
 def test_archive_inflation_member_and_header_bounds(self):
  with self.assertRaises(ValueError):e.parse_package(b'x'*(4*1024**2+1),{})
  with self.assertRaises(ValueError):e.parse_package(package([('large',b'x'*(33*1024**2),tarfile.REGTYPE)]),{})
  with self.assertRaises(ValueError):e.parse_package(package([(str(i),b'',tarfile.DIRTYPE) for i in range(2049)]),{})
  name='usr/include/eigen3/Eigen/Core';body=b'x'*(2*1024**2+1)
  with self.assertRaises(ValueError):e.parse_package(package([(name,body,tarfile.REGTYPE)]),{name:dict(nbytes=len(body),sha256=e.sha(body))})
 def test_changed_archive_and_host_alias_never_stage(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);fake=root/'bad.deb';fake.write_bytes(b'bad');dest=root/'private';dest.mkdir()
   with self.assertRaises(ValueError):e.qualify_eigen(fake,dest)
   (dest/'usr').symlink_to('/usr')
   with self.assertRaises(ValueError):e.qualify_eigen(e.ROOT/e.contract()['eigen_package_path'],dest)
   self.assertFalse((dest/'manifest.json').exists())
if __name__=='__main__':unittest.main()
