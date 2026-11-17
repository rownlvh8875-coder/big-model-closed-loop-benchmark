"""Literal numerical contracts; a mode/offset/threshold change must break these."""
import copy,hashlib,math,struct,unittest
from fractions import Fraction as F
try:from scripts import sdk3_sampling_envelope as h
except ImportError:h=None

def window(values=(0.,0.,.075,0.)):
    raw=[struct.pack('<f',v) for v in values];return dict(status='CAPTURED',resident_before=True,expected_nbytes=16,compression=1,size_xy=[2,2],num_components=1,component_width=4,component_type=2,byte_order='little',uv=[.5,.5],wrap_codes=[1,1],wrap_modes=['repeat','repeat'],texels=[dict(xy=xy,offset=i*4,nbytes=4,raw_hex=v.hex()) for i,(xy,v) in enumerate(zip(([0,0],[1,0],[0,1],[1,1]),raw))],sample_sha256=hashlib.sha256(b''.join(raw)).hexdigest())

class SamplingMath(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'sampling envelope helper is missing')
    def test_snorm8_literals_and_signed_clamping(self):
        self.assertEqual(h.normalize([.075,.15,-2.,2.],'snorm8_nearest_even'),[10/127,19/127,-1.,1.])
    def test_unorm8_literals_and_unsigned_clamping(self):
        self.assertEqual(h.normalize([.075,.15,-2.,2.],'unorm8_nearest_even'),[19/255,38/255,0.,1.])
    def test_codepoint_ties_are_nearest_even(self):
        self.assertEqual(h.normalize([.5,-.5,0.,1.],'snorm8_nearest_even'),[64/127,-64/127,0.,1.])
    def test_recorded_values_are_not_quantized(self):
        values=[0.,.07500000298023224,.15000000596046448,0.];self.assertEqual(h.normalize(values,'recorded_float32'),values)
    def test_yellow_predicate_is_strict_at_both_thresholds(self):
        for v,expected in ((.01,False),(.11,False),(math.nextafter(.01,1.),True),(math.nextafter(.11,0.),True),(0.,False),(.2,False)):self.assertEqual(h.yellow(v),expected)
    def test_half_texel_fraction_including_negative_repeat(self):
        self.assertEqual(h.fractions([.5,.5],[2,2]),[.5,.5]);self.assertEqual(h.fractions([0.,-1.],[2,2]),[.5,.5])
    def test_bilinear_corner_order_and_weight_models(self):
        self.assertAlmostEqual(h.bilinear([0.,0.,.075,0.],[.25,.5]),.028125);self.assertEqual(h.bilinear([0.,1.,0.,1.],[.5/256,.5],8),0.);self.assertEqual(h.bilinear([0.,1.,0.,1.],[1.5/256,.5],8),2/256)
    def test_axis_roots_are_inside_captured_cell_and_not_yellow(self):
        roots=h.threshold_roots([0.,0.,.1,0.],[.25,.5]);self.assertEqual(len(roots),2)
        by_axis={r['axis']:r for r in roots};self.assertAlmostEqual(by_axis[0]['fraction'],.8);self.assertAlmostEqual(by_axis[1]['fraction'],2/15);self.assertTrue(all(r['threshold']==.01 and not r['threshold_is_yellow'] for r in roots))
    def test_flat_or_outside_cell_thresholds_are_not_invented(self):
        self.assertEqual(h.threshold_roots([0.,0.,0.,0.],[.5,.5]),[]);self.assertEqual(h.threshold_roots([.02,.03,.02,.03],[.5,.5]),[])
    def test_upper_threshold_root_is_retained(self):
        roots=h.threshold_roots([0.,.22,0.,.22],[.25,.5]);upper=next(r for r in roots if r['threshold']==.11);self.assertEqual(upper['axis'],0);self.assertEqual(upper['fraction'],.5);self.assertEqual(upper['delta_texels'],.25)
    def test_conditional_code_and_fraction_envelope_has_literal_extrema(self):
        r=h.conditional_envelope([0.,0.,.075,0.],[.25,.5],8);self.assertAlmostEqual(r['minimum'],9/127*(.75-1/256)*(.5-1/256));self.assertAlmostEqual(r['maximum'],10/127*(.75+1/256)*(.5+1/256));self.assertTrue(r['all_yellow']);self.assertFalse(r['hardware_bound_proven'])
    def test_shader_coordinate_models_are_explicit_float32(self):
        self.assertEqual(h.attribute_uv([.5,.25],2.,'recorded_f64'),[1.5,1.]);self.assertEqual(h.attribute_uv([.5,.25],2.,'f32_separate'),[1.5,1.]);self.assertEqual(h.attribute_uv([.5,.25],2.,'f32_fma_model'),[1.5,1.])
        self.assertEqual(h.attribute_uv([.25,.75],1.001,'recorded_f64'),[.25,.75]);self.assertGreater(h.attribute_uv([.25,.75],1.001,'f32_separate')[0],.7)
    def test_float32_separate_and_fma_have_distinct_rounding_contracts(self):
        uv=[.123456789,.987654321];ratio=2.1234567
        f=lambda v:struct.unpack('=f',struct.pack('=f',v))[0]
        self.assertEqual(h.attribute_uv(uv,ratio,'f32_separate'),[f(f(f(v)*f(ratio))+.5) for v in uv]);self.assertEqual(h.attribute_uv(uv,ratio,'f32_fma_model'),[f(f(v)*f(ratio)+.5) for v in uv])
    def test_real_window_decoding_and_same_cell_scenario(self):
        w=window();r=h.scenario(w,[.5,.5],'snorm8_nearest_even',None);self.assertEqual(r['status'],'MODELED');self.assertAlmostEqual(r['value'],2.5/127);self.assertTrue(r['yellow']);self.assertFalse(r['actual_gpu_sample_proven'])
    def test_cell_escape_is_unavailable_without_extrapolation(self):
        r=h.scenario(window(),[.9,.5],'recorded_float32',None);self.assertEqual(r,dict(status='UNAVAILABLE_OUTSIDE_CAPTURED_CELL'))
    def test_absent_window_never_invents_values(self):
        self.assertEqual(h.scenario(dict(status='UNAVAILABLE_NOT_RESIDENT'),[.5,.5],'recorded_float32',8),dict(status='UNAVAILABLE_NOT_RESIDENT'))
    def test_tampered_window_raw_hash_offset_and_uv_reject(self):
        for key in ('raw','hash','offset','uv'):
            w=window()
            if key=='raw':w['texels'][0]['raw_hex']='0000c07f'
            elif key=='hash':w['sample_sha256']='00'*32
            elif key=='offset':w['texels'][0]['offset']=4
            else:w['uv']=[.9,.5]
            with self.subTest(key=key),self.assertRaises(ValueError):h.scenario(w,[.5,.5],'recorded_float32',None)
    def test_nonfinite_unknown_mode_and_bad_fraction_reject(self):
        for call in (lambda:h.normalize([math.nan],'recorded_float32'),lambda:h.normalize([0.],'bogus'),lambda:h.bilinear([0.,0.,0.,1.],[1.01,0.]),lambda:h.bilinear([0.,0.,0.,1.],[.5,.5],4),lambda:h.attribute_uv([math.inf,0.],2.,'f32_separate'),lambda:h.attribute_uv([0.,0.],0.,'recorded_f64'),lambda:h.fractions([0.,0.],[0,2])):
            with self.subTest(call=call),self.assertRaises(ValueError):call()
    def test_true_single_round_fma_above_float32_midpoint(self):
        uv=1.4904742329235887e-08;ratio=1.9995194673538208;expected=.5000000596046448
        exact=F(uv)*F(ratio)+F(1,2);self.assertLess(abs(exact-F(expected)),abs(exact-F(.5)));self.assertEqual(h.attribute_uv([uv,0.],ratio,'f32_fma_model')[0],expected)
    def test_conflicting_duplicate_texel_bytes_are_rejected(self):
        w=window();w.update(size_xy=[1,1],expected_nbytes=4,uv=[0.,0.],wrap_codes=[0,0],wrap_modes=['clamp','clamp'])
        for row in w['texels']:row.update(xy=[0,0],offset=0)
        with self.assertRaises(ValueError):h.scenario(w,[0.,0.],'recorded_float32',None)
    def test_consistent_clamp_mirror_duplicate_corners_remain_available(self):
        for mode,code in (('clamp',0),('mirror',2)):
            w=window((.075,)*4);w.update(size_xy=[1,1],expected_nbytes=4,uv=[0.,0.],wrap_codes=[code,code],wrap_modes=[mode,mode])
            for row in w['texels']:row.update(xy=[0,0],offset=0)
            r=h.scenario(w,[0.,0.],'recorded_float32',None);self.assertEqual(r['status'],'MODELED');self.assertTrue(r['yellow'])
    def test_exact_endpoint_root_is_retained(self):
        roots=h.threshold_roots([.01,.03,.01,.03],[.5,.5]);self.assertTrue(any(r['axis']==0 and r['threshold']==.01 and r['fraction']==0. for r in roots))
    def test_outside_root_cannot_round_into_the_cell(self):
        lo=math.nextafter(.01,math.inf);self.assertEqual(h.threshold_roots([lo,.03,lo,.03],[1.,.5]),[])
    def test_normalization_near_midpoint_uses_exact_input_value(self):
        self.assertEqual(h.normalize([.011811023622047244],'snorm8_nearest_even'),[1/127]);self.assertEqual(h.normalize([.0058823529411764705],'unorm8_nearest_even'),[1/255])
    def test_conditional_adjacent_codes_and_outward_bound_are_exact(self):
        r=h.conditional_envelope([2/127]*4,[.5,.5],8);self.assertAlmostEqual(r['minimum'],1/127);self.assertAlmostEqual(r['maximum'],2/127);self.assertFalse(r['all_yellow']);self.assertLessEqual(F(r['minimum']),F(1,127));self.assertGreaterEqual(F(r['maximum']),F(2,127))

if __name__=='__main__':unittest.main()
