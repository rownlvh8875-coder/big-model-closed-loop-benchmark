"""The sole review's two admission gaps, with safe CPU protocol fixtures."""
import json,tempfile,unittest
from pathlib import Path
from tests import test_sdk3_pixel_geometry_budget_host as fixtures
from scripts import run_sdk3_pixel_geometry_budget as h,sdk3_pixel_geometry as g
write=fixtures.write

class ReviewRegressions(unittest.TestCase):
    def test_reversed_shortened_or_translated_segment_cannot_erase_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.GeometryAdmission().fixture(d);path=dest/'geometry-observer.json';raw=path.read_bytes()
            for mode in ('reverse','shorten','translate'):
                m=json.loads(raw);geometry=m['geometry']
                for ray in geometry['rays']:
                    if mode=='reverse':ray['direction']=[0.,0.,-1.]
                    elif mode=='shorten':ray['max_distance']=.1
                    else:ray['origin'][2]+=10.
                triangles,_=g.load_geometry_archive(dest/'geometry.npz',geometry['triangle_archive']);geometry['hits']=g.all_ray_hits(triangles,geometry['rays']);write(path,m)
                with self.subTest(mode=mode),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_impossible_complete_mesh_counters_and_primitive_ranges_reject(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.GeometryAdmission().fixture(d);path=dest/'geometry-observer.json';raw=path.read_bytes()
            for key,value in [('vertices_read',0),('nodes_seen',0),('source_primitive_count',0),('node_ordinal',1)]:
                m=json.loads(raw)
                if key in ('vertices_read','nodes_seen'):m['geometry']['counts'][key]=value
                else:m['geometry']['meshes'][0][key]=value
                write(path,m)
                with self.subTest(key=key),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_partial_scan_allows_unfinished_vertex_and_primitive_work_without_pass(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.GeometryAdmission().fixture(d);path=dest/'geometry-observer.json';m=json.loads(path.read_text());m['geometry'].update(scan_finished_within_budget=False,truncation_reasons=['time_budget'],cpu_scan_seconds=46.);m['geometry']['counts']['vertices_read']=4;m['geometry']['meshes'][0]['source_primitive_count']=2;write(path,m);r=h.validate_receipt(dest,ref,nonce);self.assertTrue(r['geometry_recorded']);self.assertFalse(r['geometry_scan_finished']);self.assertFalse(r['renderer_diagnostic_passed'])
