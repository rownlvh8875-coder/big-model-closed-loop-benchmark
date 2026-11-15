#include "readback_command_state.h"
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <string.h>

typedef struct {uint32_t name,selector,used,known;} rc_fbo;
typedef struct {
  uintptr_t handle;uint64_t tag;uint32_t alive;
  uint32_t alignment,row_length,skip_pixels,skip_rows,pbo,read,draw;
  rc_fbo fbos[32];
} rc_context;
typedef struct {
  rc_config config;pthread_t owner;_Atomic uint32_t error;
  uint32_t busy,finished,created,live;uint64_t events;int current;
  rc_context contexts[4];
} rc_cache;
enum {RC_THREAD=1,RC_REENTRY,RC_LIMIT,RC_CONTEXT,RC_STATE,RC_IDENTITY,RC_CLOSED};
static int fail(rc_cache *c,uint32_t error){uint32_t expected=0;(void)atomic_compare_exchange_strong(&c->error,&expected,error);return -1;}
static int owner(rc_cache *c){return pthread_equal(c->owner,pthread_self())?1:(fail(c,RC_THREAD),0);}
static int prepare(rc_cache *c){
  if(!owner(c))return 0;
  if(c->busy){(void)fail(c,RC_REENTRY);return 0;}
  if(c->finished || atomic_load(&c->error))return 0;
  if(c->events>=c->config.max_events){(void)fail(c,RC_LIMIT);return 0;}
  c->busy=1;return 1;
}
static int returned(rc_cache *c,int armed){
  if(!armed)return 0;
  c->busy=0;
  if(atomic_load(&c->error))return 0;
  c->events++;return 1;
}
static int event(rc_cache *c){int armed=prepare(c);return returned(c,armed);}
static rc_context *current(rc_cache *c){
  if(c->current<0 || !c->contexts[c->current].alive){(void)fail(c,RC_CONTEXT);return NULL;}
  return &c->contexts[c->current];
}
static int find(rc_cache *c,uintptr_t handle){
  for(unsigned i=0;i<c->created;i++)if(c->contexts[i].alive && c->contexts[i].handle==handle)return (int)i;
  return -1;
}
static rc_fbo *fbo(rc_cache *c,rc_context *s,uint32_t name,int create){
  for(unsigned i=0;i<32;i++)if(s->fbos[i].used && s->fbos[i].name==name)return &s->fbos[i];
  if(create)for(unsigned i=0;i<32;i++)if(!s->fbos[i].used){s->fbos[i]=(rc_fbo){name,0,1,0};return &s->fbos[i];}
  (void)fail(c,create?RC_LIMIT:RC_STATE);return NULL;
}
size_t rc_context_size(void){return sizeof(rc_cache);}
int rc_init(void *storage,size_t bytes,const rc_config *config){
  if(!storage || (uintptr_t)storage%_Alignof(rc_cache) || bytes<sizeof(rc_cache) || !config ||
     !config->gsg || !config->texture[0] || !config->texture[1] || config->texture[0]==config->texture[1] ||
     !config->max_events || config->max_events>10000)return -1;
  rc_cache *c=storage;memset(c,0,sizeof(*c));c->config=*config;c->owner=pthread_self();c->current=-1;atomic_init(&c->error,0);return 0;
}
int rc_context_new(void *cache,uintptr_t handle,uintptr_t share){
  rc_cache *c=cache;if(!event(c))return -1;
  if(!handle || share || find(c,handle)>=0)return fail(c,RC_CONTEXT);
  if(c->created==4 || c->live==2)return fail(c,RC_LIMIT);
  unsigned i=c->created++;rc_context *s=&c->contexts[i];memset(s,0,sizeof(*s));
  s->handle=handle;s->tag=i+1;s->alive=1;s->alignment=4;s->fbos[0]=(rc_fbo){0,0,1,0};c->live++;return 0;
}
int rc_context_current(void *cache,uintptr_t handle,int success){
  rc_cache *c=cache;if(!event(c))return -1;
  if(success!=0 && success!=1)return fail(c,RC_CONTEXT);
  if(!success)return 0;
  if(!handle){c->current=-1;return 0;}
  int i=find(c,handle);if(i<0)return fail(c,RC_CONTEXT);c->current=i;return 0;
}
int rc_context_destroy(void *cache,uintptr_t handle){
  rc_cache *c=cache;if(!event(c))return -1;int i=find(c,handle);
  if(i<0)return fail(c,RC_CONTEXT);
  c->contexts[i].alive=0;c->live--;if(c->current==i)c->current=-1;return 0;
}
int rc_invalidate(void *cache){rc_cache *c=cache;if(!event(c))return -1;return fail(c,RC_STATE);}
void rc_pixel_store(void *cache,void (*original)(uint32_t,int32_t),uint32_t name,int32_t value){
  int incoming=errno;rc_cache *c=cache;int armed=prepare(c);errno=incoming;original(name,value);int result_errno=errno;
  if(returned(c,armed)){
    rc_context *s=current(c);
    if(s){
      if(name>=0xcf0 && name<=0xcf5){} /* UNPACK state has no read-layout effect. */
      else if(name==0xd05){if(value!=1 && value!=2 && value!=4 && value!=8)(void)fail(c,RC_STATE);else s->alignment=(uint32_t)value;}
      else if(name>=0xd02 && name<=0xd04){
        if(value<0 || value>4096)(void)fail(c,RC_STATE);
        else if(name==0xd02)s->row_length=(uint32_t)value;
        else if(name==0xd03)s->skip_rows=(uint32_t)value;
        else s->skip_pixels=(uint32_t)value;
      }else if((name==0xd00 || name==0xd01) && value==0){}
      else (void)fail(c,RC_STATE);
    }
  }
  errno=result_errno;
}
void rc_bind_buffer(void *cache,void (*original)(uint32_t,uint32_t),uint32_t target,uint32_t name){
  int incoming=errno;rc_cache *c=cache;int armed=prepare(c);errno=incoming;original(target,name);int result_errno=errno;
  if(returned(c,armed)){
    rc_context *s=current(c);
    if(s){
      if(target==0x88eb)s->pbo=name;
      else if(target!=0x88ec && target!=0x8892 && target!=0x8893 && target!=0x8a11 && target!=0x90d2 &&
              target!=0x8f36 && target!=0x8f37 && target!=0x8c2a && target!=0x8f3f && target!=0x90ee &&
              target!=0x8c8e && target!=0x92c0 && target!=0x9192)(void)fail(c,RC_STATE);
    }
  }
  errno=result_errno;
}
void rc_bind_framebuffer(void *cache,void (*original)(uint32_t,uint32_t),uint32_t target,uint32_t name){
  int incoming=errno;rc_cache *c=cache;int armed=prepare(c);errno=incoming;original(target,name);int result_errno=errno;
  if(returned(c,armed)){
    rc_context *s=current(c);
    if(s){
      if(target!=0x8d40 && target!=0x8ca8 && target!=0x8ca9)(void)fail(c,RC_STATE);
      else if(fbo(c,s,name,1)){
        if(target!=0x8ca9)s->read=name;
        if(target!=0x8ca8)s->draw=name;
      }
    }
  }
  errno=result_errno;
}
void rc_read_buffer(void *cache,void (*original)(uint32_t),uint32_t selector){
  int incoming=errno;rc_cache *c=cache;int armed=prepare(c);errno=incoming;original(selector);int result_errno=errno;
  if(returned(c,armed)){
    rc_context *s=current(c);
    if(s){
      int valid=selector==0 || (s->read?selector>=0x8ce0 && selector<=0x8cff:selector>=0x400 && selector<=0x407);
      if(!valid)(void)fail(c,RC_STATE);
      else{rc_fbo *f=fbo(c,s,s->read,0);if(f){f->selector=selector;f->known=1;}}
    }
  }
  errno=result_errno;
}
void rc_delete_framebuffers(void *cache,void (*original)(int32_t,const uint32_t *),int32_t n,const uint32_t *names){
  int incoming=errno;rc_cache *c=cache;int armed=prepare(c);uint32_t saved[32];
  int valid=n>=0 && n<=32 && (n==0 || names!=NULL);
  if(armed && valid && n>0)memcpy(saved,names,(size_t)n*sizeof(*names));
  errno=incoming;original(n,names);int result_errno=errno;
  if(returned(c,armed)){
    rc_context *s=current(c);
    if(!valid)(void)fail(c,RC_STATE);
    else if(s)for(int32_t j=0;j<n;j++)if(saved[j]){
      for(unsigned i=0;i<32;i++)if(s->fbos[i].used && s->fbos[i].name==saved[j])s->fbos[i]=(rc_fbo){0};
      if(s->read==saved[j])s->read=0;
      if(s->draw==saved[j])s->draw=0;
    }
  }
  errno=result_errno;
}
int rc_snapshot(void *cache,rc_state_view *out){
  rc_cache *c=cache;if(!owner(c))return -1;
  if(c->busy)return fail(c,RC_REENTRY);
  if(c->finished || atomic_load(&c->error))return -1;
  rc_context *s=current(c);if(!s)return -1;
  rc_fbo *f=fbo(c,s,s->read,0);
  if(!f || !s->read || !f->known || f->selector<0x8ce0 || f->selector>0x8cff)return fail(c,RC_STATE);
  if(!out)return fail(c,RC_STATE);
  *out=(rc_state_view){s->alignment,s->row_length,s->skip_pixels,s->skip_rows,s->pbo,s->read,s->draw,f->selector,s->tag,c->events};return 0;
}
int rc_observe(uintptr_t texture,uintptr_t gsg,rb_read_state *out,void *cache){
  rc_cache *c=cache;if(!event(c))return -1;
  if(gsg!=c->config.gsg || (texture!=c->config.texture[0] && texture!=c->config.texture[1]) || !out)return fail(c,RC_IDENTITY);
  rc_state_view v;if(rc_snapshot(cache,&v))return -1;
  *out=(rb_read_state){0};out->known=RB_KNOWN_ALL;out->alignment=v.alignment;out->row_length=v.row_length;
  out->skip_pixels=v.skip_pixels;out->skip_rows=v.skip_rows;out->pack_buffer=v.pack_buffer;out->read_fbo=v.read_fbo;out->context_tag=v.context_tag;return 0;
}
int rc_finalize(void *cache,int producer_result){
  rc_cache *c=cache;if(!owner(c))return -1;
  if(c->busy)return fail(c,RC_REENTRY);
  if(c->finished)return fail(c,RC_CLOSED);
  c->finished=1;return producer_result || atomic_load(&c->error)?-1:0;
}
void rc_get_stats(void *cache,rc_counts *out){
  rc_cache *c=cache;if(!owner(c) || !out)return;
  *out=(rc_counts){atomic_load(&c->error),c->created,c->live,c->finished,c->events};
}
