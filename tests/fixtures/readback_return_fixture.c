/* CPU-only original function. This executable never links or calls OpenGL. */
#include "readback_return_core.h"
#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *context;
static rb_read_state state;
static unsigned char *pixels,*snapshot;
static uint32_t format_value=0x80e0,producer=1;
static int width_value=5,height_value=3;
static unsigned original_calls,emits,args_ok=1,unchanged=1,errno_ok=1;
static int reentrant,depth,mutate,emit_failure,pbo_mode;
static size_t source_size=8*1024*1024;

static int emit_record(const unsigned char *header,size_t hn,const unsigned char *data,size_t n,void *user) {
  (void)user;emits++;
  if(emit_failure){(void)fwrite(header,1,7,stdout);errno=EIO;return -1;}
  if(fwrite(header,1,hn,stdout)!=hn || (n && fwrite(data,1,n,stdout)!=n))return -1;
  errno=EIO;return 0;
}
static unsigned channels(void){return format_value==0x1908 || format_value==0x80e1 ? 4u:3u;}
static void fake_original(int32_t x,int32_t y,int32_t w,int32_t h,uint32_t f,uint32_t t,void *p) {
  original_calls++;
  if(x!=-7 || y!=11 || w!=width_value || h!=height_value || f!=format_value || t!=0x1401 || p!=(pbo_mode?(void *)(uintptr_t)16:pixels))args_ok=0;
  if(reentrant && depth==0){depth=1;rb_read(context,fake_original,x,y,w,h,f,t,p,&state);depth=0;}
  if(p && !pbo_mode){
    unsigned n=channels();size_t row=(state.row_length?state.row_length:(uint32_t)w)*n;
    unsigned alignment=state.alignment?state.alignment:1;
    row=(row+alignment-1)/alignment*alignment;
    size_t offset=state.skip_rows*row+state.skip_pixels*n;
    memset(p,238,source_size);
    for(int r=0;r<h;r++)for(int c=0;c<w;c++){
      size_t pos=offset+(size_t)r*row+(size_t)c*n;
      if(pos+n>source_size)continue;
      unsigned char red=(unsigned char)(producer*10+(unsigned)r),green=(unsigned char)(c+1),blue=77;
      int bgr=f==0x80e0 || f==0x80e1;
      ((unsigned char *)p)[pos]=bgr?blue:red;((unsigned char *)p)[pos+1]=green;((unsigned char *)p)[pos+2]=bgr?red:blue;
      if(n==4)((unsigned char *)p)[pos+3]=201;
    }
    memcpy(snapshot,p,source_size);
  }
  if(mutate){state.capacity=0;state.known=0;}
  errno=EDOM;
}
static void invoke(void){
  rb_read(context,fake_original,-7,11,width_value,height_value,format_value,0x1401,pbo_mode?(void *)(uintptr_t)16:pixels,&state);
  if(errno!=EDOM)errno_ok=0;
  if(pixels && !pbo_mode && memcmp(pixels,snapshot,source_size)!=0)unchanged=0;
}
static void *on_worker(void *p){(void)p;invoke();return NULL;}
int main(int argc,char **argv){
  const char *mode=argc>1?argv[1]:"basic";
  rb_config config={0};for(unsigned i=0;i<32;i++)config.nonce[i]=(unsigned char)(i+1);
  config.enabled=strcmp(mode,"off")!=0;config.windows=1;config.reads_per_window=2;
  config.max_records=24;config.max_wire_bytes=64u*1024u*1024u;
  if(strcmp(mode,"limit")==0)config.max_records=1;
  if(strcmp(mode,"bytes")==0)config.max_wire_bytes=96+160+44;
  if(strcmp(mode,"max")==0){width_value=964;height_value=604;format_value=0x80e1;config.windows=12;}
  if(strcmp(mode,"rgb")==0)format_value=0x1907;
  if(strcmp(mode,"rgba")==0)format_value=0x1908;
  if(strcmp(mode,"bgra")==0 || strcmp(mode,"packed")==0)format_value=0x80e1;
  reentrant=strcmp(mode,"reentrant")==0;mutate=strcmp(mode,"mutate")==0;
  emit_failure=strcmp(mode,"emitfail")==0;pbo_mode=strcmp(mode,"pbo")==0;
  pixels=calloc(1,source_size);snapshot=calloc(1,source_size);
  unsigned char *scratch=calloc(1,source_size);context=calloc(1,rb_context_size());
  if(!pixels || !snapshot || !scratch || !context)return 2;
  if(strcmp(mode,"alias")==0){free(scratch);scratch=pixels;}
  int initialized=rb_init(context,rb_context_size(),config.enabled?scratch:NULL,config.enabled?source_size:0,&config,emit_record,NULL);
  if(initialized)return 3;
  for(uint32_t window=1;window<=config.windows;window++){
    if(rb_begin(context,window,window%2?1:2)!=0)break;
    if(strcmp(mode,"nested")==0)(void)rb_begin(context,window,1);
    unsigned loops=(reentrant || strcmp(mode,"shortwindow")==0)?1:2;
    for(unsigned j=0;j<loops;j++){
      producer=j+1;memset(&state,0,sizeof(state));state.known=RB_KNOWN_ALL;
      state.alignment=1;state.capacity=source_size;state.context_tag=101;state.read_fbo=7+producer;
      state.producer_camera=producer;state.label_basis=1;
      if(strcmp(mode,"packed")==0){state.alignment=4;state.row_length=8;state.skip_pixels=1;state.skip_rows=2;}
      if(strcmp(mode,"short")==0)state.capacity=10;
      if(strcmp(mode,"unknown")==0)state.known=0;
      if(pbo_mode)state.pack_buffer=4;
      if(strcmp(mode,"overlap")==0){state.row_length=5;state.skip_pixels=1;}
      if(strcmp(mode,"unknownproducer")==0){state.producer_camera=0;state.label_basis=0;}
      if(strcmp(mode,"ambiguous")==0){state.producer_camera=1;state.read_fbo=8;producer=1;}
      if(strcmp(mode,"off")==0){
        free(pixels);pixels=NULL;
        rb_read(context,fake_original,-7,11,width_value,height_value,format_value,0x1401,NULL,(const rb_read_state *)(uintptr_t)16);
        if(errno!=EDOM)errno_ok=0;
      }else if(strcmp(mode,"thread")==0){pthread_t worker;if(pthread_create(&worker,NULL,on_worker,NULL)!=0)return 4;(void)pthread_join(worker,NULL);}
      else invoke();
    }
    (void)rb_end(context);
  }
  int finished=rb_finish(context);rb_stats stats;rb_get_stats(context,&stats);
  fprintf(stderr,"{\"source\":\"SYNTHETIC_CPU_FAKE_ONLY\",\"original_calls\":%u,\"emits\":%u,\"args_ok\":%u,\"source_unchanged\":%u,\"errno_ok\":%u,\"error\":%u,\"captured\":%" PRIu64 ",\"attempts\":%" PRIu64 ",\"forwards\":%" PRIu64 ",\"wire_bytes\":%" PRIu64 ",\"finish\":%d,\"new_gl_calls\":0,\"native_admitted\":false}\n",original_calls,emits,args_ok,unchanged,errno_ok,stats.error,stats.captured,stats.attempts,stats.forwards,stats.data_wire_bytes,finished);
  if(scratch!=pixels){free(scratch);}
  free(pixels);free(snapshot);free(context);return 0;
}
