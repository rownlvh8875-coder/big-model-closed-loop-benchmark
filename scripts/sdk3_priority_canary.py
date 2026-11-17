"""Owned tiny equal-depth cards exercise both source orders and RGB tag priority."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
from bigbench.sdk3_terrain_priority import install_rgb_terrain_priority
TAG_KEY='sdk3-priority-rgb'
TERRAIN_LABEL='terrain'

def need(value,message):
    if not value:raise ValueError(message)

def run(base,core,np,out,nonce,report,buffers,shader):
    front=[1.,float(int(nonce[0],16)&1),0.];terrain=[1.-v for v in front];result=dict(protocol='sdk3-priority-tie-canary-v1',status='INCOMPLETE',tag_key=TAG_KEY,terrain_label=TERRAIN_LABEL,render_calls=0,cases=[]);report['priority_canary']=result
    root=core.NodePath('sdk3-priority-scene');card=core.CardMaker('sdk3-priority-card');card.setFrame(-1,1,-1,1);geometry=root.attachNewNode(card.generate());ground=root.attachNewNode(card.generate());ground.setTag(TAG_KEY,TERRAIN_LABEL)
    for node,color in ((geometry,front),(ground,terrain)):
        node.setShader(shader);node.setShaderInput('diagnostic_rgb',core.Vec3(*color));node.setAttrib(core.DepthTestAttrib.make(core.DepthTestAttrib.MLess));node.setDepthWrite(True)
    holder=core.NodePath('sdk3-priority-tag-state');holder.setShader(shader);initial=holder.getState();sensors={};targets=[]
    for role in ('road','wide'):
        fb=core.FrameBufferProperties();fb.setRgbColor(True);fb.setFloatColor(True);fb.setRgbaBits(16,16,16,16);fb.setDepthBits(24);fb.setMultisamples(0);buffer=base.win.makeTextureBuffer('sdk3-priority-'+role,8,8,fbp=fb);need(buffer is not None,'tiny priority output');buffers.append(buffer);buffer.setClearDepthActive(True);buffer.setClearDepth(1.);buffer.setClearColorActive(True)
        camera=core.Camera('sdk3-priority-'+role);camera.setScene(root);camera.setTagStateKey(TAG_KEY);camera.setTagState(TERRAIN_LABEL,initial);lens=core.OrthographicLens();lens.setFilmSize(2,2);lens.setNearFar(.1,10);camera.setLens(lens);cam=root.attachNewNode(camera);cam.setPos(0,-2,0);region=buffer.makeDisplayRegion();region.setCamera(cam);region.setClearDepthActive(True);texture=core.Texture('sdk3-priority-ram-'+role);texture.setFormat(core.Texture.F_rgba16);texture.setComponentType(core.Texture.TFloat);buffer.addRenderTexture(texture,core.GraphicsOutput.RTMCopyRam);sensors['bigbench_'+role]=SimpleNamespace(cam=cam);targets.append((role,buffer,texture))
    for stage in ('control','candidate'):
        if stage=='candidate':result['receipt']=install_rgb_terrain_priority(SimpleNamespace(sensors=sensors),terrain_label=TERRAIN_LABEL,tag_key=TAG_KEY,core=core)
        for first in ('geometry','terrain'):
            geometry.setBin('fixed',0 if first=='geometry' else 1);ground.setBin('fixed',0 if first=='terrain' else 1);case=dict(stage=stage,first=first,images=[]);result['cases'].append(case)
            for _ in range(2):base.graphicsEngine.renderFrame();base.graphicsEngine.syncFrame();report['canary_render_calls']+=1;result['render_calls']+=1
            expected=terrain if stage=='candidate' or first=='terrain' else front
            for role,buffer,texture in targets:
                name=f'priority-{stage}-{first}-{role}.rgba';raw=bytes(texture.getRamImageAs('RGBA'));(Path(out)/name).write_bytes(raw);width=texture.getComponentWidth();typ=int(texture.getComponentType());image=dict(camera=role,file=name,nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),component_width=width,component_type=typ);case['images'].append(image);need(typ==2 and width==4 and len(raw)==1024 and np.array_equal(np.frombuffer(raw,dtype=np.float32).reshape(64,4),np.broadcast_to(np.asarray([*expected,1.]),(64,4))),'all64 tiny pixels follow source order or fixed terrain priority')
    for _,buffer,_ in targets:buffer.setActive(False)
    root.removeNode();holder.removeNode();result['status']='PRIORITY_TIE_CANARY_RECORDED';return result
