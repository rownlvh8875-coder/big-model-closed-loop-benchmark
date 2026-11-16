"""Regressions from sole branch review; CPU doubles never import Panda."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json,shutil,subprocess,sys,tempfile,unittest
from scripts import run_sdk3_shader_path as h,sdk3_shader_path_native as native,panda_sdk3_runtime as p
from tests import test_sdk3_shader_path_host as fixtures
write=fixtures.write
class ReviewRegressions(unittest.TestCase):
    def test_workflow_entry_help_runs_without_native_or_network(self):
        run=subprocess.run([sys.executable,'-I','-B',str(Path(h.__file__).resolve()),'--help'],capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,0,run.stderr);self.assertIn('--run',run.stdout)
    def test_rehashed_crlf_shader_is_not_exact_variant_match(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.ShaderAdmission().fixture(d);path=dest/'shader.json';x=json.loads(path.read_text());desc=x['shaders'][0]['stages']['fragment']['text'];q=dest/desc['file'];old=q.read_bytes();new=old.replace(b'\n',b'\r\n');self.assertNotEqual(old,new);q.write_bytes(new);x['bytes_captured']+=len(new)-len(old);desc.update(nbytes=len(new),sha256=hashlib.sha256(new).hexdigest());write(path,x);r=h.validate_receipt(dest,ref,nonce);self.assertFalse(r['shader_variants_matched']);self.assertTrue(r['shader_recorded'])
    def test_real_snapshot_partial_preserves_saved_vertex_on_oversize_or_timeout(self):
        for failure in ('oversize','timeout'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as d:
                dest,ref,nonce=fixtures.ShaderAdmission().fixture(d);prior=json.loads((dest/'shader.json').read_text());vertex=(dest/prior['shaders'][0]['stages']['vertex']['text']['file']).read_bytes().decode();m=json.loads((dest/'material.json').read_text());geometry=json.loads((dest/'geometry-observer.json').read_text())['geometry']
                rows=[json.loads(v) for v in (dest/'progress.jsonl').read_text().splitlines()];shift=False
                for row in rows:
                    if row['event']=='checkpoint' and row['metadata'].get('stage')=='GEOMETRY_RETURN':shift=True
                    if shift:row['elapsed_s']+=30
                (dest/'progress.jsonl').write_text(''.join(json.dumps(v)+'\n' for v in rows))
                site=Path(d)/'site';root=Path(__file__).resolve().parents[1]
                for name in h.SOURCE_PINS:
                    target=site/'metadrive'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'docs/evidence/sdk3-shader-path-01/frozen-source'/(name+'.data'),target)
                for q in dest.glob('shader-text-*.txt'):q.unlink()
                clock=[0.]
                class Shader:
                    this=100
                    def getText(self,stage):
                        if stage==1:
                            if failure=='timeout':clock[0]=21.
                            return vertex
                        return 'x'*262145
                    def getFilename(self,stage):return ''
                    def getLanguage(self):return 2
                    def getErrorFlag(self):return False
                shader=Shader();attrib=SimpleNamespace(this=101,getShader=lambda:shader,hasShaderInput=lambda name:False);state=SimpleNamespace(this=13,getAttrib=lambda slot:attrib);state.compose=lambda other:state
                class ScenePath:
                    def __str__(self):return 'synthetic/road'
                    def getNetState(self):return state
                    def node(self):return SimpleNamespace(getGeomState=lambda i:None)
                origin=object();cam=SimpleNamespace(getParent=lambda:origin,node=lambda:SimpleNamespace(getInitialState=lambda:'',getTagStateKey=lambda:'rgb'));engine=SimpleNamespace(origin=origin,pbrpipe=SimpleNamespace(**prior['pipeline']),render=SimpleNamespace(findAllMatches=lambda pattern:[ScenePath()]));sensor=SimpleNamespace(cam=cam);core=SimpleNamespace(Shader=SimpleNamespace(ST_vertex=1,ST_fragment=2),ShaderAttrib=SimpleNamespace(getClassSlot=lambda:1),InternalName=SimpleNamespace(make=lambda value:value));journal=SimpleNamespace(started=-(m['material_exit_elapsed_s']+.00001))
                with patch.object(native.p,'SITE',str(site)),patch.object(native.os,'getpid',return_value=11),patch.object(native.time,'monotonic',side_effect=lambda:clock[0]):observed=native.snapshot_shader(core,engine,sensor,geometry,dest,nonce,journal)
                self.assertEqual(observed['status'],'SHADER_PARTIAL');self.assertIn('time_budget' if failure=='timeout' else 'inspection_error',observed['truncation_reasons']);self.assertEqual(len(list(dest.glob('shader-text-*.txt'))),13);observed['observer_finalized']=True;write(dest/'shader.json',observed);result=h.validate_receipt(dest,ref,nonce);self.assertTrue(result['shader_recorded']);self.assertFalse(result['shader_complete'])
