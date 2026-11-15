import struct,subprocess,tempfile,unittest
from pathlib import Path
from scripts import panda_sdk_cg_eigen_gate as g
# Handwritten inert ELF fixtures; none is loaded or called.
VENDOR13=bytes.fromhex('534889fb4883ec10488b86600600008b50f8488d78e885d2781a483b3d7b2b090075294889034883c4104889d85bc30f1f440000488d74240f31d2e8ac90feff4889034883c4104889d85bc3488b15412f0900803a00740c8340f801ebc5660f1f440000488d48f8f0830101ebb5')
class GateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
  for label,cet,offsets,ifunc in [('new',True,(0x688,0x68c,0x670),False),('old',True,(0x678,0x67c,0x660),False),('plain',False,(0x688,0x68c,0x670),False),('ifunc',True,(0x688,0x68c,0x670),True)]:
   lines=['.text']
   for name,offset,head in [(g.MAJOR,offsets[0],'8b87'),(g.MINOR,offsets[1],'8b87'),(g.VENDOR,offsets[2],'488b86')]:
    raw=(bytes.fromhex('f30f1efa') if cet else b'')+bytes.fromhex(head)+struct.pack('<I',offset)+b'\xc3';lines+=['.globl '+name,'.type '+name+(', @gnu_indirect_function' if ifunc and name==g.MAJOR else ', @function'),name+':','.byte '+','.join(str(x) for x in raw),'.size '+name+',.-'+name]
   lines+=['.data','.globl '+g.VTABLE,'.type '+g.VTABLE+', @object',g.VTABLE+':','.zero 1024','.size '+g.VTABLE+',1024'];p=cls.root/(label+'.S');p.write_text('\n'.join(lines)+'\n');subprocess.run(['/usr/bin/gcc','-nostdlib','-shared','-fPIC',str(p),'-o',str(cls.root/(label+'.so'))],capture_output=True,check=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_cet_complete_getters_and_consumed_candidate_rejects(self):
  for label in ['new','plain']:self.assertEqual(g.candidate_offsets((self.root/(label+'.so')).read_bytes())['offsets'],g.EXPECTED)
  old=g.candidate_offsets((self.root/'old.so').read_bytes())
  with self.assertRaises(ValueError):g.check_offsets(old['offsets'],dict(offsets=old['offsets']))
  for raw in [bytes.fromhex('f30f1efa')*2+bytes.fromhex('8b8788060000c3'),bytes.fromhex('f30f1e'),bytes.fromhex('8b8788060000c390')]:
   with self.assertRaises(ValueError):g.decode_int_getter(raw)
  with self.assertRaises(ValueError):g.candidate_offsets((self.root/'ifunc.so').read_bytes())
 def test_complete_vendor_shape_and_decoy_suffix(self):
  self.assertEqual(g.decode_vendor_getter(bytes.fromhex('f30f1efa')+VENDOR13),0x660)
  raw=bytes.fromhex('488b8670060000488b8660060000c3')
  with self.assertRaises(ValueError):g.decode_vendor_getter(raw)
  for raw in [VENDOR13+b'\x90',VENDOR13[:-1],bytes.fromhex('f30f1efa')*2+VENDOR13]:
   with self.assertRaises(ValueError):g.decode_vendor_getter(raw)
 def test_unbacked_and_overlapping_symbols_reject(self):
  raw=(self.root/'new.so').read_bytes()
  with self.assertRaises(ValueError):g.candidate_offsets(raw[:100])
  # A real dynamic symbol table substitution moves minor onto major without changing file bytes.
  meta=g.elf.inspect_elf(raw);major=next(r for r in meta['exports'] if r['name']==g.MAJOR);minor=next(r for r in meta['exports'] if r['name']==g.MINOR);from unittest.mock import patch
  minor['value']=major['value']
  with patch.object(g.elf,'inspect_elf',return_value=meta):
   with self.assertRaises(ValueError):g.candidate_offsets(raw)
 def test_no_runtime_promotion_or_unlisted_weak_exceptions(self):
  r=g.audit_candidate(self.root/'new.so',self.root/'absent',self.root/'absent',{},{});self.assertEqual(r['status'],'STATIC_CG_EIGEN_CANDIDATE_REJECTED')
  for k in ['native_admitted','full_object_abi_qualified','previous_abort_fixed','candidate_installed','runtime_mapping_qualified']:self.assertFalse(r[k])
  with self.assertRaises(ValueError):g.check_symbol_availability(dict(root_strong_symbols_available=True,missing=[],unsupported_features=[],weak_unresolved=[dict(name='not_allowed')]))
if __name__=='__main__':unittest.main()

class CopyCallTests(unittest.TestCase):
 def test_real_cet_plt_copy_binding_and_unrelated_target(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);lines=['.text'];clone='_ZNSs4_Rep8_M_cloneERKSaIcEm';body=bytearray(VENDOR13);struct.pack_into('<I',body,11,0x670)
   for name,offset in [(g.MAJOR,0x688),(g.MINOR,0x68c)]:
    raw=bytes.fromhex('f30f1efa8b87')+struct.pack('<I',offset)+b'\xc3';lines+=['.globl '+name,'.type '+name+', @function',name+':','.byte '+','.join(map(str,raw)),'.size '+name+',.-'+name]
   lines+=['.type '+clone+', @function','.globl '+g.VENDOR,'.type '+g.VENDOR+', @function',g.VENDOR+':','.byte '+','.join(map(str,bytes.fromhex('f30f1efa')+body[:59])),'call '+clone+'@PLT','.byte '+','.join(map(str,body[64:])) ,'.size '+g.VENDOR+',.-'+g.VENDOR,'.data','.globl '+g.VTABLE,'.type '+g.VTABLE+', @object',g.VTABLE+':','.zero 1024','.size '+g.VTABLE+',1024'];source=root/'copy.S';source.write_text('\n'.join(lines)+'\n');subprocess.run(['/usr/bin/gcc','-nostdlib','-shared','-fPIC','-Wl,-z,ibtplt',str(source),'-o',str(root/'copy.so')],capture_output=True,check=True)
   raw=(root/'copy.so').read_bytes();observed=g.candidate_offsets(raw);self.assertEqual(observed['offsets'],g.EXPECTED);meta=observed['loader'];v=next(r for r in meta['exports'] if r['name']==g.VENDOR);major=next(r for r in meta['exports'] if r['name']==g.MAJOR);p=next(p for p in g.elf_ranges(raw) if p['vaddr']<=v['value'] and v['value']+v['nbytes']<=p['vaddr']+p['filesz']);at=p['offset']+v['value']-p['vaddr'];bad=bytearray(raw);struct.pack_into('<i',bad,at+64,major['value']-(v['value']+68))
   with self.assertRaises(ValueError):g.candidate_offsets(bytes(bad))
