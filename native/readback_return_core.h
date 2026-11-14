#ifndef READBACK_RETURN_CORE_H
#define READBACK_RETURN_CORE_H
#include <stddef.h>
#include <stdint.h>

/* Caller owns aligned context storage and private scratch for the entire lifetime.
 * Metadata and capacity must describe valid accessible memory before the call.
 * This core cannot authenticate an adapter, GPU write, camera or frame identity.
 * No concurrent lifecycle calls: begin/end/finish/stats run on the init thread.
 * A scoped foreign-thread read only forwards and records a sticky error.
 * The original must be nonnull and must return normally (no longjmp).
 * Footer bytes alone cannot attest to their emitter's eventual return status.
 * Acceptance requires an out-of-band successful rb_finish result/error/counters
 * bound to the finalized stream by the trusted caller, even with a full footer.
 */
#define RB_KNOWN_ALL 255u
typedef void (*rb_read_fn)(int32_t,int32_t,int32_t,int32_t,uint32_t,uint32_t,void *);
typedef int (*rb_emit_fn)(const unsigned char *,size_t,const unsigned char *,size_t,void *);
typedef struct {
  unsigned char nonce[32];
  uint32_t enabled,windows,reads_per_window,max_records;
  uint64_t max_wire_bytes;
} rb_config;
typedef struct {
  uint32_t known,alignment,row_length,skip_pixels,skip_rows,pack_buffer,read_fbo;
  uint32_t producer_camera,label_basis;
  uint64_t context_tag,capacity;
} rb_read_state;
typedef struct {
  uint32_t error;
  uint64_t captured,attempts,forwards,data_wire_bytes;
} rb_stats;
enum rb_error {
  RB_OK=0,RB_CONFIG,RB_SEQUENCE,RB_THREAD,RB_REENTRANT,RB_METADATA,RB_PBO,
  RB_LAYOUT,RB_EXTENT,RB_ALIAS,RB_LIMIT,RB_EMIT,RB_NO_ORIGINAL
};
size_t rb_context_size(void);
int rb_init(void *,size_t,unsigned char *,size_t,const rb_config *,rb_emit_fn,void *);
int rb_begin(void *,uint32_t host_call,uint32_t requested_camera);
void rb_read(void *,rb_read_fn,int32_t,int32_t,int32_t,int32_t,uint32_t,uint32_t,void *,const rb_read_state *);
int rb_end(void *);
int rb_finish(void *);
void rb_get_stats(void *,rb_stats *);
#endif
