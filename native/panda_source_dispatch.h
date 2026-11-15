#ifndef PANDA_SOURCE_DISPATCH_H
#define PANDA_SOURCE_DISPATCH_H
#if !defined(__linux__) || !defined(__x86_64__) || defined(OPENGLES)
#error source dispatch candidate supports Linux amd64 GLX only
#endif
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#define PSD_API __attribute__((visibility("default")))
/* Candidate command events only, never driver/GPU/native authority. Observer and
 * originals return normally, do not throw/longjmp, and retain valid argument and
 * storage lifetimes. Configure before first context creation. No loader, custom
 * constructor, GL query/export or capture-arming API. Read tail stays original.
 */
enum psd_kind {
 PSD_PIXEL_STORE=1,PSD_BIND_BUFFER,PSD_BIND_FRAMEBUFFER,PSD_READ_BUFFER,
 PSD_DELETE_FRAMEBUFFER,PSD_DELETE_BUFFER,PSD_CREATE_LEGACY,PSD_CREATE_NEW,
 PSD_CREATE_ATTRIBS,PSD_CREATE_SGIX,PSD_MAKE_CURRENT,PSD_MAKE_CONTEXT_CURRENT,
 PSD_DESTROY_CONTEXT,PSD_GET_ERROR,PSD_LOOKUP=20,PSD_RESOLVER_PATH=21
};
enum psd_origin {PSD_SOURCE_COMPILED=1,PSD_SOURCE_RUNTIME=2,PSD_PATH_GLX_CORE=3,
 PSD_PATH_GLX_ARB=4,PSD_PATH_GLX_PRIVATE=5,PSD_PATH_POSIX=6};
struct psd_event {uint32_t kind,origin,argc,delete_count;uint64_t sequence,args[5],returned;char name[64];uint32_t names[32];};
struct psd_token {psd_event event;uint32_t active;};
struct psd_lookup {char name[64];uint32_t active;explicit psd_lookup(const char *);};
struct psd_counts {uint32_t configured,closed,error;uint64_t forwarded,resolutions,paths,events;};
typedef int (*psd_observer)(const psd_event *,void *);
typedef void (*psd_read_fn)(int32_t,int32_t,int32_t,int32_t,uint32_t,uint32_t,void *);
extern "C" {
PSD_API int psd_configure(psd_observer,void *,const char *const *,size_t,uint32_t);
PSD_API int psd_finish(void);
PSD_API int psd_get_stats(psd_counts *);
PSD_API int psd_bind_read(psd_read_fn);
PSD_API void psd_before(uint32_t,const uint64_t *,size_t,psd_token *);
PSD_API void psd_after(psd_token *,uint64_t);
PSD_API void psd_lookup_begin(const char *,psd_lookup *);
PSD_API void *psd_resolved(const psd_lookup *,void *,uint32_t);
PSD_API void *psd_path(uint32_t,void *);
void psd_read_pixels(int32_t,int32_t,int32_t,int32_t,uint32_t,uint32_t,void *);
}
inline psd_lookup::psd_lookup(const char *name){psd_lookup_begin(name,this);}

#include <type_traits>
namespace psd {
template<class T> struct identity {typedef T type;};
template<class T> inline typename std::enable_if<std::is_pointer<T>::value,uint64_t>::type scalar(T p){return reinterpret_cast<uintptr_t>(p);}
template<class T> inline typename std::enable_if<!std::is_pointer<T>::value,uint64_t>::type scalar(T v){return static_cast<uint64_t>(v);}
template<class R> struct invoke {
 template<class... P> static R run(R(*original)(P...),psd_token *token,P... args){
  R result=original(args...);int returned_errno=errno;psd_after(token,scalar(result));errno=returned_errno;return result;
 }
};
template<> struct invoke<void> {
 template<class... P> static void run(void(*original)(P...),psd_token *token,P... args){
  original(args...);int returned_errno=errno;psd_after(token,0);errno=returned_errno;
 }
};
/* P is deduced only from the original: argument conversions are the original
 * signature's conversions, rather than the source expression's wider type. */
template<uint32_t K,class R,class... P> inline R call(R(*original)(P...),typename identity<P>::type... args){
 static_assert(sizeof...(P)<=5,"bounded state-call signature");
 int incoming_errno=errno;uint64_t values[sizeof...(P)+1]={scalar(args)...,0};psd_token token;
 psd_before(K,values,sizeof...(P),&token);errno=incoming_errno;
 return invoke<R>::run(original,&token,args...);
}
}
#endif
