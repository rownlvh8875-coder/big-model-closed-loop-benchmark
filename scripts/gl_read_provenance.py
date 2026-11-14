"""Conservative provenance of recorded GL commands, never GPU pixel reconstruction."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math

FBO=0x8d40;READ=0x8ca8;DRAW=0x8ca9;COLOR=0x8ce0;DEPTH=0x8d00;STENCIL=0x8d20;DS=0x821a
TEX=0xde1;RBO=0x8d41
class Pointer(int):pass

# These calls do not write the framebuffer/image storage tracked by this reducer.
# Their counts remain in the report. This is deliberately not a full GL-state model.
IGNORED=set('''glAlphaFunc glAttachShader glBindAttribLocation glBindFragDataLocation
glBindSampler glBindSamplers glBlendEquation glBlendFuncSeparate glBufferData
glCheckFramebufferStatus glColor4f glColorMaterial glCompileShader glCreateShader
glCullFace glDepthFunc glDepthRange glDisableClientState glDisableVertexAttribArray
glEnableClientState glEnableVertexAttribArray glFrontFace glGenBuffers glGenSamplers
glGetActiveAttrib glGetAttribLocation glGetError glGetFloatv glGetInteger64v glGetIntegerv
glGetProgramInterfaceiv glGetQueryiv glGetRenderbufferParameteriv glGetShaderiv glGetString
glGetStringi glGetTexLevelParameteriv glHint glLightModelfv glLightModeli glLightf glLightfv
glLoadMatrixf glLogicOp glMaterialf glMaterialfv glMatrixMode glPointParameterfv glPolygonMode
glPopMatrix glPrioritizeTextures glPushMatrix glSamplerParameterf glSamplerParameterfv
glSamplerParameteri glShadeModel glShaderSource glTexParameterf glTexParameterfv glTexParameteri
glUniform1fv glUniform1uiv glUniform3fv glUniform4fv glUniformMatrix3fv glUniformMatrix4fv
glValidateProgram glVertexAttrib4fv glVertexAttribI4ui glVertexAttribPointer glVertexPointer
glViewport glViewportArrayv glXChooseFBConfig glXCreatePbuffer glXDestroyPbuffer
glXGetConfig glXGetFBConfigAttrib glXGetProcAddress glXGetVisualFromFBConfig
glXQueryExtension glXQueryExtensionsString glXQueryVersion'''.split())

def norm(v):
    if isinstance(v,Pointer):return {'host_pointer_only':True}
    if type(v) is bytes:return dict(blob_bytes=len(v),sha256=sha256(v).hexdigest())
    if type(v) is float and not math.isfinite(v):raise ValueError('finite recorded values required')
    if type(v) in (str,int,float,bool) or v is None:return v
    if type(v) in (tuple,list):return [norm(x) for x in v]
    if type(v) is dict:return {str(k):norm(x) for k,x in v.items()}
    raise ValueError('unsupported recorded value')

def integer(v,minimum=0):
    if not isinstance(v,int) or isinstance(v,bool) or v<minimum:raise ValueError('typed GL integer required')
    return int(v)

def analyze(events,*,max_calls=120000,max_nodes=20000,max_reads=256):
    if any(type(v) is not int or not 1<=v<=cap for v,cap in ((max_calls,120000),(max_nodes,20000),(max_reads,256))):
        raise ValueError('bounded analysis configuration required')
    contexts={};current=None;nodes=[];byid={};reads=[];images={};latest={};family={};counts=Counter();last=-1;calls=0
    def context():
        if current is None or current not in contexts:raise ValueError('current unshared context required')
        return contexts[current]
    def obj(c,kind,name,create=False):
        name=integer(name,1);objects=c['objects'][kind]
        if name not in objects:
            if not create:raise ValueError('unknown GL object')
            if sum(c['epochs'][kind].values())>=256:raise ValueError('object lifetime budget')
            epoch=c['epochs'][kind].get(name,0)+1;c['epochs'][kind][name]=epoch
            objects[name]=dict(key=f"c{c['id']}/{kind}:{name}:{epoch}",kind=kind,name=name,epoch=epoch,
                context=c['id'],storage={},generation={},attachments={},draw_buffers=[COLOR],read_buffer=COLOR)
        return objects[name]
    def fb(c,target):
        if target not in (FBO,READ,DRAW):raise ValueError('unsupported framebuffer target')
        return c['read'] if target==READ else c['draw']
    def image(c,o,level,aspect):
        level=integer(level);g=o['generation'].get(level,0)
        key=o['key']+f'/level{level}:storage{g}/{aspect}'
        storage=o['storage'].get(level,{})
        images[key]=dict(key=key,kind=o['kind'],name=o['name'],epoch=o['epoch'],context=c['id'],level=level,aspect=aspect,
            storage_generation=g,**deepcopy(storage))
        return key
    def attachment(c,f,slot,aspect):
        if f is None:
            key=f"c{c['id']}/default-drawable:{c['drawable']}/{aspect}:{slot}"
            images.setdefault(key,dict(key=key,kind='defaultbuffer',name=0,epoch=0,context=c['id'],level=0,aspect=aspect,samples=None))
            return key
        ref=f['attachments'].get(slot)
        if ref is None and slot in (DEPTH,STENCIL):ref=f['attachments'].get(DS)
        return image(c,ref[0],ref[1],aspect) if ref is not None else None
    def colors(c,f):return f['draw_buffers'] if f is not None else c['default_draw_buffers']
    def outputs(c,f,aspects=('color','depth','stencil'),index=None):
        keys=[]
        if 'color' in aspects:
            slots=colors(c,f)
            if index is not None:
                index=integer(index)
                if index>=len(slots):raise ValueError('clear color buffer index')
                slots=[slots[index]]
            keys.extend(attachment(c,f,s,'color') for s in slots if s!=0)
        for aspect,slot in (('depth',DEPTH),('stencil',STENCIL)):
            if aspect in aspects:keys.append(attachment(c,f,slot,aspect))
        return list(dict.fromkeys(k for k in keys if k is not None))
    def source(c,f,aspect='color'):
        slot=(f['read_buffer'] if f is not None else c['default_read_buffer']) if aspect=='color' else DEPTH if aspect=='depth' else STENCIL
        key=attachment(c,f,slot,aspect) if slot else None
        return dict(resource=key,potential_writer=latest.get(key),descriptor=deepcopy(images.get(key)),aspect=aspect)
    def emit(c,no,fn,kind,a,out,src=(),samplers=()):
        if len(nodes)>=max_nodes:raise ValueError('command node budget')
        dependencies={latest[k] for k in out if k in latest}
        for k in out:
            desc=images[k]
            if desc['kind']=='texture':
                owner=k.split('/level')[0]
                if owner in family:dependencies.add(family[owner])
        dependencies.update(s['potential_writer'] for s in src if s.get('potential_writer') is not None)
        dependencies.update(s['potential_writer'] for s in samplers if s.get('potential_writer') is not None)
        if any(i>=no or i not in byid for i in dependencies):raise ValueError('noncausal command dependency')
        out_textures={k.split('/level')[0] for k in out if images[k]['kind']=='texture'}
        node=dict(id=no,function=fn,kind=kind,context=c['id'],outputs=list(out),dependencies=sorted(dependencies),
            sources=deepcopy(list(src)),samplers=deepcopy(list(samplers)),args=norm(a),markers=list(c['markers']),
            draw_fbo=c['draw']['name'] if c['draw'] else 0,read_fbo=c['read']['name'] if c['read'] else 0,
            draw_fbo_key=c['draw']['key'] if c['draw'] else None,read_fbo_key=c['read']['key'] if c['read'] else None,
            program=c['program'],state=deepcopy(c['state']),potential_feedback=any(s['texture'] in out_textures for s in samplers),contents_reconstructed=False)
        nodes.append(node);byid[no]=node
        for k in out:
            latest[k]=no
            if images[k]['kind']=='texture':family[k.split('/level')[0]]=no
        return node
    def bound_texture(c):
        t=c['textures'].get(c['unit'])
        if t is None:raise ValueError('bound 2D texture required')
        return t
    def sampler_inputs(c):
        if c['program']==0:return []
        program=c['programs'].get(c['program'])
        if not program or not program['linked']:raise ValueError('successful program link evidence required')
        count=program['active_count']
        if count is None or set(program['reflected'])!=set(range(count)) or len(program['uniforms'])!=count:
            raise ValueError('complete active-uniform reflection coverage required')
        result=[]
        for name,u in program['uniforms'].items():
            if u['type'] not in (0x8b5e,0x8b62):continue
            if u['size']!=1 or name not in program['locations']:raise ValueError('supported reflected sampler location required')
            loc=program['locations'][name];value,assigned_count=program['units'].get(loc,(0,0))
            if assigned_count not in (0,1):raise ValueError('scalar sampler assignment required')
            unit=integer(value);t=c['textures'].get(unit)
            result.append(dict(uniform=name,type=u['type'],location=loc,unit=unit,
                unit_origin='recorded_uniform' if loc in program['units'] else 'successful_link_default_zero',
                texture=t['key'] if t else None,texture_name=t['name'] if t else 0,
                potential_writer=family.get(t['key']) if t else None))
        return result
    def route(writer):
        n=byid.get(writer);result=[]
        if not n or n['kind']!='draw_possible_write':return result
        for s in n['samplers']:
            resolve=byid.get(s['potential_writer'])
            if not resolve or resolve['kind']!='blit_possible_write':continue
            for src in resolve['sources']:
                if src['aspect']!='color' or src['descriptor'] is None:continue
                result.append(dict(rgb_draw_call=n['id'],rgb_program=n['program'],texture_name=s['texture_name'],
                    rgb_draw_fbo_key=n['draw_fbo_key'],
                    texture=s['texture'],resolve_call=resolve['id'],resolve_read_fbo=resolve['read_fbo'],resolve_draw_fbo=resolve['draw_fbo'],
                    resolve_read_fbo_key=resolve['read_fbo_key'],resolve_draw_fbo_key=resolve['draw_fbo_key'],
                    msaa_source=src['resource'],msaa_descriptor=src['descriptor'],samples=src['descriptor'].get('samples'),
                    source_potential_writer=src['potential_writer'],resolve_args=resolve['args'],contents_reconstructed=False))
        return result
    try:
        for event in events:
            calls+=1
            if calls>max_calls:raise ValueError('original call budget')
            if type(event) not in (tuple,list) or len(event)!=5:raise ValueError('five-field original call required')
            no,fn,items,ret,flags=event;no=integer(no)
            if no<=last or type(fn) is not str or type(items) not in (list,tuple) or type(flags) is not int or flags&64:
                raise ValueError('ordered complete original calls required')
            last=no;a={}
            for item in items:
                if type(item) not in (list,tuple) or len(item)!=2 or type(item[0]) is not str or item[0] in a:raise ValueError('unique named arguments required')
                a[item[0]]=item[1]
            counts[fn]+=1
            if fn in ('glXCreateContext','glXCreateContextAttribsARB'):
                if a.get('share_context',a.get('shareList',0))!=0:raise ValueError('shared context unsupported')
                cid=integer(ret,1)
                if cid in contexts:raise ValueError('duplicate context')
                contexts[cid]=dict(id=len(contexts)+1,objects={k:{} for k in ('texture','renderbuffer','framebuffer')},
                    epochs={k:{} for k in ('texture','renderbuffer','framebuffer')},read=None,draw=None,drawable=None,
                    textures={},unit=0,rbo=None,program=0,programs={},markers=[],state={},buffers={},default_draw_buffers=[],default_read_buffer=None)
                continue
            if fn=='glXMakeCurrent':
                if not ret:raise ValueError('failed context switch')
                cid=integer(a['ctx']);current=cid or None
                if current is not None:context()['drawable']=integer(a['drawable'])
                continue
            if fn=='glXDestroyContext':continue
            if fn in IGNORED:continue
            c=context()
            if fn in ('glGenTextures','glGenRenderbuffers','glGenFramebuffers'):
                kind,field={'glGenTextures':('texture','textures'),'glGenRenderbuffers':('renderbuffer','renderbuffers'),'glGenFramebuffers':('framebuffer','framebuffers')}[fn]
                names=a[field]
                if type(names) is not list or len(names)!=integer(a['n']):raise ValueError('generated names required')
                for name in names:
                    if integer(name,1) in c['objects'][kind]:raise ValueError('live name regenerated')
                    obj(c,kind,name,True)
            elif fn in ('glDeleteTextures','glDeleteRenderbuffers','glDeleteFramebuffers'):
                kind,field={'glDeleteTextures':('texture','textures'),'glDeleteRenderbuffers':('renderbuffer','renderbuffers'),'glDeleteFramebuffers':('framebuffer','framebuffers')}[fn]
                names=a[field]
                if type(names) is not list or len(names)!=integer(a['n']):raise ValueError('deleted names required')
                for name in names:
                    old=c['objects'][kind].pop(integer(name),None)
                    if old is None:continue
                    if kind in ('texture','renderbuffer'):
                        if kind=='texture':c['textures']={u:t for u,t in c['textures'].items() if t is not old}
                        elif c['rbo'] is old:c['rbo']=None
                        for f in (c['read'],c['draw']):
                            if f is not None:f['attachments']={s:x for s,x in f['attachments'].items() if x[0] is not old}
                    elif kind=='framebuffer':
                        if c['read'] is old:c['read']=None
                        if c['draw'] is old:c['draw']=None
            elif fn=='glBindFramebuffer':
                target=a['target'];name=integer(a['framebuffer']);f=obj(c,'framebuffer',name,True) if name else None
                if target not in (FBO,READ,DRAW):raise ValueError('framebuffer bind target')
                if target in (FBO,READ):c['read']=f
                if target in (FBO,DRAW):c['draw']=f
            elif fn in ('glFramebufferTexture2D','glFramebufferRenderbuffer'):
                f=fb(c,a['target'])
                if f is None:raise ValueError('default framebuffer attachment unsupported')
                slot=integer(a['attachment'])
                if fn=='glFramebufferTexture2D':
                    if a['textarget']!=TEX or integer(a['level'])!=0:raise ValueError('2D level-zero attachment required')
                    name=integer(a['texture']);ref=(obj(c,'texture',name),0) if name else None
                else:
                    if a['renderbuffertarget']!=RBO:raise ValueError('renderbuffer attachment target')
                    name=integer(a['renderbuffer']);ref=(obj(c,'renderbuffer',name),0) if name else None
                if ref is None:f['attachments'].pop(slot,None)
                else:f['attachments'][slot]=ref
            elif fn=='glBindRenderbuffer':
                if a['target']!=RBO:raise ValueError('renderbuffer target')
                name=integer(a['renderbuffer']);c['rbo']=obj(c,'renderbuffer',name,True) if name else None
            elif fn in ('glRenderbufferStorage','glRenderbufferStorageMultisample','glTexImage2D','glTexSubImage2D'):
                texture=fn.startswith('glTex');o=bound_texture(c) if texture else c['rbo']
                if o is None or a['target']!=(TEX if texture else RBO):raise ValueError('storage binding required')
                level=integer(a['level']) if texture else 0
                if fn!='glTexSubImage2D':
                    o['generation'][level]=o['generation'].get(level,0)+1
                    o['storage'][level]=dict(width=integer(a['width'],1),height=integer(a['height'],1),internalformat=integer(a['internalformat']),samples=0 if texture else integer(a.get('samples',0)))
                aspects=('color','depth','stencil')
                out=[image(c,o,level,s) for s in aspects]
                emit(c,no,fn,'cpu_upload_or_storage',a,out)
            elif fn=='glGenerateMipmap':
                if a['target']!=TEX:raise ValueError('mipmap target')
                t=bound_texture(c);src=family.get(t['key'])
                emit(c,no,fn,'mipmap_family_update',a,[],[dict(resource=t['key'],potential_writer=src)])
                family[t['key']]=no
            elif fn=='glActiveTexture':c['unit']=integer(a['texture']-0x84c0)
            elif fn=='glBindTexture':
                if a['target']!=TEX:raise ValueError('only 2D texture bindings supported')
                name=integer(a['texture'])
                if name:c['textures'][c['unit']]=obj(c,'texture',name,True)
                else:c['textures'].pop(c['unit'],None)
            elif fn=='glBindTextures':
                values=a['textures'];count=integer(a['count']);first=integer(a['first'])
                if values is None or values==0:values=[0]*count
                if type(values) is not list or len(values)!=count:raise ValueError('multibind texture values')
                for i,name in enumerate(values):
                    if integer(name):c['textures'][first+i]=obj(c,'texture',name)
                    else:c['textures'].pop(first+i,None)
            elif fn in ('glDrawBuffer','glDrawBuffers','glReadBuffer'):
                f=c['read'] if fn=='glReadBuffer' else c['draw']
                if fn=='glReadBuffer':
                    selected=integer(a['mode'])
                    if f is None:
                        if selected not in (0,0x404,0x405):raise ValueError('unsupported default read selector')
                        c['default_read_buffer']=selected
                    else:f['read_buffer']=selected
                else:
                    if fn=='glDrawBuffer':selected=[integer(a['mode'])]
                    else:
                        if type(a['bufs']) is not list or len(a['bufs'])!=integer(a['n']):raise ValueError('draw buffers values')
                        selected=[integer(v) for v in a['bufs']]
                    if f is None:
                        if any(v not in (0,0x404,0x405) for v in selected):raise ValueError('unsupported default draw selector')
                        c['default_draw_buffers']=selected
                    else:f['draw_buffers']=selected
            elif fn=='glCreateProgram':c['programs'][integer(ret,1)]=dict(linked=False,uniforms={},locations={},units={},active_count=None,reflected={})
            elif fn=='glLinkProgram':
                c['programs'][a['program']]=dict(linked=False,uniforms={},locations={},units={},active_count=None,reflected={})
            elif fn=='glGetProgramiv':
                if a['pname']==0x8b82:c['programs'][a['program']]['linked']=a['params']==[1]
                elif a['pname']==0x8b86:
                    if type(a['params']) is not list or len(a['params'])!=1:raise ValueError('active uniform count required')
                    value=integer(a['params'][0])
                    if value>1024:raise ValueError('active uniform count cap')
                    c['programs'][a['program']]['active_count']=value
            elif fn=='glGetActiveUniform':
                typ=integer(a['type'][0]);size=integer(a['size'][0],1);name=a['name']
                if type(name) is not str or len(a['type'])!=1 or len(a['size'])!=1:raise ValueError('recorded uniform reflection required')
                if typ not in (0x8b5e,0x8b62) and (0x8b5d<=typ<=0x8b64 or 0x8dc0<=typ<=0x8dd7 or 0x900c<=typ<=0x900f or 0x9108<=typ<=0x910d):raise ValueError('unsupported sampler type')
                c['programs'][a['program']]['uniforms'][name]=dict(type=typ,size=size)
                c['programs'][a['program']]['reflected'][integer(a['index'])]=name
            elif fn=='glGetUniformLocation':
                loc=integer(ret,-1)
                if loc>=0:c['programs'][a['program']]['locations'][a['name']]=loc
            elif fn=='glUseProgram':c['program']=integer(a['program'])
            elif fn in ('glUniform1i','glUniform1iv'):
                program=c['programs'][c['program']];loc=integer(a['location'],-1)
                if loc>=0:
                    if not program['linked']:raise ValueError('assignment before successful link')
                    if fn=='glUniform1i':values=[a['v0']]
                    else:
                        if type(a['value']) is not list or len(a['value'])!=integer(a['count']):raise ValueError('integer uniform assignment values required')
                        values=a['value']
                    for offset,value in enumerate(values):program['units'][loc+offset]=(integer(value,-2147483648),len(values))
            elif fn.startswith(('glDrawArrays','glDrawElements','glDrawRangeElements')):
                emit(c,no,fn,'draw_possible_write',a,outputs(c,c['draw']),samplers=sampler_inputs(c))
            elif fn in ('glClear','glClearBufferfv','glClearBufferfi'):
                if fn=='glClear':aspects=tuple(s for s,bit in (('color',0x4000),('depth',0x100),('stencil',0x400)) if a['mask']&bit);index=None
                else:
                    aspects={0x1800:('color',),0x1801:('depth',),0x1802:('stencil',),0x84f9:('depth','stencil')}[a['buffer']]
                    index=a['drawbuffer'] if aspects==('color',) else None
                emit(c,no,fn,'clear_possible_write',a,outputs(c,c['draw'],aspects,index))
            elif fn=='glBlitFramebuffer':
                aspects=tuple(s for s,bit in (('color',0x4000),('depth',0x100),('stencil',0x400)) if a['mask']&bit)
                emit(c,no,fn,'blit_possible_write',a,outputs(c,c['draw'],aspects),[source(c,c['read'],s) for s in aspects])
            elif fn=='glReadPixels':
                if len(reads)>=max_reads:raise ValueError('read budget')
                if a['format'] not in (0x1907,0x1908,0x80e0,0x80e1):raise ValueError('only recorded color reads supported')
                src=source(c,c['read']);reads.append(dict(call=no,context=c['id'],read_fbo=c['read']['name'] if c['read'] else 0,
                    read_fbo_key=c['read']['key'] if c['read'] else None,
                    read_buffer=c['read']['read_buffer'] if c['read'] else c['default_read_buffer'],source=src['resource'],source_descriptor=src['descriptor'],
                    potential_writer=src['potential_writer'],args=norm({k:v for k,v in a.items() if k!='pixels'}),
                    pixels_observed=False,markers=list(c['markers']),routes=route(src['potential_writer'])))
            elif fn=='glPushGroupMarkerEXT':
                if type(a['marker']) is not str:raise ValueError('string marker required')
                c['markers'].append(a['marker'])
            elif fn=='glPopGroupMarkerEXT':
                if not c['markers']:raise ValueError('unbalanced marker pop')
                c['markers'].pop()
            elif fn in ('glEnable','glDisable'):c['state']['cap:'+str(integer(a['cap']))]=fn=='glEnable'
            elif fn in ('glScissor','glScissorArrayv','glColorMask','glColorMaski','glDepthMask','glStencilMask','glStencilMaskSeparate','glClearColor','glClearDepth','glClearStencil','glPixelStorei'):
                c['state'][fn]=norm(a)
            elif fn=='glBindBuffer':c['buffers'][integer(a['target'])]=integer(a['buffer'])
            else:raise ValueError('unsupported recorded operation: '+fn)
    except (KeyError,IndexError,TypeError,OverflowError) as exc:
        raise ValueError('malformed or unsupported recorded call') from exc
    result=dict(schema='gl-read-command-provenance-v1',status='SCOPED_COMMAND_PROVENANCE_COMPLETE',calls=calls,
        function_counts=dict(counts),contexts=len(contexts),nodes=nodes,images=images,reads=reads,
        gpu_contents_reconstructed=False,gpu_completion_proven=False,native_execution_proven=False,
        new_native_calls=0,new_gl_calls=0,new_model_calls=0,new_ort_sessions=0,
        limitations=['Potential writer commands and conservative dependencies, not actual executed pixel writes.',
            'Default/undefined contents, sampling LOD, partial coverage, full rasterizer/vertex/uniform state and fetch execution are not reconstructed.',
            'ReadPixels arguments contain no authenticated returned pixels. Markers/ordinals are not a host or sealed GPU-frame identity.'])
    if len(json.dumps(result,allow_nan=False).encode())>16*1024*1024:raise ValueError('report byte budget')
    return result
