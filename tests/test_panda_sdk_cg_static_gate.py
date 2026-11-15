import json,shutil,struct,subprocess,tempfile,unittest
from pathlib import Path
from scripts import panda_sdk_cg_static_gate as g
class GateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
  for name,offsets in [('new',(0x688,0x68c,0x670)),('old',(0x618,0x61c,0x600))]:
   text=['.text']
   for symbol,offset,head in [(g.MAJOR,offsets[0],'8b87'),(g.MINOR,offsets[1],'8b87'),(g.VENDOR,offsets[2],'488b86')]:
    raw=bytes.fromhex(head)+struct.pack('<I',offset)+b'\xc3';text += [f'.global {symbol}',f'.type {symbol}, @function',symbol+':','.byte '+','.join(str(x) for x in raw),f'.size {symbol}, .-{symbol}']
   text+=['.data','.global '+g.VTABLE,'.type '+g.VTABLE+', @object',g.VTABLE+':','.zero 1024','.size '+g.VTABLE+',1024'];src=cls.root/(name+'.S');src.write_text('\n'.join(text)+'\n');subprocess.run(['/usr/bin/gcc','-nostdlib','-shared','-fPIC',str(src),'-o',str(cls.root/(name+'.so'))],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  text=(cls.root/'new.S').read_text().replace('.type '+g.MAJOR+', @function','.type '+g.MAJOR+', @gnu_indirect_function');(cls.root/'ifunc.S').write_text(text);subprocess.run(['/usr/bin/gcc','-nostdlib','-shared','-fPIC',str(cls.root/'ifunc.S'),'-o',str(cls.root/'ifunc.so')],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  vals=[g.MAGIC,1,8,0,1,96,144,912,8192,0x670,0x688,0x68c]
  for name,extra in [('layout',''),('code','int forbidden(void){return 1;}'),('init','__attribute__((section(".init_array"))) void *bad[1]={0};'),('reloc','extern int missing; void *pointer=&missing;')]:
   src=cls.root/(name+'.c');src.write_text('__attribute__((used,section(".panda_cg_layout"))) const unsigned long long layout[]={'+','.join(str(x) for x in vals)+'};\n'+extra);subprocess.run(['/usr/bin/gcc','-c',str(src),'-o',str(cls.root/(name+'.o'))],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_old_and_forged_offsets_reject(self):
  new=g.candidate_offsets((self.root/'new.so').read_bytes());old=g.candidate_offsets((self.root/'old.so').read_bytes());layout=g.layout_from_object((self.root/'layout.o').read_bytes());g.check_layout(new,layout)
  with self.assertRaises(ValueError):g.check_layout(old,layout)
  fake=dict(layout,offsets=old['offsets'])
  with self.assertRaises(ValueError):g.check_layout(new,fake)
 def test_unknown_instruction_and_truncated_elf_reject(self):
  for raw in [b'\x90'*7,b'\x8b\x87'+b'\0'*3,b'\xc3']:
   with self.assertRaises(ValueError):g.decode_int_getter(raw)
  for raw in [b'\x90'*10+b'\x48\x8b\x86'+struct.pack('<I',0x670),b'\xc3']:
   with self.assertRaises(ValueError):g.decode_vendor_getter(raw)
  with self.assertRaises(ValueError):g.candidate_offsets((self.root/'new.so').read_bytes()[:100])
 def test_descriptor_code_initializers_magic_and_bounds_reject(self):
  for name in ['code','init','reloc']:
   with self.assertRaises(ValueError):g.layout_from_object((self.root/(name+'.o')).read_bytes())
  raw=bytearray((self.root/'layout.o').read_bytes());at=raw.find(struct.pack('<Q',g.MAGIC));self.assertGreater(at,0);raw[at]=0
  with self.assertRaises(ValueError):g.layout_from_object(bytes(raw))
  with self.assertRaises(ValueError):g.layout_from_object(b'not ELF')
 def test_no_runtime_promotion(self):
  result=g.audit_candidate(self.root/'new.so',self.root/'layout.o',{},self.root/'absent',{})
  self.assertEqual(result['status'],'STATIC_CG_CANDIDATE_REJECTED');self.assertFalse(result['native_admitted']);self.assertFalse(result['full_object_abi_qualified']);self.assertFalse(result['previous_abort_fixed']);self.assertFalse(result['candidate_installed']);self.assertTrue(result['reasons'])
 def test_vendor_known_prefix_and_old_offset_bytes(self):
  self.assertEqual(g.decode_vendor_getter(bytes.fromhex('488b86')+struct.pack('<I',0x670)+b'\xc3'),0x670)
  self.assertEqual(g.decode_vendor_getter(bytes.fromhex('41544881c6')+struct.pack('<I',0x670)+bytes.fromhex('4989fce8000000004c89e0415cc3')),0x670)
 def test_changed_provider_and_weak_exception_reject(self):
  with self.assertRaises(ValueError):g.check_symbol_availability(dict(root_strong_symbols_available=True,missing=[],unsupported_features=[],weak_unresolved=[dict(name='unlisted')]))
  g.check_symbol_availability(dict(root_strong_symbols_available=True,missing=[],unsupported_features=[],weak_unresolved=[dict(name=n) for n in g.WEAK]))
 def test_getter_ifunc_rejected(self):
  with self.assertRaises(ValueError):g.candidate_offsets((self.root/'ifunc.so').read_bytes())
if __name__=='__main__':unittest.main()

class CompleteVendorTests(unittest.TestCase):
 def test_decoy_load_and_unknown_suffix_reject(self):
  good=bytes.fromhex('488b86')+struct.pack('<I',0x670)
  for raw in [good+bytes.fromhex('488b86')+struct.pack('<I',0x600)+b'\xc3',good+b'\x90\xc3',good+b'\xc3\x90']:
   with self.assertRaises(ValueError):g.decode_vendor_getter(raw)
  self.assertEqual(g.decode_vendor_getter(good+b'\xc3'),0x670)

 def test_complete_pinned_old_string_copy_stays_negative(self):
  raw=(g.ROOT/'docs/evidence/panda-sdk-link-audit-01/before-review/build/candidate-libpandagl.so.data').read_bytes();code=g.candidate_offsets(raw);self.assertEqual(code['offsets'],dict(major=0x618,minor=0x61c,vendor=0x600))

 def test_string_copy_shape_cannot_call_an_unrelated_function(self):
  raw=bytearray((g.ROOT/'docs/evidence/panda-sdk-link-audit-01/before-review/build/candidate-libpandagl.so.data').read_bytes());meta=g.elf.inspect_elf(bytes(raw));loads=g.elf_ranges(bytes(raw));vendor=next(r for r in meta['exports'] if r['name']==g.VENDOR);other=next(r for r in meta['exports'] if r['name']==g.MAJOR);segment=next(p for p in loads if p['vaddr']<=vendor['value']<p['vaddr']+p['filesz']);start=segment['offset']+vendor['value']-segment['vaddr'];struct.pack_into('<i',raw,start+56,other['value']-(vendor['value']+60))
  with self.assertRaises(ValueError):g.candidate_offsets(bytes(raw))
