/* First-party CPU originals for an installed SDK C ABI probe. No GL calls. */
#include "panda_cache_adapter.h"
#include <dlfcn.h>
#include <cstdio>
#include <cstring>
#include <cstdint>
namespace {
struct alignas(16) adapter_storage {unsigned char before[16],data[2640344],after[16];};
struct alignas(16) cache_storage {unsigned char before[16],data[2320],after[16];};
static adapter_storage A;static cache_storage C;
static unsigned used,calls,creates,reject_switch,args_ok=1,errno_ok=1,returns_ok=1;
static uint64_t trace[32][7];static uintptr_t wrappers[7],originals[7];
static void enter(uint64_t kind,uint64_t a=0,uint64_t b=0,uint64_t c=0,uint64_t d=0){
 if(calls>=32){args_ok=0;return;}trace[calls][0]=kind;trace[calls][1]=a;trace[calls][2]=b;trace[calls][3]=c;trace[calls][4]=d;trace[calls][5]=static_cast<uint64_t>(errno);++calls;if(errno!=ERANGE)errno_ok=0;
}
static void leave(uint64_t result=0){if(calls && calls<=32)trace[calls-1][6]=result;errno=EDOM;}
static void checked(){if(errno!=EDOM)errno_ok=0;}
static void *create(void *display,void *visual,void *share,int direct){
 enter(7,reinterpret_cast<uintptr_t>(display),reinterpret_cast<uintptr_t>(visual),reinterpret_cast<uintptr_t>(share),static_cast<uint32_t>(direct));if(display!=(void*)1||visual!=(void*)2||share||direct!=1)args_ok=0;++creates;void *r=(void*)(creates==2?0x2222ul:0x1111ul);leave(reinterpret_cast<uintptr_t>(r));return r;
}
static int make(void *display,unsigned long drawable,void *context){
 enter(11,reinterpret_cast<uintptr_t>(display),drawable,reinterpret_cast<uintptr_t>(context));if(display!=(void*)1||(!context && drawable)|| (context && context!=(void*)0x1111 && context!=(void*)0x2222))args_ok=0;int r=reject_switch?0:1;leave(static_cast<unsigned>(r));return r;
}
static void destroy(void *display,void *context){enter(13,reinterpret_cast<uintptr_t>(display),reinterpret_cast<uintptr_t>(context));if(display!=(void*)1 || (context!=(void*)0x1111&&context!=(void*)0x2222))args_ok=0;leave();}
static void frame(uint32_t target,uint32_t name){enter(3,target,name);if(target!=0x8d40 || name<9 || name>11)args_ok=0;leave();}
static void selector(uint32_t name){enter(4,name);if(name!=0x8ce0)args_ok=0;leave();}
static void buffer(uint32_t target,uint32_t name){enter(2,target,name);if(target!=0x88eb || (name!=42&&name!=77))args_ok=0;leave();}
static void deletion(int32_t count,const uint32_t *names){enter(6,static_cast<uint32_t>(count),reinterpret_cast<uintptr_t>(names));if(count!=1||!names||names[0]!=42)args_ok=0;leave();}
static bool guards(){for(unsigned i=0;i<16;++i)if(A.before[i]!=165||A.after[i]!=165||C.before[i]!=165||C.after[i]!=165)return false;return true;}
}
extern "C" __attribute__((visibility("default"))) int probe_run(void *handle,int mode,char *out,size_t capacity){
 if(!handle||mode<0||mode>2||!out||capacity<65536||used++)return -1;
 #define API(n) auto n##_fn=reinterpret_cast<decltype(&n)>(dlsym(handle,#n));if(!n##_fn)return -2
 API(pca_context_size);API(rc_context_size);API(pca_install);API(rc_init);API(pca_attach);API(pca_snapshot);API(pca_get_stats);API(pca_finish);API(psd_lookup_begin);API(psd_resolved);API(psd_path);API(psd_get_stats);
 #undef API
 const size_t as=pca_context_size_fn(),cs=rc_context_size_fn();if(as!=2640344||cs!=2320)return -3;
 std::memset(A.before,165,16);std::memset(A.after,165,16);std::memset(C.before,165,16);std::memset(C.after,165,16);
 const rc_config cfg={0x333,{0x1111,0x2222},256};if(pca_install_fn(A.data,sizeof(A.data),nullptr,0,256)||rc_init_fn(C.data,sizeof(C.data),&cfg))return -4;
 const char *names[]={"glXCreateContext","glXMakeCurrent","glXDestroyContext","glBindFramebuffer","glReadBuffer","glBindBufferARB","glDeleteBuffersARB"};
 void *ptrs[]={reinterpret_cast<void*>(create),reinterpret_cast<void*>(make),reinterpret_cast<void*>(destroy),reinterpret_cast<void*>(frame),reinterpret_cast<void*>(selector),reinterpret_cast<void*>(buffer),reinterpret_cast<void*>(deletion)};
 for(unsigned i=0;i<7;++i){
  alignas(psd_lookup) unsigned char raw[sizeof(psd_lookup)]={};auto l=reinterpret_cast<psd_lookup*>(raw);errno=ERANGE;psd_lookup_begin_fn(names[i],l);void *p=ptrs[i];for(unsigned origin=3;origin<=6;++origin)p=psd_path_fn(origin,p);p=psd_resolved_fn(l,p,PSD_SOURCE_RUNTIME);if(errno!=ERANGE)errno_ok=0;if(!p||p==ptrs[i])return -5;wrappers[i]=reinterpret_cast<uintptr_t>(p);originals[i]=reinterpret_cast<uintptr_t>(ptrs[i]);
 }
 auto cr=reinterpret_cast<decltype(&create)>(wrappers[0]);auto mk=reinterpret_cast<decltype(&make)>(wrappers[1]);auto de=reinterpret_cast<decltype(&destroy)>(wrappers[2]);auto fb=reinterpret_cast<decltype(&frame)>(wrappers[3]);auto rd=reinterpret_cast<decltype(&selector)>(wrappers[4]);auto bb=reinterpret_cast<decltype(&buffer)>(wrappers[5]);auto db=reinterpret_cast<decltype(&deletion)>(wrappers[6]);
 auto new_context=[&](){errno=ERANGE;void *r=cr((void*)1,(void*)2,nullptr,1);checked();if(r!=(void*)(creates==2?0x2222ul:0x1111ul))returns_ok=0;return r;};
 auto current=[&](unsigned long draw,void *ctx,int expected=1){errno=ERANGE;int r=mk((void*)1,draw,ctx);checked();if(r!=expected)returns_ok=0;};
 auto fbo=[&](uint32_t n){errno=ERANGE;fb(0x8d40,n);checked();errno=ERANGE;rd(0x8ce0);checked();};
 auto drop=[&](void *ctx){errno=ERANGE;de((void*)1,ctx);checked();};
 auto pack=[&](uint32_t n){errno=ERANGE;bb(0x88eb,n);checked();};
 unsigned packs[5]={},life[6]={};uint64_t tags[5]={};unsigned index=0;
 auto snapshot=[&](){rc_state_view s={};if(index>=5||pca_snapshot_fn(A.data,&s))return false;packs[index]=s.pack_buffer;tags[index]=s.context_tag;++index;return true;};
 void *one=new_context();current(7,one);fbo(9);if(pca_attach_fn(A.data,C.data))return -6;
 pack(42);if(!snapshot())return -7;uint32_t deleted=42;errno=ERANGE;db(1,&deleted);checked();if(!snapshot())return -8;
 void *two=new_context();current(8,two);fbo(10);pack(77);if(!snapshot())return -9;
 unsigned failed_preserved=0;if(mode==1){reject_switch=1;current(7,one,0);reject_switch=0;rc_state_view s={};failed_preserved=pca_snapshot_fn(A.data,&s)==0&&s.pack_buffer==77&&s.context_tag==tags[2];}
 current(7,one);if(!snapshot())return -10;drop(one);pca_counts counts={};if(pca_get_stats_fn(A.data,&counts))return -11;life[0]=counts.live;life[1]=counts.pending;
 current(8,two);if(pca_get_stats_fn(A.data,&counts))return -12;life[2]=counts.live;life[3]=counts.pending;drop(two);current(0,nullptr);
 one=new_context();current(9,one);fbo(11);if(!snapshot())return -13;drop(one);current(0,nullptr);
 if(pca_get_stats_fn(A.data,&counts))return -14;life[4]=counts.created;life[5]=counts.live;int finish=pca_finish_fn(A.data,mode==2?1:0);if(pca_get_stats_fn(A.data,&counts))return -15;
 bool guard=guards();int offset=std::snprintf(out,capacity,"{\"schema\":\"panda-sdk-dispatch-probe-v1\",\"mode\":%d,\"sizes\":[%zu,%zu],\"original_calls\":%u,\"args_ok\":%u,\"errno_ok\":%u,\"returns_ok\":%u,\"guards_ok\":%u,\"pack_snapshots\":[%u,%u,%u,%u,%u],\"tags\":[%llu,%llu,%llu,%llu,%llu],\"lifecycle\":[%u,%u,%u,%u,%u,%u],\"failed_switch_preserved\":%u,\"finish\":%d,\"adapter_error\":%u,\"source_error\":%u,\"source_closed\":%u,\"forwarded\":%llu,\"resolutions\":%llu,\"paths\":%llu,\"events\":%llu,\"bootstrap\":%u,\"replayed\":%llu,\"applied\":%llu,\"pbo_resets\":%llu,\"live\":%u,\"pending\":%u,\"native_admitted\":false,\"driver_state_qualified\":false,\"wrappers\":[",mode,as,cs,calls,args_ok,errno_ok,returns_ok,guard?1u:0u,packs[0],packs[1],packs[2],packs[3],packs[4],(unsigned long long)tags[0],(unsigned long long)tags[1],(unsigned long long)tags[2],(unsigned long long)tags[3],(unsigned long long)tags[4],life[0],life[1],life[2],life[3],life[4],life[5],failed_preserved,finish,counts.error,counts.source.error,counts.source.closed,(unsigned long long)counts.source.forwarded,(unsigned long long)counts.source.resolutions,(unsigned long long)counts.source.paths,(unsigned long long)counts.events,counts.bootstrap,(unsigned long long)counts.replayed,(unsigned long long)counts.applied,(unsigned long long)counts.pbo_resets,counts.live,counts.pending);
 auto add=[&](const char *fmt,unsigned long long v){if(offset<0 || static_cast<size_t>(offset)>=capacity)return false;int n=std::snprintf(out+offset,capacity-static_cast<size_t>(offset),fmt,v);if(n<0||static_cast<size_t>(n)>=capacity-static_cast<size_t>(offset))return false;offset+=n;return true;};
 for(unsigned i=0;i<7;++i)if(!add(i?",%llu":"%llu",wrappers[i]))return -16;if(!add("],\"originals\":[",0))return -16;
 for(unsigned i=0;i<7;++i)if(!add(i?",%llu":"%llu",originals[i]))return -16;if(!add("],\"trace\":[",0))return -16;
 for(unsigned i=0;i<calls && i<32;++i){if(!add(i?",[":"[",0))return -16;for(unsigned j=0;j<7;++j)if(!add(j?",%llu":"%llu",trace[i][j]))return -16;if(!add("]",0))return -16;}
 if(!add("]}",0))return -16;
 return finish || !guard || !args_ok || !errno_ok || !returns_ok?-17:0;
}
