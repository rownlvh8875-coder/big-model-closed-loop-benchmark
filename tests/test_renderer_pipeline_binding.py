"""Structural supplied classes only; no Panda imports or native authority."""
from copy import deepcopy
import importlib
import unittest
import ast
from pathlib import Path
from tests import test_renderer_pipeline_observer as synthetic
from tests.test_renderer_task_binding import Matrix,Node

try:
    binding=importlib.import_module('scripts.renderer_pipeline_binding')
except ModuleNotFoundError as exc:
    if exc.name!='scripts.renderer_pipeline_binding':raise
    binding=None


class PipelineBindingTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(binding,'structural pipeline binding required')
    def test_pinned_repo_ram_call_line_matches_ast_without_native_import(self):
        raw=(Path(__file__).resolve().parents[1]/'bigbench/metadrive_camera.py').read_bytes()
        calls=[n for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.Call) and ast.unparse(n.func)=='texture.getRamImageAs']
        self.assertEqual(len(calls),1)
        self.assertEqual(getattr(binding,'LINES',{}).get('road_image_as'),calls[0].lineno)
        self.assertEqual(getattr(binding,'LINES',{}).get('wide_image_as'),calls[0].lineno)
    def fixture(self):
        p,m,r,w,b=synthetic.fixture();e=p.env.engine
        e.main_camera=e.chase;e.main_camera.engine=e;e.main_camera.camera=e.camera=Node();e.main_camera.run_task=True
        e.main_camera._chase_task=e.main_camera.chase
        e.pssm.engine=e;e.pssm.num_splits=2
        class Rig:
            def get_mvp_array(self):return e.pssm.matrices
        e.pssm.camera_rig=Rig();e.graphicsEngine=e.graphics;r.copy_texture=r.storage;w.copy_texture=w.storage
        return e,b
    def bind(self,e,b,**kwargs):
        return binding.bind_engine(e,pssm_class=synthetic.PSSM,chase_class=synthetic.Chase,
            matrix_class=Matrix,igloop_function=synthetic.Engine.igloop,c_targets=b['c'],**kwargs)
    def test_exact_native_owner_structure_and_submission_named_getter_accounting(self):
        e,b=self.fixture();bound=self.bind(e,b);raw=deepcopy(e.pssm.matrices);s=bound['submission'](raw)
        self.assertEqual(s['matrices'],raw)
        self.assertEqual(bound['submission_counts'],dict(snapshots_attempted=1,snapshots_returned=1,
            named_getter_attempts=32,named_getter_returns=32,private_matrix_allocations=2,private_matrix_assignments=2,matrix_array_reads=2))
        self.assertIs(bound['python']['igLoop'].__self__,e)
        self.assertIs(bound['python']['road_ram'].__self__,e.sensors['bigbench_road'])
        self.assertFalse(bound['native_admission_proven'])
    def test_submitted_private_matrix_copies_do_not_alias_original(self):
        e,b=self.fixture();bound=self.bind(e,b);s=bound['submission'](e.pssm.matrices)
        e.pssm.matrices[0][0][0]=99.;self.assertEqual(s['matrices'][0][0][0],1.)
    def test_foreign_shader_render_and_ram_owners_are_rejected(self):
        for key,value in [('shader_inputs',[].extend),('render_frame',[].append),('road_image_as',bytearray().copy)]:
            e,b=self.fixture();b['c'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.bind(e,b)
    def test_changed_owner_after_binding_fails_before_more_getters(self):
        e,b=self.fixture();bound=self.bind(e,b);e.graphicsEngine=[]
        with self.assertRaises(ValueError):bound['submission'](e.pssm.matrices)
        self.assertEqual(bound['submission_counts']['named_getter_attempts'],0)
    def test_submission_cap_and_invalid_array_fail_closed(self):
        e,b=self.fixture();bound=self.bind(e,b,max_submissions=2)
        bound['submission'](e.pssm.matrices);bound['submission'](e.pssm.matrices)
        with self.assertRaises(ValueError):bound['submission'](e.pssm.matrices)
        self.assertEqual(bound['submission_counts']['named_getter_attempts'],64)
        for raw in ([],[[[float('nan')]*4 for _ in range(4)] for _ in range(2)]):
            e,b=self.fixture();bound=self.bind(e,b)
            with self.subTest(raw=raw),self.assertRaises(ValueError):bound['submission'](raw)
            self.assertEqual(bound['submission_counts']['snapshots_returned'],0)


if __name__=='__main__':unittest.main()
