"""CPU-only frozen-loader variants and bounded shader evidence."""
from pathlib import Path
import hashlib,re
import numpy as np

ALIASES={'p3d_TextureBaseColor':'p3d_TextureModulate','p3d_TextureMetalRoughness':'p3d_TextureSelector','p3d_TextureNormal':'p3d_TextureNormal','p3d_TextureEmission':'p3d_TextureEmission'}
CONFIG_FLAGS=('use_normal_maps','use_emission_maps','enable_fog','use_occlusion_maps','use_330','enable_hardware_skinning')
INPUT_NAMES=('PSSMShadowAtlas','pssm_mvps','pssm_nearfar','border_bias','use_pssm','fog','split_count','light_direction')

def pipeline_defines(config):
    if type(config.get('max_lights')) is not int or not 1<=config['max_lights']<=64 or any(type(config.get(k)) is not bool for k in CONFIG_FLAGS):raise ValueError('explicit bounded pipeline flags')
    result={'MAX_LIGHTS':config['max_lights']}
    for key,name in zip(CONFIG_FLAGS,('USE_NORMAL_MAP','USE_EMISSION_MAP','ENABLE_FOG','USE_OCCLUSION_MAP','USE_330','ENABLE_SKINNING')):
        if config[key]:result[name]=''
    return result

def variant(raw,defines,stage):
    if not isinstance(raw,str) or stage not in ('vertex','fragment'):raise ValueError('shader text/stage')
    lines=raw.split('\n');version=next((line for line in lines if '#version' in line),None)
    if version is None:raise ValueError('missing frozen GLSL version')
    lines.remove(version);mapping=dict(defines);mapping.update(ALIASES);result='\n'.join([version]+[f'#define {key} {value}' for key,value in mapping.items()]+['#line 1']+lines)
    if 'USE_330' in mapping:
        result=result.replace('#version 120','#version 330').replace('varying ','out ' if stage=='vertex' else 'in ')
        if stage=='vertex':result=result.replace('attribute ','in ')
    return result

def tonemap(rgb,exposure=1.):
    array=np.asarray(rgb,float)
    if array.ndim<1 or array.shape[-1]!=3 or not np.isfinite(array).all() or type(exposure) not in (int,float) or not np.isfinite(exposure) or exposure<0:raise ValueError('finite RGB and nonnegative exposure')
    color=np.maximum(0.,array*exposure-.004)
    return color*(6.2*color+.5)/(color*(6.2*color+1.7)+.06)

class TextStore:
    def __init__(self,folder,max_file=262144,max_total=2097152):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);self.max_file=max_file;self.max_total=max_total;self.used=0;self.count=0
    def save(self,text,label):
        if not isinstance(text,str) or re.fullmatch('[a-z0-9-]{1,40}',label) is None:raise ValueError('bounded shader text label')
        raw=text.encode('utf-8')
        if not 0<len(raw)<=self.max_file or self.used+len(raw)>self.max_total:raise ValueError('shader text byte budget')
        name=f'shader-text-{self.count+1:03d}-{label}.txt'
        with (self.folder/name).open('xb') as f:f.write(raw)
        self.count+=1;self.used+=len(raw);return dict(file=name,nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
