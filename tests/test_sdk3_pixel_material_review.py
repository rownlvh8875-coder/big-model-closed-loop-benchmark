"""Single-review evidence-admission regressions; CPU only."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from tests import test_sdk3_pixel_material_host as fixtures
from scripts import run_sdk3_pixel_material as h
write=fixtures.write

class ReviewRegressions(unittest.TestCase):
    def test_render_state_pointer_must_match_geometry_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.MaterialAdmission().fixture(d);path=dest/'material.json';m=json.loads(path.read_text());m['meshes'][0]['net_state_pointer']=999999;write(path,m)
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_missing_nonfinite_or_inconsistent_material_values_reject(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.MaterialAdmission().fixture(d);path=dest/'material.json';raw=path.read_bytes()
            for bad in [{},{'available':True,'text':'invalid','name':'x','shininess':float('nan')},{'available':True,'text':'invalid','name':'x','shininess':0.,'diffuse':{'api_available':True,'defined':True,'value':[float('inf'),1.]}}]:
                m=json.loads(raw);m['meshes'][0]['material']=bad;write(path,m)
                with self.subTest(bad=bad),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_cm_off_one_requires_actual_uncompressed_extent(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.MaterialAdmission().fixture(d);path=dest/'material.json';m=json.loads(path.read_text());m['textures'][0]['ram'].update(compression=1,expected_nbytes=7);write(path,m)
            with self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_ram_and_asset_availability_cannot_contradict_their_source(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.MaterialAdmission().fixture(d);path=dest/'material.json';raw=path.read_bytes()
            for kind,bad in [('asset',dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=True)),('ram',dict(status='UNAVAILABLE_NO_PATH')),('ram',dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=True))]:
                m=json.loads(raw);m['textures'][0][kind]=bad
                if kind=='ram':m['bytes_captured']=0;(dest/'material-001-ram.bin').unlink(missing_ok=True)
                else:(dest/'material-001-ram.bin').write_bytes(b'abc')
                write(path,m)
                with self.subTest(kind=kind,bad=bad),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_explicit_unavailable_material_is_valid_cpu_state(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.MaterialAdmission().fixture(d);path=dest/'material.json';m=json.loads(path.read_text());m['meshes'][0]['material']=dict(available=False,text='None');write(path,m);r=h.validate_receipt(dest,ref,nonce);self.assertTrue(r['material_recorded']);self.assertFalse(r['gpu_material_result_proven'])
    def test_specific_compressed_ram_receipt_keeps_expected_uncompressed_size(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.MaterialAdmission().fixture(d);path=dest/'material.json';m=json.loads(path.read_text());raw=b'\xff\xff\x00\x00\x00\x00\x00\x00';(dest/'material-001-ram.bin').write_bytes(raw);texture=m['textures'][0];texture.update(x_size=4,y_size=4);texture['ram'].update(compression=4,expected_nbytes=48,nbytes=8,sha256=hashlib.sha256(raw).hexdigest());m['bytes_captured']=8;write(path,m);r=h.validate_receipt(dest,ref,nonce);self.assertEqual(r['material']['captured_bytes'],8);self.assertFalse(r['gpu_material_result_proven'])
