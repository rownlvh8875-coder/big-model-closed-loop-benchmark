"""Pure CPU contracts for UV math and resident/bounded data reads."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from scripts import sdk3_pixel_material as m

class Buffer:
    def __init__(self,data,length=None):self.data=data;self.length=len(data) if length is None else length;self.data_reads=0
    def __len__(self):return self.length
    def getData(self):self.data_reads+=1;return self.data
class Texture:
    def __init__(self,resident=True,expected=3,buffer=None):self.resident=resident;self.expected=expected;self.buffer=buffer or Buffer(b'abc');self.ram_calls=0
    def hasRamImage(self):return self.resident
    def getExpectedRamImageSize(self):return self.expected
    def getRamImageCompression(self):return 0
    def getRamImage(self):self.ram_calls+=1;return self.buffer

class MaterialMathAndIO(unittest.TestCase):
    def test_actual_barycentric_uv_and_homogeneous_texture_transform(self):
        self.assertEqual(m.interpolate_uv([[0,0],[2,0],[0,2]],[.25,.25,.5]),[.5,1.])
        matrix=[[2,0,0,0],[0,3,0,0],[0,0,1,0],[1,-1,0,1]]
        self.assertEqual(m.transform_uv([.25,.5],matrix),[1.5,.5,0.,1.])
    def test_bad_weights_nonfinite_or_wrong_attribute_shape_reject(self):
        for uv,b in [([[0,0],[1,0],[0,1]],[1,1,1]),([[0,0],[1,0],[0,1]],[-.1,.1,1]),([[0,0],[float('nan'),0],[0,1]],[1,0,0]),([[0,0],[1,0]],[.5,.5,0])]:
            with self.subTest(uv=uv,b=b),self.assertRaises(ValueError):m.interpolate_uv(uv,b)
    def test_absent_ram_never_calls_get_image(self):
        with tempfile.TemporaryDirectory() as td:
            t=Texture(resident=False);r=m.capture_cached_ram(t,m.BoundedStore(Path(td)));self.assertEqual(r['status'],'UNAVAILABLE_NOT_RESIDENT');self.assertEqual(t.ram_calls,0);self.assertEqual(list(Path(td).iterdir()),[])
    def test_expected_or_actual_oversize_stops_before_data_copy(self):
        with tempfile.TemporaryDirectory() as td:
            store=m.BoundedStore(Path(td),max_file=4,max_total=8);t=Texture(expected=9);self.assertEqual(m.capture_cached_ram(t,store)['status'],'UNAVAILABLE_LIMIT');self.assertEqual(t.ram_calls,0)
            b=Buffer(b'abc',length=9);t=Texture(expected=3,buffer=b);self.assertEqual(m.capture_cached_ram(t,store)['status'],'UNAVAILABLE_LIMIT');self.assertEqual(b.data_reads,0)
    def test_resident_raw_bytes_are_bound_by_size_and_sha(self):
        with tempfile.TemporaryDirectory() as td:
            store=m.BoundedStore(Path(td));t=Texture();r=m.capture_cached_ram(t,store);self.assertEqual(r['status'],'CAPTURED');self.assertEqual((Path(td)/r['file']).read_bytes(),b'abc');self.assertEqual(r['sha256'],hashlib.sha256(b'abc').hexdigest());self.assertEqual(r['nbytes'],3);self.assertEqual(t.ram_calls,1)
    def test_asset_symlink_escape_or_oversize_never_copies(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);allowed=root/'assets';allowed.mkdir();outside=root/'outside.png';outside.write_bytes(b'secret');(allowed/'escape.png').symlink_to(outside);out=root/'out';out.mkdir();store=m.BoundedStore(out,max_file=4,max_total=8)
            self.assertEqual(store.copy_asset(allowed/'escape.png',[allowed])['status'],'UNAVAILABLE_OUTSIDE_ASSET_ROOT');big=allowed/'large.png';big.write_bytes(b'12345');self.assertEqual(store.copy_asset(big,[allowed])['status'],'UNAVAILABLE_LIMIT');self.assertEqual(list(out.iterdir()),[])
    def test_readonly_asset_and_global_budget_are_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);assets=root/'assets';assets.mkdir();image=assets/'color.png';image.write_bytes(b'1234');out=root/'out';out.mkdir();store=m.BoundedStore(out,max_file=4,max_total=6);a=store.copy_asset(image,[assets]);self.assertEqual(a['status'],'CAPTURED');self.assertEqual((out/a['file']).read_bytes(),b'1234');self.assertEqual(store.save(b'abc','ram')['status'],'UNAVAILABLE_LIMIT');self.assertEqual(store.used,4)
