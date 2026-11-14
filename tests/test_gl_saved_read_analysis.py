"""Route comparison is not pixel equality or cross-cohort frame association."""
from copy import deepcopy
import importlib
from pathlib import Path
import tempfile
from hashlib import sha256
import unittest
from tests import test_gl_read_provenance as fixture
from scripts import gl_read_provenance as reducer
try:a=importlib.import_module('scripts.analyze_saved_gl_reads')
except ModuleNotFoundError as exc:
    if exc.name!='scripts.analyze_saved_gl_reads':raise
    a=None

class SavedReadAnalysisTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(a,'actual saved read-route consumer required')
    def data(self):return reducer.analyze(fixture.route_fixture()[0].rows)
    def test_route_comparison_ignores_command_ordinals_but_preserves_structure(self):
        x=self.data();y=deepcopy(x);y['reads'][0]['call']+=100
        r=a.compare_reports(x,y);self.assertTrue(r['reads'][0]['same_route_topology'])
        self.assertFalse(r['pixel_equality_proven']);self.assertFalse(r['sealed_frame_association_proven'])
    def test_changed_resolve_samples_or_scissor_is_visible(self):
        x=self.data()
        for mutate in (lambda y:y['reads'][0]['routes'][0].update(samples=8),
                       lambda y:next(n for n in y['nodes'] if n['kind']=='blit_possible_write')['state'].update({'cap:3089':True})):
            y=deepcopy(x);mutate(y)
            with self.subTest(mutate=mutate):self.assertFalse(a.compare_reports(x,y)['reads'][0]['same_route_topology'])
    def test_changed_read_endpoint_or_texture_lifetime_breaks_route_equality(self):
        x=self.data()
        for mutate in (lambda y:y['reads'][0].update(read_fbo=99),lambda y:y['reads'][0].update(read_buffer=0x8ce1),
                       lambda y:y['reads'][0]['source_descriptor'].update(epoch=2),
                       lambda y:y['reads'][0]['routes'][0].update(texture='c1/texture:1:2')):
            y=deepcopy(x);mutate(y)
            with self.subTest(mutate=mutate):self.assertFalse(a.compare_reports(x,y)['reads'][0]['same_route_topology'])
    def test_two_missing_routes_are_unobserved_not_equal(self):
        x=self.data();x['reads'][0]['routes']=[]
        self.assertIsNone(a.compare_reports(x,x)['reads'][0]['same_route_topology'])
    def test_read_count_or_camera_marker_mismatch_does_not_align(self):
        x=self.data();y=deepcopy(x);y['reads']=[]
        with self.assertRaises(ValueError):a.compare_reports(x,y)
        y=deepcopy(x);y['reads'][0]['markers']=['other camera']
        self.assertIsNone(a.compare_reports(x,y)['reads'][0]['same_route_topology'])
    def test_existing_output_is_preserved_before_any_decoder_action(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);sentinel=p/'original';sentinel.write_text('keep')
            with self.assertRaises(ValueError):a.run(p,p/'tool',p/'deb',p)
            self.assertEqual(sentinel.read_text(),'keep')
    def test_reducer_failure_closes_original_decoder_stream(self):
        self.assertTrue(hasattr(a,'analyze_events'),'decoder lifecycle consumer required')
        closed=[]
        def events():
            try:yield (1,'glUnsupportedWriter',[],None,0)
            finally:closed.append(True)
        with self.assertRaises(ValueError):a.analyze_events(events())
        self.assertEqual(closed,[True])
    def test_changed_source_cannot_get_fresh_preservation_assertion(self):
        self.assertTrue(hasattr(a,'verify_source_snapshot'),'current source hashing required')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);f=root/'legacy.py';f.write_bytes(b'original')
            expected={'legacy.py':sha256(b'original').hexdigest()}
            self.assertEqual(a.verify_source_snapshot(root,expected)['source_pins_preserved'],1)
            f.write_bytes(b'changed')
            with self.assertRaises(ValueError):a.verify_source_snapshot(root,expected)

if __name__=='__main__':unittest.main()
