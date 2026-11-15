import struct,subprocess,tempfile,unittest
from pathlib import Path
from scripts import panda_sdk_cg_eigen_layout as l
class LiteralTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.words=[0x50414e4441434732,2,8,0,1,88,104,848,3984,0x670,0x688,0x68c,1,1,16,16]
  for label,extra in [('good','__attribute__((constructor)) static void unrelated(void){}'),('reloc','extern int variable; __attribute__((section(".panda_cg_layout_v2"))) void *wrong=&variable;')]:
   p=cls.root/(label+'.c');text='__attribute__((used,section(".panda_cg_layout_v2"))) const unsigned long long panda_cg_layout_v2[]={'+','.join(map(str,cls.words))+'};\n'+extra
   if label=='reloc':text='extern const unsigned long long variable; __attribute__((used,section(".panda_cg_layout_v2"))) const unsigned long long *const panda_cg_layout_v2[16]={&variable};'
   p.write_text(text);subprocess.run(['/usr/bin/gcc','-c',str(p),'-o',str(cls.root/(label+'.o'))],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_parent_init_is_data_but_selected_relocation_rejects(self):
  raw=(self.root/'good.o').read_bytes();r=l.extract_literal(raw);self.assertEqual(len(r['raw']),128);self.assertEqual(l.validate_descriptor(r['raw'])['offsets'],dict(vendor=0x670,major=0x688,minor=0x68c));self.assertFalse(r['target_execution']);self.assertIn(b'.init_array',raw)
  with self.assertRaises(ValueError):l.extract_literal((self.root/'reloc.o').read_bytes())
 def test_descriptor_flags_truncation_duplicate_and_relocation_info_reject(self):
  original=(self.root/'good.o').read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',original);sections=[struct.unpack_from('<IIQQQQIIQQ',original,h[6]+64*i) for i in range(h[12])];names=original[sections[h[13]][4]:sections[h[13]][4]+sections[h[13]][5]];target=next(i for i,s in enumerate(sections) if names[s[0]:names.find(b'\0',s[0])]==b'.panda_cg_layout_v2')
  variants=[]
  for flags in [3,6]:
   raw=bytearray(original);struct.pack_into('<Q',raw,h[6]+64*target+8,flags);variants.append(bytes(raw))
  raw=bytearray(original);other=next(i for i,s in enumerate(sections) if i!=target and s[1]==1 and s[5]);struct.pack_into('<I',raw,h[6]+64*other,sections[target][0]);variants.append(bytes(raw))
  raw=bytearray(original);rel=next(i for i,s in enumerate(sections) if s[1]==4);struct.pack_into('<I',raw,h[6]+64*rel+44,target);variants.append(bytes(raw));variants.extend([original[:100],b'x'*1024,b'x'*(1024**2+1)])
  for raw in variants:
   with self.assertRaises(ValueError):l.extract_literal(raw)
 def test_fixed_words_effective_flags_and_raw_parent_binding(self):
  r=l.extract_literal((self.root/'good.o').read_bytes());d=l.validate_descriptor(r['raw']);self.assertEqual(d['vector_alignment'],16)
  for index,value in [(0,0),(1,1),(3,1),(4,0),(12,0),(13,0),(14,4),(15,8)]:
   words=self.words.copy();words[index]=value
   with self.assertRaises(ValueError):l.validate_descriptor(struct.pack('<16Q',*words))
  with self.assertRaises(ValueError):l.verify_pair((self.root/'good.o').read_bytes(),r['raw'][:-1]+b'\1')
if __name__=='__main__':unittest.main()
