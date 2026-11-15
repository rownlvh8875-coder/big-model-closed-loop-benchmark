#ifndef PANDA_CACHE_ADAPTER_H
#define PANDA_CACHE_ADAPTER_H
#include "panda_source_activity.h"
extern "C" {
#include "readback_command_state.h"
}
/* Command metadata only. Install before first context activity on the serialized
 * owner. Caller retains valid, aligned, disjoint adapter/cache storage and input
 * lifetimes; adapter exclusively owns attached cache mutation/finalization.
 * Callers use pca snapshot/observe/finish; originals return normally. No GL query/loader/bridge/capture arming.
 * Bootstrap replay calls CPU no-ops, never the GL originals. Sharing is rejected.
 * Snapshot/observe/finish require healthy source+cache. An actual downstream finish
 * result is combined, not authenticated as a sink receipt or native admission.
 */
struct pca_counts {
 uint32_t error,attached,finished,bootstrap,created,live,pending;
 uint64_t events,replayed,applied,buffer_deletes,pbo_resets;
 psd_counts source;
};
extern "C" {
size_t pca_context_size(void);
int pca_install(void *,size_t,const char *const *,size_t,uint32_t);
int pca_attach(void *,void *fresh_cache);
int pca_observer(const psd_event *,void *);
int pca_snapshot(void *,rc_state_view *);
int pca_observe(uintptr_t,uintptr_t,rb_read_state *,void *);
int pca_finish(void *,int actual_downstream_finish_result);
int pca_get_stats(void *,pca_counts *);
}
#endif
