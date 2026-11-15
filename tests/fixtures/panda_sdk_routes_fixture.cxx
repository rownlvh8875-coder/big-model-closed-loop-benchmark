/* Handwritten CPU originals only. No Panda/GL/X11 library is loaded. */
#include "panda_cache_adapter.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
struct _XDisplay;struct __GLXFBConfigRec;
using Display=_XDisplay;using Config=__GLXFBConfigRec*;
using Base=void(*)(uint32_t,uint32_t,uint32_t);
using Pbuffer=unsigned long(*)(Display*,Config,const int*);
using Pixmap=unsigned long(*)(Display*,Config,unsigned long,const int*);
using SGIXPbuffer=unsigned long(*)(Display*,Config,unsigned,unsigned,int*);
using SGIXPixmap=unsigned long(*)(Display*,Config,unsigned long);
using Destroy=void(*)(Display*,unsigned long);
static const char *mode;static unsigned calls,args_ok=1,errno_ok=1,returns_ok=1;static bool reject_switch;
static int attrs[]={0};static const unsigned long H=0x100000900ul,P=0x100000007ul;
static bool is(const char *s){return !std::strcmp(mode,s);}
static void enter(){++calls;if(errno!=ERANGE)errno_ok=0;}
static void leave(){errno=is("preserve")?ERANGE:EDOM;}
static void checked(){if(errno!=(is("preserve")?ERANGE:EDOM))errno_ok=0;}
static Display *display(){return reinterpret_cast<Display*>(is("wrong_display")?2ul:1ul);}
static Config config(){return reinterpret_cast<Config>(2ul);}
static void base(uint32_t target,uint32_t index,uint32_t buffer){enter();if(index!=(is("maxbits")?UINT32_MAX:3u) || buffer!=123 || (target!=0x92c0 && target!=0x8c8e && target!=0x8a11 && target!=0x90d2 && !(is("invalid_target") && target==0x88eb)))args_ok=0;leave();}
static volatile unsigned other_marker;
static void base_other(uint32_t target,uint32_t index,uint32_t buffer){++other_marker;base(target,index,buffer);}
static unsigned long pbuffer(Display *d,Config c,const int *a){enter();if(d!=display()||c!=config()||a!=attrs)args_ok=0;leave();return H;}
static unsigned long pixmap(Display *d,Config c,unsigned long p,const int *a){enter();if(d!=display()||c!=config()||p!=P||a!=attrs)args_ok=0;leave();return H+1;}
static unsigned long sgix_pbuffer(Display *d,Config c,unsigned w,unsigned h,int *a){enter();if(d!=display()||c!=config()||w!=(is("maxbits")?UINT32_MAX:964u)||h!=(is("maxbits")?0u:604u)||a!=attrs)args_ok=0;leave();return H+2;}
static unsigned long sgix_pixmap(Display *d,Config c,unsigned long p){enter();if(d!=display()||c!=config()||p!=P)args_ok=0;leave();return H+3;}
static void destroy(Display *d,unsigned long p){enter();if(d!=display()||(p!=H&&p!=H+2))args_ok=0;leave();}
static void *create(void *d,void *v,void *share,int direct){enter();if(d!=(void*)1||v!=(void*)2||share||direct!=1)args_ok=0;leave();return (void*)0x111;}
static int make(void *d,unsigned long draw,void *ctx){enter();if(d!=(void*)1||ctx!=(void*)0x111||(draw!=7&&draw!=H))args_ok=0;leave();return reject_switch?0:1;}
static int make_both(void *d,unsigned long draw,unsigned long read,void *ctx){enter();if(d!=(void*)1||ctx!=(void*)0x111||draw!=7||read!=H)args_ok=0;leave();return 1;}
static void bind_frame(uint32_t target,uint32_t name){enter();if(target!=0x8d40u||name!=9)args_ok=0;leave();}
static void read_selector(uint32_t selector){enter();if(selector!=0x8ce0u)args_ok=0;leave();}
static void noop(){}
static void *resolve(const char *name,void *original){
 errno=ERANGE;psd_lookup l(name);void *p=original;
 if(is("paths"))for(unsigned o=PSD_PATH_GLX_CORE;o<=PSD_PATH_POSIX;++o)p=psd_path(o,p);
 void *r=psd_resolved(&l,p,is("compiled_origin")?PSD_SOURCE_COMPILED:PSD_SOURCE_RUNTIME);if(errno!=ERANGE)errno_ok=0;return r;
}
static void current(unsigned long draw){errno=ERANGE;(void)psd::call<PSD_MAKE_CURRENT>(make,(void*)1,draw,(void*)0x111);checked();}
int main(int argc,char **argv){
 if(argc<2)return 2;
 mode=argv[1];void *adapter=std::calloc(1,pca_context_size()),*cache=std::calloc(1,rc_context_size());if(!adapter||!cache)return 2;
 char safe_storage[257][64]={};const char *safe[257]={};size_t safe_count=0;
 if(argc==3){FILE *f=std::fopen(argv[2],"rb");if(!f)return 2;while(safe_count<257&&std::fgets(safe_storage[safe_count],64,f)){size_t n=std::strlen(safe_storage[safe_count]);if(n&&safe_storage[safe_count][n-1]=='\n')safe_storage[safe_count][--n]=0;if(n<3||n>63)return 2;safe[safe_count]=safe_storage[safe_count];++safe_count;}if(!std::feof(f)&&std::fgetc(f)!=EOF){std::fclose(f);return 2;}std::fclose(f);}
 int configured=is("off")?0:pca_install(adapter,pca_context_size(),safe,safe_count,10000);
 if(is("cap257")){psd_counts s={};psd_get_stats(&s);std::printf("{\"configure_result\":%d,\"configured\":%u,\"safe_count\":%zu,\"native_admitted\":false}\n",configured,s.configured,safe_count);std::free(adapter);std::free(cache);return 0;}
 if(configured)return 2;
 if(!is("off"))for(size_t i=0;i<safe_count;++i)if(resolve(safe[i],(void*)noop)!=(void*)noop)returns_ok=0;
 errno=ERANGE;if(psd::call<PSD_CREATE_LEGACY>(create,(void*)1,(void*)2,(void*)nullptr,1)!=(void*)0x111)returns_ok=0;checked();current(7);errno=ERANGE;psd::call<PSD_BIND_FRAMEBUFFER>(bind_frame,0x8d40u,9u);checked();errno=ERANGE;psd::call<PSD_READ_BUFFER>(read_selector,0x8ce0u);checked();
 if(!is("off")){rc_config c={0x333,{0x1111,0x2222},10000};if(rc_init(cache,rc_context_size(),&c)||pca_attach(adapter,cache))return 2;}
 rc_state_view before={};if(!is("off")&&pca_snapshot(adapter,&before))return 2;
 if(is("unknown")){
  Base f=(Base)resolve("glBindBufferBaseEXT",(void*)base);errno=ERANGE;f(0x90d2,3,123);checked();
 }else if(is("destroy_current_draw")||is("destroy_current_read")||is("switch_away")||is("failed_switch")){
  Pbuffer f=(Pbuffer)resolve("glXCreatePbuffer",(void*)pbuffer);errno=ERANGE;if(f(display(),config(),attrs)!=H)returns_ok=0;checked();
  if(is("destroy_current_read")){errno=ERANGE;(void)psd::call<PSD_MAKE_CONTEXT_CURRENT>(make_both,(void*)1,7ul,H,(void*)0x111);checked();}else current(H);
  if(is("switch_away")||is("failed_switch")){reject_switch=is("failed_switch");current(7);}
  Destroy d=(Destroy)resolve("glXDestroyPbuffer",(void*)destroy);errno=ERANGE;d(display(),H);checked();
 }else{
  Base f=(Base)resolve("glBindBufferBase",is("nulls")?nullptr:(void*)base);
  if(f){const uint32_t targets[]={0x92c0,0x8c8e,0x8a11,0x90d2};for(uint32_t t:targets){errno=ERANGE;f(is("invalid_target")?0x88ebu:t,is("maxbits")?UINT32_MAX:3u,123);checked();if(is("invalid_target")||is("rebind")||is("null_after_bound"))break;}}
  if(is("rebind")||is("null_after_bound")){
   Base next=(Base)resolve("glBindBufferBase",is("rebind")?(void*)base_other:nullptr);
   if(is("null_after_bound")){if(next)returns_ok=0;next=(Base)resolve("glBindBufferBase",(void*)base);}
   errno=ERANGE;next(0x90d2,3,123);checked();
  }else{
   Pbuffer a=(Pbuffer)resolve("glXCreatePbuffer",is("nulls")?nullptr:(void*)pbuffer);if(a){errno=ERANGE;if(a(display(),config(),attrs)!=H)returns_ok=0;checked();}
   Pixmap b=(Pixmap)resolve("glXCreatePixmap",is("nulls")?nullptr:(void*)pixmap);if(b){errno=ERANGE;if(b(display(),config(),P,attrs)!=H+1)returns_ok=0;checked();}
   SGIXPbuffer c=(SGIXPbuffer)resolve("glXCreateGLXPbufferSGIX",is("nulls")?nullptr:(void*)sgix_pbuffer);if(c){errno=ERANGE;if(c(display(),config(),is("maxbits")?UINT32_MAX:964u,is("maxbits")?0u:604u,attrs)!=H+2)returns_ok=0;checked();}
   SGIXPixmap d=(SGIXPixmap)resolve("glXCreateGLXPixmapWithConfigSGIX",is("nulls")?nullptr:(void*)sgix_pixmap);if(d){errno=ERANGE;if(d(display(),config(),P)!=H+3)returns_ok=0;checked();}
   Destroy e=(Destroy)resolve("glXDestroyPbuffer",is("nulls")?nullptr:(void*)destroy);if(e){errno=ERANGE;e(display(),H);checked();}
   Destroy g=(Destroy)resolve("glXDestroyGLXPbufferSGIX",is("nulls")?nullptr:(void*)destroy);if(g){errno=ERANGE;g(display(),H+2);checked();}
  }
 }
 rc_state_view after;std::memset(&after,255,sizeof(after));int snapshot=is("off")?-2:pca_snapshot(adapter,&after);unsigned stale=0;if(snapshot)for(unsigned char b:reinterpret_cast<unsigned char(&)[sizeof(after)]>(after))stale|=b;
 int finish=is("off")?0:pca_finish(adapter,0);psd_counts s={};psd_get_stats(&s);pca_counts p={};if(!is("off"))pca_get_stats(adapter,&p);
 std::printf("{\"finish\":%d,\"snapshot\":%d,\"source_error\":%u,\"adapter_error\":%u,\"calls\":%u,\"args_ok\":%u,\"errno_ok\":%u,\"returns_ok\":%u,\"stale\":%u,\"before_pack\":%u,\"after_pack\":%u,\"forwarded\":%llu,\"resolutions\":%llu,\"paths\":%llu,\"configured\":%u,\"native_admitted\":false}\n",finish,snapshot,s.error,p.error,calls,args_ok,errno_ok,returns_ok,is("off")?0:stale,before.pack_buffer,is("off")?0:after.pack_buffer,(unsigned long long)s.forwarded,(unsigned long long)s.resolutions,(unsigned long long)s.paths,s.configured);
 std::free(adapter);std::free(cache);return 0;
}
