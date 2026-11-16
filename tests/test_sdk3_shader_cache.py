from pathlib import Path
import hashlib,json,tempfile,unittest
from scripts import sdk3_shader_cache as c,sdk3_shader_path as old
ROOT=Path(__file__).resolve().parents[1]
class CachePreprocessTests(unittest.TestCase):
    def test_comments_blank_lines_trailing_whitespace_and_eof_are_literal(self):
        raw='#version 330\n#define FLAG  \n// comment\nvec4 v;  // note\n  \n'
        self.assertEqual(c.preprocess_cache(raw),'#version 330\n#define FLAG\n\nvec4 v;\n')
        self.assertEqual(c.preprocess_cache('#version 330\nvoid main() {}'),'#version 330\nvoid main() {}\n')
    def test_source_crlf_is_supported_without_normalizing_any_actual_cache(self):
        self.assertEqual(c.preprocess_cache('#version 150\r\n// comment\r\nvoid main() {}\r\n'),'#version 150\n\nvoid main() {}\n')
    def test_unsupported_block_continuation_directives_quotes_nul_or_nonascii_reject(self):
        cases=['/* block */','x\\\ny','x\\\r\ny','#include "file"','#pragma once','#extension GL_EXT_x : enable','#unknown 1','const char* s="//not comment";','x\x00y','//한글']
        for tail in cases:
            with self.subTest(tail=tail),self.assertRaises(ValueError):c.preprocess_cache('#version 330\n'+tail)
    def test_size_bound_and_comment_quotes(self):
        with self.assertRaises(ValueError):c.preprocess_cache('x'*262145)
        self.assertEqual(c.preprocess_cache('#version 330\n// "quoted comment"\nx;'),'#version 330\n\nx;\n')
    def test_six_prior_cache_sha_pairs_reproduce_and_code_mutation_stays_distinct(self):
        folder=ROOT/'docs/evidence/sdk3-shader-path-01/actual/bundle/renderer';manifest=json.loads((folder/'shader.json').read_text());raw={v['name']:(folder/v['file']).read_bytes().decode() for v in manifest['sources']};defines=old.pipeline_defines(manifest['pipeline']);roles=[('pipeline',0),('skybox',1),('tonemap',2)];count=0
        for role,shader_id in roles:
            for stage,name in zip(('vertex','fragment'),('simplepbr.vert','simplepbr.frag') if role=='pipeline' else ('skybox.vert','skybox.frag') if role=='skybox' else ('post.vert','tonemap.frag')):
                source=raw[('assets/shaders/' if role=='skybox' else 'third_party/simplepbr/shaders/')+name+'.glsl'];generated=source if role=='skybox' else old.variant(source,defines if role=='pipeline' else {},stage);actual=(folder/manifest['shaders'][shader_id]['stages'][stage]['text']['file']).read_bytes();expected=c.preprocess_cache(generated).encode();self.assertEqual(expected,actual);self.assertEqual(hashlib.sha256(expected).hexdigest(),manifest['shaders'][shader_id]['stages'][stage]['text']['sha256']);self.assertNotEqual(c.preprocess_cache(generated.replace('void main()','void changed()',1)).encode(),actual);count+=1
        self.assertEqual(count,6)
