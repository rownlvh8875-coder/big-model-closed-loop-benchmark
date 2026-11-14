#include "readback_return_core.h"
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <string.h>

#define RB_SPAN (8u*1024u*1024u)
#define RB_WIRE (64u*1024u*1024u)
typedef struct {
  rb_config config;
  pthread_t owner;
  _Atomic uint32_t error,active;
  _Atomic uint64_t forwards;
  unsigned char *scratch;
  size_t scratch_cap;
  rb_emit_fn emit;
  void *user;
  uint64_t attempts,captured,data_bytes,closed,window_start;
  uint32_t call,camera,busy,finished;
} rb_context;

static int fail(rb_context *c,uint32_t error) {
  uint32_t expected=0;
  (void)atomic_compare_exchange_strong(&c->error,&expected,error);
  return -1;
}
static int owner(rb_context *c) {
  return pthread_equal(c->owner,pthread_self()) ? 1 : (fail(c,RB_THREAD),0);
}
static void u32(unsigned char *p,uint32_t n) {
  for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(n>>(i*8));
}
static void u64(unsigned char *p,uint64_t n) {
  for(unsigned i=0;i<8;i++)p[i]=(unsigned char)(n>>(i*8));
}
size_t rb_context_size(void){return sizeof(rb_context);}
int rb_init(void *storage,size_t bytes,unsigned char *scratch,size_t cap,
            const rb_config *config,rb_emit_fn emit,void *user) {
  if(!storage || bytes<sizeof(rb_context) || (uintptr_t)storage%_Alignof(rb_context) || !config || !emit)return -1;
  unsigned nonce=0;for(unsigned i=0;i<32;i++)nonce|=config->nonce[i];
  if(!nonce || config->enabled>1 || !config->windows || config->windows>12 ||
     !config->reads_per_window || config->reads_per_window>2 || !config->max_records ||
     config->max_records>24 || config->max_wire_bytes<96 || config->max_wire_bytes>RB_WIRE ||
     (config->enabled && (!scratch || !cap || cap>RB_SPAN)))return -1;
  rb_context *c=storage;memset(c,0,sizeof(*c));c->config=*config;
  c->owner=pthread_self();atomic_init(&c->error,0);atomic_init(&c->active,0);atomic_init(&c->forwards,0);
  c->scratch=scratch;c->scratch_cap=cap;c->emit=emit;c->user=user;return 0;
}
int rb_begin(void *ctx,uint32_t call,uint32_t camera) {
  rb_context *c=ctx;
  if(!owner(c))return -1;
  if(c->busy)return fail(c,RB_REENTRANT);
  if(atomic_load(&c->error))return -1;
  if(c->finished || atomic_load(&c->active) || c->closed>=c->config.windows ||
     call!=c->closed+1 || camera!=(call%2?1u:2u))return fail(c,RB_SEQUENCE);
  c->call=call;c->camera=camera;c->window_start=atomic_load(&c->forwards);
  atomic_store(&c->active,1);return 0;
}
static int layout(rb_context *c,const rb_read_state *s,int32_t w,int32_t h,uint32_t f,uint32_t t,
                  void *pixels,uint64_t *stride,uint64_t *offset,uint64_t *payload) {
  if(s->known!=RB_KNOWN_ALL || !s->context_tag || s->producer_camera>2 || s->label_basis>1 ||
     ((s->producer_camera==0)!=(s->label_basis==0)))return fail(c,RB_METADATA);
  if(s->pack_buffer)return fail(c,RB_PBO);
  unsigned n=(f==0x1907 || f==0x80e0)?3:(f==0x1908 || f==0x80e1)?4:0;
  if(!n || t!=0x1401 || w<1 || w>964 || h<1 || h>604 ||
     (s->alignment!=1 && s->alignment!=2 && s->alignment!=4 && s->alignment!=8) ||
     s->row_length>4096 || s->skip_pixels>4096 || s->skip_rows>4096)return fail(c,RB_LAYOUT);
  uint64_t row=s->row_length?s->row_length:(uint32_t)w;
  if(s->skip_pixels+(uint64_t)w>row)return fail(c,RB_LAYOUT);
  *stride=(row*n+s->alignment-1)/s->alignment*s->alignment;
  *offset=s->skip_rows*(*stride)+s->skip_pixels*(uint64_t)n;
  uint64_t span=*offset+(h-1)*(*stride)+(uint64_t)w*n;
  *payload=(uint64_t)w*h*n;
  if(!pixels || !s->capacity || s->capacity>RB_SPAN || span>s->capacity || span>RB_SPAN ||
     *payload>c->scratch_cap)return fail(c,RB_EXTENT);
  uintptr_t p=(uintptr_t)pixels,q=(uintptr_t)c->scratch;
  if(p>UINTPTR_MAX-span || q>UINTPTR_MAX-*payload)return fail(c,RB_EXTENT);
  if(p<q+*payload && q<p+span)return fail(c,RB_ALIAS);
  return 0;
}
void rb_read(void *ctx,rb_read_fn original,int32_t x,int32_t y,int32_t w,int32_t h,
             uint32_t f,uint32_t t,void *pixels,const rb_read_state *state) {
  rb_context *c=ctx;
  if(!original){(void)fail(c,RB_NO_ORIGINAL);return;}
  if(!atomic_load(&c->active)){original(x,y,w,h,f,t,pixels);return;}
  uint64_t ordinal=atomic_fetch_add(&c->forwards,1)+1;
  if(!owner(c)){original(x,y,w,h,f,t,pixels);return;}
  if(c->busy){(void)fail(c,RB_REENTRANT);original(x,y,w,h,f,t,pixels);return;}
  /* Bound observation before touching metadata, even on the excess call itself. */
  if(ordinal-c->window_start>c->config.reads_per_window)(void)fail(c,RB_SEQUENCE);
  c->busy=1;
  rb_read_state saved={0};
  int observe=c->config.enabled && !atomic_load(&c->error);
  if(observe && state)saved=*state;
  original(x,y,w,h,f,t,pixels);
  int original_errno=errno;
  if(observe && !atomic_load(&c->error)){
    uint64_t stride=0,offset=0,n=0;c->attempts++;
    if(layout(c,&saved,w,h,f,t,pixels,&stride,&offset,&n)==0){
      if(c->captured>=c->config.max_records || c->data_bytes+160+n+96>c->config.max_wire_bytes){
        (void)fail(c,RB_LIMIT);
      }else{
        size_t columns=(size_t)(n/(uint32_t)h);
        for(int32_t row=0;row<h;row++)memcpy(c->scratch+(size_t)row*columns,
            (const unsigned char *)pixels+offset+(size_t)row*stride,columns);
        unsigned char header[160]={0};memcpy(header,"RBRET001",8);u32(header+8,1);u32(header+12,160);
        u64(header+16,c->captured+1);memcpy(header+24,c->config.nonce,32);
        u32(header+56,c->call);u32(header+60,c->camera);u32(header+64,saved.producer_camera);
        u32(header+68,saved.read_fbo);u64(header+72,saved.context_tag);
        u32(header+80,(uint32_t)x);u32(header+84,(uint32_t)y);u32(header+88,(uint32_t)w);u32(header+92,(uint32_t)h);
        u32(header+96,f);u32(header+100,t);u32(header+104,saved.alignment);u32(header+108,saved.row_length);
        u32(header+112,saved.skip_pixels);u32(header+116,saved.skip_rows);u32(header+120,saved.pack_buffer);
        u32(header+124,saved.label_basis);u64(header+128,n);u64(header+136,stride);u64(header+144,offset);u64(header+152,saved.capacity);
        if(c->emit(header,sizeof(header),c->scratch,(size_t)n,c->user)!=0)(void)fail(c,RB_EMIT);
        else{c->captured++;c->data_bytes+=sizeof(header)+n;}
      }
    }
  }
  c->busy=0;errno=original_errno;
}
int rb_end(void *ctx) {
  rb_context *c=ctx;if(!owner(c))return -1;
  if(c->busy)return fail(c,RB_REENTRANT);
  if(c->finished || !atomic_load(&c->active))return fail(c,RB_SEQUENCE);
  atomic_store(&c->active,0);c->closed++;
  if(atomic_load(&c->forwards)-c->window_start!=c->config.reads_per_window)(void)fail(c,RB_SEQUENCE);
  return atomic_load(&c->error)?-1:0;
}
int rb_finish(void *ctx) {
  rb_context *c=ctx;if(!owner(c))return -1;
  if(c->busy)return fail(c,RB_REENTRANT);
  if(c->finished)return fail(c,RB_SEQUENCE);
  c->finished=1;
  uint64_t expected=c->config.windows*c->config.reads_per_window;
  if(atomic_load(&c->active) || c->closed!=c->config.windows || atomic_load(&c->forwards)!=expected ||
     c->captured!=(c->config.enabled?expected:0) || c->attempts!=c->captured)(void)fail(c,RB_SEQUENCE);
  atomic_store(&c->active,0);
  unsigned char footer[96]={0};memcpy(footer,"RBEND001",8);u32(footer+8,1);u32(footer+12,96);
  memcpy(footer+16,c->config.nonce,32);u64(footer+48,atomic_load(&c->forwards));u64(footer+56,c->attempts);
  u64(footer+64,c->captured);u64(footer+72,c->data_bytes);u64(footer+80,c->closed);
  u32(footer+88,atomic_load(&c->error));u32(footer+92,c->config.enabled);
  if(c->emit(footer,sizeof(footer),NULL,0,c->user)!=0)(void)fail(c,RB_EMIT);
  return atomic_load(&c->error)?-1:0;
}
void rb_get_stats(void *ctx,rb_stats *out) {
  rb_context *c=ctx;if(!owner(c) || !out)return;
  out->error=atomic_load(&c->error);out->forwards=atomic_load(&c->forwards);
  out->attempts=c->attempts;out->captured=c->captured;out->data_wire_bytes=c->data_bytes;
}
