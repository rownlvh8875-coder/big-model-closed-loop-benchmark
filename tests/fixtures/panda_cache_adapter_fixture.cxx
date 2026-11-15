#include "panda_cache_adapter.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <pthread.h>
struct cpu_call {int32_t x,y,w,h;uint32_t f,t;void *p;uintptr_t tex,gsg,capacity,image;int32_t z,view;};
extern "C" int pca_fixture_call(const cpu_call *);
static const char *mode;static void *adapter;static uintptr_t next_handle=0x111;static unsigned originals,reads,args_ok=1,errno_ok=1,regs_ok=1,depth,read_ready,stale_output;
static unsigned char pixels[128];
static bool is(const char *s){return !std::strcmp(mode,s);}
static void enter(){++originals;if(errno!=ERANGE)args_ok=0;}
static void leave(){if(!is("preserve"))errno=EDOM;}
static void checked(){if(errno!=(is("preserve")?ERANGE:EDOM))errno_ok=0;}
static void *create(void *display,void *visual,void *share,int direct){enter();if(display!=(void*)1 || visual!=(void*)2 || share!=(is("shared")?(void*)3:nullptr) || direct!=1)args_ok=0;leave();return (void*)next_handle;}
static void *create_new(void *display,void *config,int type,void *share,int direct){return create(display,config,share,direct!=type?direct:0);}
static void *create_attribs(void *display,void *config,void *share,int direct,const int *attrs){if(!attrs || attrs[0])args_ok=0;return create(display,config,share,direct);}
static int make(void *display,unsigned long draw,void *ctx){enter();if((display!=(void*)1 && !(is("display") && display==(void*)2)) || draw!=7 || !ctx)args_ok=0;leave();return is("truthy_current")?-1:is("failed_switch") && ctx==(void*)0x222?0:1;}
static int make_both(void *display,unsigned long draw,unsigned long read,void *ctx){enter();if(display!=(void*)1 || (draw || read || ctx))args_ok=0;leave();return 1;}
static void destroy(void *display,void *ctx){enter();if(display!=(void*)1 || !ctx)args_ok=0;leave();}
static void store(uint32_t name,int32_t value){enter();if(name!=0xd05 || value!=1)args_ok=0;
 if(is("source_reentry") && !depth){depth=1;errno=ERANGE;psd::call<PSD_PIXEL_STORE>(store,name,value);checked();depth=0;}
 if(is("original_snapshot") && read_ready){rc_state_view v;std::memset(&v,255,sizeof(v));if(pca_snapshot(adapter,&v)==0)args_ok=0;for(unsigned char c:reinterpret_cast<unsigned char(&)[sizeof(v)]>(v))stale_output|=c;}
 leave();}
static void bind_buffer(uint32_t target,uint32_t name){enter();if(target!=0x88eb || (name!=7 && name!=0))args_ok=0;leave();}
static void bind_frame(uint32_t target,uint32_t name){enter();if((target!=0x8d40 && target!=0x8ca9) || (name!=9 && name!=99))args_ok=0;leave();}
static void select_read(uint32_t value){enter();if(value!=0x8ce0)args_ok=0;leave();}
static void remove_buffers(int32_t n,const uint32_t *names){enter();int want=is("empty_delete")?0:is("delete_bad")?33:is("delete_negative")?-1:1;
 if(n!=want || (n>0 && (!names || names[0]!=(is("unrelated_delete") || is("two_contexts") || is("failed_switch")?8u:is("zero_delete")?0u:7u))))args_ok=0;
 if(is("delete_mutate") && n>0)const_cast<uint32_t*>(names)[0]=99;
 leave();}
static void remove_second(int32_t n,const uint32_t *names){enter();if(n!=1 || names[0]!=7)args_ok=0;leave();}
static void remove_frames(int32_t n,const uint32_t *names){enter();if(n!=1 || names[0]!=(is("draw_delete")?99u:9u))args_ok=0;if(is("fbo_mutate"))const_cast<uint32_t*>(names)[0]=42;leave();}
static uint32_t get_error(){enter();leave();return is("nonzero_error")?0x502:0;}
static void read_original(int32_t x,int32_t y,int32_t w,int32_t h,uint32_t f,uint32_t t,void *p){++reads;if(x!=-7 || y!=11 || w!=5 || h!=3 || f!=0x1907 || t!=0x1401 || p!=pixels || errno!=ERANGE)args_ok=0;leave();}
static void new_context(){errno=ERANGE;
 if(is("new") || is("sgix")){void *p=is("new")?psd::call<PSD_CREATE_NEW>(create_new,(void*)1,(void*)2,3,(void*)nullptr,1):psd::call<PSD_CREATE_SGIX>(create_new,(void*)1,(void*)2,3,(void*)nullptr,1);if(p!=(void*)next_handle)args_ok=0;}
 else if(is("attribs")){int attrs[]={0};if(psd::call<PSD_CREATE_ATTRIBS>(create_attribs,(void*)1,(void*)2,(void*)nullptr,1,attrs)!=(void*)next_handle)args_ok=0;}
 else if(psd::call<PSD_CREATE_LEGACY>(create,(void*)1,(void*)2,is("shared")?(void*)3:nullptr,1)!=(void*)next_handle)args_ok=0;
 checked();}
static void current(uintptr_t handle,uintptr_t display=1){errno=ERANGE;int r=psd::call<PSD_MAKE_CURRENT>(make,(void*)display,7ul,(void*)handle);if(r!=(is("truthy_current")?-1:is("failed_switch") && handle==0x222?0:1))args_ok=0;checked();}
static void unbind(){errno=ERANGE;if(psd::call<PSD_MAKE_CONTEXT_CURRENT>(make_both,(void*)1,0ul,0ul,(void*)nullptr)!=1)args_ok=0;checked();}
static void dead(uintptr_t handle){errno=ERANGE;psd::call<PSD_DESTROY_CONTEXT>(destroy,(void*)1,(void*)handle);checked();}
static void buffer(){errno=ERANGE;psd::call<PSD_BIND_BUFFER>(bind_buffer,0x88ebu,7u);checked();}
static void *foreign(void *){if(is("source_thread")){errno=ERANGE;psd::call<PSD_PIXEL_STORE>(store,0xd05u,1);checked();}else{rc_state_view v;std::memset(&v,255,sizeof(v));if(pca_snapshot(adapter,&v)==0)args_ok=0;}return nullptr;}
int main(int argc,char **argv){mode=argc>1?argv[1]:"bootstrap";adapter=std::malloc(pca_context_size());void *cache=std::malloc(rc_context_size());if(!adapter || !cache)return 2;
 rc_config cfg={0x333,{0x1111,0x2222},10000};if(rc_init(cache,rc_context_size(),&cfg) || psd_bind_read(read_original) || pca_install(adapter,pca_context_size(),nullptr,0,is("eventcap")?2:10000))return 3;
 if(is("install_twice") && pca_install(adapter,pca_context_size(),nullptr,0,10000)==0)args_ok=0;
 if(is("live") || is("original_snapshot"))if(pca_attach(adapter,cache))return 4;
 if(is("failed_create")){next_handle=0;new_context();next_handle=0x111;}
 new_context();current(0x111);
 if(is("aliases")){
  errno=ERANGE;psd_lookup l("glBindBufferARB");void *p=(void*)bind_buffer;for(unsigned o=PSD_PATH_GLX_CORE;o<=PSD_PATH_POSIX;++o)p=psd_path(o,p);void *r=psd_resolved(&l,p,PSD_SOURCE_RUNTIME);if(errno!=ERANGE)errno_ok=0;
  errno=ERANGE;((void(*)(uint32_t,uint32_t))r)(0x88eb,7);checked();
 }else buffer();
 uint32_t names[33]={is("unrelated_delete") || is("two_contexts") || is("failed_switch")?8u:is("zero_delete")?0u:7u};int count=is("empty_delete")?0:is("delete_bad")?33:is("delete_negative")?-1:1;
 if(is("aliases")){errno=ERANGE;psd_lookup l("glDeleteBuffersARB");void *r=psd_resolved(&l,(void*)remove_buffers,PSD_SOURCE_COMPILED);if(errno!=ERANGE)errno_ok=0;errno=ERANGE;((void(*)(int32_t,const uint32_t*))r)(count,names);checked();}
 else {errno=ERANGE;psd::call<PSD_DELETE_BUFFER>(remove_buffers,count,is("empty_delete")?(const uint32_t*)nullptr:names);checked();}
 errno=ERANGE;psd::call<PSD_PIXEL_STORE>(store,0xd05u,1);checked();
 if(is("overlap"))(void)pca_attach(adapter,adapter);
 if(is("dirty_cache"))rc_context_new(cache,0x999,0);
 if(!is("live") && !is("original_snapshot") && !is("no_attach"))(void)pca_attach(adapter,cache);
 if(is("double_attach"))(void)pca_attach(adapter,cache);
 if(is("two_contexts") || is("failed_switch") || is("livecap")){
  next_handle=0x222;new_context();current(0x222);
  if(is("two_contexts")){buffer();uint32_t second[]={7};errno=ERANGE;psd::call<PSD_DELETE_BUFFER>(remove_second,1,(const uint32_t*)second);checked();current(0x111);}
  if(is("livecap")){next_handle=0x333;new_context();}
 }
 if(is("display"))current(0x111,2);
 if(is("unknown_context"))current(0x999);
 if(is("pending_destroy") || is("pending_release") || is("pending_rebind") || is("double_destroy")){
  dead(0x111);if(is("pending_rebind"))current(0x111);if(is("double_destroy"))dead(0x111);
  if(is("pending_release")){unbind();new_context();current(0x111);}
 }
 if(is("lifetimes")){dead(0x111);unbind();for(unsigned i=0;i<4;++i){next_handle=0x200+i;new_context();current(next_handle);dead(next_handle);unbind();}}
 errno=ERANGE;psd::call<PSD_BIND_FRAMEBUFFER>(bind_frame,0x8d40u,9u);checked();errno=ERANGE;psd::call<PSD_READ_BUFFER>(select_read,0x8ce0u);checked();read_ready=1;
 errno=ERANGE;if(psd::call<PSD_GET_ERROR>(get_error)!=(is("nonzero_error")?0x502u:0u))args_ok=0;checked();
 if(is("original_snapshot")){errno=ERANGE;psd::call<PSD_PIXEL_STORE>(store,0xd05u,1);checked();}
 if(is("fbo_deleted") || is("fbo_mutate") || is("draw_delete")){
  if(is("draw_delete")){errno=ERANGE;psd::call<PSD_BIND_FRAMEBUFFER>(bind_frame,0x8ca9u,99u);checked();}
  uint32_t f[]={is("draw_delete")?99u:9u};errno=ERANGE;psd::call<PSD_DELETE_FRAMEBUFFER>(remove_frames,1,(const uint32_t*)f);checked();
 }
 if(is("source_error")){errno=ERANGE;psd_lookup l("glUnknownState");if(psd_resolved(&l,(void*)bind_buffer,PSD_SOURCE_RUNTIME)!=(void*)bind_buffer || errno!=ERANGE)args_ok=0;}
 if(is("pending_known") || is("pending_unknown")){
  errno=ERANGE;psd_lookup pending(is("pending_known")?"glBindBuffer":"glUnknownState");
  rb_read_state r;std::memset(&r,255,sizeof(r));if(pca_observe(0x1111,0x333,&r,adapter)==0)args_ok=0;
  for(unsigned char b:reinterpret_cast<unsigned char(&)[sizeof(r)]>(r))stale_output|=b;
  rc_state_view v;std::memset(&v,255,sizeof(v));if(pca_snapshot(adapter,&v)==0)args_ok=0;
  for(unsigned char b:reinterpret_cast<unsigned char(&)[sizeof(v)]>(v))stale_output|=b;
  if(psd_resolved(&pending,(void*)bind_buffer,PSD_SOURCE_RUNTIME)!=(void*)bind_buffer || errno!=ERANGE)args_ok=0;
 }
 if(is("forged")){if(pca_observer(nullptr,adapter)==0)args_ok=0;}
 if(is("source_thread") || is("adapter_thread")){pthread_t t;if(pthread_create(&t,nullptr,foreign,nullptr))return 5;pthread_join(t,nullptr);}
 if(is("identity")){rb_read_state v;std::memset(&v,255,sizeof(v));if(pca_observe(0x999,0x333,&v,adapter)==0)args_ok=0;for(unsigned char c:reinterpret_cast<unsigned char(&)[sizeof(v)]>(v))stale_output|=c;}
 if(is("external_finish"))(void)psd_finish();
 if(is("observe")){rb_read_state r={};if(pca_observe(0x1111,0x333,&r,adapter) || r.known!=RB_KNOWN_ALL || r.read_fbo!=9 || r.pack_buffer)args_ok=0;}
 rc_state_view v;std::memset(&v,255,sizeof(v));int snap=pca_snapshot(adapter,&v);if(snap)for(unsigned char c:reinterpret_cast<unsigned char(&)[sizeof(v)]>(v))stale_output|=c;
 cpu_call call={-7,11,5,3,0x1907,0x1401,pixels,0x1111,0x333,128,(uintptr_t)pixels,-1,0};errno=ERANGE;if(!pca_fixture_call(&call))regs_ok=0;checked();
 int finish=pca_finish(adapter,is("downstream")?1:0);if(is("double_finish"))finish=pca_finish(adapter,0);
 if(is("after_finish")){errno=ERANGE;psd::call<PSD_PIXEL_STORE>(store,0xd05u,1);checked();}
 pca_counts s={};if(pca_get_stats(adapter,&s))return 6;rc_counts c={};rc_get_stats(cache,&c);
 std::printf("{\"originals\":%u,\"reads\":%u,\"args_ok\":%u,\"errno_ok\":%u,\"regs_ok\":%u,\"finish\":%d,\"adapter_error\":%u,\"source_error\":%u,\"cache_error\":%u,\"cache_events\":%llu,\"events\":%llu,\"replayed\":%llu,\"applied\":%llu,\"pack_buffer\":%u,\"read_fbo\":%u,\"draw_fbo\":%u,\"context_tag\":%llu,\"created\":%u,\"pending\":%u,\"resets\":%llu,\"source_resolutions\":%llu,\"source_paths\":%llu,\"stale_output\":%u,\"native_admitted\":false}\n",originals,reads,args_ok,errno_ok,regs_ok,finish,s.error,s.source.error,c.error,(unsigned long long)c.events,(unsigned long long)s.events,(unsigned long long)s.replayed,(unsigned long long)s.applied,v.pack_buffer,v.read_fbo,v.draw_fbo,(unsigned long long)v.context_tag,s.created,s.pending,(unsigned long long)s.pbo_resets,(unsigned long long)s.source.resolutions,(unsigned long long)s.source.paths,stale_output);
 std::free(cache);std::free(adapter);return 0;
}
