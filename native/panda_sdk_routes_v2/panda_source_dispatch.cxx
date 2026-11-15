#include "panda_source_dispatch.h"
#include <cstring>
#include <pthread.h>
#ifdef PSD_PANDA_BUILD
#include <GL/glx.h>
#include <GL/glxext.h>
#endif
static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"Linux amd64 ABI");
namespace {
struct state {
 uint32_t configured,closed,error,busy,cap,safe_count;pthread_t owner;psd_observer observer;void *user;const psd_lookup *lookup;
 uint64_t forwarded,resolutions,paths,events;char safe[256][64];void *slots[64];
};
state S={};
enum {E_THREAD=1,E_REENTRY,E_LIMIT,E_INPUT,E_CALLBACK,E_ORIGINAL_ERROR,E_RESOLVER,E_CLOSED};
uint32_t load(const uint32_t *p){return __atomic_load_n(p,__ATOMIC_ACQUIRE);}
bool owner(){return pthread_equal(S.owner,pthread_self())!=0;}
void fail(uint32_t code){uint32_t zero=0;__atomic_compare_exchange_n(&S.error,&zero,code,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE);}
bool active(){return load(&S.configured) && !load(&S.closed);}
bool name_copy(const char *name,char out[64]){
 if(!name)return false;
 for(unsigned i=0;i<64;++i){out[i]=name[i];if(!name[i])return i>2 && name[0]=='g' && name[1]=='l';}
 return false;
}
bool unsafe(const char *name){
 const char *prefix[]={"glPixelStore","glBindBuffer","glDeleteBuffers","glBindFramebuffer","glDeleteFramebuffers","glReadBuffer",
 "glNamedFramebufferReadBuffer","glFramebufferReadBuffer","glPushClientAttrib","glPopClientAttrib","glPushAttrib","glPopAttrib",
 "glClientAttribDefault","glXCreate","glXMake","glXDestroy","glXCopyContext","glReadPixels","glGetError"};
 for(unsigned i=0;i<sizeof(prefix)/sizeof(prefix[0]);++i)if(!std::strncmp(name,prefix[i],std::strlen(prefix[i])))return true;
 return false;
}
}
#ifndef PSD_ORIGINAL_READ
#define PSD_ORIGINAL_READ nullptr
#endif
extern "C" {__attribute__((visibility("hidden"))) psd_read_fn psd_read_target=PSD_ORIGINAL_READ;}
asm(".text\n.globl psd_read_pixels\n.hidden psd_read_pixels\n.type psd_read_pixels,@function\n"
    "psd_read_pixels:\n jmp *psd_read_target(%rip)\n.size psd_read_pixels,.-psd_read_pixels\n.section .note.GNU-stack,\"\",@progbits\n.previous\n");
extern "C" int psd_bind_read(psd_read_fn original){
 if(!original)return -1;
 psd_read_fn empty=nullptr;
 return __atomic_compare_exchange_n(&psd_read_target,&empty,original,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)?0:-1;
}
extern "C" int psd_configure(psd_observer observer,void *user,const char *const *safe,size_t count,uint32_t cap){
 if(load(&S.configured) || !observer || count>256 || (count && !safe) || !cap || cap>10000)return -1;
 for(size_t i=0;i<count;++i){
  if(!name_copy(safe[i],S.safe[i]) || unsafe(S.safe[i]))return -1;
  for(size_t j=0;j<i;++j)if(!std::strcmp(S.safe[j],S.safe[i]))return -1;
 }
 S.observer=observer;S.user=user;S.cap=cap;S.safe_count=(uint32_t)count;S.owner=pthread_self();
 __atomic_store_n(&S.configured,1u,__ATOMIC_RELEASE);return 0;
}
extern "C" void psd_before(uint32_t kind,const uint64_t *args,size_t argc,psd_token *token){
 int saved_errno=errno;*token=psd_token{};
 if(!active()){errno=saved_errno;return;}
 if(kind>=PSD_PIXEL_STORE && kind<=PSD_DESTROY_DRAWABLE)__atomic_fetch_add(&S.forwarded,1u,__ATOMIC_RELAXED);
 else if(kind==PSD_LOOKUP)__atomic_fetch_add(&S.resolutions,1u,__ATOMIC_RELAXED);
 else if(kind==PSD_RESOLVER_PATH)__atomic_fetch_add(&S.paths,1u,__ATOMIC_RELAXED);
 else {fail(E_INPUT);errno=saved_errno;return;}
 if(!owner()){fail(E_THREAD);errno=saved_errno;return;}
 if(S.busy || (S.lookup && kind!=PSD_RESOLVER_PATH)){fail(E_REENTRY);errno=saved_errno;return;}
 if(load(&S.error)){errno=saved_errno;return;}
 if(argc>5 || (argc && !args)){fail(E_INPUT);errno=saved_errno;return;}
 const unsigned arities[]={0,2,2,2,1,2,2,4,5,5,5,3,4,2,0,3,3,4,5,2};
 unsigned expected=kind<=PSD_DESTROY_DRAWABLE?arities[kind]:(kind==PSD_LOOKUP?0u:1u);
 if(argc!=expected){fail(E_INPUT);errno=saved_errno;return;}
 if(S.events>=S.cap){fail(E_LIMIT);errno=saved_errno;return;}
 S.busy=1;token->active=1;token->event.kind=kind;token->event.argc=(uint32_t)argc;
 for(size_t i=0;i<argc;++i)token->event.args[i]=args[i];
 if(kind==PSD_DELETE_BUFFER || kind==PSD_DELETE_FRAMEBUFFER){
  uint32_t bits=(uint32_t)args[0];int32_t count;std::memcpy(&count,&bits,4);
  if(argc!=2 || count<0 || count>32 || (count && !args[1])){fail(E_INPUT);S.busy=0;token->active=0;}
  else {token->event.delete_count=(uint32_t)count;if(count)std::memcpy(token->event.names,(const void *)(uintptr_t)args[1],(size_t)count*4);}
 }
 errno=saved_errno;
}
extern "C" void psd_after(psd_token *token,uint64_t returned){
 int saved_errno=errno;
 if(!token->active){errno=saved_errno;return;}
 if(!load(&S.error)){
  token->event.returned=returned;token->event.sequence=++S.events;
  if(S.observer(&token->event,S.user))fail(E_CALLBACK);
  if(token->event.kind==PSD_GET_ERROR && returned)fail(E_ORIGINAL_ERROR);
 }
 S.busy=0;token->active=0;errno=saved_errno;
}
extern "C" void psd_lookup_begin(const char *name,psd_lookup *request){
 int saved_errno=errno;std::memset(request->name,0,sizeof(request->name));request->active=0;
 if(active()){
  if(!owner())fail(E_THREAD);
  else if(S.busy || S.lookup)fail(E_REENTRY);
  else if(!load(&S.error)){if(name_copy(name,request->name)){request->active=1;S.lookup=request;}else fail(E_INPUT);}
 }
 errno=saved_errno;
}
#ifndef PSD_PANDA_BUILD
struct _XDisplay;
struct __GLXFBConfigRec;
#endif
namespace {
struct _XDisplay;
struct context;
struct fbconfig;
typedef void(*store_fn)(uint32_t,int32_t);
typedef void(*pair_fn)(uint32_t,uint32_t);
typedef void(*read_fn)(uint32_t);
typedef void(*delete_fn)(int32_t,const uint32_t *);
#ifdef PSD_PANDA_BUILD
typedef decltype(&glXCreateContext) legacy_fn;
typedef decltype(&glXCreateNewContext) new_fn;
typedef PFNGLXCREATECONTEXTATTRIBSARBPROC attrib_fn;
typedef PFNGLXCREATECONTEXTWITHCONFIGSGIXPROC sgix_fn;
typedef decltype(&glXMakeCurrent) current_fn;
typedef decltype(&glXMakeContextCurrent) both_fn;
typedef decltype(&glXDestroyContext) destroy_fn;
typedef PFNGLBINDBUFFERBASEPROC buffer_base_fn;
typedef PFNGLXCREATEPBUFFERPROC create_pbuffer_fn;
typedef PFNGLXCREATEPIXMAPPROC create_pixmap_fn;
typedef PFNGLXCREATEGLXPBUFFERSGIXPROC create_sgix_pbuffer_fn;
typedef PFNGLXCREATEGLXPIXMAPWITHCONFIGSGIXPROC create_sgix_pixmap_fn;
typedef PFNGLXDESTROYPBUFFERPROC destroy_pbuffer_fn;
typedef PFNGLXDESTROYGLXPBUFFERSGIXPROC destroy_sgix_pbuffer_fn;
#else
typedef context *(*new_fn)(_XDisplay *,fbconfig *,int,context *,int);
typedef context *(*attrib_fn)(_XDisplay *,fbconfig *,context *,int,const int *);
typedef new_fn sgix_fn;
typedef context *(*legacy_fn)(_XDisplay *,void *,context *,int);
typedef int(*current_fn)(_XDisplay *,unsigned long,context *);
typedef int(*both_fn)(_XDisplay *,unsigned long,unsigned long,context *);
typedef void(*destroy_fn)(_XDisplay *,context *);
typedef void(*buffer_base_fn)(uint32_t,uint32_t,uint32_t);
typedef unsigned long(*create_pbuffer_fn)(::_XDisplay *,::__GLXFBConfigRec *,const int *);
typedef unsigned long(*create_pixmap_fn)(::_XDisplay *,::__GLXFBConfigRec *,unsigned long,const int *);
typedef unsigned long(*create_sgix_pbuffer_fn)(::_XDisplay *,::__GLXFBConfigRec *,unsigned int,unsigned int,int *);
typedef unsigned long(*create_sgix_pixmap_fn)(::_XDisplay *,::__GLXFBConfigRec *,unsigned long);
typedef void(*destroy_pbuffer_fn)(::_XDisplay *,unsigned long);
typedef destroy_pbuffer_fn destroy_sgix_pbuffer_fn;
#endif
typedef uint32_t(*error_fn)();
template<unsigned I,uint32_t K,class F> struct route;
template<unsigned I,uint32_t K,class R,class... A> struct route<I,K,R(*)(A...)>{
 static R invoke(A... args){R(*original)(A...)=reinterpret_cast<R(*)(A...)>(__atomic_load_n(&S.slots[I],__ATOMIC_ACQUIRE));return psd::call<K>(original,args...);}
};
struct entry {const char *name;unsigned slot;void *wrapper;};
}
extern "C" void *psd_resolved(const psd_lookup *request,void *value,uint32_t origin){
 int saved_errno=errno;
 if(!request->active || !active()){errno=saved_errno;return value;}
 if(!owner()){fail(E_THREAD);errno=saved_errno;return value;}
 if(S.lookup!=request){fail(E_REENTRY);errno=saved_errno;return value;}
 S.lookup=nullptr;
 psd_token token;psd_before(PSD_LOOKUP,nullptr,0,&token);token.event.origin=origin;
 if(token.active)std::memcpy(token.event.name,request->name,64);
 psd_after(&token,(uintptr_t)value);
 if(load(&S.error)){errno=saved_errno;return value;}
 if(origin!=PSD_SOURCE_COMPILED && origin!=PSD_SOURCE_RUNTIME){fail(E_INPUT);errno=saved_errno;return value;}
 if(!std::strcmp(request->name,"glReadPixels")){
  if(value && value!=(void *)__atomic_load_n(&psd_read_target,__ATOMIC_ACQUIRE)){fail(E_RESOLVER);errno=saved_errno;return value;}
  errno=saved_errno;return value?(void *)psd_read_pixels:nullptr;
 }
#define PSD_ROUTE(N,I,K,T) {N,I,(void *)&route<I,K,T>::invoke}
 const entry entries[]={
  PSD_ROUTE("glPixelStorei",0,PSD_PIXEL_STORE,store_fn),
  PSD_ROUTE("glBindBuffer",1,PSD_BIND_BUFFER,pair_fn),PSD_ROUTE("glBindBufferARB",2,PSD_BIND_BUFFER,pair_fn),
  PSD_ROUTE("glBindFramebuffer",3,PSD_BIND_FRAMEBUFFER,pair_fn),PSD_ROUTE("glBindFramebufferEXT",4,PSD_BIND_FRAMEBUFFER,pair_fn),PSD_ROUTE("glBindFramebufferOES",5,PSD_BIND_FRAMEBUFFER,pair_fn),
  PSD_ROUTE("glReadBuffer",6,PSD_READ_BUFFER,read_fn),PSD_ROUTE("glReadBufferNV",7,PSD_READ_BUFFER,read_fn),
  PSD_ROUTE("glDeleteFramebuffers",8,PSD_DELETE_FRAMEBUFFER,delete_fn),PSD_ROUTE("glDeleteFramebuffersEXT",9,PSD_DELETE_FRAMEBUFFER,delete_fn),PSD_ROUTE("glDeleteFramebuffersOES",10,PSD_DELETE_FRAMEBUFFER,delete_fn),
  PSD_ROUTE("glDeleteBuffers",11,PSD_DELETE_BUFFER,delete_fn),PSD_ROUTE("glDeleteBuffersARB",12,PSD_DELETE_BUFFER,delete_fn),
  PSD_ROUTE("glXCreateContext",13,PSD_CREATE_LEGACY,legacy_fn),PSD_ROUTE("glXCreateNewContext",14,PSD_CREATE_NEW,new_fn),
  PSD_ROUTE("glXCreateContextAttribsARB",15,PSD_CREATE_ATTRIBS,attrib_fn),PSD_ROUTE("glXCreateContextWithConfigSGIX",16,PSD_CREATE_SGIX,sgix_fn),
  PSD_ROUTE("glXMakeCurrent",17,PSD_MAKE_CURRENT,current_fn),PSD_ROUTE("glXMakeContextCurrent",18,PSD_MAKE_CONTEXT_CURRENT,both_fn),
  PSD_ROUTE("glXDestroyContext",19,PSD_DESTROY_CONTEXT,destroy_fn),PSD_ROUTE("glGetError",20,PSD_GET_ERROR,error_fn),
  PSD_ROUTE("glBindBufferBase",21,PSD_BIND_BUFFER_BASE,buffer_base_fn),
  PSD_ROUTE("glXCreatePbuffer",22,PSD_CREATE_DRAWABLE3,create_pbuffer_fn),
  PSD_ROUTE("glXCreatePixmap",23,PSD_CREATE_DRAWABLE4,create_pixmap_fn),
  PSD_ROUTE("glXCreateGLXPbufferSGIX",24,PSD_CREATE_DRAWABLE5,create_sgix_pbuffer_fn),
  PSD_ROUTE("glXCreateGLXPixmapWithConfigSGIX",25,PSD_CREATE_DRAWABLE3,create_sgix_pixmap_fn),
  PSD_ROUTE("glXDestroyPbuffer",26,PSD_DESTROY_DRAWABLE,destroy_pbuffer_fn),
  PSD_ROUTE("glXDestroyGLXPbufferSGIX",27,PSD_DESTROY_DRAWABLE,destroy_sgix_pbuffer_fn)
 };
#undef PSD_ROUTE
 for(unsigned i=0;i<sizeof(entries)/sizeof(entries[0]);++i)if(!std::strcmp(request->name,entries[i].name)){
  if(!value){errno=saved_errno;return nullptr;}
  void *empty=nullptr;
  if(!__atomic_compare_exchange_n(&S.slots[entries[i].slot],&empty,value,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE) && empty!=value){fail(E_RESOLVER);errno=saved_errno;return value;}
  errno=saved_errno;return entries[i].wrapper;
 }
 for(uint32_t i=0;i<S.safe_count;++i)if(!std::strcmp(request->name,S.safe[i])){errno=saved_errno;return value;}
 fail(E_RESOLVER);errno=saved_errno;return value;
}
extern "C" void *psd_path(uint32_t origin,void *value){
 int saved_errno=errno;uint64_t args[]={origin};psd_token token;psd_before(PSD_RESOLVER_PATH,args,1,&token);token.event.origin=origin;
 psd_after(&token,(uintptr_t)value);errno=saved_errno;return value;
}
extern "C" int psd_finish(void){
 if(!load(&S.configured))return 0;
 if(!owner()){fail(E_THREAD);return -1;}
 if(S.busy || S.lookup){fail(E_REENTRY);return -1;}
 if(load(&S.closed)){fail(E_CLOSED);return -1;}
 __atomic_store_n(&S.closed,1u,__ATOMIC_RELEASE);return load(&S.error)?-1:0;
}
extern "C" int psd_get_stats(psd_counts *out){
 if(!out || (load(&S.configured) && !owner()))return -1;
 *out=psd_counts{load(&S.configured),load(&S.closed),load(&S.error),__atomic_load_n(&S.forwarded,__ATOMIC_RELAXED),
 __atomic_load_n(&S.resolutions,__ATOMIC_RELAXED),__atomic_load_n(&S.paths,__ATOMIC_RELAXED),S.events};return 0;
}
