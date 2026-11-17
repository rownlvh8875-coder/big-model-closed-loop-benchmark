from pathlib import Path
import copy,json,shutil,subprocess,sys,tempfile,unittest
try:from scripts import run_sdk3_sampling_envelope as h
except ImportError:h=None
ROOT=Path(__file__).resolve().parents[1]
class EnvelopeAdmission(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'authenticated sampling driver is missing')
    def test_actual_inputs_produce_135_explicit_models_with_no_gpu_promotion(self):
        x=h.analyze(h.load_inputs(ROOT));self.assertEqual(len(x['points']),5);self.assertEqual(x['scenario_count'],135);self.assertEqual(x['modeled_scenario_count'],135);self.assertTrue(all(v['yellow'] for p in x['points'] for v in p['scenarios']));self.assertEqual(x['native_renderer_processes_this_step'],0);self.assertEqual(x['official_model_processes'],0);self.assertEqual(x['onnx_inferences'],0)
        for flag in h.FALSE_FLAGS:self.assertIs(x[flag],False)
        self.assertTrue(x['prior_prepared_boundary_revalidated']);self.assertFalse(x['fresh_source_images_verified']);self.assertEqual(x['source']['actual_run'],44067526874)
    def test_actual_center_uses_nonzero_mip_and_conditional_envelopes(self):
        x=h.analyze(h.load_inputs(ROOT));center=x['points'][0];base=next(v for v in center['scenarios'] if v['coordinate_model']=='recorded_f64' and v['format_model']=='recorded_float32' and v['weight_bits'] is None);snorm=next(v for v in center['scenarios'] if v['coordinate_model']=='recorded_f64' and v['format_model']=='snorm8_nearest_even' and v['weight_bits'] is None);self.assertAlmostEqual(base['value'],.01687556688432301);self.assertAlmostEqual(snorm['value'],.01771712988320027);self.assertTrue(all(v['all_yellow'] for v in center['conditional_envelopes']));closest=min(center['threshold_roots'],key=lambda r:abs(r['delta_texels']));self.assertEqual(closest['axis'],1);self.assertGreater(closest['world_displacement_norm'],.005);self.assertLess(closest['world_displacement_norm'],.012)
    def test_index_or_input_raw_tampering_is_rejected_before_modeling(self):
        x=h.load_inputs(ROOT)
        for kind in ('index','raw','missing'):
            y=copy.deepcopy(x)
            if kind=='index':y['index_raw']+=b' '
            elif kind=='raw':key=next(iter(y['files']));y['files'][key]+=b' '
            else:y['files'].pop(next(iter(y['files'])))
            with self.subTest(kind=kind),self.assertRaises(ValueError):h.analyze(y)
    def test_identity_and_prior_proof_claim_mutations_reject(self):
        docs=h.documents(h.load_inputs(ROOT))
        for name,key,value in [('prepared.json','pid',99),('terrain.json','nonce','bad'),('prepared.json','target_read_sha256','00'*32),('independent-observation.json','analysis_validated',False),('prepared.json','gpu_pixel_owner_proven',True),('report.json','onnx_inferences',1)]:
            y=copy.deepcopy(docs);y[name][key]=value
            with self.subTest(name=name,key=key),self.assertRaises(ValueError):h.validate_bindings(y)
    def test_missing_and_changed_disk_inputs_cannot_be_authenticated(self):
        index=json.loads((ROOT/'docs/evidence/sdk3-sampling-envelope-01/input-index.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ['docs/evidence/sdk3-sampling-envelope-01/input-index.json']+[r['path'] for r in index['files']]:
                q=root/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,q)
            self.assertEqual(len(h.load_inputs(root)['files']),11);q=root/index['files'][0]['path'];q.write_bytes(q.read_bytes()+b' ')
            with self.assertRaises(ValueError):h.load_inputs(root)
            q.unlink()
            with self.assertRaises(ValueError):h.load_inputs(root)
    def test_cli_result_is_bounded_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'new-result';command=[sys.executable,'-I','-B',str(ROOT/'scripts/run_sdk3_sampling_envelope.py'),'--out',str(out)];r=subprocess.run(command,capture_output=True,text=True,timeout=30);self.assertEqual(r.returncode,0,r.stderr);raw=(out/'result.json').read_bytes();self.assertLess(len(raw),1048576);self.assertEqual(json.loads(raw)['scenario_count'],135);r=subprocess.run(command,capture_output=True,text=True,timeout=30);self.assertNotEqual(r.returncode,0);self.assertEqual((out/'result.json').read_bytes(),raw)
    def test_cold_help_has_no_runtime_dependency_requirement(self):
        r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/run_sdk3_sampling_envelope.py'),'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--out',r.stdout)
    def test_proxy_world_displacement_and_unknown_neighbor_limit_are_explicit(self):
        x=h.analyze(h.load_inputs(ROOT));self.assertTrue(x['within_captured_cells_only']);self.assertTrue(x['input_points_are_geomnode_proxies']);self.assertFalse(x['actual_sample_coordinates_proven']);self.assertTrue(all(0<=v['fraction']<=1 for p in x['points'] for v in p['threshold_roots']));self.assertEqual(x['source']['input_file_count'],11)
if __name__=='__main__':unittest.main()
