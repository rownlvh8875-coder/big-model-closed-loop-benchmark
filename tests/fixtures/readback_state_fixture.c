/* Command cache + existing assembly/core integration. All originals are CPU fakes. */
#include "readback_command_state.h"
#include "panda_readback_bridge.h"
#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {int32_t x,y,w,h;uint32_t format,type;void *pixels;uintptr_t texture,gsg,capacity,image;int32_t z,view;} cpu_call;
extern int pb_fixture_call(const cpu_call *);
extern void pb_fixture_return(void);
static void *cache,*bridge;
static const char *mode;
static uint32_t expected_a,expected_b;
static unsigned commands,reads,args_ok=1,errno_ok=1,source_ok=1,regs_ok=1,depth;
static uint32_t first_selector;
static unsigned char pixels[4096],snapshot[4096];
static const uint32_t *expected_names;
static void entered(uint32_t a,uint32_t b){commands++;if(errno!=ERANGE || a!=expected_a || b!=expected_b)args_ok=0;}
static void done(void){if(strcmp(mode,"preserve")!=0)errno=EDOM;}
static void ps(uint32_t p,int32_t v){entered(p,(uint32_t)v);if(strcmp(mode,"reentrant")==0 && !depth){depth=1;rc_pixel_store(cache,ps,p,v);depth=0;}done();}
static void bind(uint32_t p,uint32_t v){entered(p,v);done();}
static void rb(uint32_t v){entered(v,0);done();}
static void del(int32_t n,const uint32_t *names){
  entered((uint32_t)n,0);if(names!=expected_names)args_ok=0;
  if(strcmp(mode,"delete_mutate")==0 && n>0)((uint32_t *)names)[0]=99;
  done();
}
static void check_errno(void){if(errno!=(strcmp(mode,"preserve")==0?ERANGE:EDOM))errno_ok=0;}
static void store(uint32_t p,int32_t v){expected_a=p;expected_b=(uint32_t)v;errno=ERANGE;rc_pixel_store(cache,ps,p,v);check_errno();}
static void buffer(uint32_t p,uint32_t v){expected_a=p;expected_b=v;errno=ERANGE;rc_bind_buffer(cache,bind,p,v);check_errno();}
static void fbo(uint32_t p,uint32_t v){expected_a=p;expected_b=v;errno=ERANGE;rc_bind_framebuffer(cache,bind,p,v);check_errno();}
static void selector(uint32_t v){expected_a=v;expected_b=0;errno=ERANGE;rc_read_buffer(cache,rb,v);check_errno();}
static void remove_fbo(uint32_t name){expected_names=&name;expected_a=1;expected_b=0;errno=ERANGE;rc_delete_framebuffers(cache,del,1,&name);check_errno();}
static int emit(const unsigned char *h,size_t hn,const unsigned char *p,size_t n,void *u){
  (void)u;if(fwrite(h,1,hn,stdout)!=hn || (n && fwrite(p,1,n,stdout)!=n))return -1;
  errno=EIO;return strcmp(mode,"footerfail")==0 && hn==96?-1:0;
}
static void original(int32_t x,int32_t y,int32_t w,int32_t h,uint32_t f,uint32_t t,void *p){
  reads++;if(x!=-7 || y!=11 || w!=5 || h!=3 || f!=0x80e0 || t!=0x1401 || p!=pixels || errno!=ERANGE)args_ok=0;
  size_t stride=strcmp(mode,"packed")==0?24:16,offset=strcmp(mode,"packed")==0?51:0;
  memset(pixels,238,sizeof(pixels));
  for(unsigned r=0;r<3;r++)for(unsigned c=0;c<5;c++){size_t pos=offset+r*stride+c*3;pixels[pos]=77;pixels[pos+1]=(unsigned char)(c+1);pixels[pos+2]=(unsigned char)(10+r);}
  memcpy(snapshot,pixels,sizeof(pixels));errno=EDOM;
}
static void *foreign(void *u){(void)u;store(0xd05,1);return NULL;}
int main(int argc,char **argv){
  mode=argc>1?argv[1]:"basic";cache=calloc(1,rc_context_size());bridge=calloc(1,pb_context_size());
  unsigned char *scratch=calloc(1,4096);if(!cache || !bridge || !scratch)return 2;
  rc_config cfg={0x333,{0x111,0x222},10000};if(strcmp(mode,"eventcap")==0)cfg.max_events=5;
  /* Optional CPU-fake registry identities; never a live-handle transport. */
  if(argc==5){cfg.texture[0]=(uintptr_t)strtoull(argv[2],NULL,10);cfg.texture[1]=(uintptr_t)strtoull(argv[3],NULL,10);cfg.gsg=(uintptr_t)strtoull(argv[4],NULL,10);}
  if(rc_init(cache,rc_context_size(),&cfg))return 3;
  (void)rc_context_new(cache,10,0);(void)rc_context_current(cache,10,1);
  if(strcmp(mode,"unknownctx")==0)(void)rc_context_current(cache,99,1);
  if(strcmp(mode,"failedswitch")==0)(void)rc_context_current(cache,99,0);
  if(strcmp(mode,"shared")==0)(void)rc_context_new(cache,20,10);
  if(strcmp(mode,"duplicatectx")==0)(void)rc_context_new(cache,10,0);
  if(strcmp(mode,"destroy")==0)(void)rc_context_destroy(cache,10);
  if(strcmp(mode,"unbound")==0)(void)rc_context_current(cache,0,1);
  if(strcmp(mode,"reuse")==0){(void)rc_context_destroy(cache,10);(void)rc_context_new(cache,10,0);(void)rc_context_current(cache,10,1);}
  if(strcmp(mode,"livecap")==0){(void)rc_context_new(cache,20,0);(void)rc_context_new(cache,30,0);}
  if(strcmp(mode,"lifetimes")==0)for(uintptr_t i=0;i<4;i++){(void)rc_context_destroy(cache,10+i);(void)rc_context_new(cache,11+i,0);(void)rc_context_current(cache,11+i,1);}
  if(strcmp(mode,"invalidate")==0)(void)rc_invalidate(cache);
  if(strcmp(mode,"badalign")==0 || strcmp(mode,"offinvalid")==0)store(0xd05,3);
  if(strcmp(mode,"rowoverflow")==0)store(0xd02,4097);
  if(strcmp(mode,"swap")==0)store(0xd00,1);
  if(strcmp(mode,"unknownenum")==0)store(0xffffffff,1);
  if(strcmp(mode,"unpack")==0){store(0xcf5,8);buffer(0x88ec,17);}
  if(strcmp(mode,"packed")==0){store(0xd05,8);store(0xd02,8);store(0xd03,2);store(0xd04,1);}
  if(strcmp(mode,"pbo")==0)buffer(0x88eb,4);
  if(strcmp(mode,"pbo_reset")==0){buffer(0x88eb,4);buffer(0x88eb,0);}
  if(strcmp(mode,"reentrant")==0)store(0xd05,4);
  if(strcmp(mode,"failed_delete")==0){store(0xd05,3);expected_a=1;expected_b=0;expected_names=(const uint32_t *)(uintptr_t)16;errno=ERANGE;rc_delete_framebuffers(cache,del,1,expected_names);check_errno();}
  if(strcmp(mode,"foreignidentity")==0){rb_read_state out;(void)rc_observe(999,0x333,&out,cache);}
  if(strcmp(mode,"fbocap")==0)for(uint32_t i=1;i<=32;i++)fbo(0x8d40,i);
  if(strcmp(mode,"thread")==0){pthread_t t;if(pthread_create(&t,NULL,foreign,NULL))return 4;(void)pthread_join(t,NULL);}
  if(strcmp(mode,"restore")==0){fbo(0x8d40,8);selector(0x8ce0);(void)rc_context_new(cache,20,0);(void)rc_context_current(cache,20,1);fbo(0x8d40,9);selector(0x8ce1);(void)rc_context_current(cache,10,1);}
  if(strcmp(mode,"isolation")==0){(void)rc_context_new(cache,20,0);(void)rc_context_current(cache,20,1);store(0xd05,8);store(0xd02,8);buffer(0x88eb,4);(void)rc_context_current(cache,10,1);}
  if(strcmp(mode,"selector_restore")==0){fbo(0x8d40,8);selector(0x8ce1);fbo(0x8d40,9);selector(0x8ce0);}
  rb_config config={0};for(unsigned i=0;i<32;i++)config.nonce[i]=(unsigned char)(i+1);
  config.enabled=strncmp(mode,"off",3)!=0;config.windows=strcmp(mode,"windows")==0?12:1;config.reads_per_window=2;config.max_records=24;config.max_wire_bytes=64u*1024u*1024u;
  pb_binding binding={original,(uintptr_t)pb_fixture_return,cfg.gsg,{cfg.texture[0],cfg.texture[1]},rc_observe,cache};
  if(pb_install(bridge,pb_context_size(),&config,scratch,4096,emit,NULL,&binding))return 5;
  for(uint32_t win=1;win<=config.windows;win++){
    if(pb_begin(bridge,win,win%2?1:2))break;
    for(unsigned i=0;i<2;i++){
      uint32_t name=strcmp(mode,"defaultfbo")==0?0:8+i;
      if(strcmp(mode,"read_target")==0){fbo(0x8d40,99);fbo(0x8ca8,name);}else fbo(0x8d40,name);
      if(strcmp(mode,"missingselector")!=0 && strcmp(mode,"selector_restore")!=0)selector(strcmp(mode,"readnone")==0?0:name?0x8ce0:0x405);
      if(strcmp(mode,"selector_restore")==0 && i==0){rc_state_view v;if(rc_snapshot(cache,&v)==0)first_selector=v.read_selector;}
      if(strcmp(mode,"draw")==0)fbo(0x8ca9,99);
      if(strcmp(mode,"delete_draw")==0){fbo(0x8ca9,99);remove_fbo(99);}
      if(strcmp(mode,"delete_bound")==0 || strcmp(mode,"delete_mutate")==0){remove_fbo(name);fbo(0x8d40,name);}
      cpu_call call={-7,11,5,3,0x80e0,0x1401,pixels,cfg.texture[i],cfg.gsg,4096,(uintptr_t)pixels,-1,0};
      errno=ERANGE;if(!pb_fixture_call(&call))regs_ok=0;if(errno!=EDOM)errno_ok=0;
      if(memcmp(pixels,snapshot,sizeof(pixels)))source_ok=0;
    }
    (void)pb_end(bridge);
  }
  rc_state_view view={0};int known=rc_snapshot(cache,&view);
  int finish=rc_finalize(cache,pb_finish(bridge));pb_stats bs;pb_get_stats(bridge,&bs);rc_counts stats;rc_get_stats(cache,&stats);
  fprintf(stderr,"{\"source\":\"SYNTHETIC_COMMANDS_AND_CPU_CALLER_ONLY\",\"commands_only\":true,\"first_selector\":%u,\"commands\":%u,\"original_calls\":%u,\"args_ok\":%u,\"regs_ok\":%u,\"errno_ok\":%u,\"source_ok\":%u,\"cache_error\":%u,\"contexts_created\":%u,\"events\":%" PRIu64 ",\"known\":%d,\"context_tag\":%" PRIu64 ",\"read_fbo\":%u,\"draw_fbo\":%u,\"read_selector\":%u,\"alignment\":%u,\"row_length\":%u,\"skip_rows\":%u,\"skip_pixels\":%u,\"error\":%u,\"bridge_error\":%u,\"captured\":%" PRIu64 ",\"attempts\":%" PRIu64 ",\"forwards\":%" PRIu64 ",\"wire_bytes\":%" PRIu64 ",\"finish\":%d,\"new_gl_calls\":0,\"driver_state_proven\":false,\"runtime_admission_ready\":false}\n",first_selector,commands,reads,args_ok,regs_ok,errno_ok,source_ok,stats.error,stats.contexts_created,stats.events,known,view.context_tag,view.read_fbo,view.draw_fbo,view.read_selector,view.alignment,view.row_length,view.skip_rows,view.skip_pixels,bs.core.error,bs.bridge_error,bs.core.captured,bs.core.attempts,bs.core.forwards,bs.core.data_wire_bytes,finish);
  free(scratch);free(bridge);free(cache);return 0;
}
