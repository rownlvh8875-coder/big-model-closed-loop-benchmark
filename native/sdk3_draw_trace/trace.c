#define _GNU_SOURCE
#include "trace.h"
#include <dlfcn.h>
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
_Static_assert(sizeof(void*)==8 && sizeof(int)==4 && sizeof(float)==4,"Linux amd64 GL ABI");
static struct dt_stats S={.version=1,.restored=1};
static FILE *output;static char directory[4096];static unsigned cap;static int phase,px,py,busy;
static void *gl_handle,*sdk_handle;static int depth_probe_enabled,depth_probe_used;static unsigned terrain_rows;
int dt_enable_depth_probe(int enabled){if(S.active||(enabled!=0&&enabled!=1))return -1;depth_probe_enabled=enabled;return 0;}
enum {E_INIT=1,E_LIMIT,E_GL,E_STATE,E_LOOKUP,E_QUERY,E_PROGRAM};
static void fail(unsigned code){if(!S.error)S.error=code;}
#define FN(R,N,A) typedef R(*N##_fn)A;static N##_fn q_##N
FN(void,glGetIntegerv,(unsigned,int*));FN(void,glGetFloatv,(unsigned,float*));FN(void,glGetBooleanv,(unsigned,unsigned char*));
FN(unsigned char,glIsEnabled,(unsigned));FN(unsigned,glGetError,(void));FN(void*,glXGetCurrentContext,(void));
FN(void,glBindFramebuffer,(unsigned,unsigned));FN(void,glReadBuffer,(unsigned));FN(void,glDrawBuffer,(unsigned));
FN(void,glBindRenderbuffer,(unsigned,unsigned));FN(void,glBindBuffer,(unsigned,unsigned));FN(void,glPixelStorei,(unsigned,int));FN(void,glActiveTexture,(unsigned));
FN(void,glGenFramebuffers,(int,unsigned*));FN(void,glGenRenderbuffers,(int,unsigned*));FN(void,glDeleteFramebuffers,(int,const unsigned*));FN(void,glDeleteRenderbuffers,(int,const unsigned*));
FN(void,glRenderbufferStorage,(unsigned,unsigned,int,int));FN(void,glFramebufferRenderbuffer,(unsigned,unsigned,unsigned,unsigned));FN(unsigned,glCheckFramebufferStatus,(unsigned));
FN(void,glGetFramebufferAttachmentParameteriv,(unsigned,unsigned,unsigned,int*));FN(void,glGetRenderbufferParameteriv,(unsigned,unsigned,int*));
FN(void,glBlitFramebuffer,(int,int,int,int,int,int,int,int,unsigned,unsigned));FN(void,glScissor,(int,int,int,int));FN(void,glEnable,(unsigned));FN(void,glDisable,(unsigned));FN(void,glDepthMask,(unsigned char));FN(void,glClearBufferfv,(unsigned,int,const float*));FN(void,glFramebufferTexture2D,(unsigned,unsigned,unsigned,unsigned,int));
FN(void,glReadPixels,(int,int,int,int,unsigned,unsigned,void*));FN(void,glGetMultisamplefv,(unsigned,unsigned,float*));
FN(void,glGetProgramiv,(unsigned,unsigned,int*));FN(void,glGetAttachedShaders,(unsigned,int,int*,unsigned*));FN(void,glGetShaderiv,(unsigned,unsigned,int*));FN(void,glGetShaderSource,(unsigned,int,int*,char*));
FN(void,glGetActiveUniform,(unsigned,unsigned,int,int*,int*,unsigned*,char*));FN(int,glGetUniformLocation,(unsigned,const char*));FN(void,glGetUniformfv,(unsigned,int,float*));FN(void,glGetUniformiv,(unsigned,int,int*));
FN(void,glGetIntegeri_v,(unsigned,unsigned,int*));FN(void,glGetTexLevelParameteriv,(unsigned,int,unsigned,int*));FN(void,glGetTexParameteriv,(unsigned,unsigned,int*));FN(void,glGetSamplerParameteriv,(unsigned,unsigned,int*));
#define Q(N,...) (S.queries++,q_##N(__VA_ARGS__))
static int iv(unsigned name){int v=0;Q(glGetIntegerv,name,&v);return v;}
static void *symbol(const char *name){if(!gl_handle){const char *path=getenv("SDK3_DRAW_TRACE_GL");gl_handle=dlopen(path?path:"libGL.so.1",RTLD_NOW|RTLD_LOCAL);}return gl_handle?dlsym(gl_handle,name):NULL;}
#define BIND(N) do{q_##N=(N##_fn)symbol(#N);if(!q_##N){fail(E_INIT);return -1;}}while(0)
static int init(void){
 BIND(glGetIntegerv);BIND(glGetFloatv);BIND(glGetBooleanv);BIND(glIsEnabled);BIND(glGetError);BIND(glXGetCurrentContext);
 BIND(glBindFramebuffer);BIND(glReadBuffer);BIND(glDrawBuffer);BIND(glBindRenderbuffer);BIND(glBindBuffer);BIND(glPixelStorei);BIND(glActiveTexture);
 BIND(glGenFramebuffers);BIND(glGenRenderbuffers);BIND(glDeleteFramebuffers);BIND(glDeleteRenderbuffers);BIND(glRenderbufferStorage);BIND(glFramebufferRenderbuffer);BIND(glCheckFramebufferStatus);
 BIND(glGetFramebufferAttachmentParameteriv);BIND(glGetRenderbufferParameteriv);BIND(glBlitFramebuffer);BIND(glReadPixels);BIND(glScissor);BIND(glEnable);BIND(glDisable);BIND(glDepthMask);BIND(glClearBufferfv);BIND(glFramebufferTexture2D);BIND(glGetMultisamplefv);
 BIND(glGetProgramiv);BIND(glGetAttachedShaders);BIND(glGetShaderiv);BIND(glGetShaderSource);BIND(glGetActiveUniform);BIND(glGetUniformLocation);BIND(glGetUniformfv);BIND(glGetUniformiv);
 BIND(glGetIntegeri_v);BIND(glGetTexLevelParameteriv);BIND(glGetTexParameteriv);BIND(glGetSamplerParameteriv);return 0;
}
static void number(float v){if(isfinite(v))fprintf(output,"%.9g",(double)v);else fputs("null",output);}
static void floats(const float *v,int n){fputc('[',output);for(int i=0;i<n;i++){if(i)fputc(',',output);number(v[i]);}fputc(']',output);}
static void ints(const int *v,int n){fputc('[',output);for(int i=0;i<n;i++)fprintf(output,"%s%d",i?",":"",v[i]);fputc(']',output);}
static void bits(const float *v,int n){fputc('[',output);for(int i=0;i<n;i++){uint32_t b;memcpy(&b,v+i,4);fprintf(output,"%s%u",i?",":"",b);}fputc(']',output);}
struct snapshot {int viewport[4],scissor[4],draw,read,samples,sample_buffers,max_samples,depth_bits,depth_func,depth_write,depth_test,blend,cull,offset,scissor_test;float range[2],color[4],depth,positions[32];unsigned error_before,error_after;int valid,restored;uintptr_t context;};
static unsigned resolve_fbo,resolve_color,resolve_depth,resolve_color_format,resolve_depth_format;
static const unsigned pack_names[8]={0xd05,0xd02,0xd03,0xd04,0xd00,0xd01,0x806c,0x806b};
static int rb_format(unsigned attachment){int type=0,name=0,format=0;Q(glGetFramebufferAttachmentParameteriv,0x8ca8,attachment,0x8cd0,&type);if(type!=0x8d41)return 0;Q(glGetFramebufferAttachmentParameteriv,0x8ca8,attachment,0x8cd1,&name);Q(glBindRenderbuffer,0x8d41,(unsigned)name);Q(glGetRenderbufferParameteriv,0x8d41,0x8d44,&format);return format;}
static int make_resolve(unsigned color,unsigned depth){
 if(resolve_fbo)return resolve_color_format==color && resolve_depth_format==depth;
 Q(glGenFramebuffers,1,&resolve_fbo);Q(glBindFramebuffer,0x8ca9,resolve_fbo);Q(glGenRenderbuffers,1,&resolve_color);Q(glBindRenderbuffer,0x8d41,resolve_color);Q(glRenderbufferStorage,0x8d41,color,1,1);Q(glFramebufferRenderbuffer,0x8ca9,0x8ce0,0x8d41,resolve_color);Q(glDrawBuffer,0x8ce0);
 if(depth){Q(glGenRenderbuffers,1,&resolve_depth);Q(glBindRenderbuffer,0x8d41,resolve_depth);Q(glRenderbufferStorage,0x8d41,depth,1,1);Q(glFramebufferRenderbuffer,0x8ca9,0x8d00,0x8d41,resolve_depth);}
 resolve_color_format=color;resolve_depth_format=depth;return Q(glCheckFramebufferStatus,0x8ca9)==0x8cd5;
}
static void snapshot(struct snapshot *r){
 memset(r,0,sizeof(*r));r->depth=NAN;for(int i=0;i<4;i++)r->color[i]=NAN;
 r->error_before=Q(glGetError);r->context=(uintptr_t)Q(glXGetCurrentContext);r->draw=iv(0x8ca6);r->read=iv(0x8caa);int old_readbuf=iv(0xc02),old_rb=iv(0x8ca7),old_pbo=iv(0x88ed),saved_pack[8];
 for(int i=0;i<8;i++)saved_pack[i]=iv(pack_names[i]);
 Q(glGetIntegerv,0xba2,r->viewport);Q(glGetIntegerv,0xc10,r->scissor);r->samples=iv(0x80a9);r->sample_buffers=iv(0x80a8);r->max_samples=iv(0x8d57);r->depth_bits=iv(0xd56);r->depth_func=iv(0xb74);r->depth_write=iv(0xb72);r->depth_test=Q(glIsEnabled,0xb71);r->blend=Q(glIsEnabled,0xbe2);r->cull=Q(glIsEnabled,0xb44);r->offset=Q(glIsEnabled,0x8037);r->scissor_test=Q(glIsEnabled,0xc11);Q(glGetFloatv,0xb70,r->range);
 int coordinate_ok=px>=r->viewport[0]&&py>=r->viewport[1]&&px<r->viewport[0]+r->viewport[2]&&py<r->viewport[1]+r->viewport[3]&&r->samples>=0&&r->samples<=16;
 if(r->samples>0&&r->samples<=16)for(int i=0;i<r->samples;i++)Q(glGetMultisamplefv,0x8e50,(unsigned)i,r->positions+2*i);
 Q(glBindFramebuffer,0x8ca8,(unsigned)r->draw);int source_readbuf=iv(0xc02);unsigned source_buffer=r->draw?0x8ce0:(unsigned)iv(0x8825);Q(glReadBuffer,source_buffer);
 Q(glBindBuffer,0x88eb,0);for(int i=0;i<8;i++)Q(glPixelStorei,pack_names[i],i?0:1);
 int read_x=px,read_y=py,ready=coordinate_ok;
 if(ready&&r->samples){int color=rb_format(0x8ce0),depth=r->depth_bits?rb_format(0x8d00):0;ready=color>0&&(!r->depth_bits||depth>0)&&make_resolve((unsigned)color,(unsigned)depth);if(ready){Q(glBindFramebuffer,0x8ca8,(unsigned)r->draw);Q(glBindFramebuffer,0x8ca9,resolve_fbo);Q(glBlitFramebuffer,px,py,px+1,py+1,0,0,1,1,0x4000u|(r->depth_bits?0x0100u:0),0x2600);S.blits++;Q(glBindFramebuffer,0x8ca8,resolve_fbo);Q(glReadBuffer,0x8ce0);read_x=read_y=0;}}
 if(ready){Q(glReadPixels,read_x,read_y,1,1,0x1908,0x1406,r->color);S.readbacks++;if(r->depth_bits){Q(glReadPixels,read_x,read_y,1,1,0x1902,0x1406,&r->depth);S.readbacks++;}}
 Q(glBindFramebuffer,0x8ca8,(unsigned)r->draw);Q(glReadBuffer,(unsigned)source_readbuf);Q(glBindFramebuffer,0x8ca8,(unsigned)r->read);Q(glReadBuffer,(unsigned)old_readbuf);Q(glBindFramebuffer,0x8ca9,(unsigned)r->draw);Q(glBindRenderbuffer,0x8d41,(unsigned)old_rb);
 for(int i=0;i<8;i++){Q(glPixelStorei,pack_names[i],saved_pack[i]);}
 Q(glBindBuffer,0x88eb,(unsigned)old_pbo);
 r->restored=iv(0x8ca6)==r->draw&&iv(0x8caa)==r->read&&iv(0xc02)==old_readbuf&&iv(0x8ca7)==old_rb&&iv(0x88ed)==old_pbo;
 for(int i=0;i<8;i++)r->restored&=iv(pack_names[i])==saved_pack[i];
 r->error_after=Q(glGetError);r->valid=ready&&!r->error_before&&!r->error_after&&r->restored;if(!r->restored){S.restored=0;fail(E_STATE);}if(!r->valid)fail(E_GL);
}
static void print_snapshot(const struct snapshot *r){
 fprintf(output,"{\"valid\":%s,\"restored\":%s,\"context\":%llu,\"draw_fbo\":%d,\"read_fbo\":%d,\"viewport\":",r->valid?"true":"false",r->restored?"true":"false",(unsigned long long)r->context,r->draw,r->read);ints(r->viewport,4);fputs(",\"color\":",output);floats(r->color,4);fputs(",\"color_bits\":",output);bits(r->color,4);fputs(",\"depth\":",output);number(r->depth);fputs(",\"depth_bits32\":",output);bits(&r->depth,1);fprintf(output,",\"samples\":%d,\"sample_buffers\":%d,\"max_samples\":%d,\"sample_positions\":",r->samples,r->sample_buffers,r->max_samples);floats(r->positions,r->samples>0&&r->samples<=16?2*r->samples:0);fprintf(output,",\"depth_bits\":%d,\"depth_func\":%d,\"depth_write\":%d,\"depth_test\":%d,\"blend\":%d,\"cull\":%d,\"polygon_offset\":%d,\"depth_range\":",r->depth_bits,r->depth_func,r->depth_write,r->depth_test,r->blend,r->cull,r->offset);floats(r->range,2);fputs(",\"scissor\":",output);ints(r->scissor,4);fprintf(output,",\"scissor_test\":%d",r->scissor_test);fprintf(output,",\"gl_error_before\":%u,\"gl_error_after\":%u}",r->error_before,r->error_after);
}
static const char *uniform_names[12]={"p3d_ModelViewProjectionMatrix","p3d_ModelMatrix","elevation_texture_ratio","attribute_tex","ShaderTerrainMesh.heightfield","yellow_tex","p3d_ModelViewMatrix","p3d_ProjectionMatrix","ShaderTerrainMesh.data_texture","ShaderTerrainMesh.view_index","ShaderTerrainMesh.terrain_size","ShaderTerrainMesh.chunk_size"};
struct program {unsigned id;int location[12],table_count;};static struct program programs[8];static unsigned program_count,source_count;static size_t source_bytes;
static struct program *program(unsigned id){
 if(!id)return NULL;
 for(unsigned i=0;i<program_count;i++){if(programs[i].id==id)return programs+i;}
 if(program_count==8){fail(E_PROGRAM);return NULL;}
 struct program *p=programs+program_count++;p->id=id;for(int i=0;i<12;i++)p->location[i]=-1;int count=0;Q(glGetProgramiv,id,0x8b86,&count);if(count<0||count>256){fail(E_PROGRAM);return p;}
 for(int i=0;i<count;i++){char name[512]={0};int n=0,size=0;unsigned type=0;Q(glGetActiveUniform,id,(unsigned)i,512,&n,&size,&type,name);if(n<=0||n>=512)continue;if(!strcmp(name,"p3d_TransformTable[0]")||!strcmp(name,"p3d_TransformTable")){if(type!=0x8b5c||size<1||size>100){fail(E_PROGRAM);}else{p->table_count=size;}continue;}if(size!=1)continue;for(int k=0;k<12;k++)if(!strcmp(name,uniform_names[k])&&type==((k<2||k==6||k==7)?0x8b5c:k==2?0x1406:k>=9?0x1404:0x8b5e))p->location[k]=Q(glGetUniformLocation,id,name);}
 unsigned attached[8];int n=0;Q(glGetAttachedShaders,id,8,&n,attached);fprintf(output,"{\"event\":\"program\",\"program\":%u,\"sources\":[",id);int emitted=0;
 for(int i=0;i<n&&i<8;i++){int length=0,type=0;Q(glGetShaderiv,attached[i],0x8b88,&length);Q(glGetShaderiv,attached[i],0x8b4f,&type);if(length<=1)continue;if(length>262145||source_count>=16||source_bytes+(size_t)length>4194304){fail(E_PROGRAM);continue;}char *text=malloc((size_t)length);if(!text){fail(E_INIT);continue;}int actual=0;Q(glGetShaderSource,attached[i],length,&actual,text);char file[96],path[4200];snprintf(file,sizeof(file),"gpu-shader-%u-%u.txt",id,source_count++);snprintf(path,sizeof(path),"%s/%s",directory,file);FILE *f=fopen(path,"wx");if(!f||actual<0||actual>=length){if(f)fclose(f);free(text);fail(E_INIT);continue;}size_t wrote=fwrite(text,1,(size_t)actual,f);fclose(f);free(text);if(wrote!=(size_t)actual){fail(E_INIT);continue;}source_bytes+=(size_t)actual;fprintf(output,"%s{\"shader\":%u,\"type\":%d,\"file\":\"%s\",\"nbytes\":%d}",emitted++?",":"",attached[i],type,file,actual);}
 fputs("]}\n",output);return p;
}
static void sampler(unsigned id,int location){
 if(location<0){fputs("null",output);return;}int unit=0;Q(glGetUniformiv,id,location,&unit);if(unit<0||unit>31){fail(E_PROGRAM);fputs("null",output);return;}int active=iv(0x84e0),sampler=0,w=0,h=0,format=0;Q(glActiveTexture,0x84c0u+(unsigned)unit);int texture=iv(0x8069);Q(glGetIntegeri_v,0x8919,(unsigned)unit,&sampler);Q(glGetTexLevelParameteriv,0xde1,0,0x1000,&w);Q(glGetTexLevelParameteriv,0xde1,0,0x1001,&h);Q(glGetTexLevelParameteriv,0xde1,0,0x1003,&format);unsigned names[5]={0x2801,0x2800,0x2802,0x2803,0x884c};int values[5]={0};for(int i=0;i<5;i++){if(sampler)Q(glGetSamplerParameteriv,(unsigned)sampler,names[i],values+i);else Q(glGetTexParameteriv,0xde1,names[i],values+i);}Q(glActiveTexture,(unsigned)active);int restored=iv(0x84e0)==active;if(!restored){S.restored=0;fail(E_STATE);}fprintf(output,"{\"unit\":%d,\"texture\":%d,\"sampler\":%d,\"width\":%d,\"height\":%d,\"internal_format\":%d,\"filter_wrap_compare\":",unit,texture,sampler,w,h,format);ints(values,5);fprintf(output,",\"restored\":%s}",restored?"true":"false");
}
static void uniforms(struct program *p){
 if(!p){fputs("null",output);return;}const char *keys[12]={"mvp","model","elevation_ratio","attribute","heightfield","yellow","model_view","projection","terrain_data_texture","terrain_view_index","terrain_size","terrain_chunk_size"};fputc('{',output);
 for(int i=0;i<12;i++){fprintf(output,"%s\"%s\":",i?",":"",keys[i]);if(i==3||i==4||i==5||i==8){sampler(p->id,p->location[i]);}else if(p->location[i]<0){fputs("null",output);}else if(i>=9){int value=0;Q(glGetUniformiv,p->id,p->location[i],&value);fprintf(output,"%d",value);}else{float values[16]={0};Q(glGetUniformfv,p->id,p->location[i],values);if(i==2){number(values[0]);}else{floats(values,16);}}}fputc('}',output);
}
static void transform_table(struct program *p){
 if(!p||!p->table_count){fputs("null",output);return;}int count=p->table_count,valid=1;float values[1600]={0};unsigned initial_error=Q(glGetError);
 for(int i=0;i<count;i++){char name[64];snprintf(name,sizeof(name),"p3d_TransformTable[%d]",i);int location=Q(glGetUniformLocation,p->id,name);if(location<0){valid=0;continue;}Q(glGetUniformfv,p->id,location,values+i*16);for(int j=0;j<16;j++){valid&=isfinite(values[i*16+j]);}}
 unsigned error=Q(glGetError);if(initial_error||error||!valid){fail(E_PROGRAM);}fprintf(output,"{\"status\":\"%s\",\"uniform\":\"p3d_TransformTable\",\"count\":%d,\"nbytes\":%d,\"gl_error_before\":%u,\"gl_error_after\":%u,\"float_bits\":",valid&&!initial_error&&!error?"MATRICES_RECORDED":"MATRICES_PARTIAL",count,count*64,initial_error,error);bits(values,count*16);fputc('}',output);
}

static int clear_target_depth(const struct snapshot *before){
 if(depth_probe_used||!before->valid||!before->depth_bits||!before->depth_test||!before->depth_write){fail(E_STATE);return 0;}depth_probe_used=1;
 Q(glEnable,0xc11);Q(glScissor,px,py,1,1);Q(glDepthMask,1);float one=1;Q(glClearBufferfv,0x1801,0,&one);
 Q(glScissor,before->scissor[0],before->scissor[1],before->scissor[2],before->scissor[3]);if(!before->scissor_test){Q(glDisable,0xc11);}Q(glDepthMask,(unsigned char)before->depth_write);
 int box[4];Q(glGetIntegerv,0xc10,box);int restored=!memcmp(box,before->scissor,sizeof(box))&&Q(glIsEnabled,0xc11)==before->scissor_test&&iv(0xb72)==before->depth_write;
 unsigned error=Q(glGetError);if(error){fail(E_GL);}if(!restored){S.restored=0;fail(E_STATE);}return restored&&!error;
}
static void terrain_row(struct program *p,int instances){
 if(!p||p->location[8]<0||p->location[9]<0){fputs("null",output);return;}
 if(terrain_rows>=2||instances<1||instances>64){fail(E_LIMIT);fputs("{\"status\":\"UNAVAILABLE_LIMIT\"}",output);return;}terrain_rows++;
 int unit=0,view=0;Q(glGetUniformiv,p->id,p->location[8],&unit);Q(glGetUniformiv,p->id,p->location[9],&view);if(unit<0||unit>31){fail(E_PROGRAM);fputs("{\"status\":\"UNAVAILABLE_UNIT\"}",output);return;}
 int old_active=iv(0x84e0),texture=0,w=0,h=0,format=0;Q(glActiveTexture,0x84c0u+(unsigned)unit);texture=iv(0x8069);Q(glGetTexLevelParameteriv,0xde1,0,0x1000,&w);Q(glGetTexLevelParameteriv,0xde1,0,0x1001,&h);Q(glGetTexLevelParameteriv,0xde1,0,0x1003,&format);Q(glActiveTexture,(unsigned)old_active);
 if(!texture||w<instances||h<1||h>65536||view<0||view>=h||format!=0x8814){fail(E_PROGRAM);fputs("{\"status\":\"UNAVAILABLE_LAYOUT\"}",output);return;}
 int old_read=iv(0x8caa),old_buffer=iv(0xc02),old_pbo=iv(0x88ed),saved[8];for(int i=0;i<8;i++){saved[i]=iv(pack_names[i]);}unsigned initial_error=Q(glGetError),fbo=0;float values[256]={0};Q(glGenFramebuffers,1,&fbo);Q(glBindFramebuffer,0x8ca8,fbo);Q(glFramebufferTexture2D,0x8ca8,0x8ce0,0xde1,(unsigned)texture,0);Q(glReadBuffer,0x8ce0);int complete=Q(glCheckFramebufferStatus,0x8ca8)==0x8cd5;
 Q(glBindBuffer,0x88eb,0);for(int i=0;i<8;i++){Q(glPixelStorei,pack_names[i],i?0:1);}if(complete){Q(glReadPixels,0,view,instances,1,0x1908,0x1406,values);S.readbacks++;}
 for(int i=0;i<8;i++){Q(glPixelStorei,pack_names[i],saved[i]);}Q(glBindBuffer,0x88eb,(unsigned)old_pbo);Q(glBindFramebuffer,0x8ca8,(unsigned)old_read);Q(glReadBuffer,(unsigned)old_buffer);Q(glDeleteFramebuffers,1,&fbo);
 int restored=iv(0x8caa)==old_read&&iv(0xc02)==old_buffer&&iv(0x88ed)==old_pbo&&iv(0x84e0)==old_active;for(int i=0;i<8;i++){restored&=iv(pack_names[i])==saved[i];}int finite=1;for(int i=0;i<instances*4;i++){finite&=isfinite(values[i]);}unsigned error=Q(glGetError);if(!restored){S.restored=0;fail(E_STATE);}if(initial_error||error||!complete){fail(E_GL);}if(!finite){fail(E_PROGRAM);}
 fprintf(output,"{\"status\":\"%s\",\"texture\":%d,\"unit\":%d,\"texture_size\":[%d,%d],\"internal_format\":%d,\"view_index\":%d,\"width\":%d,\"nbytes\":%d,\"restored\":%s,\"gl_error_before\":%u,\"gl_error_after\":%u,\"values\":",complete&&!initial_error&&!error&&restored&&finite?"ROW_RECORDED":"ROW_PARTIAL",texture,unit,w,h,format,view,instances,instances*16,restored?"true":"false",initial_error,error);floats(values,instances*4);fputs(",\"float_bits\":",output);bits(values,instances*4);fputc('}',output);
}

struct record {int enabled,kind,count,instances,depth_probed,depth_probe_state;unsigned mode,id;struct snapshot before;struct program *p;};
static void before(struct record *r,int kind,unsigned mode,int count,int instances){
 memset(r,0,sizeof(*r));S.forwards++;if(!S.active||busy||S.error)return;if(S.draws>=cap||S.readbacks+5>2048){fail(E_LIMIT);return;}if(S.queries+2048>100000){fail(E_QUERY);return;}busy=1;r->enabled=1;r->kind=kind;r->mode=mode;r->count=count;r->instances=instances;r->id=(unsigned)iv(0x8b8d);r->p=program(r->id);snapshot(&r->before);if(depth_probe_enabled&&phase==1&&r->p&&r->p->location[2]>=0&&r->p->location[3]>=0&&r->p->location[4]>=0){int was_used=depth_probe_used;r->depth_probe_state=clear_target_depth(&r->before);r->depth_probed=depth_probe_used!=was_used;}busy=0;
}
static void after(struct record *r){
 if(!r->enabled)return;
 busy=1;struct snapshot after;snapshot(&after);S.draws++;fprintf(output,"{\"event\":\"draw\",\"pid\":%ld,\"sequence\":%llu,\"phase\":%d,\"pixel_gl\":[%d,%d],\"kind\":%d,\"mode\":%u,\"count\":%d,\"instances\":%d,\"program\":%u,\"restored\":%s,\"before\":",(long)getpid(),(unsigned long long)S.draws,phase,px,py,r->kind,r->mode,r->count,r->instances,r->id,r->before.restored&&after.restored?"true":"false");print_snapshot(&r->before);fputs(",\"after\":",output);print_snapshot(&after);fputs(",\"uniforms\":",output);uniforms(r->p);fputs(",\"transform_table\":",output);transform_table(r->p);fputs(",\"terrain_data_row\":",output);terrain_row(r->p,r->instances);fputs(",\"depth_probe\":",output);if(r->depth_probed){fprintf(output,"{\"cleared_pixels\":1,\"state_restored\":%s,\"original_depth_bits32\":",r->depth_probe_state?"true":"false");bits(&r->before.depth,1);fputc('}',output);}else{fputs("null",output);}fputs("}\n",output);fflush(output);busy=0;
}
static void release(void){if(resolve_fbo){Q(glDeleteFramebuffers,1,&resolve_fbo);resolve_fbo=0;}if(resolve_color){Q(glDeleteRenderbuffers,1,&resolve_color);resolve_color=0;}if(resolve_depth){Q(glDeleteRenderbuffers,1,&resolve_depth);resolve_depth=0;}}
int dt_configure(const char *path,unsigned maximum){if(output||!path||!maximum||maximum>512||strlen(path)>=sizeof(directory))return -1;strcpy(directory,path);char *slash=strrchr(directory,'/');if(!slash)return -1;*slash=0;output=fopen(path,"wx");if(!output)return -1;cap=maximum;if(init())return -1;fprintf(output,"{\"event\":\"configured\",\"pid\":%ld,\"max_draws\":%u}\n",(long)getpid(),cap);return 0;}
int dt_begin(int region,int x,int y){if(!output||S.active||region<0||region>2||x<0||y<0||S.error)return -1;phase=region;px=x;py=y;S.active=1;return 0;}
int dt_end(void){S.active=0;if(q_glDeleteFramebuffers)release();if(output)fflush(output);return S.error?-1:0;}
int dt_close(void){dt_end();if(output){fclose(output);output=NULL;}return S.error?-1:0;}
int dt_get_stats(struct dt_stats *out){if(!out)return -1;*out=S;return 0;}
/* SDK extension lookup remains exact and default-OFF; only its returned draw pointer is observed. */
struct lookup {char name[64];uint32_t active;};
typedef void(*begin_fn)(const char*,struct lookup*);typedef void*(*resolved_fn)(const struct lookup*,void*,uint32_t);
static begin_fn original_begin;static resolved_fn original_resolved;
static void sdk_originals(void){if(original_begin&&original_resolved)return;const char *path=getenv("SDK3_DRAW_TRACE_SDK");if(!path)path="/opt/venv/lib/python3.11/site-packages/panda3d/libpandagl.so";sdk_handle=dlopen(path,RTLD_NOW|RTLD_NOLOAD);if(sdk_handle){original_begin=(begin_fn)dlsym(sdk_handle,"psd_lookup_begin");original_resolved=(resolved_fn)dlsym(sdk_handle,"psd_resolved");}if(!original_begin||!original_resolved)_exit(125);}
struct binding {const struct lookup *request;char name[64];};static __thread struct binding names[16];static __thread unsigned name_count;
void psd_lookup_begin(const char *name,struct lookup *request){int incoming=errno;sdk_originals();errno=incoming;original_begin(name,request);int returned=errno;S.lookups++;if(name_count<16&&name&&strnlen(name,64)<64){names[name_count].request=request;strcpy(names[name_count++].name,name);}else fail(E_LOOKUP);errno=returned;}
static void *route(const char *,void *);
void *psd_resolved(const struct lookup *request,void *value,uint32_t origin){int incoming=errno;sdk_originals();errno=incoming;void *result=original_resolved(request,value,origin);int returned=errno;char name[64]={0};unsigned i=name_count;while(i&&names[i-1].request!=request)i--;if(i){strcpy(name,names[i-1].name);memmove(names+i-1,names+i,(name_count-i)*sizeof(*names));name_count--;}else fail(E_LOOKUP);if(result&&name[0])result=route(name,result);errno=returned;return result;}
/* Separate slots preserve the exact function returned for every alias. */
#define ARR(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,int first,int n){int incoming=errno;struct record r;before(&r,1,m,n,1);errno=incoming;((void(*)(unsigned,int,int))real_##SLOT)(m,first,n);int returned=errno;after(&r);errno=returned;}
#define ELEM(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,int n,unsigned t,const void *p){int incoming=errno;struct record r;before(&r,2,m,n,1);errno=incoming;((void(*)(unsigned,int,unsigned,const void*))real_##SLOT)(m,n,t,p);int returned=errno;after(&r);errno=returned;}
#define RANGE(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,unsigned a,unsigned b,int n,unsigned t,const void *p){int incoming=errno;struct record r;before(&r,3,m,n,1);errno=incoming;((void(*)(unsigned,unsigned,unsigned,int,unsigned,const void*))real_##SLOT)(m,a,b,n,t,p);int returned=errno;after(&r);errno=returned;}
#define ARRI(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,int first,int n,int k){int incoming=errno;struct record r;before(&r,4,m,n,k);errno=incoming;((void(*)(unsigned,int,int,int))real_##SLOT)(m,first,n,k);int returned=errno;after(&r);errno=returned;}
#define ELEMI(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,int n,unsigned t,const void *p,int k){int incoming=errno;struct record r;before(&r,5,m,n,k);errno=incoming;((void(*)(unsigned,int,unsigned,const void*,int))real_##SLOT)(m,n,t,p,k);int returned=errno;after(&r);errno=returned;}
#define ARRD(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,const void *p){int incoming=errno;struct record r;before(&r,6,m,-1,-1);errno=incoming;((void(*)(unsigned,const void*))real_##SLOT)(m,p);int returned=errno;after(&r);errno=returned;}
#define ELEMD(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,unsigned t,const void *p){int incoming=errno;struct record r;before(&r,7,m,-1,-1);errno=incoming;((void(*)(unsigned,unsigned,const void*))real_##SLOT)(m,t,p);int returned=errno;after(&r);errno=returned;}
#define ROUTES(XA,XE,XR,XAI,XEI,XAD,XED) XA(a,"glDrawArrays") XE(e,"glDrawElements") XR(r,"glDrawRangeElements") XR(re,"glDrawRangeElementsEXT") XAI(ai,"glDrawArraysInstanced") XAI(aia,"glDrawArraysInstancedARB") XAI(aie,"glDrawArraysInstancedEXT") XAI(ain,"glDrawArraysInstancedNV") XAI(aig,"glDrawArraysInstancedANGLE") XEI(ei,"glDrawElementsInstanced") XEI(eia,"glDrawElementsInstancedARB") XEI(eie,"glDrawElementsInstancedEXT") XEI(ein,"glDrawElementsInstancedNV") XEI(eig,"glDrawElementsInstancedANGLE") XAD(ad,"glDrawArraysIndirect") XED(ed,"glDrawElementsIndirect")
ROUTES(ARR,ELEM,RANGE,ARRI,ELEMI,ARRD,ELEMD)
#define MATCH(SLOT,NAME) if(!strcmp(name,NAME)){if(value==(void*)wrap_##SLOT)return value;if(real_##SLOT&&real_##SLOT!=value){fail(E_LOOKUP);return value;}real_##SLOT=value;return (void*)wrap_##SLOT;}
static void *route(const char *name,void *value){ROUTES(MATCH,MATCH,MATCH,MATCH,MATCH,MATCH,MATCH)return value;}
void glDrawArrays(unsigned m,int first,int n){int saved=errno;if(!real_a)real_a=symbol("glDrawArrays");if(!real_a)_exit(125);errno=saved;wrap_a(m,first,n);}
void glDrawElements(unsigned m,int n,unsigned t,const void *p){int saved=errno;if(!real_e)real_e=symbol("glDrawElements");if(!real_e)_exit(125);errno=saved;wrap_e(m,n,t,p);}
