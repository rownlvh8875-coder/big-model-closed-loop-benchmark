#include "panda_readback_bridge.h"
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <string.h>

typedef struct {
  int32_t x,y,w,h;uint32_t format,type;
  void *pixels;
  uintptr_t return_pc,texture,gsg,capacity,image,entry_sp;
} pb_frame;
_Static_assert(sizeof(void *)==8 && sizeof(pb_frame)==80,"Linux amd64 frame ABI");
_Static_assert(offsetof(pb_frame,pixels)==24 && offsetof(pb_frame,entry_sp)==72,"assembly offsets");
typedef struct {
  pb_binding binding;
  rb_config config;
  pthread_t owner;
  void *core;
  _Atomic uint32_t error,active;
  _Atomic uint64_t entries;
  uint64_t window_start;
  uint32_t busy;
} pb_context;
static _Atomic(pb_context *) installed;
enum {PB_CALLSITE=1,PB_IDENTITY,PB_EXTENT,PB_VIEW,PB_THREAD,PB_REENTRANT,PB_STATE,PB_LIMIT,PB_SEQUENCE};
static int fail(pb_context *c,uint32_t error){
  uint32_t expected=0;(void)atomic_compare_exchange_strong(&c->error,&expected,error);return -1;
}
static int owner(pb_context *c){return pthread_equal(c->owner,pthread_self())?1:(fail(c,PB_THREAD),0);}
static void forward(pb_context *c,const pb_frame *f,const rb_read_state *state,int incoming_errno){
  errno=incoming_errno;
  rb_read(c->core,c->binding.original,f->x,f->y,f->w,f->h,f->format,f->type,f->pixels,state);
}
static size_t core_offset(void){
  size_t a=_Alignof(max_align_t);return (sizeof(pb_context)+a-1)/a*a;
}
size_t pb_context_size(void){return core_offset()+rb_context_size();}
int pb_install(void *storage,size_t bytes,const rb_config *config,unsigned char *scratch,size_t cap,
               rb_emit_fn emit,void *user,const pb_binding *binding){
  if(atomic_load(&installed) || !storage || (uintptr_t)storage%_Alignof(max_align_t) || bytes<pb_context_size() ||
     !config || !binding || !binding->original || !binding->expected_return || !binding->gsg ||
     !binding->texture[0] || !binding->texture[1] || binding->texture[0]==binding->texture[1] ||
     (config->enabled && !binding->observe))return -1;
  pb_context *c=storage;memset(c,0,sizeof(*c));c->config=*config;c->binding=*binding;
  c->owner=pthread_self();c->core=(unsigned char *)storage+core_offset();
  atomic_init(&c->error,0);atomic_init(&c->active,0);atomic_init(&c->entries,0);
  if(rb_init(c->core,bytes-core_offset(),scratch,cap,config,emit,user))return -1;
  pb_context *expected=NULL;
  if(!atomic_compare_exchange_strong(&installed,&expected,c))return -1;
  return 0;
}
int pb_begin(void *ctx,uint32_t call,uint32_t camera){
  pb_context *c=ctx;if(!owner(c))return -1;
  if(c->busy)return fail(c,PB_REENTRANT);
  if(atomic_load(&c->error))return -1;
  if(atomic_load(&c->active))return fail(c,PB_SEQUENCE);
  if(rb_begin(c->core,call,camera))return -1;
  c->window_start=atomic_load(&c->entries);atomic_store(&c->active,1);return 0;
}
/* Hidden C endpoint for the assembly frame; not a public arbitrary-frame API. */
__attribute__((visibility("hidden"))) void pb_dispatch(const pb_frame *f){
  int incoming_errno=errno;
  pb_context *c=atomic_load(&installed);
  if(!c)__builtin_trap(); /* Entry-before-install violates the documented ABI. */
  if(!atomic_load(&c->active)){
    forward(c,f,NULL,incoming_errno);return;
  }
  uint64_t ordinal=atomic_fetch_add(&c->entries,1)+1;
  if(!owner(c)){
    forward(c,f,NULL,incoming_errno);return;
  }
  if(c->busy){
    (void)fail(c,PB_REENTRANT);
    forward(c,f,NULL,incoming_errno);return;
  }
  c->busy=1;rb_read_state state={0};unsigned producer=0;
  if(ordinal-c->window_start>c->config.reads_per_window)(void)fail(c,PB_LIMIT);
  if(!atomic_load(&c->error)){
    if(f->return_pc!=c->binding.expected_return)(void)fail(c,PB_CALLSITE);
    else if(f->gsg!=c->binding.gsg)(void)fail(c,PB_IDENTITY);
    else{
      if(f->texture==c->binding.texture[0])producer=1;
      else if(f->texture==c->binding.texture[1])producer=2;
      else (void)fail(c,PB_IDENTITY);
    }
  }
  /* Only an identity-bound, exact caller ABI permits reading these stack slots. */
  if(!atomic_load(&c->error)){
    int32_t z,view;
    if(f->entry_sp>UINTPTR_MAX-52)(void)fail(c,PB_VIEW);
    else{
      memcpy(&z,(const void *)(f->entry_sp+28),sizeof(z));
      memcpy(&view,(const void *)(f->entry_sp+48),sizeof(view));
      if(z!=-1 || view!=0)(void)fail(c,PB_VIEW);
    }
  }
  if(c->config.enabled && !atomic_load(&c->error)){
    if(f->image!=(uintptr_t)f->pixels || !f->capacity || f->capacity>8u*1024u*1024u)(void)fail(c,PB_EXTENT);
    else if(c->binding.observe(f->texture,f->gsg,&state,c->binding.observe_user)!=0)(void)fail(c,PB_STATE);
    if(atomic_load(&c->error))state.known=0;
    state.capacity=f->capacity;state.producer_camera=producer;state.label_basis=1;
  }
  forward(c,f,&state,incoming_errno);
  int original_errno=errno;c->busy=0;errno=original_errno;
}
int pb_end(void *ctx){
  pb_context *c=ctx;if(!owner(c))return -1;
  if(c->busy)return fail(c,PB_REENTRANT);
  if(!atomic_load(&c->active))return fail(c,PB_SEQUENCE);
  atomic_store(&c->active,0);int rc=rb_end(c->core);
  return rc || atomic_load(&c->error)?-1:0;
}
int pb_finish(void *ctx){
  pb_context *c=ctx;if(!owner(c))return -1;
  if(c->busy)return fail(c,PB_REENTRANT);
  atomic_store(&c->active,0);int rc=rb_finish(c->core);
  return rc || atomic_load(&c->error)?-1:0;
}
void pb_get_stats(void *ctx,pb_stats *out){
  pb_context *c=ctx;if(!owner(c) || !out)return;
  rb_get_stats(c->core,&out->core);out->bridge_error=atomic_load(&c->error);
}
