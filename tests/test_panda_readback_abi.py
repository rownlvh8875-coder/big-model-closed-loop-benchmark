"""Byte-level ELF mutations; no shared object is loaded or executed."""
import hashlib
import struct
import unittest
try:
    from scripts import panda_readback_abi as abi
except ImportError:
    abi=None

GSG=b'_ZN23GLGraphicsStateGuardian23framebuffer_copy_to_ramEP7TextureiiPK13DisplayRegionRK12RenderBuffer'

def elf_fixture():
    b=bytearray(0x48000);ident=b'\x7fELF\x02\x01\x01'+bytes(9)
    struct.pack_into('<16sHHIQQQIHHHHHH',b,0,ident,3,62,1,0,64,0x47000,0,64,56,2,64,4,0)
    struct.pack_into('<IIQQQQQQ',b,64,1,5,0x1000,0x29000,0,0x40000,0x40000,0x1000)
    struct.pack_into('<IIQQQQQQ',b,120,1,6,0x42000,0xc9000,0,0x4000,0x4000,0x1000)
    # Independent VA-to-offset mapping for this artificial ELF, not the real file.
    start=0x62c50-0x29000+0x1000;b[start:start+4227]=b'\x90'*4227
    call=0x6305c-0x29000+0x1000;b[call:call+5]=b'\xe8'+struct.pack('<i',0x29aa0-0x63061)
    plt=0x29aa0-0x29000+0x1000;b[plt:plt+6]=b'\xff\x25'+struct.pack('<i',0xcc550-(0x29aa0+6))
    strings=b'\0glReadPixels\0'+GSG+b'\0';b[0x46100:0x46100+len(strings)]=strings
    # Three dynamic symbols: null, GL import, outer GSG function.
    struct.pack_into('<IBBHQQ',b,0x46018,1,18,0,0,0,0)
    struct.pack_into('<IBBHQQ',b,0x46030,14,18,0,1,0x62c50,4227)
    struct.pack_into('<QQq',b,0x46300,0xcc550,(1<<32)|7,0)
    struct.pack_into('<IIQQQQIIQQ',b,0x47040,0,11,2,0,0x46000,72,2,0,8,24)
    struct.pack_into('<IIQQQQIIQQ',b,0x47080,0,3,2,0,0x46100,len(strings),0,0,1,0)
    struct.pack_into('<IIQQQQIIQQ',b,0x470c0,0,4,2,0,0x46300,24,1,0,8,24)
    return bytes(b)

def patch(b,offset,fmt,value):
    out=bytearray(b);struct.pack_into(fmt,out,offset,value);return bytes(out)

class PandaReadbackAbiTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(abi,'bounded pinned ELF ABI qualifier required')
    def test_structural_call_and_relocation_are_bound_without_claiming_pinned_identity(self):
        result=abi.inspect_elf(elf_fixture())
        self.assertEqual((result['method_va'],result['method_nbytes'],result['call_va'],result['return_va'],result['plt_va'],result['got_va']),
                         (0x62c50,4227,0x6305c,0x63061,0x29aa0,0xcc550))
        self.assertIs(result['pinned_identity_matched'],False);self.assertIs(result['runtime_admission_ready'],False)
    def test_synthetic_valid_structure_never_qualifies_as_pinned_panda(self):
        with self.assertRaises(ValueError):abi.qualify_elf(elf_fixture())
    def test_header_class_endian_machine_and_table_bounds_reject(self):
        b=elf_fixture()
        for off,fmt,value in ((4,'B',1),(5,'B',2),(16,'H',2),(18,'H',3),(32,'Q',len(b)),(56,'H',1000),(58,'H',1),(60,'H',1000)):
            with self.subTest(offset=off),self.assertRaises(ValueError):abi.inspect_elf(patch(b,off,fmt,value))
        for cut in (0,63,0x46310,0x470ff):
            with self.subTest(cut=cut),self.assertRaises(ValueError):abi.inspect_elf(b[:cut])
    def test_executable_mapping_overlap_writable_or_extent_drift_reject(self):
        b=elf_fixture()
        for off,fmt,value in ((68,'I',4),(68,'I',7),(96,'Q',1),(104,'Q',0),(136,'Q',0x62c50),(128,'Q',len(b))):
            with self.subTest(offset=off),self.assertRaises(ValueError):abi.inspect_elf(patch(b,off,fmt,value))
    def test_direct_call_plt_got_and_dynamic_import_mutations_reject(self):
        b=elf_fixture();call=0x6305c-0x29000+0x1000;plt=0x29aa0-0x29000+0x1000
        for off,fmt,value in ((call,'B',0x90),(call+1,'i',0),(plt,'B',0x90),(plt+2,'i',0),
                              (0x46300,'Q',0xcc558),(0x46308,'Q',(1<<32)|6),(0x46018+6,'H',1),
                              (0x46030+8,'Q',0x62c51),(0x470c0+40,'I',0),(0x46101,'B',ord('x'))):
            with self.subTest(offset=off),self.assertRaises(ValueError):abi.inspect_elf(patch(b,off,fmt,value))
    def test_duplicate_got_relocation_or_symbol_and_nonterminated_strings_reject(self):
        b=bytearray(elf_fixture());b[0x46318:0x46330]=b[0x46300:0x46318]
        struct.pack_into('<Q',b,0x470c0+32,48)
        with self.assertRaises(ValueError):abi.inspect_elf(bytes(b))
        b=bytearray(elf_fixture());b[0x46048:0x46060]=b[0x46030:0x46048];struct.pack_into('<Q',b,0x47040+32,96)
        with self.assertRaises(ValueError):abi.inspect_elf(bytes(b))
        b=bytearray(elf_fixture());b[0x46100+14+len(GSG)]=ord('x')
        with self.assertRaises(ValueError):abi.inspect_elf(bytes(b))

if __name__=='__main__':unittest.main()
