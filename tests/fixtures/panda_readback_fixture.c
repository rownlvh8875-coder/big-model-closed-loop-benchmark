/* Synthetic malloc/GL-shaped calls only. Never links or loads Panda/OpenGL. */
#include "panda_readback_bridge.h"
#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  int32_t x,y,w,h;uint32_t format,type;
  void *pixels;uintptr_t texture,gsg,capacity,image;
  int32_t z,view;
} cpu_call;
extern int pb_fixture_call(const cpu_call *);
extern void pb_fixture_return(void);
static cpu_call call;
static unsigned char *pixels,*snapshot;
static size_t capacity=4096;
static void *bridge;
static const char *mode;
static unsigned originals,callbacks,emits,args_ok=1,regs_ok=1,errno_ok=1,source_ok=1,incoming_ok=1,depth;
static uint32_t producer=1;

static int observer(uintptr_t texture,uintptr_t gsg,rb_read_state *out,void *user) {
  (void)user;callbacks++;
  if(gsg!=0x333 || texture!=(producer==1?0x111u:0x222u))args_ok=0;
  memset(out,0,sizeof(*out));out->known=RB_KNOWN_ALL;out->alignment=1;
  out->context_tag=101;out->read_fbo=7+producer;
  /* A lying capacity/producer here must be replaced by register/registry values. */
  out->capacity=UINT64_MAX;out->producer_camera=3;out->label_basis=0;
  if(strcmp(mode,"packed")==0){out->alignment=8;out->row_length=8;out->skip_rows=2;out->skip_pixels=1;}
  if(strcmp(mode,"pbo")==0)out->pack_buffer=4;
  if(strcmp(mode,"unknown")==0)out->known=0;
  errno=EIO;return strcmp(mode,"statefail")==0?-1:0;
}
static int emitter(const unsigned char *header,size_t n,const unsigned char *payload,size_t size,void *user) {
  (void)user;emits++;
  if(strcmp(mode,"partial")==0){(void)fwrite(header,1,7,stdout);return -1;}
  if(fwrite(header,1,n,stdout)!=n || (size && fwrite(payload,1,size,stdout)!=size))return -1;
  errno=EIO;return strcmp(mode,"footerfail")==0 && n==96?-1:0;
}
static void original(int32_t x,int32_t y,int32_t w,int32_t h,uint32_t format,uint32_t type,void *p) {
  if(strstr(mode,"errno_")!=NULL && errno!=ERANGE)incoming_ok=0;
  originals++;
  if(x!=call.x || y!=call.y || w!=call.w || h!=call.h || format!=call.format || type!=call.type || p!=call.pixels)args_ok=0;
  if(strcmp(mode,"reentrant")==0 && !depth){depth=1;if(!pb_fixture_call(&call))regs_ok=0;depth=0;}
  if(p==pixels){
    unsigned n=format==0x1908 || format==0x80e1?4:3;size_t stride=(size_t)w*n,offset=0;
    if(strcmp(mode,"packed")==0){stride=24;offset=51;}
    memset(pixels,238,capacity);
    for(int r=0;r<h;r++)for(int c=0;c<w;c++){
      size_t pos=offset+(size_t)r*stride+(size_t)c*n;if(pos+n>capacity)continue;
      int bgr=format==0x80e0 || format==0x80e1;
      pixels[pos]=(unsigned char)(bgr?77:producer*10+(unsigned)r);pixels[pos+1]=(unsigned char)(c+1);
      pixels[pos+2]=(unsigned char)(bgr?producer*10+(unsigned)r:77);if(n==4)pixels[pos+3]=201;
    }
    memcpy(snapshot,pixels,capacity);
  }
  if(strstr(mode,"errno_keep")==NULL)errno=EDOM;
}
static void invoke(void){
  if(strstr(mode,"errno_")!=NULL)errno=ERANGE;
  if(strstr(mode,"wrongreturn")!=NULL)pb_entry(call.x,call.y,call.w,call.h,call.format,call.type,call.pixels);
  else if(!pb_fixture_call(&call))regs_ok=0;
  if(errno!=(strstr(mode,"errno_keep")!=NULL?ERANGE:EDOM))errno_ok=0;
  if(memcmp(pixels,snapshot,capacity))source_ok=0;
}
static void *worker(void *arg){(void)arg;invoke();return NULL;}
int main(int argc,char **argv){
  mode=argc>1?argv[1]:"basic";
  rb_config config={0};for(unsigned i=0;i<32;i++)config.nonce[i]=(unsigned char)(i+1);
  config.enabled=strncmp(mode,"off",3)!=0;config.windows=1;config.reads_per_window=2;
  config.max_records=24;config.max_wire_bytes=64u*1024u*1024u;
  call=(cpu_call){-2147483631,2147483624,5,3,0x80e0,0,0,0,0,0,0,-1,0};call.type=0x1401;
  if(strcmp(mode,"max")==0){call.w=964;call.h=604;call.format=0x80e1;config.windows=12;capacity=8*1024*1024;}
  if(strcmp(mode,"rgba")==0)call.format=0x1908;
  if(strcmp(mode,"rgb")==0)call.format=0x1907;
  if(strcmp(mode,"limit")==0)config.max_records=1;
  if(strcmp(mode,"bytes")==0)config.max_wire_bytes=96+160+44;
  pixels=calloc(1,capacity);snapshot=calloc(1,capacity);unsigned char *scratch=calloc(1,capacity);
  bridge=calloc(1,pb_context_size());if(!pixels || !snapshot || !scratch || !bridge)return 2;
  pb_binding binding={original,(uintptr_t)pb_fixture_return,0x333,{0x111,0x222},observer,NULL};
  if(!config.enabled)binding.observe=NULL;
  if(strcmp(mode,"initbad")==0){pb_binding bad=binding;bad.texture[1]=bad.texture[0];if(pb_install(bridge,pb_context_size(),&config,scratch,capacity,emitter,NULL,&bad)==0)return 3;}
  if(pb_install(bridge,pb_context_size(),&config,scratch,capacity,emitter,NULL,&binding)!=0)return 4;
  if(strcmp(mode,"duplicate")==0 && pb_install(bridge,pb_context_size(),&config,scratch,capacity,emitter,NULL,&binding)==0)return 5;
  if(strcmp(mode,"outside")==0)invoke();
  for(uint32_t window=1;window<=config.windows;window++){
    if(pb_begin(bridge,window,window%2?1:2)!=0)break;
    if(strcmp(mode,"nested")==0)(void)pb_begin(bridge,window,1);
    unsigned loops=strcmp(mode,"reentrant")==0 || strcmp(mode,"shortwindow")==0?1:2;
    if(strcmp(mode,"excess")==0)loops=3;
    for(unsigned i=0;i<loops;i++){
      producer=i%2+1;call.texture=producer==1?0x111:0x222;call.gsg=0x333;call.capacity=capacity;call.pixels=pixels;call.image=(uintptr_t)pixels;
      if(!config.enabled){call.pixels=(void *)(uintptr_t)16;call.image=16;}
      if(strcmp(mode,"texture")==0)call.texture=0x999;
      if(strcmp(mode,"gsg")==0)call.gsg=0x444;
      if(strcmp(mode,"image")==0)call.image++;
      if(strcmp(mode,"short")==0)call.capacity=10;
      if(strcmp(mode,"zero")==0)call.capacity=0;
      if(strcmp(mode,"overflow")==0)call.capacity=UINTPTR_MAX;
      if(strcmp(mode,"z")==0)call.z=0;
      if(strcmp(mode,"view")==0)call.view=1;
      if(strcmp(mode,"thread")==0){pthread_t t;if(pthread_create(&t,NULL,worker,NULL)!=0)return 6;(void)pthread_join(t,NULL);}
      else invoke();
    }
    (void)pb_end(bridge);
  }
  int finish=pb_finish(bridge);
  if(strcmp(mode,"outside")==0)invoke();
  pb_stats stats;pb_get_stats(bridge,&stats);
  fprintf(stderr,"{\"source\":\"SYNTHETIC_CPU_ABI_CALLER_ONLY\",\"original_calls\":%u,\"callbacks\":%u,\"emits\":%u,\"args_ok\":%u,\"regs_ok\":%u,\"errno_ok\":%u,\"source_ok\":%u,\"incoming_ok\":%u,\"error\":%u,\"bridge_error\":%u,\"captured\":%" PRIu64 ",\"attempts\":%" PRIu64 ",\"forwards\":%" PRIu64 ",\"wire_bytes\":%" PRIu64 ",\"finish\":%d,\"new_gl_calls\":0,\"runtime_admission_ready\":false}\n",originals,callbacks,emits,args_ok,regs_ok,errno_ok,source_ok,incoming_ok,stats.core.error,stats.bridge_error,stats.core.captured,stats.core.attempts,stats.core.forwards,stats.core.data_wire_bytes,finish);
  free(bridge);free(scratch);free(snapshot);free(pixels);return 0;
}
