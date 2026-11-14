#include "readback_call_delivery.h"
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <string.h>
_Static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"Linux amd64 GLX ABI");
enum {EV_NEW=1,EV_CURRENT,EV_DESTROY,EV_STORE,EV_BUFFER,EV_FRAME,EV_READ,EV_DELETE};
enum {RD_THREAD=1,RD_REENTRY,RD_SEQUENCE,RD_LIMIT,RD_STATE,RD_CACHE,RD_PROC,RD_GL_ERROR,RD_DISPLAY};
typedef struct {uint32_t kind,a,b;int32_t value;uintptr_t handle,share;uint32_t names[32];} rd_event;
typedef struct {
  rd_dispatch original;pthread_t owner;_Atomic uint32_t error,closed;
  _Atomic uint64_t forwarded,resolvers;uint32_t busy,closing,bound,cap,boot_count,safe_count;
  uint64_t events,replayed,nonzero_errors;rd_display *display;void *cache,*bridge;
  char safe[256][64];rd_event bootstrap[10000];
} rd_state;
static _Atomic(rd_state *) installed;
__attribute__((visibility("hidden"))) _Atomic(rb_read_fn) rd_read_target;
static rd_state *state(void){rd_state *d=atomic_load(&installed);if(!d)__builtin_trap();return d;}
static int is_owner(rd_state *d){return pthread_equal(d->owner,pthread_self());}
static int fail(rd_state *d,uint32_t error){
  uint32_t expected=0;(void)atomic_compare_exchange_strong(&d->error,&expected,error);
  if(is_owner(d) && d->cache && !atomic_load(&d->closed))(void)rc_invalidate(d->cache);
  return -1;
}
static int begin(rd_state *d){
  atomic_fetch_add(&d->forwarded,1);
  if(atomic_load(&d->closed))return 0;
  if(!is_owner(d)){(void)fail(d,RD_THREAD);return 0;}
  if(d->busy || d->closing){(void)fail(d,RD_REENTRY);return 0;}
  if(atomic_load(&d->error))return 0;
  d->busy=1;return 1;
}
static int returned(rd_state *d,int armed){if(!armed)return 0;d->busy=0;return !atomic_load(&d->error);}
static void noop_pair(uint32_t a,uint32_t b){(void)a;(void)b;}
static void noop_store(uint32_t a,int32_t b){(void)a;(void)b;}
static void noop_read(uint32_t a){(void)a;}
static void noop_delete(int32_t n,const uint32_t *p){(void)n;(void)p;}
static int apply(rd_state *d,const rd_event *e){
  switch(e->kind){
    case EV_NEW:if(e->handle && rc_context_new(d->cache,e->handle,e->share))return -1;break;
    case EV_CURRENT:if(rc_context_current(d->cache,e->handle,e->value!=0))return -1;break;
    case EV_DESTROY:if(rc_context_destroy(d->cache,e->handle))return -1;break;
    case EV_STORE:rc_pixel_store(d->cache,noop_store,e->a,e->value);break;
    case EV_BUFFER:rc_bind_buffer(d->cache,noop_pair,e->a,e->b);break;
    case EV_FRAME:rc_bind_framebuffer(d->cache,noop_pair,e->a,e->b);break;
    case EV_READ:rc_read_buffer(d->cache,noop_read,e->a);break;
    case EV_DELETE:rc_delete_framebuffers(d->cache,noop_delete,e->value,e->names);break;
    default:return -1;
  }
  rc_counts c={.error=1};rc_get_stats(d->cache,&c);return c.error?-1:0;
}
static void deliver(rd_state *d,const rd_event *e){
  if(d->events>=d->cap){(void)fail(d,RD_LIMIT);return;}
  d->events++;
  if(d->cache){if(apply(d,e))(void)fail(d,RD_CACHE);}
  else d->bootstrap[d->boot_count++]=*e;
}
static int copy_name(const unsigned char *input,char out[64]){
  if(!input)return 0;
  for(unsigned i=0;i<64;i++){out[i]=(char)input[i];if(!out[i])return i>1 && out[0]=='g' && out[1]=='l';}
  return 0;
}
static int unsafe_name(const char *s){
  const char *prefix[]={"glPixelStore","glBindBuffer","glDeleteBuffers","glBindFramebuffer","glDeleteFramebuffers","glReadBuffer","glPushClientAttrib","glPopClientAttrib","glXCreate","glXMake","glXDestroy"};
  for(unsigned i=0;i<sizeof(prefix)/sizeof(prefix[0]);i++)if(!strncmp(s,prefix[i],strlen(prefix[i])))return 1;
  return 0;
}
size_t rd_context_size(void){return sizeof(rd_state);}
int rd_install(void *storage,size_t bytes,const rd_dispatch *original,const char *const *safe,size_t count,uint32_t cap){
  if(atomic_load(&installed) || !storage || (uintptr_t)storage%_Alignof(rd_state) || bytes<sizeof(rd_state) || !original || count>256 || (count && !safe) || !cap || cap>10000)return -1;
  if(!original->pixel_store || !original->bind_buffer || !original->bind_framebuffer || !original->read_buffer || !original->delete_framebuffers || !original->read_pixels ||
     !original->create_new || !original->make_current || !original->destroy_context || !original->get_error || !original->get_proc)return -1;
  rd_state *d=storage;memset(d,0,sizeof(*d));d->original=*original;d->owner=pthread_self();d->cap=cap;
  atomic_init(&d->error,0);atomic_init(&d->closed,0);atomic_init(&d->forwarded,0);atomic_init(&d->resolvers,0);
  for(size_t i=0;i<count;i++){
    if(!copy_name((const unsigned char *)safe[i],d->safe[i]) || unsafe_name(d->safe[i]))return -1;
    for(size_t j=0;j<i;j++)if(!strcmp(d->safe[j],d->safe[i]))return -1;
  }
  d->safe_count=(uint32_t)count;rd_state *expected=NULL;
  atomic_store(&rd_read_target,original->read_pixels);
  if(!atomic_compare_exchange_strong(&installed,&expected,d))return -1;
  return 0;
}
int rd_attach(void *cache){
  rd_state *d=state();if(!is_owner(d))return fail(d,RD_THREAD);
  if(d->busy || d->cache || atomic_load(&d->closed) || atomic_load(&d->error) || !cache)return fail(d,RD_SEQUENCE);
  rc_counts c={.error=1};rc_get_stats(cache,&c);if(c.error || c.events || c.contexts_created || c.finalized)return fail(d,RD_CACHE);
  d->cache=cache;d->busy=1;
  for(uint32_t i=0;i<d->boot_count;i++){if(apply(d,&d->bootstrap[i])){d->busy=0;return fail(d,RD_CACHE);}d->replayed++;}
  d->busy=0;return 0;
}
int rd_bind_bridge(void *storage,size_t bytes,const rb_config *config,unsigned char *scratch,size_t cap,rb_emit_fn emit,void *user,const pb_binding *binding){
  rd_state *d=state();if(!is_owner(d))return fail(d,RD_THREAD);
  if(d->busy || d->bound || !d->cache || atomic_load(&d->closed) || atomic_load(&d->error) || !binding || binding->original!=d->original.read_pixels || binding->observe!=rd_observe || binding->observe_user!=d)return fail(d,RD_SEQUENCE);
  if(pb_install(storage,bytes,config,scratch,cap,emit,user,binding))return fail(d,RD_STATE);
  d->bridge=storage;d->bound=1;atomic_store(&rd_read_target,pb_entry);return 0;
}
int rd_observe(uintptr_t texture,uintptr_t gsg,rb_read_state *out,void *user){
  rd_state *d=state();if(!is_owner(d))return fail(d,RD_THREAD);
  if(user!=d || d->busy || d->closing || !d->bound || !d->cache || atomic_load(&d->closed) || atomic_load(&d->error))return fail(d,RD_STATE);
  if(rc_observe(texture,gsg,out,d->cache))return fail(d,RD_CACHE);
  return 0;
}
int rd_invalidate(void){rd_state *d=state();return fail(d,RD_STATE);}

#define PAIR_WRAPPER(NAME,FIELD,KIND) \
void NAME(uint32_t a,uint32_t b){int incoming=errno;rd_state *d=state();int armed=begin(d);errno=incoming;d->original.FIELD(a,b);int result=errno; \
if(returned(d,armed)){rd_event e={0};e.kind=KIND;e.a=a;e.b=b;deliver(d,&e);}errno=result;}
PAIR_WRAPPER(rd_bind_buffer,bind_buffer,EV_BUFFER)
PAIR_WRAPPER(rd_bind_buffer_arb,bind_buffer_arb,EV_BUFFER)
PAIR_WRAPPER(rd_bind_framebuffer,bind_framebuffer,EV_FRAME)
PAIR_WRAPPER(rd_bind_framebuffer_ext,bind_framebuffer_ext,EV_FRAME)
void rd_pixel_store(uint32_t a,int32_t b){
  int incoming=errno;rd_state *d=state();int armed=begin(d);errno=incoming;d->original.pixel_store(a,b);int result=errno;
  if(returned(d,armed)){rd_event e={0};e.kind=EV_STORE;e.a=a;e.value=b;deliver(d,&e);}errno=result;
}
void rd_read_buffer(uint32_t a){
  int incoming=errno;rd_state *d=state();int armed=begin(d);errno=incoming;d->original.read_buffer(a);int result=errno;
  if(returned(d,armed)){rd_event e={0};e.kind=EV_READ;e.a=a;deliver(d,&e);}errno=result;
}
static void delete_frames(int32_t n,const uint32_t *names,int ext){
  int incoming=errno;rd_state *d=state();int armed=begin(d);rd_event e={0};int valid=n>=0 && n<=32 && (n==0 || names);
  if(armed && valid && n)memcpy(e.names,names,(size_t)n*sizeof(*names));
  errno=incoming;(ext?d->original.delete_framebuffers_ext:d->original.delete_framebuffers)(n,names);int result=errno;
  if(returned(d,armed)){if(!valid)(void)fail(d,RD_STATE);else{e.kind=EV_DELETE;e.value=n;deliver(d,&e);}}errno=result;
}
void rd_delete_framebuffers(int32_t n,const uint32_t *p){delete_frames(n,p,0);}
void rd_delete_framebuffers_ext(int32_t n,const uint32_t *p){delete_frames(n,p,1);}
static int display(rd_state *d,rd_display *value){
  if(!value || (d->display && d->display!=value))return fail(d,RD_DISPLAY);
  d->display=value;return 0;
}
rd_context rd_create_new(rd_display *p,rd_fbconfig cfg,int type,rd_context share,int direct){
  int incoming=errno;rd_state *d=state();int armed=begin(d);errno=incoming;rd_context ctx=d->original.create_new(p,cfg,type,share,direct);int result=errno;
  if(returned(d,armed) && display(d,p)==0){rd_event e={0};e.kind=EV_NEW;e.handle=(uintptr_t)ctx;e.share=(uintptr_t)share;deliver(d,&e);}errno=result;return ctx;
}
rd_context rd_create_attribs(rd_display *p,rd_fbconfig cfg,rd_context share,int direct,const int *attrs){
  int incoming=errno;rd_state *d=state();int armed=begin(d);errno=incoming;rd_context ctx=d->original.create_attribs(p,cfg,share,direct,attrs);int result=errno;
  if(returned(d,armed) && display(d,p)==0){rd_event e={0};e.kind=EV_NEW;e.handle=(uintptr_t)ctx;e.share=(uintptr_t)share;deliver(d,&e);}errno=result;return ctx;
}
static void current_event(rd_state *d,rd_display *p,rd_context ctx,int success){
  if(display(d,p)==0){rd_event e={0};e.kind=EV_CURRENT;e.handle=(uintptr_t)ctx;e.value=success;deliver(d,&e);}
}
int rd_make_current(rd_display *p,unsigned long draw,rd_context ctx){
  int incoming=errno;rd_state *d=state();int armed=begin(d);errno=incoming;int ok=d->original.make_current(p,draw,ctx);int result=errno;
  if(returned(d,armed)){current_event(d,p,ctx,ok);}errno=result;return ok;
}
int rd_make_context_current(rd_display *p,unsigned long draw,unsigned long read,rd_context ctx){
  int incoming=errno;rd_state *d=state();int armed=begin(d);errno=incoming;int ok=d->original.make_context_current(p,draw,read,ctx);int result=errno;
  if(returned(d,armed)){current_event(d,p,ctx,ok);}errno=result;return ok;
}
void rd_destroy_context(rd_display *p,rd_context ctx){
  int incoming=errno;rd_state *d=state();int armed=begin(d);errno=incoming;d->original.destroy_context(p,ctx);int result=errno;
  if(returned(d,armed) && display(d,p)==0){rd_event e={0};e.kind=EV_DESTROY;e.handle=(uintptr_t)ctx;deliver(d,&e);}errno=result;
}
uint32_t rd_get_error(void){
  int incoming=errno;rd_state *d=state();int armed=begin(d);errno=incoming;uint32_t value=d->original.get_error();int result=errno;
  if(returned(d,armed) && value){d->nonzero_errors++;(void)fail(d,RD_GL_ERROR);}errno=result;return value;
}
static rd_proc route(rd_state *d,const char *name,rd_proc value){
  struct entry {const char *name;rd_proc original,wrapper;} entries[]={
#define ROUTE(N,F,W) {N,(rd_proc)d->original.F,(rd_proc)W}
    ROUTE("glPixelStorei",pixel_store,rd_pixel_store),ROUTE("glBindBuffer",bind_buffer,rd_bind_buffer),ROUTE("glBindBufferARB",bind_buffer_arb,rd_bind_buffer_arb),
    ROUTE("glBindFramebuffer",bind_framebuffer,rd_bind_framebuffer),ROUTE("glBindFramebufferEXT",bind_framebuffer_ext,rd_bind_framebuffer_ext),
    ROUTE("glReadBuffer",read_buffer,rd_read_buffer),ROUTE("glDeleteFramebuffers",delete_framebuffers,rd_delete_framebuffers),ROUTE("glDeleteFramebuffersEXT",delete_framebuffers_ext,rd_delete_framebuffers_ext),
    ROUTE("glReadPixels",read_pixels,rd_read_pixels),ROUTE("glXCreateNewContext",create_new,rd_create_new),ROUTE("glXCreateContextAttribsARB",create_attribs,rd_create_attribs),
    ROUTE("glXMakeCurrent",make_current,rd_make_current),ROUTE("glXMakeContextCurrent",make_context_current,rd_make_context_current),ROUTE("glXDestroyContext",destroy_context,rd_destroy_context),
    ROUTE("glGetError",get_error,rd_get_error),ROUTE("glXGetProcAddress",get_proc,rd_get_proc),ROUTE("glXGetProcAddressARB",get_proc_arb,rd_get_proc_arb)
  };
  for(unsigned i=0;i<sizeof(entries)/sizeof(entries[0]);i++)if(!strcmp(name,entries[i].name)){
    if(value!=entries[i].original){(void)fail(d,RD_PROC);return value;}
    return value?entries[i].wrapper:NULL;
  }
  for(uint32_t i=0;i<d->safe_count;i++)if(!strcmp(name,d->safe[i]))return value;
  if(!atomic_load(&d->closed))(void)fail(d,RD_PROC);
  return value;
}
static rd_proc get_proc(const unsigned char *name,int arb){
  int incoming=errno;rd_state *d=state();int armed=begin(d);char saved[64];int valid=copy_name(name,saved);
  atomic_fetch_add(&d->resolvers,1);errno=incoming;rd_proc value=(arb?d->original.get_proc_arb:d->original.get_proc)(name);int result=errno;
  (void)returned(d,armed);
  if(valid)value=route(d,saved,value);else if(!atomic_load(&d->closed))(void)fail(d,RD_PROC);
  errno=result;return value;
}
rd_proc rd_get_proc(const unsigned char *name){return get_proc(name,0);}
rd_proc rd_get_proc_arb(const unsigned char *name){return get_proc(name,1);}
int rd_finish(void){
  rd_state *d=state();if(!is_owner(d))return fail(d,RD_THREAD);
  if(d->busy || d->closing || atomic_load(&d->closed))return fail(d,RD_SEQUENCE);
  d->closing=1;int result=d->bound?pb_finish(d->bridge):-1;
  if(d->cache)result=rc_finalize(d->cache,result);
  atomic_store(&rd_read_target,d->original.read_pixels);d->closing=0;atomic_store(&d->closed,1);
  return result || atomic_load(&d->error)?-1:0;
}
void rd_get_stats(rd_counts *out){
  rd_state *d=state();if(!is_owner(d) || !out)return;
  *out=(rd_counts){atomic_load(&d->error),d->cache!=NULL,d->bound,atomic_load(&d->closed),atomic_load(&d->forwarded),d->events,d->replayed,atomic_load(&d->resolvers),d->nonzero_errors};
}
