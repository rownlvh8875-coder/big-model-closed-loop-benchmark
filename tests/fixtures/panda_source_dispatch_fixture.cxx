/* CPU originals only: no GL/Panda headers, linkage or loading. */
#include "panda_source_dispatch.h"
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <pthread.h>
struct cpu_call {int32_t x,y,w,h;uint32_t f,t;void *p;uintptr_t tex,gsg,capacity,image;int32_t z,view;};
extern "C" int psd_fixture_call(const cpu_call *);
static const char *mode;
static unsigned originals,lookups,read_calls,observer_calls,args_ok=1,errno_ok=1,regs_ok=1,depth,snapshot_ok=1,normalized_ok=1;
static unsigned char pixels[128];
static psd_event observed[64];
static void check_in(){++originals;if(errno!=ERANGE)args_ok=0;}
static void check_out(){if(std::strcmp(mode,"preserve"))errno=EDOM;}
static void checked(){if(errno!=(std::strcmp(mode,"preserve")?EDOM:ERANGE))errno_ok=0;}
static void store(uint32_t a,int32_t b){check_in();if(a!=0xd05 || b!=(std::strcmp(mode,"normalize")?1:3))args_ok=0;
 if(!std::strcmp(mode,"reentry") && !depth){depth=1;psd::call<PSD_PIXEL_STORE>(store,a,b);depth=0;}check_out();}
static void frame(uint32_t a,uint32_t b){check_in();if(a!=0x8d40 || b!=7)args_ok=0;check_out();}
static void frame_ext(uint32_t a,uint32_t b){check_in();if(a!=0x8d40 || b!=7)args_ok=0;check_out();}
static void *legacy(void *d,void *v,void *share,int direct){check_in();if(d!=(void *)1 || v!=(void *)2 || share || direct!=1)args_ok=0;check_out();return !std::strcmp(mode,"createfail")?nullptr:(void *)0x111;}
static void remove_buffers(int32_t n,const uint32_t *names){check_in();if(n!=(std::strcmp(mode,"delete_bad")?1:33) || names[0]!=7)args_ok=0;const_cast<uint32_t *>(names)[0]=999;check_out();}
static uint32_t get_error(){check_in();check_out();return 0x502;}
static void original_read(int32_t x,int32_t y,int32_t w,int32_t h,uint32_t f,uint32_t t,void *p){
 ++read_calls;if(x!=-7 || y!=11 || w!=5 || h!=3 || f!=0x1907 || t!=0x1401 || p!=pixels || errno!=ERANGE)args_ok=0;check_out();}
static int observer(const psd_event *event,void *user){
 if(user!=observed)args_ok=0;if(observer_calls<64)observed[observer_calls]=*event;++observer_calls;
 if(event->kind==PSD_DELETE_BUFFER && (event->delete_count!=1 || event->names[0]!=7))snapshot_ok=0;
 if(event->kind==PSD_PIXEL_STORE && event->args[1]!=(std::strcmp(mode,"normalize")?1u:3u))normalized_ok=0;
 if(!std::strcmp(mode,"callback_reentry") && !depth){depth=1;errno=ERANGE;psd::call<PSD_PIXEL_STORE>(store,0xd05u,1);depth=0;}
 errno=EIO;return !std::strcmp(mode,"callbackfail")?-1:0;
}
static void *resolver(char *name){++lookups;if(errno!=ERANGE)args_ok=0;void *p=(void *)frame;
 if(!std::strcmp(name,"glBindFramebufferEXT"))p=!std::strcmp(mode,"null")?nullptr:(void *)frame_ext;
 if(!std::strcmp(mode,"mutate_name"))std::strcpy(name,"glNotKnown");
 check_out();return p;
}
static void *foreign(void *){errno=ERANGE;psd::call<PSD_PIXEL_STORE>(store,0xd05u,1);checked();return nullptr;}
int main(int argc,char **argv){
 mode=argc>1?argv[1]:"basic";
 if(psd_bind_read(original_read))return 2;
 const char *safe[]={!std::strcmp(mode,"unsafe_config")?"glPopAttrib":"glDrawArrays"};
 if(std::strcmp(mode,"off") && psd_configure(observer,observed,safe,1,!std::strcmp(mode,"cap")?1:10000))return 3;
 errno=ERANGE;void *ctx=psd::call<PSD_CREATE_LEGACY>(legacy,(void *)1,(void *)2,(void *)nullptr,1);checked();
 if(ctx!=(!std::strcmp(mode,"createfail")?nullptr:(void *)0x111))args_ok=0;
 int early=0;if(!std::strcmp(mode,"closed"))early=psd_finish();
 errno=ERANGE;
 if(!std::strcmp(mode,"normalize")){volatile uint64_t wide=(uint64_t(1)<<32)+3;psd::call<PSD_PIXEL_STORE>(store,0xd05ull,wide);}
 else psd::call<PSD_PIXEL_STORE>(store,0xd05u,1);
 checked();
 if(!std::strcmp(mode,"badshape")){psd_token bad;psd_before(PSD_DELETE_BUFFER,nullptr,0,&bad);psd_after(&bad,0);}
 if(!std::strcmp(mode,"aliases") || !std::strcmp(mode,"null") || !std::strcmp(mode,"mismatch") ||
    !std::strcmp(mode,"unknown") || !std::strcmp(mode,"safe") || !std::strcmp(mode,"mutate_name") || !std::strcmp(mode,"paths")){
   char name[64];std::strcpy(name,!std::strcmp(mode,"unknown")?"glNotKnown":!std::strcmp(mode,"safe")?"glDrawArrays":"glBindFramebufferEXT");
   errno=ERANGE;psd_lookup request(name);void *p=resolver(name);
   if(!std::strcmp(mode,"paths"))p=psd_path(PSD_PATH_GLX_PRIVATE,p);
   void *wrapped=psd_resolved(&request,p,PSD_SOURCE_RUNTIME);checked();
   if(!std::strcmp(mode,"null")){if(wrapped)args_ok=0;}
   else if(!std::strcmp(mode,"unknown") || !std::strcmp(mode,"safe")){if(wrapped!=p)args_ok=0;}
   else {if(wrapped==p)args_ok=0;errno=ERANGE;((void(*)(uint32_t,uint32_t))wrapped)(0x8d40,7);checked();}
   if(!std::strcmp(mode,"aliases")){
     std::strcpy(name,"glBindFramebuffer");errno=ERANGE;psd_lookup core(name);p=resolver(name);wrapped=psd_resolved(&core,p,PSD_SOURCE_COMPILED);checked();
     if(wrapped==p)args_ok=0;errno=ERANGE;((void(*)(uint32_t,uint32_t))wrapped)(0x8d40,7);checked();
   }
   if(!std::strcmp(mode,"mismatch")){
     std::strcpy(name,"glBindFramebufferEXT");errno=ERANGE;psd_lookup next(name);++lookups;check_out();
     wrapped=psd_resolved(&next,(void *)frame,PSD_SOURCE_RUNTIME);checked();if(wrapped!=(void *)frame)args_ok=0;
     errno=ERANGE;((void(*)(uint32_t,uint32_t))wrapped)(0x8d40,7);checked();
   }
 }
 if(!std::strcmp(mode,"delete") || !std::strcmp(mode,"delete_bad")){
   uint32_t names[33]={7};errno=ERANGE;psd::call<PSD_DELETE_BUFFER>(remove_buffers,!std::strcmp(mode,"delete_bad")?33:1,(const uint32_t *)names);checked();
   if(names[0]!=999)args_ok=0;
 }
 if(!std::strcmp(mode,"glerror")){errno=ERANGE;if(psd::call<PSD_GET_ERROR>(get_error)!=0x502)args_ok=0;checked();}
 if(!std::strcmp(mode,"thread")){pthread_t t;if(pthread_create(&t,nullptr,foreign,nullptr))return 4;(void)pthread_join(t,nullptr);}
 cpu_call call={-7,11,5,3,0x1907,0x1401,pixels,0x111,0x333,128,(uintptr_t)pixels,-1,0};
 errno=ERANGE;if(!psd_fixture_call(&call))regs_ok=0;checked();
 int finish=!std::strcmp(mode,"closed")?early:psd_finish();
 psd_counts stats={};if(psd_get_stats(&stats))return 5;
 std::printf("{\"kind\":\"CPU_SOURCE_DISPATCH_ONLY\",\"originals\":%u,\"lookups\":%u,\"reads\":%u,\"observer_calls\":%u,\"args_ok\":%u,\"errno_ok\":%u,\"regs_ok\":%u,\"snapshot_ok\":%u,\"normalized_ok\":%u,\"finish\":%d,\"error\":%u,\"events\":%llu,\"forwarded\":%llu,\"resolutions\":%llu,\"paths\":%llu,\"native_admitted\":false}\n",
 originals,lookups,read_calls,observer_calls,args_ok,errno_ok,regs_ok,snapshot_ok,normalized_ok,finish,stats.error,(unsigned long long)stats.events,(unsigned long long)stats.forwarded,(unsigned long long)stats.resolutions,(unsigned long long)stats.paths);
 return 0;
}
