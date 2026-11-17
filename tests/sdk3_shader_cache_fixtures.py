"""CPU-only snapshot fixture with non-getCell PSSM matrices and real retained texts."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,shutil
from scripts import sdk3_shader_path_native as previous,run_sdk3_shader_path as oldhost
from tests import test_sdk3_shader_path_host as oldfixture
ROOT=Path(__file__).resolve().parents[1]
MATRICES=[[[float(100*k+10*r+c) for c in range(4)] for r in range(4)] for k in range(2)]
class Unaligned:
    def __init__(self,values):self.values=[list(row) for row in values]
class Aligned:
    def __init__(self,source):self.values=[list(row) for row in source.values]
    def getCell(self,r,c):return self.values[r][c]
def texture(pointer,name):
    values=dict(XSize=964,YSize=604,ZSize=1,NumComponents=4,ComponentWidth=4,ComponentType=2,Format=21,TextureType=1)
    return SimpleNamespace(this=pointer,getName=lambda:name,**{'get'+key:lambda v=value:v for key,value in values.items()})
def fixture(folder,native,*,mutate_matrices=None):
    dest,ref,nonce=oldfixture.ShaderAdmission().fixture(folder);before=json.loads((dest/'shader.json').read_text());material=json.loads((dest/'material.json').read_text());geometry=json.loads((dest/'geometry-observer.json').read_text())['geometry'];site=Path(folder)/'site'
    for name in oldhost.SOURCE_PINS:
        target=site/'metadrive'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'docs/evidence/sdk3-shader-path-01/frozen-source'/(name+'.data'),target)
    for q in dest.glob('shader-text-*.txt'):q.unlink()
    retained=ROOT/'docs/evidence/sdk3-shader-path-01/actual/bundle/renderer'
    class Shader:
        def __init__(self,pointer,files):self.this=pointer;self.files=files
        def getText(self,stage):return (retained/self.files[stage-1]).read_bytes().decode()
        def getFilename(self,stage):return ''
        def getLanguage(self):return 2
        def getErrorFlag(self):return False
    def shader_input(name,value):
        if name in ('tex','PSSMShadowAtlas'):return SimpleNamespace(getValueType=lambda:1,getPriority=lambda:0,getTexture=lambda:value)
        if name in ('exposure','border_bias'):return SimpleNamespace(getValueType=lambda:3,getPriority=lambda:0,getVector=lambda:value)
        return SimpleNamespace(getValueType=lambda:4,getPriority=lambda:0)
    def attrib(pointer,shader,values):return SimpleNamespace(this=pointer,getShader=lambda:shader,hasShaderInput=lambda name:name in values,getShaderInput=lambda name:shader_input(name,values[name]))
    scene=texture(300,'scene');atlas=texture(400,'PSSMShadowMap');values={name:None for name in oldhost.s.INPUT_NAMES};values.update(PSSMShadowAtlas=atlas,border_bias=[.058,0.,0.,0.]);scene_attrib=attrib(101,Shader(100,['shader-text-013-vertex.txt','shader-text-014-fragment.txt']),values);tone_attrib=attrib(501,Shader(102,['shader-text-017-vertex.txt','shader-text-018-fragment.txt']),dict(tex=scene,exposure=[1.,0.,0.,0.]))
    state=SimpleNamespace(this=13,getAttrib=lambda slot:scene_attrib);state.compose=lambda other:state
    class ScenePath:
        def __str__(self):return 'synthetic/road'
        def getNetState(self):return state
        def node(self):return SimpleNamespace(getGeomState=lambda i:None)
    tone_state=SimpleNamespace(this=500,getAttrib=lambda slot:tone_attrib)
    class Quad:
        def __str__(self):return 'synthetic/quad'
        def getNetState(self):return tone_state
    origin=object();cam=SimpleNamespace(getParent=lambda:origin,node=lambda:SimpleNamespace(getInitialState=lambda:'',getTagStateKey=lambda:'rgb'));matrices=[Unaligned(v) for v in MATRICES]
    if mutate_matrices is not None:mutate_matrices(matrices)
    shadow=SimpleNamespace(num_splits=2,use_pssm=True,fog=True,freeze_pssm=False,border_bias=.058,camera_rig=SimpleNamespace(get_mvp_array=lambda:matrices,get_nearfar_array=lambda:[[.1,10.],[10.,1000.]]));engine=SimpleNamespace(origin=origin,pbrpipe=SimpleNamespace(**before['pipeline']),render=SimpleNamespace(findAllMatches=lambda pattern:[ScenePath()]),pssm=shadow);sensor=SimpleNamespace(cam=cam,tonemap_quad=Quad(),scene_tex=scene,copy_texture=SimpleNamespace(this=301));core=SimpleNamespace(LMatrix4f=Aligned,Shader=SimpleNamespace(ST_vertex=1,ST_fragment=2),ShaderAttrib=SimpleNamespace(getClassSlot=lambda:1),InternalName=SimpleNamespace(make=lambda value:value));journal=SimpleNamespace(started=-(material['material_exit_elapsed_s']+.00001))
    with patch.object(previous.p,'SITE',str(site)),patch.object(previous.os,'getpid',return_value=11),patch.object(previous.time,'monotonic',return_value=0.):result=native.snapshot_shader(core,engine,sensor,geometry,dest,nonce,journal)
    result['observer_finalized']=True;(dest/'shader.json').write_text(json.dumps(result,indent=2)+'\n');return dest,ref,nonce,result
