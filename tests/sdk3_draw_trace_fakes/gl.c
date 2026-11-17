#include <stdint.h>
#include <math.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
static int clear_error,bad_row;void fake_clear_error(void){clear_error=1;}void fake_bad_row(void){bad_row=1;}
static int reflect_terrain=1;void fake_plain_program(void){reflect_terrain=0;}
static int terrain_scene,scissor_on,depth_mask=1,scissor_box[4]={0,0,8,8},row_fbo;static float grid_depth[64];
static int calls,fail,args_ok=1,queries,samples,draw=77,readfb=78,readbuf=0x8ce0,rb=92,packbuf=17,active=0x84c3;
static int pack[8]={8,11,7,6,1,1,13,3};static unsigned err,nextid=100;static unsigned formats[512];
static const unsigned packenum[8]={0xd05,0xd02,0xd03,0xd04,0xd00,0xd01,0x806c,0x806b};
static void counted(void){++queries;errno=ENOENT;}
void fake_setup(int n,int f){samples=n;fail=f;}
void fake_terrain_scene(void){terrain_scene=1;scissor_on=1;scissor_box[0]=1;scissor_box[1]=2;scissor_box[2]=6;scissor_box[3]=5;for(int i=0;i<64;i++)grid_depth[i]=.42f;}
int fake_changed_pixels(void){int count=0;for(int i=0;i<64;i++)count+=grid_depth[i]!=.42f;return count;}
int fake_calls(void){return calls;}int fake_args_ok(void){return args_ok;}int fake_queries(void){return queries;}
int fake_restored(void){const int want[8]={8,11,7,6,1,1,13,3};return draw==77&&readfb==78&&readbuf==0x8ce0&&rb==92&&packbuf==17&&active==0x84c3&&!memcmp(want,pack,sizeof(pack))&&(!terrain_scene||(scissor_on&&depth_mask==1&&scissor_box[0]==1&&scissor_box[1]==2&&scissor_box[2]==6&&scissor_box[3]==5));}
static void call(int ok){args_ok&=ok&&errno==EDOM;++calls;if(terrain_scene)for(int i=0;i<64;i++)if(.6f<grid_depth[i])grid_depth[i]=.6f;errno=ERANGE;}
void glDrawArrays(unsigned m,int f,int n){call(m==4&&f==17&&n==31);}
void glDrawElements(unsigned m,int n,unsigned t,const void *p){call(m==4&&n==31&&t==5125&&(uintptr_t)p==0x12345000);}
void glDrawRangeElements(unsigned m,unsigned a,unsigned b,int n,unsigned t,const void *p){call(m==4&&a==17&&b==53&&n==31&&t==5125&&(uintptr_t)p==0x12345000);}
void glDrawArraysInstanced(unsigned m,int f,int n,int k){call(m==4&&f==17&&n==31&&k==7);}
void glDrawElementsInstanced(unsigned m,int n,unsigned t,const void *p,int k){call(m==4&&n==31&&t==5125&&(uintptr_t)p==0x12345000&&k==7);}
void glDrawElementsInstancedARB(unsigned m,int n,unsigned t,const void *p,int k){glDrawElementsInstanced(m,n,t,p,k);}
void glDrawArraysInstancedEXT(unsigned m,int f,int n,int k){glDrawArraysInstanced(m,f,n,k);}
void glDrawElementsIndirect(unsigned m,unsigned t,const void *p){call(m==4&&t==5125&&(uintptr_t)p==0x12345000);}
void glDrawArraysIndirect(unsigned m,const void *p){call(m==4&&(uintptr_t)p==0x12345000);}
void glGetIntegerv(unsigned p,int *v){counted();*v=0;for(int i=0;i<8;i++)if(p==packenum[i]){*v=pack[i];return;}switch(p){case 0x8ca6:*v=draw;break;case 0x8caa:*v=readfb;break;case 0xc02:*v=readbuf;break;case 0x8ca7:*v=rb;break;case 0x88ed:*v=packbuf;break;case 0x84e0:*v=active;break;case 0x8b8d:*v=reflect_terrain?7:8;break;case 0xc10:memcpy(v,scissor_box,sizeof(scissor_box));break;case 0xba2:v[0]=v[1]=0;v[2]=v[3]=8;break;case 0x80a8:*v=draw==77&&samples>0;break;case 0x8d57:*v=4;break;case 0x80a9:*v=draw==77?samples:0;break;case 0xd56:*v=24;break;case 0xb74:*v=0x203;break;case 0x8069:*v=55+active-0x84c0;break;case 0xb72:*v=depth_mask;break;}}
void glScissor(int x,int y,int w,int h){counted();scissor_box[0]=x;scissor_box[1]=y;scissor_box[2]=w;scissor_box[3]=h;}
void glEnable(unsigned p){counted();if(p==0xc11)scissor_on=1;}
void glDisable(unsigned p){counted();if(p==0xc11)scissor_on=0;}
void glDepthMask(unsigned char value){counted();depth_mask=value;}
void glClearBufferfv(unsigned p,int b,const float *v){counted();if(p!=0x1801||b||!terrain_scene){err=0x502;return;}for(int y=0;y<8;y++)for(int x=0;x<8;x++)if(depth_mask&&(!scissor_on||(x>=scissor_box[0]&&y>=scissor_box[1]&&x<scissor_box[0]+scissor_box[2]&&y<scissor_box[1]+scissor_box[3])))grid_depth[y*8+x]=*v;if(clear_error)err=0x502;}
void glFramebufferTexture2D(unsigned t,unsigned a,unsigned target,unsigned texture,int level){counted();if(t!=0x8ca8||a!=0x8ce0||target!=0xde1||texture!=66||level)err=0x502;row_fbo=readfb;}
void glGetFloatv(unsigned p,float *v){counted();if(p==0xb70){v[0]=0;v[1]=1;}else *v=0;}
void glGetBooleanv(unsigned p,unsigned char *v){counted();*v=p==0xb72;}
unsigned char glIsEnabled(unsigned p){counted();return p==0xb71||(p==0xc11&&scissor_on);}
unsigned glGetError(void){counted();unsigned e=err;err=0;return e;}
const unsigned char *glGetString(unsigned p){(void)p;counted();return (const unsigned char *)"FAKE_CPU_ONLY";}
void *glXGetCurrentContext(void){return (void *)(uintptr_t)0xabc;}
void glBindFramebuffer(unsigned target,unsigned id){counted();if(target==0x8d40){draw=readfb=(int)id;}else if(target==0x8ca9)draw=(int)id;else if(target==0x8ca8)readfb=(int)id;}
void glReadBuffer(unsigned b){counted();readbuf=(int)b;}
void glDrawBuffer(unsigned b){(void)b;counted();}
void glBindRenderbuffer(unsigned t,unsigned id){(void)t;counted();rb=(int)id;}
void glBindBuffer(unsigned t,unsigned id){counted();if(t==0x88eb)packbuf=(int)id;}
void glPixelStorei(unsigned p,int v){counted();for(int i=0;i<8;i++)if(packenum[i]==p)pack[i]=v;}
void glActiveTexture(unsigned a){counted();active=(int)a;}
void glGenFramebuffers(int n,unsigned *p){counted();while(n--)*p++=nextid++;}
void glGenRenderbuffers(int n,unsigned *p){glGenFramebuffers(n,p);}
void glDeleteFramebuffers(int n,const unsigned *p){(void)n;(void)p;counted();}
void glDeleteRenderbuffers(int n,const unsigned *p){(void)n;(void)p;counted();}
void glRenderbufferStorage(unsigned target,unsigned fmt,int w,int h){(void)target;counted();if(rb>=0&&rb<512)formats[rb]=fmt;if(w!=1||h!=1)err=0x501;}
void glFramebufferRenderbuffer(unsigned t,unsigned a,unsigned rt,unsigned id){(void)t;(void)a;(void)rt;(void)id;counted();}
unsigned glCheckFramebufferStatus(unsigned t){(void)t;counted();return 0x8cd5;}
void glGetFramebufferAttachmentParameteriv(unsigned t,unsigned a,unsigned p,int *v){(void)t;counted();*v=p==0x8cd0?0x8d41:(a==0x8ce0?88:89);}
void glGetRenderbufferParameteriv(unsigned t,unsigned p,int *v){(void)t;counted();*v=p==0x8d44?(rb==88?0x881a:rb==89?0x81a6:(int)formats[rb]):8;}
void glBlitFramebuffer(int ax,int ay,int bx,int by,int cx,int cy,int dx,int dy,unsigned mask,unsigned filter){counted();(void)mask;if(bx-ax!=1||by-ay!=1||cx||cy||dx!=1||dy!=1||filter!=0x2600)err=0x501;}
void glReadPixels(int x,int y,int w,int h,unsigned format,unsigned type,void *p){counted();if(fail){err=0x502;return;}if(packbuf||pack[0]!=1||pack[1]||pack[2]||pack[3]||pack[4]||pack[5]||pack[6]||pack[7]||h!=1||type!=0x1406){err=0x502;return;}float *v=p;if(terrain_scene&&readfb==row_fbo&&row_fbo){if(x||y!=2||w<1||w>8||format!=0x1908){err=0x502;return;}for(int i=0;i<w;i++){v[i*4]=(float)i;v[i*4+1]=2;v[i*4+2]=1;v[i*4+3]=.5f;}if(bad_row)v[0]=NAN;return;}if(w!=1){err=0x502;return;}if(terrain_scene){if(x<0||x>7||y<0||y>7){err=0x502;return;}float z=grid_depth[y*8+x];if(format==0x1902)*v=z;else{v[0]=z==.42f?.3f:1;v[1]=.5f;v[2]=z==.42f?.7f:0;v[3]=1;}return;}if(format==0x1902)*v=.42f;else{v[0]=calls*.1f;v[1]=.5f;v[2]=.75f;v[3]=1.;}}

void glGetMultisamplefv(unsigned p,unsigned i,float *v){(void)p;counted();v[0]=(i+.5f)/16;v[1]=.5f;}
void glGetProgramiv(unsigned p,unsigned q,int *v){(void)p;counted();*v=q==0x8b82?1:q==0x8b86&&terrain_scene&&reflect_terrain?11:0;}
void glGetAttachedShaders(unsigned p,int n,int *count,unsigned *s){(void)p;(void)n;(void)s;counted();*count=0;}
void glGetShaderiv(unsigned s,unsigned p,int *v){(void)s;(void)p;counted();*v=0;}
void glGetShaderSource(unsigned s,int n,int *len,char *text){(void)s;(void)n;(void)text;counted();*len=0;}
static const char *names[12]={"p3d_ModelViewProjectionMatrix","p3d_ModelMatrix","elevation_texture_ratio","attribute_tex","ShaderTerrainMesh.heightfield","yellow_tex","p3d_ModelViewMatrix","p3d_ProjectionMatrix","ShaderTerrainMesh.data_texture","ShaderTerrainMesh.view_index","ShaderTerrainMesh.terrain_size","ShaderTerrainMesh.chunk_size"};
void glGetActiveUniform(unsigned p,unsigned i,int n,int *len,int *size,unsigned *type,char *name){(void)p;counted();unsigned map[11]={0,1,2,3,4,6,7,8,9,10,11};if(!terrain_scene||i>=11){*len=*size=0;*type=0;return;}int k=(int)map[i];snprintf(name,(size_t)n,"%s",names[k]);*len=(int)strlen(name);*size=1;*type=k==0||k==1||k==6||k==7?0x8b5c:k==2?0x1406:k>=9?0x1404:0x8b5e;}
int glGetUniformLocation(unsigned p,const char *n){(void)p;counted();for(int i=0;i<12;i++)if(!strcmp(n,names[i]))return i;return -1;}
void glGetUniformfv(unsigned p,int l,float *v){(void)p;counted();if(l==2){*v=2;return;}for(int i=0;i<16;i++)v[i]=i%5==0?1:0;}
void glGetUniformiv(unsigned p,int l,int *v){(void)p;counted();*v=l==3?10:l==4?1:l==5?3:l==8?11:l==9?2:l==10?2048:l==11?128:0;}

void glGetIntegeri_v(unsigned p,unsigned i,int *v){(void)p;(void)i;counted();*v=0;}
void glGetTexLevelParameteriv(unsigned t,int l,unsigned p,int *v){(void)t;(void)l;counted();*v=p==0x1000||p==0x1001?8:active==0x84cb?0x8814:0x8f94;}
void glGetTexParameteriv(unsigned t,unsigned p,int *v){(void)t;(void)p;counted();*v=0;}
void glGetSamplerParameteriv(unsigned s,unsigned p,int *v){glGetTexParameteriv(s,p,v);}
