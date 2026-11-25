/* Forward the frozen SDK's draw entry points and notify a scoped observation callback. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

typedef void (*tap_fn)(unsigned, int, const char *, unsigned, int, int);
static _Thread_local tap_fn tap;
static _Thread_local unsigned ordinal;
static _Thread_local int busy;
static _Thread_local unsigned faults;
static unsigned unrecognized_draws;
static char last_unrecognized[64];

int wide_draw_begin(tap_fn callback) {
    if (tap || !callback) return -1;
    ordinal = 0;
    tap = callback;
    return 0;
}
int wide_draw_end(unsigned *draws, unsigned *missing, char *name) {
    *draws = ordinal;
    *missing = unrecognized_draws + faults;
    memcpy(name,last_unrecognized,64);
    tap = NULL;
    return busy ? -1 : 0;
}
static unsigned before(const char *name, unsigned mode, int count, int instances) {
    if (!tap || busy) return 0;
    busy = 1;
    unsigned number = ++ordinal;
    tap(number,0,name,mode,count,instances);
    busy = 0;
    return number;
}
static void after(unsigned number,const char *name,unsigned mode,int count,int instances) {
    if (!number || !tap) return;
    busy = 1;
    tap(number,1,name,mode,count,instances);
    busy = 0;
}

struct lookup {char name[64];uint32_t active;};
typedef void (*begin_fn)(const char *,struct lookup *);
typedef void *(*resolved_fn)(const struct lookup *,void *,uint32_t);
static begin_fn real_begin;
static resolved_fn real_resolved;
static void initialize_sdk(void) {
    if (real_begin && real_resolved) return;
    void *sdk=dlopen("/opt/venv/lib/python3.11/site-packages/panda3d/libpandagl.so",
                     RTLD_NOW|RTLD_NOLOAD);
    if (sdk) {
        real_begin=(begin_fn)dlsym(sdk,"psd_lookup_begin");
        real_resolved=(resolved_fn)dlsym(sdk,"psd_resolved");
    }
    if (!real_begin || !real_resolved) _exit(125);
}
struct binding {const struct lookup *request;char name[64];};
static _Thread_local struct binding pending[16];
static _Thread_local unsigned pending_count;
void psd_lookup_begin(const char *name,struct lookup *request) {
    int incoming=errno;
    initialize_sdk();
    errno=incoming;
    real_begin(name,request);
    int returned=errno;
    if (pending_count<16 && name && strnlen(name,64)<64) {
        pending[pending_count].request=request;
        strcpy(pending[pending_count++].name,name);
    } else {
        faults++;
    }
    errno=returned;
}
static void *route(const char *,void *);
void *psd_resolved(const struct lookup *request,void *value,uint32_t origin) {
    int incoming=errno;
    initialize_sdk();
    errno=incoming;
    void *result=real_resolved(request,value,origin);
    int returned=errno;
    unsigned index=pending_count;
    while(index && pending[index-1].request!=request) index--;
    if(index) {
        char name[64];
        strcpy(name,pending[index-1].name);
        memmove(pending+index-1,pending+index,(pending_count-index)*sizeof(*pending));
        pending_count--;
        if (result) result=route(name,result);
    } else {
        faults++;
    }
    errno=returned;
    return result;
}
#define ARR(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,int first,int n){int incoming=errno;unsigned ticket=before(NAME,m,n,1);errno=incoming;((void(*)(unsigned,int,int))real_##SLOT)(m,first,n);int returned=errno;after(ticket,NAME,m,n,1);errno=returned;}
#define ELEM(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,int n,unsigned t,const void *p){int incoming=errno;unsigned ticket=before(NAME,m,n,1);errno=incoming;((void(*)(unsigned,int,unsigned,const void*))real_##SLOT)(m,n,t,p);int returned=errno;after(ticket,NAME,m,n,1);errno=returned;}
#define RANGE(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,unsigned a,unsigned b,int n,unsigned t,const void *p){int incoming=errno;unsigned ticket=before(NAME,m,n,1);errno=incoming;((void(*)(unsigned,unsigned,unsigned,int,unsigned,const void*))real_##SLOT)(m,a,b,n,t,p);int returned=errno;after(ticket,NAME,m,n,1);errno=returned;}
#define ARRI(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,int first,int n,int k){int incoming=errno;unsigned ticket=before(NAME,m,n,k);errno=incoming;((void(*)(unsigned,int,int,int))real_##SLOT)(m,first,n,k);int returned=errno;after(ticket,NAME,m,n,k);errno=returned;}
#define ELEMI(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,int n,unsigned t,const void *p,int k){int incoming=errno;unsigned ticket=before(NAME,m,n,k);errno=incoming;((void(*)(unsigned,int,unsigned,const void*,int))real_##SLOT)(m,n,t,p,k);int returned=errno;after(ticket,NAME,m,n,k);errno=returned;}
#define ARRD(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,const void *p){int incoming=errno;unsigned ticket=before(NAME,m,-1,-1);errno=incoming;((void(*)(unsigned,const void*))real_##SLOT)(m,p);int returned=errno;after(ticket,NAME,m,-1,-1);errno=returned;}
#define ELEMD(SLOT,NAME) static void *real_##SLOT;static void wrap_##SLOT(unsigned m,unsigned t,const void *p){int incoming=errno;unsigned ticket=before(NAME,m,-1,-1);errno=incoming;((void(*)(unsigned,unsigned,const void*))real_##SLOT)(m,t,p);int returned=errno;after(ticket,NAME,m,-1,-1);errno=returned;}
#define ROUTES(XA,XE,XR,XAI,XEI,XAD,XED) XA(a,"glDrawArrays") XE(e,"glDrawElements") XR(r,"glDrawRangeElements") XR(re,"glDrawRangeElementsEXT") XAI(ai,"glDrawArraysInstanced") XAI(aia,"glDrawArraysInstancedARB") XAI(aie,"glDrawArraysInstancedEXT") XAI(ain,"glDrawArraysInstancedNV") XAI(aig,"glDrawArraysInstancedANGLE") XEI(ei,"glDrawElementsInstanced") XEI(eia,"glDrawElementsInstancedARB") XEI(eie,"glDrawElementsInstancedEXT") XEI(ein,"glDrawElementsInstancedNV") XEI(eig,"glDrawElementsInstancedANGLE") XAD(ad,"glDrawArraysIndirect") XED(ed,"glDrawElementsIndirect")
ROUTES(ARR,ELEM,RANGE,ARRI,ELEMI,ARRD,ELEMD)
#define MATCH(SLOT,NAME) \
    if(!strcmp(name,NAME)){ \
        if(value==(void*)wrap_##SLOT)return value; \
        if(real_##SLOT && real_##SLOT!=value){faults++;return value;} \
        real_##SLOT=value;return (void*)wrap_##SLOT; \
    }
static void *route(const char *name,void *value){
    ROUTES(MATCH,MATCH,MATCH,MATCH,MATCH,MATCH,MATCH)
    if (!strncmp(name,"glDrawArrays",12)||!strncmp(name,"glDrawElements",14)||
        !strncmp(name,"glDrawRangeElements",19)||!strncmp(name,"glMultiDraw",11)) {
        unrecognized_draws++;
        strcpy(last_unrecognized,name);
    }
    return value;
}
static void *symbol(const char *name){
    static void *lib;
    if(!lib)lib=dlopen("libGL.so.1",RTLD_NOW|RTLD_LOCAL);
    return lib?dlsym(lib,name):NULL;
}
void glDrawArrays(unsigned m,int first,int n){
    int saved=errno;
    if(!real_a)real_a=symbol("glDrawArrays");
    if(!real_a)_exit(125);
    errno=saved;
    wrap_a(m,first,n);
}
void glDrawElements(unsigned m,int n,unsigned t,const void *p){
    int saved=errno;
    if(!real_e)real_e=symbol("glDrawElements");
    if(!real_e)_exit(125);
    errno=saved;
    wrap_e(m,n,t,p);
}
