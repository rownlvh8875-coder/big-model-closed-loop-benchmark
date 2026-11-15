"""Compile harmless shared objects, inspect bytes; never load target libraries."""
import copy,os,struct,subprocess,tempfile,unittest
from pathlib import Path
try:from scripts import panda_sdk_link_elf as elf
except ImportError:elf=None
class LoaderSymbolTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);p=cls.root
  (p/'provider.cpp').write_text('#include <string>\nvoid panda_log(const std::string&) {}\n')
  (p/'consumer.cpp').write_text('#include <string>\nextern void panda_log(const std::string&); extern "C" void call_log(const std::string &s) { panda_log(s); }\n')
  env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}
  def run(args):subprocess.run(args,cwd=p,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
  run(['/usr/bin/g++','-shared','-fPIC','-D_GLIBCXX_USE_CXX11_ABI=0','-Wl,-soname,libprovider.so','provider.cpp','-o','libprovider.so'])
  for abi in (0,1):run(['/usr/bin/g++','-shared','-fPIC','-D_GLIBCXX_USE_CXX11_ABI='+str(abi),'consumer.cpp','-L.','-Wl,--no-as-needed','-lprovider','-o','consumer'+str(abi)+'.so'])
  (p/'version.c').write_text('int value(void) {return 1;}\n');(p/'use.c').write_text('extern int value(void);extern void absent(void) __attribute__((weak));int call(void){if(absent)absent();return value();}\n')
  for v in (1,2):
   (p/'version.map').write_text('ABI_'+str(v)+' { global: value; local: *; };\n');run(['/usr/bin/gcc','-shared','-fPIC','version.c','-Wl,--version-script=version.map','-Wl,-soname,libversion.so','-o','v'+str(v)+'.so'])
  (p/'libversion.so').write_bytes((p/'v1.so').read_bytes());run(['/usr/bin/gcc','-shared','-fPIC','use.c','-L.','-lversion','-o','use.so'])
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):self.assertIsNotNone(elf,'PT-only symbol/version inspector missing')
 def read(self,name):return elf.inspect_elf((self.root/name).read_bytes())
 def test_old_and_new_string_abi_mismatch_and_repair(self):
  provider=self.read('libprovider.so');bad=elf.available_imports(self.read('consumer1.so'),[provider]);good=elf.available_imports(self.read('consumer0.so'),[provider]);self.assertTrue(any('panda_log' in x['name'] for x in bad['missing']));self.assertFalse(any('panda_log' in x['name'] for x in good['missing']));self.assertFalse(good['native_admitted'])
 def test_required_version_and_weak_undefined_are_distinct(self):
  root=self.read('use.so');good=elf.available_imports(root,[self.read('v1.so')]);bad=elf.available_imports(root,[self.read('v2.so')]);self.assertFalse(any(x['name']=='value' for x in good['missing']));self.assertTrue(any(x['name']=='value' and x['version']=='ABI_1' for x in bad['missing']));self.assertTrue(any(x['name']=='absent' for x in good['weak_unresolved']))
 def test_sectionless_file_has_same_loader_metadata(self):
  b=bytearray((self.root/'use.so').read_bytes());struct.pack_into('<Q',b,40,0);struct.pack_into('<HHH',b,58,0,0,0);a=self.read('use.so');r=elf.inspect_elf(bytes(b));self.assertEqual(a['imports'],r['imports']);self.assertEqual(a['exports'],r['exports']);self.assertFalse(r['section_headers_used'])
 def test_bad_header_and_outside_dynamic_metadata_reject(self):
  raw=(self.root/'use.so').read_bytes()
  for data in (raw[:63],b'BAD!'+raw[4:]):
   with self.assertRaises(ValueError):elf.inspect_elf(data)
  b=bytearray(raw);header=struct.unpack_from('<16sHHIQQQIHHHHHH',b)
  for i in range(header[10]):
   ph=struct.unpack_from('<IIQQQQQQ',b,header[5]+56*i)
   if ph[0]==2:
    for at in range(ph[2],ph[2]+ph[5],16):
     tag,value=struct.unpack_from('<qQ',b,at)
     if tag==5:struct.pack_into('<Q',b,at+8,2**63);break
  with self.assertRaises(ValueError):elf.inspect_elf(bytes(b))
 def test_relocation_target_and_exported_code_must_be_in_mapped_spans(self):
  for case in ('relocation','function'):
   b=bytearray((self.root/('use.so' if case=='relocation' else 'v1.so')).read_bytes());h=struct.unpack_from('<16sHHIQQQIHHHHHH',b);ph=[struct.unpack_from('<IIQQQQQQ',b,h[5]+56*i) for i in range(h[10])];dyn=next(x for x in ph if x[0]==2);tags=dict(struct.unpack_from('<qQ',b,o) for o in range(dyn[2],dyn[2]+dyn[5],16))
   def offset(va):
    p=next(x for x in ph if x[0]==1 and x[3]<=va<x[3]+x[5]);return p[2]+va-p[3]
   if case=='relocation':
    at=offset(tags[7]);size=tags[8];slot=next(o for o in range(at,at+size,24) if struct.unpack_from('<Q',b,o+8)[0]>>32);struct.pack_into('<Q',b,slot,2**63)
   else:
    at=offset(tags[6]);slot=next(o for o in range(at,offset(tags[5]),24) if (struct.unpack_from('<IBBHQQ',b,o)[1]&15)==2 and struct.unpack_from('<IBBHQQ',b,o)[3]!=0);struct.pack_into('<Q',b,slot+8,2**63)
   with self.subTest(case=case),self.assertRaises(ValueError):elf.inspect_elf(bytes(b))
 def test_hidden_nondefault_export_cannot_satisfy_unversioned_import(self):
  root=dict(imports=[dict(name='x',version=None,version_library=None,binding=1,symbol_type=2)],unsupported_features=[]);provider=dict(path='CPU',soname='libx.so',exports=[dict(name='x',version='ABI_1',default_version=False,symbol_type=2)])
  r=elf.available_imports(root,[provider]);self.assertEqual(len(r['missing']),1);provider['exports'][0]['default_version']=True;self.assertFalse(elf.available_imports(root,[provider])['missing'])
 def test_large_but_bounded_relative_table_and_over_budget_reject(self):
  b=bytearray((self.root/'use.so').read_bytes());h=struct.unpack_from('<16sHHIQQQIHHHHHH',b);ph=[(h[5]+56*i,struct.unpack_from('<IIQQQQQQ',b,h[5]+56*i)) for i in range(h[10])];dyn=next(p for _,p in ph if p[0]==2);slot,p=max((r for r in ph if r[1][0]==1),key=lambda r:r[1][3]);start=(len(b)+7)&~7;va=p[3]+start-p[2];count=345403;b.extend(b'\0'*(start-len(b)));b.extend(struct.pack('<QQq',p[3],8,0)*count);extent=len(b)-p[2];struct.pack_into('<QQ',b,slot+32,extent,extent)
  for at in range(dyn[2],dyn[2]+dyn[5],16):
   tag,_=struct.unpack_from('<qQ',b,at)
   if tag==7:struct.pack_into('<Q',b,at+8,va)
   if tag==8:size_slot=at+8;struct.pack_into('<Q',b,size_slot,count*24)
  self.assertGreaterEqual(elf.inspect_elf(bytes(b))['relocation_count'],count)
  struct.pack_into('<Q',b,size_slot,(524288+1)*24)
  with self.assertRaisesRegex(ValueError,'relocation table extent'):elf.inspect_elf(bytes(b))
 def test_all_matching_candidates_are_reported_without_binding_authority(self):
  root=self.read('use.so');a=self.read('v1.so');b=copy.deepcopy(a);a['path']='one';b['path']='two';r=elf.available_imports(root,[a,b]);hit=next(x for x in r['resolved'] if x['name']=='value');self.assertEqual(hit['provider_candidates'],['one','two']);self.assertFalse(r['runtime_mapping_qualified'])
if __name__=='__main__':unittest.main()
