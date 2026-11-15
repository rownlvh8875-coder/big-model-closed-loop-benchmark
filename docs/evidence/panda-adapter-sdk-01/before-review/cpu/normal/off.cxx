#include "panda_cache_adapter.h"
#include <cstdio>
struct cpu_call {int32_t x,y,w,h;uint32_t f,t;void *p;uintptr_t tex,gsg,capacity,image;int32_t z,view;};
extern "C" int pca_fixture_call(const cpu_call*);
static unsigned calls,ok=1;static unsigned char pixels[128];
static void original(int32_t x,int32_t y,int32_t w,int32_t h,uint32_t f,uint32_t t,void*p){++calls;if(x!=-7||y!=11||w!=5||h!=3||f!=0x1907||t!=0x1401||p!=pixels||errno!=ERANGE)ok=0;errno=EDOM;}
int main(){psd_counts s={};if(psd_get_stats(&s)||s.configured||psd_bind_read(original))return 1;cpu_call a={-7,11,5,3,0x1907,0x1401,pixels,0x1111,0x333,128,(uintptr_t)pixels,-1,0};errno=ERANGE;int regs=pca_fixture_call(&a);if(psd_get_stats(&s)||s.events||s.configured||calls!=1||!ok||!regs||errno!=EDOM||psd_source_idle(nullptr,nullptr)==0)return 2;std::printf("CPU_DEFAULT_OFF_ORIGINAL_ONLY\n");}
