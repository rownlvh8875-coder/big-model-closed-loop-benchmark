/* CPU-shaped GL/GLX originals only. No GL/Panda library is linked or loaded. */
#define _POSIX_C_SOURCE 200809L
#include "readback_call_delivery.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/resource.h>
#include <unistd.h>
typedef struct {int32_t x,y,w,h;uint32_t f,t;void *p;uintptr_t tex,gsg,capacity,image;int32_t z,view;} cpu_call;
extern int rd_fixture_call(const cpu_call *);
extern void rd_fixture_return(void);
static const char *mode;
static unsigned originals,reads,resolves,args_ok=1,errno_ok=1,regs_ok=1,depth;
static unsigned char pixels[4096];
static uint32_t want_a,want_b;static rd_context want_share;static rd_display *want_display;
static void *delivery;
static void entered(uint32_t a,uint32_t b){originals++;if(a!=want_a || b!=want_b || errno!=ERANGE)args_ok=0;}
static void output_errno(void){if(strcmp(mode,"preserve")!=0)errno=EDOM;}
void rd_probe_store(uint32_t name,int32_t value){entered(name,(uint32_t)value);if(strcmp(mode,"reentrant")==0 && !depth){depth=1;rd_pixel_store(name,value);depth=0;}output_errno();}
static void buffer(uint32_t a,uint32_t b){entered(a,b);output_errno();}
static void frame(uint32_t a,uint32_t b){entered(a,b);output_errno();}
static void frame_ext(uint32_t a,uint32_t b){entered(a,b);output_errno();}
static void selector(uint32_t a){entered(a,0);output_errno();}
static void remove_frames(int32_t n,const uint32_t *names){entered((uint32_t)n,n>0?names[0]:0);output_errno();}
static rd_context create_new(rd_display *d,rd_fbconfig cfg,int type,rd_context share,int direct){
 originals++;if(d!=want_display || cfg!=(rd_fbconfig)(uintptr_t)2 || type!=3 || share!=want_share || direct!=1 || errno!=ERANGE)args_ok=0;
 output_errno();return strcmp(mode,"createfail")==0 && originals==1?NULL:(rd_context)(uintptr_t)(d==(rd_display *)(uintptr_t)1?10:20);
}
static rd_context create_attr(rd_display *d,rd_fbconfig cfg,rd_context share,int direct,const int *attrs){
 originals++;if(d!=want_display || cfg!=(rd_fbconfig)(uintptr_t)2 || share!=want_share || direct!=1 || attrs[0]!=0x2091 || attrs[1]!=3 || attrs[2]!=0 || errno!=ERANGE)args_ok=0;
 output_errno();return (rd_context)(uintptr_t)10;
}
static int make_current(rd_display *d,unsigned long draw,rd_context ctx){originals++;if(d!=want_display || draw!=17 || errno!=ERANGE)args_ok=0;output_errno();return ctx==(rd_context)(uintptr_t)99?0:1;}
static int make_both(rd_display *d,unsigned long draw,unsigned long read,rd_context ctx){originals++;if(d!=want_display || draw!=17 || read!=18 || ctx!=(rd_context)(uintptr_t)10 || errno!=ERANGE)args_ok=0;output_errno();return 1;}
static void destroy(rd_display *d,rd_context ctx){originals++;if(d!=want_display || ctx!=(rd_context)(uintptr_t)10 || errno!=ERANGE)args_ok=0;output_errno();}
static uint32_t error_value(void){originals++;if(errno!=ERANGE)args_ok=0;output_errno();return strcmp(mode,"glerror")==0?0x502:0;}
void rd_probe_read(int32_t x,int32_t y,int32_t w,int32_t h,uint32_t f,uint32_t t,void *p){
 reads++;if(x!=-7 || y!=11 || w!=5 || h!=3 || f!=0x80e0 || t!=0x1401 || p!=pixels || errno!=ERANGE)args_ok=0;
 for(unsigned r=0;r<3;r++)for(unsigned c=0;c<5;c++){size_t i=r*15+c*3;pixels[i]=77;pixels[i+1]=(unsigned char)(c+1);pixels[i+2]=(unsigned char)(10+r);}
 output_errno();
}
static rd_proc resolver(const unsigned char *name){
 resolves++;if(errno!=ERANGE)args_ok=0;output_errno();
 if(!strcmp((const char *)name,"glReadPixels"))return (rd_proc)rd_probe_read;
 if(!strcmp((const char *)name,"glBindFramebufferEXT"))return strcmp(mode,"mismatch")==0?(rd_proc)buffer:strcmp(mode,"null")==0?NULL:(rd_proc)frame_ext;
 if(!strcmp((const char *)name,"glPixelStorei"))return (rd_proc)rd_probe_store;
 return (rd_proc)buffer;
}
static void expected(uint32_t a,uint32_t b){want_a=a;want_b=b;errno=ERANGE;}
static void checked(void){if(errno!=(strcmp(mode,"preserve")==0?ERANGE:EDOM))errno_ok=0;}
static int emit(const unsigned char *h,size_t hn,const unsigned char *p,size_t n,void *u){
 (void)u;if(fwrite(h,1,hn,stdout)!=hn || (n && fwrite(p,1,n,stdout)!=n))return -1;
 errno=EIO;return strcmp(mode,"footerfail")==0 && hn==96?-1:0;
}
static void *foreign(void *p){(void)p;expected(0xd05,1);rd_pixel_store(0xd05,1);checked();return NULL;}
int main(int argc,char **argv){
 mode=argc>1?argv[1]:"basic";delivery=calloc(1,rd_context_size());void *cache=calloc(1,rc_context_size()),*bridge=calloc(1,pb_context_size());unsigned char *scratch=calloc(1,4096);
 const char *control=getenv("RD_CONTROL_FD"),*nonce=getenv("RD_NONCE");int channel=control?atoi(control):-1;
 if(channel>=0){struct rlimit cap={64u*1024u*1024u,64u*1024u*1024u};if(setrlimit(RLIMIT_FSIZE,&cap))return 7;}
 if(!delivery || !cache || !bridge || !scratch)return 2;
 rd_dispatch dispatch={0};dispatch.pixel_store=rd_probe_store;dispatch.bind_buffer=buffer;dispatch.bind_buffer_arb=buffer;dispatch.bind_framebuffer=frame;dispatch.bind_framebuffer_ext=strcmp(mode,"null")==0?NULL:frame_ext;dispatch.read_buffer=selector;dispatch.delete_framebuffers=remove_frames;dispatch.delete_framebuffers_ext=remove_frames;dispatch.read_pixels=rd_probe_read;
 dispatch.create_new=create_new;dispatch.create_attribs=create_attr;dispatch.make_current=make_current;dispatch.make_context_current=make_both;dispatch.destroy_context=destroy;dispatch.get_error=error_value;dispatch.get_proc=resolver;dispatch.get_proc_arb=resolver;
 const char *safe[]={argc>2?argv[2]:"glDrawArrays"};
 if(rd_install(delivery,rd_context_size(),&dispatch,safe,1,strcmp(mode,"cap")==0?3:10000)){
   free(scratch);free(bridge);free(cache);free(delivery);return 3;
 }
 want_display=(rd_display *)(uintptr_t)1;want_share=strcmp(mode,"shared")==0?(rd_context)(uintptr_t)7:NULL;
 errno=ERANGE;rd_context ctx;
 if(strcmp(mode,"attrib")==0){int attrs[]={0x2091,3,0};ctx=rd_create_attribs(want_display,(rd_fbconfig)(uintptr_t)2,want_share,1,attrs);}
 else ctx=rd_create_new(want_display,(rd_fbconfig)(uintptr_t)2,3,want_share,1);
 checked();if(!ctx){errno=ERANGE;ctx=rd_create_new(want_display,(rd_fbconfig)(uintptr_t)2,3,NULL,1);checked();}
 if(strcmp(mode,"failedswitch")==0){errno=ERANGE;if(rd_make_current(want_display,17,(rd_context)(uintptr_t)99)!=0)args_ok=0;checked();}
 errno=ERANGE;
 if(strcmp(mode,"makeboth")==0){if(rd_make_context_current(want_display,17,18,ctx)!=1)args_ok=0;}
 else if(rd_make_current(want_display,17,ctx)!=1)args_ok=0;
 checked();expected(0xd05,1);rd_pixel_store(0xd05,1);checked();expected(0x8d40,8);rd_bind_framebuffer(0x8d40,8);checked();expected(0x8ce0,0);rd_read_buffer(0x8ce0);checked();
 rc_config config={0x333,{0x111,0x222},10000};if(rc_init(cache,rc_context_size(),&config))return 4;
 unsigned before=originals;int attached=rd_attach(cache);if(originals!=before)args_ok=0;
 rb_config core={0};for(unsigned i=0;i<32;i++)core.nonce[i]=(unsigned char)(i+1);core.enabled=strncmp(mode,"off",3)!=0;core.windows=1;core.reads_per_window=2;core.max_records=24;core.max_wire_bytes=64u*1024u*1024u;
 if(channel>=0){
   if(!nonce || strlen(nonce)!=64)return 7;
   for(unsigned i=0;i<32;i++){unsigned n;if(sscanf(nonce+2*i,"%2x",&n)!=1)return 7;core.nonce[i]=(unsigned char)n;}
 }
 pb_binding binding={rd_probe_read,(uintptr_t)rd_fixture_return,0x333,{0x111,0x222},rd_observe,delivery};
 int bound=attached==0?rd_bind_bridge(bridge,pb_context_size(),&core,scratch,4096,emit,NULL,&binding):-1;
 if(strcmp(mode,"display")==0){want_display=(rd_display *)(uintptr_t)2;errno=ERANGE;(void)rd_create_new(want_display,(rd_fbconfig)(uintptr_t)2,3,NULL,1);checked();}
 if(strcmp(mode,"thread")==0){pthread_t t;if(pthread_create(&t,NULL,foreign,NULL))return 5;(void)pthread_join(t,NULL);}
 if(strcmp(mode,"unknown")==0){errno=ERANGE;if(rd_get_proc((const unsigned char *)"glNotClassified")!=(rd_proc)buffer)args_ok=0;checked();}
 if(strcmp(mode,"mismatch")==0 || strcmp(mode,"null")==0){errno=ERANGE;rd_proc p=rd_get_proc_arb((const unsigned char *)"glBindFramebufferEXT");if(p!=(strcmp(mode,"null")==0?NULL:(rd_proc)buffer))args_ok=0;checked();}
 if(strcmp(mode,"safe")==0){errno=ERANGE;if(rd_get_proc((const unsigned char *)"glDrawArrays")!=(rd_proc)buffer)args_ok=0;checked();}
 if(strcmp(mode,"glerror")==0){errno=ERANGE;if(rd_get_error()!=0x502)args_ok=0;checked();}
 if(strcmp(mode,"invalidate")==0 || strcmp(mode,"offinvalid")==0)(void)rd_invalidate();
 if(strcmp(mode,"destroy")==0){errno=ERANGE;rd_destroy_context(want_display,ctx);checked();}
 if(bound==0)(void)pb_begin(bridge,1,1);
 for(unsigned i=0;i<2;i++){
   expected(0x8d40,8+i);
   if(strcmp(mode,"aliases")==0){errno=ERANGE;rd_proc p=rd_get_proc((const unsigned char *)"glBindFramebufferEXT");checked();errno=ERANGE;((void(*)(uint32_t,uint32_t))p)(0x8d40,8+i);}
   else rd_bind_framebuffer(0x8d40,8+i);
   checked();expected(0x8ce0,0);rd_read_buffer(0x8ce0);checked();
   if(strcmp(mode,"pbo")==0){expected(0x88eb,4);rd_bind_buffer_arb(0x88eb,4);checked();}
   if(strcmp(mode,"delete")==0){uint32_t name=99;expected(0x8ca9,99);rd_bind_framebuffer_ext(0x8ca9,99);checked();expected(1,99);rd_delete_framebuffers_ext(1,&name);checked();}
   errno=ERANGE;if(rd_get_proc((const unsigned char *)"glReadPixels")!=(rd_proc)rd_read_pixels)args_ok=0;checked();
   cpu_call call={-7,11,5,3,0x80e0,0x1401,pixels,i?0x222:0x111,0x333,4096,(uintptr_t)pixels,-1,0};errno=ERANGE;if(!rd_fixture_call(&call))regs_ok=0;checked();
 }
 if(bound==0)(void)pb_end(bridge);
 int finish=rd_finish();pb_stats stats={0};if(bound==0)pb_get_stats(bridge,&stats);rd_counts counts;rd_get_stats(&counts);
 if(channel>=0 && (fflush(stdout) || fsync(STDOUT_FILENO)))finish=-1;
 char status[4096];int status_n=snprintf(status,sizeof(status),"{\"source\":\"SYNTHETIC_TYPED_DISPATCH_ONLY\",\"original_commands\":%u,\"original_calls\":%u,\"resolver_calls\":%u,\"args_ok\":%u,\"errno_ok\":%u,\"regs_ok\":%u,\"attached\":%d,\"bound\":%d,\"delivery_error\":%u,\"events\":%" PRIu64 ",\"replayed\":%" PRIu64 ",\"error\":%u,\"captured\":%" PRIu64 ",\"attempts\":%" PRIu64 ",\"forwards\":%" PRIu64 ",\"wire_bytes\":%" PRIu64 ",\"finish\":%d,\"driver_state_proven\":false,\"runtime_admission_ready\":false}",originals,reads,resolves,args_ok,errno_ok,regs_ok,attached,bound,counts.error,counts.events,counts.replayed,stats.core.error,stats.core.captured,stats.core.attempts,stats.core.forwards+(strcmp(mode,"channel_status")==0),stats.core.data_wire_bytes,finish);
 if(status_n<0 || (size_t)status_n>=sizeof(status))return 8;
 fprintf(stderr,"%s\n",status);
 if(channel>=0 && strcmp(mode,"channel_empty")!=0){
   struct stat spool;if(fstat(STDOUT_FILENO,&spool) || !S_ISREG(spool.st_mode))return 9;
   char packet[8192];int n=snprintf(packet,sizeof(packet),"{\"schema\":\"readback-cpu-producer-ready-v1\",\"nonce\":\"%s\",\"pid\":%ld,\"code\":{\"rd_probe_store\":%" PRIuPTR ",\"rd_probe_read\":%" PRIuPTR ",\"rd_fixture_call\":%" PRIuPTR "},\"stream_nbytes\":%jd,\"status\":%s}",strcmp(mode,"channel_nonce")==0?"0000000000000000000000000000000000000000000000000000000000000000":nonce,(long)getpid()+(strcmp(mode,"channel_pid")==0),(uintptr_t)rd_probe_store+(strcmp(mode,"channel_map")==0),(uintptr_t)rd_probe_read,(uintptr_t)rd_fixture_call,(intmax_t)spool.st_size,status);
   if(n<0 || (size_t)n>=sizeof(packet) || send(channel,packet,(size_t)n,0)!=n)return 10;
   if(strcmp(mode,"channel_extra")==0 && send(channel,packet,(size_t)n,0)!=n)return 10;
   char ack;if(recv(channel,&ack,1,0)!=1 || ack!='A')return 11;
   if(strcmp(mode,"channel_tamper")==0 && (lseek(STDOUT_FILENO,0,SEEK_SET)<0 || write(STDOUT_FILENO,"X",1)!=1 || fsync(STDOUT_FILENO)))return 12;
 }
 free(scratch);free(bridge);free(cache);free(delivery);return strcmp(mode,"channel_exit")==0?3:0;
}
