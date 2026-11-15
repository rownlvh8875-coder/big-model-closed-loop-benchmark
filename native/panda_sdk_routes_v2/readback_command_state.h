#ifndef READBACK_COMMAND_STATE_H
#define READBACK_COMMAND_STATE_H
#include "readback_return_core.h"
/* COMMAND-DERIVED state only. No GL query, loader, native admission or driver-state
 * attestation. Context events must come from actual original creation/current/
 * destruction calls; that delivery/coverage/error transport is not qualified here.
 * Invalidate on uncovered mutators (e.g. client attribute stack restoration).
 * Caller-owned aligned storage/config, valid delete input extent/lifetimes and
 * normally returning nonnull originals are preconditions. One lifecycle/event
 * owner; foreign calls still forward and poison metadata acceptance.
 * Finalize once with actual bridge finish result AND successful external sink
 * finalization. The receipt must bind that result; a core footer is insufficient.
 * After finalize, wrappers only forward and observation is unavailable.
 */
typedef struct {uintptr_t gsg,texture[2];uint32_t max_events;} rc_config;
typedef struct {
  uint32_t alignment,row_length,skip_pixels,skip_rows,pack_buffer,read_fbo,draw_fbo,read_selector;
  uint64_t context_tag,events;
} rc_state_view;
typedef struct {uint32_t error,contexts_created,live_contexts,finalized;uint64_t events;} rc_counts;
size_t rc_context_size(void);
int rc_init(void *,size_t,const rc_config *);
int rc_context_new(void *,uintptr_t handle,uintptr_t share);
int rc_context_current(void *,uintptr_t handle,int original_succeeded);
int rc_context_destroy(void *,uintptr_t handle);
int rc_invalidate(void *);
void rc_pixel_store(void *,void (*original)(uint32_t,int32_t),uint32_t,int32_t);
void rc_bind_buffer(void *,void (*original)(uint32_t,uint32_t),uint32_t,uint32_t);
void rc_bind_framebuffer(void *,void (*original)(uint32_t,uint32_t),uint32_t,uint32_t);
void rc_read_buffer(void *,void (*original)(uint32_t),uint32_t);
void rc_delete_framebuffers(void *,void (*original)(int32_t,const uint32_t *),int32_t,const uint32_t *);
int rc_observe(uintptr_t texture,uintptr_t gsg,rb_read_state *out,void *cache);
int rc_snapshot(void *,rc_state_view *);
int rc_finalize(void *,int producer_finish_result);
void rc_get_stats(void *,rc_counts *);
#endif
