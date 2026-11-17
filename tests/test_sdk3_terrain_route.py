"""Exercise the real pinned terrain route and reject substituted evidence."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile,unittest
from scripts import sdk3_terrain_route as route

ROOT=Path(__file__).resolve().parents[1]
INDEX='docs/evidence/sdk3-terrain-route-01/input-index.json'
SOURCE='docs/evidence/sdk3-terrain-route-01/frozen-source/'

class TerrainRouteTests(unittest.TestCase):
    def fixture(self,root):
        root=Path(root)
        for name in [INDEX,*json.loads((ROOT/INDEX).read_text())['files']]:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
        return root

    def test_rgb_tag_route_resolves_parent_shaders_not_asset_samples(self):
        x=route.audit(ROOT);r=x['source_route']
        self.assertEqual((r['camera_tag_key'],r['terrain_tag_label']),('rgb','TERRAIN'))
        self.assertEqual(r['resolved_vertex'],'shaders/terrain.vert.glsl')
        self.assertEqual(r['resolved_fragment'],'shaders/terrain.frag.glsl')
        self.assertTrue(r['sample_sources_are_distinct'])

    def test_procedural_node_is_pandanode_outside_geomnode_query(self):
        x=route.audit(ROOT);r=x['source_route']
        self.assertEqual(r['terrain_node_base'],'PandaNode');self.assertEqual(r['query_base'],'GeomNode')
        self.assertTrue(x['procedural']['uses_instance_data']);self.assertTrue(x['procedural']['uses_heightfield_displacement'])
        self.assertEqual(x['prior_observation']['geom_mesh_count'],2)
        self.assertFalse(x['prior_observation']['cpu_scene_coverage_proven'])

    def test_yellow_predicate_and_fill_are_source_candidates_only(self):
        x=route.audit(ROOT);r=x['yellow_branch']
        self.assertEqual((r['attribute_red_lower_exclusive'],r['attribute_red_upper_exclusive']),(.01,.11))
        self.assertEqual(r['source_fill_rgb'],[1.,200/255,0.]);self.assertEqual(r['texture_uniform'],'yellow_tex')
        self.assertEqual(x['prior_observation']['target_rgb'],[199,187,0])
        self.assertIn('attribute_tex_sample',x['unobserved'])

    def test_actual_cached_six_stages_exclude_both_terrain_stages(self):
        x=route.audit(ROOT);p=x['prior_observation']
        self.assertEqual((p['shader_objects'],p['shader_stages']),(3,6))
        self.assertTrue(p['camera_key_matches_source']);self.assertEqual(p['terrain_stage_matches'],{'vertex':[],'fragment':[]})
        self.assertFalse(p['terrain_program_present'])

    def test_runtime_and_official_gates_stay_false(self):
        x=route.audit(ROOT)
        for k in ['runtime_terrain_present_proven','camera_terrain_tag_state_proven','gpu_program_execution_proven','gpu_pixel_owner_proven','depth_tie_proven','unique_cause_proven','repair_proven','original_matrix_gate_passed','stage7_complete']:
            with self.subTest(k=k):self.assertIs(x[k],False)
        self.assertEqual(x['new_native_processes'],0);self.assertEqual(x['new_model_processes'],0)
        self.assertIn('camera_tag_shader_priority',x['unobserved'])

    def test_citations_bind_exact_source_lines_and_hashes(self):
        x=route.audit(ROOT);self.assertGreaterEqual(len(x['citations']),10)
        for name,row in x['citations'].items():
            data=(ROOT/row['file']).read_bytes();lines=data.decode().splitlines()
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])
                self.assertEqual(lines[row['line']-1],row['text'])

    def test_result_is_deterministic_without_clock_or_runtime_import(self):
        self.assertEqual(route.audit(ROOT),route.audit(ROOT))
        self.assertNotIn('panda3d',sys.modules);self.assertNotIn('metadrive',sys.modules)

    def test_each_substituted_input_rejects_even_without_manifest_change(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d)
            for name in json.loads((root/INDEX).read_text())['files']:
                p=root/name;raw=p.read_bytes();p.write_bytes(raw+b'\n')
                with self.subTest(name=name),self.assertRaises(ValueError):route.audit(root)
                p.write_bytes(raw)

    def test_same_named_asset_sample_cannot_replace_actual_terrain_shader(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/(SOURCE+'shaders/terrain.frag.glsl.data')
            p.write_bytes((root/(SOURCE+'assets/shaders/terrain.frag.glsl.data')).read_bytes())
            with self.assertRaises(ValueError):route.audit(root)

    def test_rehashed_manifest_cannot_authorize_forged_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/(SOURCE+'shaders/terrain.frag.glsl.data');p.write_bytes(b'#version 330\nvoid main(){}\n')
            q=root/INDEX;x=json.loads(q.read_text());x['files'][p.relative_to(root).as_posix()]={'nbytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()};q.write_text(json.dumps(x))
            with self.assertRaises(ValueError):route.audit(root)

    def test_forged_previous_gpu_claim_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/'docs/evidence/sdk3-shader-cache-01/actual/bundle/renderer/geometry-observer.json';x=json.loads(p.read_text());x['geometry']['gpu_pixel_owner_proven']=True;p.write_text(json.dumps(x))
            with self.assertRaises(ValueError):route.audit(root)

    def test_modified_cached_bytes_with_rehashed_descriptor_reject(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/'docs/evidence/sdk3-shader-cache-01/actual/bundle/renderer/shader.json';x=json.loads(p.read_text());desc=x['shaders'][0]['stages']['fragment']['text'];q=p.parent/desc['file'];raw=q.read_bytes().replace(b'\n',b'\r\n');q.write_bytes(raw);desc.update(nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());p.write_text(json.dumps(x))
            with self.assertRaises(ValueError):route.audit(root)

    def test_missing_input_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);(root/(SOURCE+'engine/core/terrain.py.data')).unlink()
            with self.assertRaises(ValueError):route.audit(root)

    def test_oversized_input_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);(root/(SOURCE+'engine/core/terrain.py.data')).write_bytes(b'x'*262145)
            with self.assertRaises(ValueError):route.audit(root)

    def test_leaf_symlink_to_even_identical_bytes_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/(SOURCE+'engine/core/terrain.py.data');p.unlink();p.symlink_to(ROOT/p.relative_to(root))
            with self.assertRaises(ValueError):route.audit(root)

    def test_parent_symlink_escape_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/(SOURCE+'engine');shutil.rmtree(p);p.symlink_to(ROOT/(SOURCE+'engine'),target_is_directory=True)
            with self.assertRaises(ValueError):route.audit(root)

    def test_audit_does_not_modify_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);before={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()};route.audit(root)
            self.assertEqual(before,{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()})

    def test_isolated_cli_emits_exact_same_json(self):
        r=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/sdk3_terrain_route.py')],capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout),route.audit(ROOT))

if __name__=='__main__':unittest.main()
