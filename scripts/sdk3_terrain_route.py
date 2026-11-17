"""Audit one immutable procedural-terrain source route; never execute it."""
from pathlib import Path, PurePosixPath
import ast
import hashlib
import json
import posixpath
import re
import stat
import sys

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.sdk3_shader_cache import POLICY_ID, preprocess_cache

INDEX = 'docs/evidence/sdk3-terrain-route-01/input-index.json'
INDEX_SHA256 = '023a4e33bbaeebf71ecc7aabfed7d540762831080fdcd29d5bc3a76fc7220b4a'
SOURCE = 'docs/evidence/sdk3-terrain-route-01/frozen-source/'
PRIOR = 'docs/evidence/sdk3-shader-cache-01/actual/bundle/renderer/'
MAX_FILE_BYTES = 262144
MAX_TOTAL_BYTES = 1048576


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _read(root, name, pin):
    parts = PurePosixPath(name).parts
    _need(parts and not PurePosixPath(name).is_absolute() and '..' not in parts,
          'repository-relative evidence path')
    path = root
    try:
        for part in parts:
            path = path / part
            _need(not path.is_symlink(), 'symlink evidence is not admitted')
        metadata = path.stat()
        _need(stat.S_ISREG(metadata.st_mode) and 0 < metadata.st_size <= MAX_FILE_BYTES,
              'bounded regular evidence file')
        _need(path.resolve().is_relative_to(root), 'confined evidence file')
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError('missing or unreadable evidence: ' + name) from error
    _need(len(raw) == pin['nbytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'],
          'exact pinned evidence bytes: ' + name)
    return raw


def _class_value(tree, class_name, name):
    owner = next(node for node in tree.body
                 if isinstance(node, ast.ClassDef) and node.name == class_name)
    return next(node.value for node in owner.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name
                        for target in node.targets))


def audit(repo_root):
    """Return deterministic, cited source evidence with all runtime gates false."""
    root = Path(repo_root).resolve()
    index_raw = _read(root, INDEX, dict(nbytes=4020, sha256=INDEX_SHA256))
    index = json.loads(index_raw)
    data = {name: _read(root, name, pin) for name, pin in index['files'].items()}
    total = sum(map(len, data.values()))
    _need(total <= MAX_TOTAL_BYTES, 'bounded total evidence bytes')
    text = {name: raw.decode('utf-8') for name, raw in data.items()}
    citations = {}

    def source(name):
        return text[SOURCE + name + '.data']

    def cite(key, name, needle):
        lines = text[name].splitlines()
        hits = [(i, line) for i, line in enumerate(lines, 1) if needle in line]
        _need(len(hits) == 1, 'unique pinned source citation: ' + key)
        line, content = hits[0]
        citations[key] = dict(file=name, sha256=index['files'][name]['sha256'],
                              line=line, text=content)

    constants = ast.parse(source('constants.py'))
    rgb_key = ast.literal_eval(_class_value(constants, 'CameraTagStateKey', 'RGB'))
    terrain_label = ast.literal_eval(_class_value(constants, 'Semantics', 'TERRAIN').args[0])
    rgb = ast.parse(source('component/sensors/rgb_camera.py'))
    load = next(node for node in ast.walk(rgb) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == 'make_render_state')
    names = [ast.literal_eval(arg) for arg in load.args[1:]]
    _need(names == ['terrain.vert.glsl', 'terrain.frag.glsl'], 'fixed terrain shader names')
    terrain = ast.parse(source('engine/core/terrain.py'))
    terrain_class = next(node for node in terrain.body
                         if isinstance(node, ast.ClassDef) and node.name == 'Terrain')
    make = next(node for node in terrain_class.body
                if isinstance(node, ast.FunctionDef) and node.name == 'make_render_state')
    prefixes = [ast.literal_eval(node.value.args[0]) for node in make.body
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == 'file_path']
    _need(prefixes == ['../shaders', '../shaders'], 'parent shader route')
    resolved = [posixpath.normpath(posixpath.join('assets', prefix, name))
                for prefix, name in zip(prefixes, names)]
    geom_source = 'scripts/sdk3_pixel_geometry_native.py'
    query = next(node for node in ast.walk(ast.parse(text[geom_source]))
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and node.func.attr == 'findAllMatches')
    query_name = ast.literal_eval(query.args[0])
    _need(query_name == '**/+GeomNode', 'prior GeomNode-only CPU query')
    header = 'docs/evidence/sdk3-terrain-route-01/panda-reference/shaderTerrainMesh.h.data'
    base = re.search(r'class EXPCL_PANDA_GRUTIL ShaderTerrainMesh : public (\w+) \{', text[header])
    _need(base is not None and base[1] == 'PandaNode', 'official procedural node base')

    for key, name, needle in [
        ('rgb_camera_tag', 'component/sensors/rgb_camera.py', 'cam.setTagStateKey(CameraTagStateKey.RGB)'),
        ('rgb_terrain_shader', 'component/sensors/rgb_camera.py', 'Semantics.TERRAIN.label, Terrain.make_render_state'),
        ('asset_base', 'engine/asset_loader.py', 'asset_path = pathlib.PurePosixPath'),
        ('asset_join', 'engine/asset_loader.py', 'path = AssetLoader.asset_path.joinpath(*path_string)'),
        ('parent_shader_route', 'engine/core/terrain.py', 'vert = AssetLoader.file_path("../shaders", vert)'),
        ('terrain_construct', 'engine/core/terrain.py', 'self._mesh_terrain_node = ShaderTerrainMesh()'),
        ('terrain_rgb_tag', 'engine/core/terrain.py', 'self._mesh_terrain.setTag(CameraTagStateKey.RGB, self.SEMANTIC_LABEL)'),
        ('terrain_semantics', 'engine/core/terrain.py', 'SEMANTIC_LABEL = Semantics.TERRAIN.label'),
        ('yellow_fill', 'engine/core/terrain.py', 'yellow_lane_line.fill(*(255 / 255, 200 / 255, 0 / 255))'),
        ('yellow_input', 'engine/core/terrain.py', 'self._mesh_terrain.set_shader_input("yellow_tex", self.yellow_lane_line)'),
        ('instanced_data', 'shaders/terrain.vert.glsl', 'ivec2(gl_InstanceID, ShaderTerrainMesh.view_index), 0);'),
        ('height_displacement', 'shaders/terrain.vert.glsl', 'chunk_position.z += texture(ShaderTerrainMesh.heightfield, terrain_uv).x;'),
        ('attribute_lower_bound', 'shaders/terrain.frag.glsl', 'if ((attri.r > 0.01)'),
        ('attribute_upper_bound', 'shaders/terrain.frag.glsl', 'if (value < 0.11)'),
        ('yellow_sample', 'shaders/terrain.frag.glsl', 'diffuse=texture(yellow_tex, terrain_uv * road_tex_ratio).rgb;'),
        ('fog_after_diffuse', 'shaders/terrain.frag.glsl', 'shading = mix(shading, vec3(0.7, 0.7, 0.8), fog_factor);'),
    ]:
        cite(key, SOURCE + name + '.data', needle)
    cite('procedural_node_base', header, 'class EXPCL_PANDA_GRUTIL ShaderTerrainMesh : public PandaNode {')
    cite('prior_geom_query', geom_source, "paths=world.findAllMatches('**/+GeomNode')")

    shader = json.loads(text[PRIOR + 'shader.json'])
    geometry = json.loads(text[PRIOR + 'geometry-observer.json'])
    _need(shader['protocol'] == 'sdk3-shader-path-v1'
          and shader['pid'] == geometry['pid'] and shader['nonce'] == geometry['nonce']
          and shader['target_read_sha256'] == geometry['target_read_sha256'],
          'same retained actual observer identity and target')
    _need(geometry['geometry']['cpu_scene_coverage_proven'] is False,
          'prior CPU scene coverage remains unproven')
    cached = []
    for program in shader['shaders']:
        for stage, row in program['stages'].items():
            desc = row['text']; name = PRIOR + desc['file']; raw = data[name]
            _need(hashlib.sha256(raw).hexdigest() == desc['sha256'] and len(raw) == desc['nbytes'],
                  'retained shader descriptor binding')
            cached.append((program['shader_id'], stage, raw))
    expected = {stage: preprocess_cache(source(name)).encode('utf-8')
                for stage, name in zip(('vertex', 'fragment'), resolved)}
    matches = {stage: [dict(shader_id=sid, stage=kind) for sid, kind, raw in cached
                       if raw == value] for stage, value in expected.items()}
    samples_differ = all(source(name) != source('assets/shaders/' + filename)
                         for name, filename in zip(resolved, names))
    mesh_paths = [row['path'] for row in geometry['geometry']['meshes']]
    result = dict(
        protocol='sdk3-terrain-route-audit-v1', status='SOURCE_COVERAGE_GAP_RECORDED',
        evidence=dict(index_sha256=INDEX_SHA256, files_verified=len(data), total_bytes=total,
                      image_tar_sha256=index['image_tar_sha256'], image_config=index['image_config'],
                      prior_run_id=index['prior_run_id'], prior_artifact_id=index['prior_artifact_id']),
        source_route=dict(camera_tag_key=rgb_key, terrain_tag_label=terrain_label,
                          resolved_vertex=resolved[0], resolved_fragment=resolved[1],
                          sample_sources_are_distinct=samples_differ,
                          terrain_node_base=base[1], query_base=query_name.split('/+')[-1]),
        procedural=dict(uses_instance_data=True, uses_heightfield_displacement=True),
        yellow_branch=dict(attribute_red_lower_exclusive=.01, attribute_red_upper_exclusive=.11,
                           bounds_condition_also_required=True, texture_uniform='yellow_tex',
                           source_fill_rgb=[1., 200/255, 0.],
                           note='Source branch only; live attribute sample, fog and lighting are unobserved'),
        prior_observation=dict(cached_camera_tag_key=shader['camera']['tag_state_key'],
                               camera_key_matches_source=shader['camera']['tag_state_key'] == rgb_key,
                               shader_objects=len(shader['shaders']), shader_stages=len(cached),
                               terrain_stage_matches=matches,
                               terrain_program_present=bool(matches['vertex'] and matches['fragment']),
                               expected_cache_policy_id=POLICY_ID,
                               expected_terrain_sha256={k: hashlib.sha256(v).hexdigest() for k,v in expected.items()},
                               geom_mesh_count=len(mesh_paths), geom_mesh_paths=mesh_paths,
                               cpu_scene_coverage_proven=False, target_rgb=geometry['target_pixel_rgb']),
        unobserved=['runtime_terrain_node', 'camera_terrain_tag_state', 'camera_tag_shader_priority',
                    'attribute_tex_sample', 'terrain_heightfield_and_lod', 'effective_gpu_inputs',
                    'hdr_pixel_before_tonemap', 'gpu_pixel_owner', 'depth_tie'],
        citations=citations, new_native_processes=0, new_model_processes=0)
    for flag in ('runtime_terrain_present_proven', 'camera_terrain_tag_state_proven',
                 'gpu_program_execution_proven', 'gpu_pixel_owner_proven', 'depth_tie_proven',
                 'unique_cause_proven', 'repair_proven', 'original_matrix_gate_passed', 'stage7_complete'):
        result[flag] = False
    return result


if __name__ == '__main__':
    print(json.dumps(audit(Path(__file__).resolve().parents[1]), indent=2, sort_keys=True))
