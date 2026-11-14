"""Hand-constructed command histories; no GL execution or native authority."""
import importlib
import unittest

try:p=importlib.import_module('scripts.gl_read_provenance')
except ModuleNotFoundError as exc:
    if exc.name!='scripts.gl_read_provenance':raise
    p=None

FBO=0x8d40;READ=0x8ca8;DRAW=0x8ca9;COLOR=0x8ce0;TEX=0xde1;RBO=0x8d41

class Events:
    def __init__(self):self.rows=[];self.context(11)
    def add(self,fn,ret=None,flags=0,**args):
        no=len(self.rows)+1;self.rows.append((no,fn,list(args.items()),ret,flags));return no
    def context(self,name,share=0):
        self.add('glXCreateContextAttribsARB',ret=name,share_context=share)
        self.add('glXMakeCurrent',ret=True,ctx=name,drawable=100+name)
    def texture(self,name=1,level=0,pixels=None):
        self.add('glGenTextures',n=1,textures=[name]);self.add('glBindTexture',target=TEX,texture=name)
        return self.add('glTexImage2D',target=TEX,level=level,internalformat=0x881a,width=64,height=32,border=0,format=0x1908,type=0x1406,pixels=pixels)
    def renderbuffer(self,name=1,samples=4):
        self.add('glGenRenderbuffers',n=1,renderbuffers=[name]);self.add('glBindRenderbuffer',target=RBO,renderbuffer=name)
        return self.add('glRenderbufferStorageMultisample',target=RBO,samples=samples,internalformat=0x881a,width=64,height=32)
    def framebuffer(self,name=1,texture=None,renderbuffer=None,attachment=COLOR):
        self.add('glGenFramebuffers',n=1,framebuffers=[name]);self.add('glBindFramebuffer',target=FBO,framebuffer=name)
        if texture is not None:self.add('glFramebufferTexture2D',target=FBO,attachment=attachment,textarget=TEX,texture=texture,level=0)
        if renderbuffer is not None:self.add('glFramebufferRenderbuffer',target=FBO,attachment=attachment,renderbuffertarget=RBO,renderbuffer=renderbuffer)
    def shader(self):
        self.add('glCreateProgram',ret=7);self.add('glLinkProgram',program=7)
        self.add('glGetProgramiv',program=7,pname=0x8b82,params=[1])
        self.add('glGetProgramiv',program=7,pname=0x8b86,params=[1])
        self.add('glGetActiveUniform',program=7,index=0,bufSize=64,length=None,size=[1],type=[0x8b5e],name='tex')
        self.add('glGetUniformLocation',ret=1,program=7,name='tex');self.add('glUseProgram',program=7)
    def clear(self):return self.add('glClearBufferfv',buffer=0x1800,drawbuffer=0,value=[0.,0.,0.,1.])
    def read(self):return self.add('glReadPixels',x=0,y=0,width=64,height=32,format=0x80e0,type=0x1401,pixels=123456)

def route_fixture():
    e=Events();e.texture();e.renderbuffer();e.framebuffer(2,renderbuffer=1);e.clear()
    e.add('glDrawArrays',mode=4,first=0,count=3)
    e.framebuffer(3,texture=1);e.add('glBindFramebuffer',target=READ,framebuffer=2)
    blit=e.add('glBlitFramebuffer',srcX0=0,srcY0=0,srcX1=64,srcY1=32,dstX0=0,dstY0=0,dstX1=64,dstY1=32,mask=0x4000,filter=0x2600)
    e.renderbuffer(2,samples=0);e.framebuffer(4,renderbuffer=2);e.shader()
    draw=e.add('glDrawArrays',mode=4,first=0,count=3);read=e.read()
    return e,blit,draw,read


class ReadProvenanceTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(p,'bounded read provenance reducer required')
    def test_original_rgb_read_route_includes_msaa_blit_and_shader_texture(self):
        e,blit,draw,read=route_fixture();r=p.analyze(e.rows);q=r['reads'][0]
        self.assertEqual((q['call'],q['potential_writer']),(read,draw));self.assertFalse(q['pixels_observed'])
        route=q['routes'][0]
        self.assertEqual((route['rgb_program'],route['texture_name'],route['resolve_read_fbo'],route['resolve_draw_fbo'],route['samples']),(7,1,2,3,4))
        self.assertEqual(route['resolve_call'],blit)
        self.assertFalse(r['gpu_completion_proven']);self.assertFalse(r['native_execution_proven'])
    def test_texture_one_and_renderbuffer_one_do_not_alias(self):
        e=Events();e.texture();e.renderbuffer();e.framebuffer(1,texture=1);a=e.clear()
        e.framebuffer(2,renderbuffer=1);e.clear();e.add('glBindFramebuffer',target=READ,framebuffer=1);e.read()
        q=p.analyze(e.rows)['reads'][0];self.assertEqual(q['potential_writer'],a)
        self.assertEqual(q['source_descriptor']['kind'],'texture')
    def test_selected_read_attachment_is_independent_of_draw_target(self):
        e=Events();e.texture(1);e.texture(2);e.framebuffer(1,texture=1)
        e.add('glFramebufferTexture2D',target=FBO,attachment=COLOR+1,textarget=TEX,texture=2,level=0)
        e.add('glDrawBuffer',mode=COLOR+1);a=e.clear();e.add('glReadBuffer',mode=COLOR+1)
        e.framebuffer(2,texture=1);e.clear();e.add('glBindFramebuffer',target=READ,framebuffer=1);e.read()
        q=p.analyze(e.rows)['reads'][0];self.assertEqual(q['potential_writer'],a);self.assertEqual(q['source_descriptor']['name'],2)
    def test_context_namespaces_do_not_share_equal_gl_names(self):
        e=Events();e.texture();e.framebuffer(1,texture=1);a=e.clear()
        e.context(22);e.texture();e.framebuffer(1,texture=1);e.clear()
        e.add('glXMakeCurrent',ret=True,ctx=11,drawable=111);e.read()
        q=p.analyze(e.rows)['reads'][0];self.assertEqual(q['potential_writer'],a);self.assertEqual(q['source_descriptor']['context'],1)
    def test_deleted_and_reused_names_receive_distinct_lifetimes(self):
        e=Events();e.texture();e.framebuffer(1,texture=1);e.clear();e.read()
        e.add('glDeleteFramebuffers',n=1,framebuffers=[1]);e.add('glDeleteTextures',n=1,textures=[1])
        e.texture();e.framebuffer(1,texture=1);e.clear();e.read();a,b=p.analyze(e.rows)['reads']
        self.assertNotEqual(a['source'],b['source']);self.assertEqual((a['source_descriptor']['epoch'],b['source_descriptor']['epoch']),(1,2))
    def test_integer_non_sampler_uniform_does_not_create_texture_dependency(self):
        e,_,draw,_=route_fixture();e.rows.pop();e.rows.pop()
        e.add('glGetProgramiv',program=7,pname=0x8b86,params=[2])
        e.add('glGetActiveUniform',program=7,index=1,bufSize=64,length=None,size=[1],type=[0x8b56],name='enabled')
        e.add('glGetUniformLocation',ret=2,program=7,name='enabled');e.add('glUniform1i',location=2,v0=1)
        draw=e.add('glDrawArrays',mode=4,first=0,count=3);e.read()
        node=next(n for n in p.analyze(e.rows)['nodes'] if n['id']==draw)
        self.assertEqual(len(node['samplers']),1);self.assertEqual(node['samplers'][0]['uniform'],'tex')
    def test_missing_or_partial_active_reflection_cannot_complete(self):
        for mode in ('no_count','partial'):
            e,_,_,_=route_fixture()
            e.rows=[row for row in e.rows if not (mode=='no_count' and row[1]=='glGetProgramiv' and dict(row[2])['pname']==0x8b86)]
            if mode=='partial':
                e.rows=[(no,fn,[(k,[2] if k=='params' else v) for k,v in args],ret,flags) if fn=='glGetProgramiv' and dict(args)['pname']==0x8b86 else (no,fn,args,ret,flags) for no,fn,args,ret,flags in e.rows]
            with self.subTest(mode=mode),self.assertRaises(ValueError):p.analyze(e.rows)
    def test_integer_assignment_before_reflection_retains_sampler_unit(self):
        e=Events();e.texture(1);e.texture(2);e.add('glActiveTexture',texture=0x84c1);e.add('glBindTexture',target=TEX,texture=2)
        e.add('glActiveTexture',texture=0x84c0);e.add('glBindTexture',target=TEX,texture=1);e.framebuffer(1,texture=1)
        e.add('glCreateProgram',ret=7);e.add('glLinkProgram',program=7);e.add('glGetProgramiv',program=7,pname=0x8b82,params=[1])
        e.add('glGetProgramiv',program=7,pname=0x8b86,params=[1]);e.add('glGetUniformLocation',ret=1,program=7,name='tex');e.add('glUseProgram',program=7)
        e.add('glUniform1i',location=1,v0=1);e.add('glGetActiveUniform',program=7,index=0,bufSize=64,length=None,size=[1],type=[0x8b5e],name='tex')
        call=e.add('glDrawArrays',mode=4,first=0,count=3);e.read();node=next(n for n in p.analyze(e.rows)['nodes'] if n['id']==call)
        self.assertEqual((node['samplers'][0]['unit'],node['samplers'][0]['texture_name']),(1,2))
    def test_default_front_and_back_are_distinct_read_resources(self):
        e=Events();e.add('glDrawBuffer',mode=0x404);front=e.clear();e.add('glReadBuffer',mode=0x404);e.read()
        e.add('glDrawBuffer',mode=0x405);back=e.clear();e.add('glReadBuffer',mode=0x405);e.read()
        a,b=p.analyze(e.rows)['reads'];self.assertEqual((a['potential_writer'],b['potential_writer']),(front,back))
        self.assertEqual((a['read_buffer'],b['read_buffer']),(0x404,0x405));self.assertNotEqual(a['source'],b['source'])
    def test_default_none_does_not_acquire_a_color_writer(self):
        e=Events();e.add('glDrawBuffer',mode=0);e.clear();e.add('glReadBuffer',mode=0);e.read()
        q=p.analyze(e.rows)['reads'][0];self.assertIsNone(q['source']);self.assertIsNone(q['potential_writer'])
    def test_partial_clear_preserves_previous_possible_producer(self):
        e=Events();e.texture();e.framebuffer(1,texture=1);a=e.clear()
        e.add('glEnable',cap=0xc11);e.add('glScissor',x=0,y=0,width=1,height=1);b=e.clear();e.read();r=p.analyze(e.rows)
        n=next(n for n in r['nodes'] if n['id']==b);self.assertIn(a,n['dependencies']);self.assertFalse(n['contents_reconstructed'])
    def test_mipmap_generation_does_not_overwrite_read_level_zero(self):
        e=Events();e.texture();e.framebuffer(1,texture=1);a=e.clear();e.add('glGenerateMipmap',target=TEX);e.read()
        self.assertEqual(p.analyze(e.rows)['reads'][0]['potential_writer'],a)
    def test_feedback_dependencies_are_snapshotted_before_output_write(self):
        e=Events();e.texture();e.framebuffer(1,texture=1);e.clear();e.shader();draw=e.add('glDrawArrays',mode=4,first=0,count=3);e.read()
        n=next(n for n in p.analyze(e.rows)['nodes'] if n['id']==draw)
        self.assertTrue(n['potential_feedback']);self.assertTrue(all(i<draw for i in n['dependencies']))
    def test_attachment_replacement_does_not_change_previous_read_record(self):
        e=Events();e.texture(1);e.texture(2);e.framebuffer(1,texture=1);e.clear();e.read()
        e.add('glFramebufferTexture2D',target=FBO,attachment=COLOR,textarget=TEX,texture=2,level=0);e.clear();e.read()
        a,b=p.analyze(e.rows)['reads'];self.assertEqual((a['source_descriptor']['name'],b['source_descriptor']['name']),(1,2))
    def test_storage_redefinition_is_unobserved_not_previous_pixels(self):
        e=Events();e.texture(pixels=b'abcd');e.framebuffer(1,texture=1);e.clear()
        new=e.add('glTexImage2D',target=TEX,level=0,internalformat=0x881a,width=64,height=32,border=0,format=0x1908,type=0x1406,pixels=None);e.read()
        r=p.analyze(e.rows);self.assertEqual(r['reads'][0]['potential_writer'],new)
        self.assertFalse(next(n for n in r['nodes'] if n['id']==new)['contents_reconstructed'])
    def test_deleting_bound_renderbuffer_detaches_it_from_bound_framebuffer(self):
        e=Events();e.renderbuffer();e.framebuffer(1,renderbuffer=1);e.clear()
        e.add('glDeleteRenderbuffers',n=1,renderbuffers=[1]);e.read()
        q=p.analyze(e.rows)['reads'][0];self.assertIsNone(q['source']);self.assertIsNone(q['potential_writer'])
    def test_shared_context_unsupported_writer_and_incomplete_call_fail_closed(self):
        for mutate in (lambda e:e.context(22,share=11),lambda e:e.add('glCopyImageSubData',srcName=1),
                       lambda e:e.add('glDrawArrays',mode=4,first=0,count=3,flags=64),
                       lambda e:e.rows.append(e.rows[-1]),lambda e:e.add('glBindFramebuffer',target=FBO)):
            e,_,_,_=route_fixture();mutate(e)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):p.analyze(e.rows)
    def test_original_call_node_read_budgets_fail_before_success(self):
        e,_,_,_=route_fixture();e.read()
        for bounds in (dict(max_calls=1),dict(max_nodes=1),dict(max_reads=1)):
            with self.subTest(bounds=bounds),self.assertRaises(ValueError):p.analyze(e.rows,**bounds)


if __name__=='__main__':unittest.main()
