"""Allow a larger logical RAM extent while preserving sparse byte reads."""
from types import FunctionType,SimpleNamespace
from scripts import sdk3_terrain_state as previous

MAX_RESIDENT_BYTES=2147483648
LIMITS=dict(previous.LIMITS,max_resident_bytes=MAX_RESIDENT_BYTES)
SPARSE_POLICY=dict(max_logical_buffer_bytes=MAX_RESIDENT_BYTES,max_window_bytes=64,max_total_sample_bytes=960,max_rss_delta_kib=32768)

def clone(function,**changes):
    result=FunctionType(function.__code__,dict(function.__globals__,**changes),function.__name__,function.__defaults__,function.__closure__);result.__kwdefaults__=dict(function.__kwdefaults__ or {});return result

def resident_window(texture,uv,core):
    return clone(previous.resident_window,MAX_RESIDENT_BYTES=MAX_RESIDENT_BYTES)(texture,uv,core)

def proxy():
    return SimpleNamespace(MAX_RESIDENT_BYTES=MAX_RESIDENT_BYTES,LIMITS=LIMITS,INPUT_NAMES=previous.INPUT_NAMES,candidate_samples=previous.candidate_samples,footprint=previous.footprint,resident_window=resident_window)

def sample_bytes(manifest):
    textures=manifest.get('textures',[]);previous._need(isinstance(textures,list) and len(textures)<=3,'bounded sparse texture table');total=0
    for texture in textures:
        windows=texture.get('windows',[]);previous._need(isinstance(windows,list) and len(windows)<=5,'bounded sparse window table')
        for item in windows:
            window=item['window'];previous._need(isinstance(window,dict),'sparse window object')
            if window.get('status')!='CAPTURED':previous._need('texels' not in window,'unavailable window has no invented bytes');continue
            texels=window.get('texels');previous._need(isinstance(texels,list) and len(texels)==4,'four sparse texels');sizes=[row.get('nbytes') for row in texels];previous._need(all(type(n) is int and n>0 for n in sizes) and sum(sizes)<=64,'64byte window read budget');total+=sum(sizes)
    previous._need(total<=960,'960byte total read budget');return total
