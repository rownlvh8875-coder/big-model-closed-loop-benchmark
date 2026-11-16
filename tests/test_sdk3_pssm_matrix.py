from types import SimpleNamespace
import math,tempfile,unittest
from scripts import sdk3_pssm_matrix as m,sdk3_shader_cache_native as native,sdk3_shader_path_native as previous
from tests.sdk3_shader_cache_fixtures import MATRICES,Unaligned,Aligned,fixture
class PSSMMatrixTests(unittest.TestCase):
    def test_unaligned_distinct_cells_are_copied_without_transpose_or_mutation(self):
        source=Unaligned(MATRICES[0]);self.assertFalse(hasattr(source,'getCell'));rows=m.matrix_rows(SimpleNamespace(LMatrix4f=Aligned),source);self.assertEqual(rows,MATRICES[0]);rows[0][0]=99.;self.assertEqual(source.values,MATRICES[0])
    def test_nonfinite_cells_and_conversion_failure_reject(self):
        source=Unaligned(MATRICES[0]);source.values[2][3]=math.nan
        with self.assertRaises(ValueError):m.matrix_rows(SimpleNamespace(LMatrix4f=Aligned),source)
        with self.assertRaises((ValueError,TypeError,AttributeError)):m.matrix_rows(SimpleNamespace(LMatrix4f=Aligned),object())
    def test_real_snapshot_captures_two_unaligned_owner_matrices_and_nearfar(self):
        with tempfile.TemporaryDirectory() as d:
            _,_,_,result=fixture(d,native);self.assertEqual(result['status'],'SHADER_RECORDED');self.assertTrue(result['selection_complete']);self.assertEqual(result['pssm_owner']['mvp_array'],MATRICES);self.assertEqual(result['pssm_owner']['nearfar_array'],[[.1,10.],[10.,1000.]]);self.assertFalse(result['pssm_owner']['input_values_bound_to_shader'])
    def test_previous_snapshot_stays_partial_and_its_globals_are_unchanged(self):
        before=previous.snapshot_shader.__globals__['material']
        with tempfile.TemporaryDirectory() as d:
            _,_,_,result=fixture(d,previous);self.assertEqual(result['status'],'SHADER_PARTIAL');self.assertIn('getCell',result['failure'])
        self.assertIs(previous.snapshot_shader.__globals__['material'],before)
