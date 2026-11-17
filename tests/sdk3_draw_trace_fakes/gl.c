#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
static int calls,fail,args_ok=1,queries,samples,draw=77,readfb=78,readbuf=0x8ce0,rb=92,packbuf=17,active=0x84c3;
static int pack[8]={8,11,7,6,1,1,13,3};static unsigned err,nextid=100;static unsigned formats[512];
static const unsigned packenum[8]={0xd05,0xd02,0xd03,0xd04,0xd00,0xd01,0x806c,0x806b};
static void counted(void){++queries;errno=ENOENT;}
void fake_setup(int n,int f){samples=n;fail=f;}
int fake_calls(void){return calls;}int fake_args_ok(void){return args_ok;}int fake_queries(void){return queries;}
int fake_restored(void){const int want[8]={8,11,7,6,1,1,13,3};return draw==77&&readfb==78&&readbuf==0x8ce0&&rb==92&&packbuf==17&&active==0x84c3&&!memcmp(want,pack,sizeof(pack));}
static void call(int ok){args_ok&=ok&&errno==EDOM;++calls;errno=ERANGE;}
void glDrawArrays(unsigned m,int f,int n){call(m==4&&f==17&&n==31);}
void glDrawElements(unsigned m,int n,unsigned t,const void *p){call(m==4&&n==31&&t==5125&&(uintptr_t)p==0x12345000);}
void glDrawRangeElements(unsigned m,unsigned a,unsigned b,int n,unsigned t,const void *p){call(m==4&&a==17&&b==53&&n==31&&t==5125&&(uintptr_t)p==0x12345000);}
void glDrawArraysInstanced(unsigned m,int f,int n,int k){call(m==4&&f==17&&n==31&&k==7);}
void glDrawElementsInstanced(unsigned m,int n,unsigned t,const void *p,int k){call(m==4&&n==31&&t==5125&&(uintptr_t)p==0x12345000&&k==7);}
void glDrawElementsInstancedARB(unsigned m,int n,unsigned t,const void *p,int k){glDrawElementsInstanced(m,n,t,p,k);}
void glDrawArraysInstancedEXT(unsigned m,int f,int n,int k){glDrawArraysInstanced(m,f,n,k);}
void glDrawElementsIndirect(unsigned m,unsigned t,const void *p){call(m==4&&t==5125&&(uintptr_t)p==0x12345000);}
void glDrawArraysIndirect(unsigned m,const void *p){call(m==4&&(uintptr_t)p==0x12345000);}
void glGetIntegerv(unsigned p,int *v){counted();*v=0;for(int i=0;i<8;i++)if(p==packenum[i]){*v=pack[i];return;}switch(p){case 0x8ca6:*v=draw;break;case 0x8caa:*v=readfb;break;case 0xc02:*v=readbuf;break;case 0x8ca7:*v=rb;break;case 0x88ed:*v=packbuf;break;case 0x84e0:*v=active;break;case 0x8b8d:*v=7;break;case 0xba2:v[0]=v[1]=0;v[2]=v[3]=8;break;case 0x80a8:*v=draw==77&&samples>0;break;case 0x8d57:*v=4;break;case 0x80a9:*v=draw==77?samples:0;break;case 0xd56:*v=24;break;case 0xb74:*v=0x203;break;case 0x8069:*v=55;break;case 0xb72:*v=1;break;}}
void glGetFloatv(unsigned p,float *v){counted();if(p==0xb70){v[0]=0;v[1]=1;}else *v=0;}
void glGetBooleanv(unsigned p,unsigned char *v){counted();*v=p==0xb72;}
unsigned char glIsEnabled(unsigned p){counted();return p==0xb71;}
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
void glReadPixels(int x,int y,int w,int h,unsigned format,unsigned type,void *p){counted();(void)x;(void)y;if(fail){err=0x502;return;}if(packbuf||pack[0]!=1||pack[1]||pack[2]||pack[3]||pack[4]||pack[5]||pack[6]||pack[7]||w!=1||h!=1||type!=0x1406){err=0x502;return;}float *v=p;if(format==0x1902)*v=.42f;else{v[0]=calls*.1f;v[1]=.5f;v[2]=.75f;v[3]=1.;}}
void glGetMultisamplefv(unsigned p,unsigned i,float *v){(void)p;counted();v[0]=(i+.5f)/16;v[1]=.5f;}
void glGetProgramiv(unsigned p,unsigned q,int *v){(void)p;counted();*v=q==0x8b82?1:0;}
void glGetAttachedShaders(unsigned p,int n,int *count,unsigned *s){(void)p;(void)n;(void)s;counted();*count=0;}
void glGetShaderiv(unsigned s,unsigned p,int *v){(void)s;(void)p;counted();*v=0;}
void glGetShaderSource(unsigned s,int n,int *len,char *text){(void)s;(void)n;(void)text;counted();*len=0;}
void glGetActiveUniform(unsigned p,unsigned i,int n,int *len,int *size,unsigned *type,char *name){(void)p;(void)i;(void)n;(void)name;counted();*len=*size=0;*type=0;}
int glGetUniformLocation(unsigned p,const char *n){(void)p;(void)n;counted();return -1;}
void glGetUniformfv(unsigned p,int l,float *v){(void)p;(void)l;counted();*v=0;}
void glGetUniformiv(unsigned p,int l,int *v){(void)p;(void)l;counted();*v=0;}
void glGetIntegeri_v(unsigned p,unsigned i,int *v){(void)p;(void)i;counted();*v=0;}
void glGetTexLevelParameteriv(unsigned t,int l,unsigned p,int *v){(void)t;(void)l;counted();*v=p==0x1000||p==0x1001?8:0x8f94;}
void glGetTexParameteriv(unsigned t,unsigned p,int *v){(void)t;(void)p;counted();*v=0;}
void glGetSamplerParameteriv(unsigned s,unsigned p,int *v){glGetTexParameteriv(s,p,v);}
