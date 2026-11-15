#include "panda_cache_adapter.h"
#include <cstring>
#include <pthread.h>
namespace {
const uint64_t MAGIC=0x5043414341434845ull;
enum {E_THREAD=1,E_REENTRY,E_SEQUENCE,E_SOURCE,E_INPUT,E_CACHE,E_CONTEXT,E_DISPLAY,E_DOWNSTREAM};
struct context {uintptr_t handle;uint32_t alive,pbo,pending;};
struct adapter {
 uint64_t magic;pthread_t owner;uint32_t error,busy,finished,cap,boot_count,created,live,pending;
 uint64_t events,replayed,applied,buffer_deletes,pbo_resets,forwarded,resolutions,paths;
 uintptr_t display;void *cache;int current;psd_counts source;context contexts[4];psd_event boot[10000];
};
static_assert(sizeof(adapter)<=3*1024*1024,"bounded caller adapter storage");
struct preserve_errno {int saved;preserve_errno():saved(errno){}~preserve_errno(){errno=saved;}};
uint32_t error(adapter *d){return __atomic_load_n(&d->error,__ATOMIC_ACQUIRE);}
adapter *get(void *p){adapter *d=static_cast<adapter*>(p);return d && d->magic==MAGIC?d:nullptr;}
bool owner(adapter *d){return pthread_equal(d->owner,pthread_self())!=0;}
int fail(adapter *d,uint32_t code){
 uint32_t zero=0;bool first=__atomic_compare_exchange_n(&d->error,&zero,code,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE);
 if(first && owner(d) && d->cache && !d->finished)(void)rc_invalidate(d->cache);
 return -1;
}
bool source_ok(adapter *d){
 psd_counts s={};if(psd_get_stats(&s)){fail(d,E_SOURCE);return false;}d->source=s;
 if(!s.configured || s.closed || s.error || s.events!=d->events || s.forwarded!=d->forwarded || s.resolutions!=d->resolutions || s.paths!=d->paths){fail(d,E_SOURCE);return false;}
 return true;
}
bool begin(adapter *d){
 if(!d)return false;
 if(!owner(d)){fail(d,E_THREAD);return false;}
 if(d->busy){fail(d,E_REENTRY);return false;}
 if(d->finished){fail(d,E_SEQUENCE);return false;}
 if(error(d))return false;
 d->busy=1;if(psd_source_idle(pca_observer,d) || !source_ok(d)){fail(d,E_SOURCE);d->busy=0;return false;}return true;
}
bool cache_ok(adapter *d){rc_counts s={};s.error=1;rc_get_stats(d->cache,&s);return !s.error && !s.finalized;}
void noop_pair(uint32_t,uint32_t){}
void noop_store(uint32_t,int32_t){}
void noop_read(uint32_t){}
void noop_delete(int32_t,const uint32_t*){}
bool u32(uint64_t n){return n<=UINT32_MAX;}
bool s32(uint64_t n){return n<=INT32_MAX || n>=UINT64_MAX-INT32_MAX;}
int32_t signed32(uint64_t n){uint32_t bits=static_cast<uint32_t>(n);int32_t result;std::memcpy(&result,&bits,4);return result;}
bool valid(const psd_event &e){
 const unsigned arity[]={0,2,2,2,1,2,2,4,5,5,5,3,4,2,0};
 bool state=e.kind>=PSD_PIXEL_STORE && e.kind<=PSD_GET_ERROR;
 if(!state && e.kind!=PSD_LOOKUP && e.kind!=PSD_RESOLVER_PATH)return false;
 unsigned expected=state?arity[e.kind]:(e.kind==PSD_LOOKUP?0u:1u);
 if(e.argc!=expected)return false;
 for(unsigned i=expected;i<5;++i)if(e.args[i])return false;
 if(e.kind==PSD_LOOKUP){const char *end=static_cast<const char*>(std::memchr(e.name,0,64));if(!end || end-e.name<3 || e.name[0]!='g' || e.name[1]!='l' || (e.origin!=PSD_SOURCE_COMPILED && e.origin!=PSD_SOURCE_RUNTIME))return false;}
 else if(e.name[0])return false;
 if(e.kind==PSD_RESOLVER_PATH){if(e.origin<PSD_PATH_GLX_CORE || e.origin>PSD_PATH_POSIX || e.args[0]!=e.origin)return false;}
 else if(state && e.origin)return false;
 bool deletion=e.kind==PSD_DELETE_BUFFER || e.kind==PSD_DELETE_FRAMEBUFFER;
 if(deletion){if(!s32(e.args[0]) || signed32(e.args[0])<0 || e.args[0]>32 || e.delete_count!=e.args[0] || (e.delete_count && !e.args[1]))return false;}
 else if(e.delete_count)return false;
 for(unsigned i=e.delete_count;i<32;++i)if(e.names[i])return false;
 switch(e.kind){
 case PSD_PIXEL_STORE:return !e.returned && u32(e.args[0]) && s32(e.args[1]);
 case PSD_BIND_BUFFER:case PSD_BIND_FRAMEBUFFER:return !e.returned && u32(e.args[0]) && u32(e.args[1]);
 case PSD_READ_BUFFER:return !e.returned && u32(e.args[0]);
 case PSD_DELETE_BUFFER:case PSD_DELETE_FRAMEBUFFER:case PSD_DESTROY_CONTEXT:return !e.returned;
 case PSD_CREATE_LEGACY:return s32(e.args[3]);
 case PSD_CREATE_NEW:case PSD_CREATE_SGIX:return s32(e.args[2]) && s32(e.args[4]);
 case PSD_CREATE_ATTRIBS:return s32(e.args[3]);
 case PSD_MAKE_CURRENT:case PSD_MAKE_CONTEXT_CURRENT:return s32(e.returned);
 case PSD_GET_ERROR:return u32(e.returned) && !e.returned;
 default:return true;
 }
}
int find(adapter *d,uintptr_t handle){for(unsigned i=0;i<d->created;++i)if(d->contexts[i].alive && d->contexts[i].handle==handle)return static_cast<int>(i);return -1;}
bool release(adapter *d,int index){
 context &c=d->contexts[index];if(rc_context_destroy(d->cache,c.handle))return false;
 if(c.pending)--d->pending;
 c.alive=0;c.pending=0;--d->live;return true;
}
bool apply(adapter *d,const psd_event &e){
 bool lifecycle=e.kind>=PSD_CREATE_LEGACY && e.kind<=PSD_DESTROY_CONTEXT;
 if(lifecycle){if(!e.args[0] || (d->display && d->display!=e.args[0])){fail(d,E_DISPLAY);return false;}d->display=e.args[0];}
 switch(e.kind){
 case PSD_CREATE_LEGACY:case PSD_CREATE_NEW:case PSD_CREATE_ATTRIBS:case PSD_CREATE_SGIX:
  if(e.returned){
   unsigned share=(e.kind==PSD_CREATE_NEW || e.kind==PSD_CREATE_SGIX)?3:2;
   if(rc_context_new(d->cache,e.returned,e.args[share]))return false;
   if(d->created>=4)return false;
   d->contexts[d->created++]={e.returned,1,0,0};++d->live;
  }break;
 case PSD_MAKE_CURRENT:case PSD_MAKE_CONTEXT_CURRENT:{
  uintptr_t handle=e.args[e.kind==PSD_MAKE_CURRENT?2:3];int index=handle?find(d,handle):-1;bool success=e.returned!=0;
  if(success && handle && (index<0 || d->contexts[index].pending))return false;
  if(rc_context_current(d->cache,handle,success?1:0))return false;
  if(success){int prior=d->current;d->current=index;if(prior>=0 && prior!=index && d->contexts[prior].pending && !release(d,prior))return false;}
  break;}
 case PSD_DESTROY_CONTEXT:{
  int index=find(d,e.args[1]);if(index<0 || d->contexts[index].pending)return false;
  if(index==d->current){d->contexts[index].pending=1;++d->pending;}
  else if(!release(d,index))return false;
  break;}
 case PSD_PIXEL_STORE:rc_pixel_store(d->cache,noop_store,static_cast<uint32_t>(e.args[0]),signed32(e.args[1]));break;
 case PSD_BIND_BUFFER:
  rc_bind_buffer(d->cache,noop_pair,static_cast<uint32_t>(e.args[0]),static_cast<uint32_t>(e.args[1]));
  if(!cache_ok(d))return false;
  if(e.args[0]==0x88eb){if(d->current<0)return false;d->contexts[d->current].pbo=static_cast<uint32_t>(e.args[1]);}break;
 case PSD_BIND_FRAMEBUFFER:rc_bind_framebuffer(d->cache,noop_pair,static_cast<uint32_t>(e.args[0]),static_cast<uint32_t>(e.args[1]));break;
 case PSD_READ_BUFFER:rc_read_buffer(d->cache,noop_read,static_cast<uint32_t>(e.args[0]));break;
 case PSD_DELETE_FRAMEBUFFER:rc_delete_framebuffers(d->cache,noop_delete,static_cast<int32_t>(e.delete_count),e.names);break;
 case PSD_DELETE_BUFFER:{
  if(d->current<0)return false;
  context &c=d->contexts[d->current];++d->buffer_deletes;
  for(unsigned i=0;i<e.delete_count;++i)if(c.pbo && e.names[i]==c.pbo){rc_bind_buffer(d->cache,noop_pair,0x88eb,0);if(!cache_ok(d))return false;c.pbo=0;++d->pbo_resets;break;}
  break;}
 default:break; // validated lookup/path/GetError(0): metadata only
 }
 if(!cache_ok(d))return false;
 ++d->applied;return true;
}
bool overlap(uintptr_t a,size_t as,uintptr_t b,size_t bs){if(a>UINTPTR_MAX-as || b>UINTPTR_MAX-bs)return true;return a<b+bs && b<a+as;}
}
extern "C" size_t pca_context_size(){return sizeof(adapter);}
extern "C" int pca_install(void *storage,size_t bytes,const char *const *safe,size_t count,uint32_t cap){
 preserve_errno keep;
 if(!storage || reinterpret_cast<uintptr_t>(storage)%alignof(adapter) || bytes<sizeof(adapter) || !cap || cap>10000)return -1;
 psd_counts source={};if(psd_get_stats(&source) || source.configured)return -1;
 adapter *d=static_cast<adapter*>(storage);std::memset(d,0,sizeof(*d));d->magic=MAGIC;d->owner=pthread_self();d->cap=cap;d->current=-1;
 if(psd_configure(pca_observer,d,safe,count,cap)){fail(d,E_SOURCE);return -1;}return 0;
}
extern "C" int pca_observer(const psd_event *event,void *user){
 preserve_errno keep;adapter *d=get(user);if(!d)return -1;
 if(!owner(d))return fail(d,E_THREAD);
 if(d->busy)return fail(d,E_REENTRY);
 if(d->finished || error(d))return fail(d,E_SEQUENCE);
 d->busy=1;
 if(!event || !valid(*event) || event->sequence!=d->events+1 || d->events>=d->cap){d->busy=0;return fail(d,E_INPUT);}
 ++d->events;if(event->kind<=PSD_GET_ERROR)++d->forwarded;else if(event->kind==PSD_LOOKUP)++d->resolutions;else ++d->paths;
 if(!source_ok(d)){d->busy=0;return -1;}
 if(d->cache){if(!apply(d,*event)){d->busy=0;return fail(d,E_CACHE);}}
 else d->boot[d->boot_count++]=*event;
 d->busy=0;return 0;
}
extern "C" int pca_attach(void *storage,void *cache){
 preserve_errno keep;adapter *d=get(storage);if(!begin(d))return -1;
 if(d->cache || !cache || overlap(reinterpret_cast<uintptr_t>(d),sizeof(*d),reinterpret_cast<uintptr_t>(cache),rc_context_size())){d->busy=0;return fail(d,E_SEQUENCE);}
 rc_counts c={};c.error=1;rc_get_stats(cache,&c);
 if(c.error || c.events || c.contexts_created || c.live_contexts || c.finalized){d->busy=0;return fail(d,E_CACHE);}
 d->cache=cache;
 for(unsigned i=0;i<d->boot_count;++i){if(!apply(d,d->boot[i])){d->busy=0;return fail(d,E_CACHE);}++d->replayed;}
 d->busy=0;return 0;
}
extern "C" int pca_snapshot(void *storage,rc_state_view *out){
 preserve_errno keep;if(out)std::memset(out,0,sizeof(*out));adapter *d=get(storage);if(!begin(d))return -1;
 int result=(!d->cache || !out)?-1:rc_snapshot(d->cache,out);
 if(result){if(out)std::memset(out,0,sizeof(*out));fail(d,E_CACHE);}d->busy=0;return result;
}
extern "C" int pca_observe(uintptr_t texture,uintptr_t gsg,rb_read_state *out,void *user){
 preserve_errno keep;if(out)std::memset(out,0,sizeof(*out));adapter *d=get(user);if(!begin(d))return -1;
 int result=(!d->cache || !out)?-1:rc_observe(texture,gsg,out,d->cache);
 if(result){if(out)std::memset(out,0,sizeof(*out));fail(d,E_CACHE);}d->busy=0;return result;
}
extern "C" int pca_finish(void *storage,int downstream){
 preserve_errno keep;adapter *d=get(storage);if(!d)return -1;
 if(!owner(d))return fail(d,E_THREAD);
 if(d->busy)return fail(d,E_REENTRY);
 if(d->finished)return fail(d,E_SEQUENCE);
 d->busy=1;(void)source_ok(d);int result=psd_finish();
 if(result)fail(d,E_SOURCE);
 if(downstream)fail(d,E_DOWNSTREAM);
 if(!d->cache)fail(d,E_SEQUENCE);
 int cache_result=d->cache?rc_finalize(d->cache,(result || downstream || error(d))?-1:0):-1;
 if(cache_result)fail(d,E_CACHE);
 d->finished=1;d->busy=0;(void)psd_get_stats(&d->source);return error(d)?-1:0;
}
extern "C" int pca_get_stats(void *storage,pca_counts *out){
 preserve_errno keep;adapter *d=get(storage);if(!d || !out)return -1;
 if(!owner(d))return fail(d,E_THREAD);
 if(d->busy)return fail(d,E_REENTRY);
 if(!d->finished)(void)source_ok(d);else (void)psd_get_stats(&d->source);
 *out={error(d),d->cache?1u:0u,d->finished,d->boot_count,d->created,d->live,d->pending,d->events,d->replayed,d->applied,d->buffer_deletes,d->pbo_resets,d->source};return 0;
}
