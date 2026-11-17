"""Real terrain snapshot over CPU-only Panda object doubles."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,shutil,struct
from scripts import sdk3_shader_cache_native as cached,sdk3_shader_cache as cache,panda_sdk3_runtime as p
from tests.sdk3_shader_cache_fixtures import fixture as old_fixture,Aligned,Unaligned
from tests.test_sdk3_terrain_state import CORE
ROOT=Path(__file__).resolve().parents[1]

def fixture(folder,native,*,absent=False,resident=True):
    dest,ref,nonce,prior=old_fixture(folder,cached);geometry=json.loads((dest/'geometry-observer.json').read_text())['geometry'];site=Path(folder)/'terrain-site'
    for name in ('shaders/terrain.vert.glsl','shaders/terrain.frag.glsl'):
        q=site/'metadrive'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'docs/evidence/sdk3-terrain-route-01/frozen-source'/(name+'.data'),q)
    class Texture:
        def __init__(self,pointer):self.this=pointer
        def getName(self):return 'cpu-resident-fixture'
        def hasRamImage(self):return resident
        def getRamImage(self):return b''.join(struct.pack('<f',i/10) for i in range(6))
        def getDefaultSampler(self):
            values=dict(WrapU=1,WrapV=1,WrapW=1,Minfilter=1,Magfilter=1,EffectiveMinfilter=1,EffectiveMagfilter=1,AnisotropicDegree=1,EffectiveAnisotropicDegree=1,BorderColor=[0.,0.,0.,0.],MinLod=-1000.,MaxLod=1000.,LodBias=0.)
            return SimpleNamespace(**{'get'+k:lambda v=v:v for k,v in values.items()})
    for key,value in dict(XSize=3,YSize=2,ZSize=1,NumComponents=1,ComponentWidth=4,ComponentType=2,Format=3,TextureType=1,ExpectedRamImageSize=24,RamImageCompression=1).items():setattr(Texture,'get'+key,lambda self,v=value:v)
    attribute,heightfield,yellow=[Texture(i) for i in (701,702,703)]
    class Shader:
        this=801
        def getLanguage(self):return 2
        def getErrorFlag(self):return False
        def getFilename(self,stage):return '/frozen/terrain.'+('vert' if stage==1 else 'frag')+'.glsl'
        def getText(self,stage):return cache.preprocess_cache((site/'metadrive/shaders'/('terrain.vert.glsl' if stage==1 else 'terrain.frag.glsl')).read_text())
    shader=Shader()
    def attrib(pointer,program,inputs):return SimpleNamespace(this=pointer,getShader=lambda:program,hasShaderInput=lambda name:name in inputs,getShaderInput=lambda name:SimpleNamespace(getValueType=lambda:1,getPriority=lambda:0,getTexture=lambda:inputs[name]))
    inputs=dict(attribute_tex=attribute,yellow_tex=yellow);net_attrib=attrib(901,None,inputs);tag_attrib=attrib(902,shader,{});composed_attrib=attrib(903,shader,inputs)
    class State:
        def __init__(self,pointer,attrib,override):self.this=pointer;self.attrib=attrib;self.override=override
        def getAttrib(self,slot):return self.attrib
        def getOverride(self,slot):return self.override
        def compose(self,other):return combined
        def __str__(self):return 'CPU state '+str(self.this)
    net,initial,tag,combined=State(1001,net_attrib,0),State(1002,None,0),State(1003,tag_attrib,7),State(1004,composed_attrib,7)
    node=SimpleNamespace(this=1101,getName=lambda:'terrain',getType=lambda:SimpleNamespace(getName=lambda:'ShaderTerrainMesh'),isOfType=lambda cls:False,getHeightfield=lambda:heightfield)
    class TerrainPath:
        def __str__(self):return 'render/terrain'
        def node(self):return node
        def isEmpty(self):return False
        def isHidden(self,mask):return False
        def getNetState(self):return net
        def getNetTag(self,key):return 'TERRAIN'
        def getTag(self,key):return 'TERRAIN'
        def getMat(self,relative):return Unaligned([[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]])
    terrain=SimpleNamespace(render=True,use_mesh_terrain=False,_terrain_size=2048,_elevation_texture_ratio=4.,_height_scale=200.,_mesh_terrain=None if absent else TerrainPath(),semantic_tex=attribute,heightfield_tex=heightfield,yellow_lane_line=yellow)
    origin=object();engine=SimpleNamespace(origin=origin,render=object(),terrain=terrain)
    camera=SimpleNamespace(getTagStateKey=lambda:'rgb',getInitialState=lambda:initial,getCameraMask=lambda:1,hasTagState=lambda value:value=='TERRAIN',getTagState=lambda value:tag)
    sensor=SimpleNamespace(cam=SimpleNamespace(getParent=lambda:origin,node=lambda:camera))
    core=SimpleNamespace(LMatrix4f=Aligned,Shader=SimpleNamespace(ST_vertex=1,ST_fragment=2),ShaderAttrib=SimpleNamespace(getClassSlot=lambda:1),InternalName=SimpleNamespace(make=lambda value:value),GeomNode=SimpleNamespace(getClassType=lambda:1),Texture=CORE.Texture,SamplerState=CORE.SamplerState)
    journal=SimpleNamespace(started=-prior['shader_exit_elapsed_s'])
    command=json.loads((dest/'command.json').read_text());command['argv'][command['argv'].index('/work/repo/scripts/sdk3_shader_path_native.py')]='/work/repo/scripts/sdk3_terrain_state_native.py';(dest/'command.json').write_text(json.dumps(command)+'\n')
    with patch.object(native.p,'SITE',str(site)),patch.object(native.os,'getpid',return_value=11),patch.object(native.time,'monotonic',return_value=0.):result=native.snapshot_terrain(core,engine,sensor,geometry,dest,nonce,journal)
    result.update(observer_finalized=True,shader_sha256=p.digest(dest/'shader.json'));(dest/'terrain.json').write_text(json.dumps(result,indent=2)+'\n');return dest,ref,nonce,result
