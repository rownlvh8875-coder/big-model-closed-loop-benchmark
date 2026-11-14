#ifndef READBACK_CALL_DELIVERY_H
#define READBACK_CALL_DELIVERY_H
#include "panda_readback_bridge.h"
#include "readback_command_state.h"
/* Inert Linux-amd64 typed delivery. No GL symbol export, constructor, resolver
 * lookup, loader or patcher. Original addresses/allowlist need independent mapped
 * qualification before real use. Originals and caller-owned storage stay alive
 * until process exit. Install once before entry, serialized owner lifecycle, valid
 * string/delete spans and normally returning originals are preconditions.
 * Replay uses CPU no-ops, never additional GL calls. Command metadata is not
 * driver-state/GPU/native authority. Unknown mutation delivery remains a gate.
 */
typedef struct _XDisplay rd_display;
typedef struct __GLXFBConfigRec *rd_fbconfig;
typedef struct __GLXcontextRec *rd_context;
typedef void (*rd_proc)(void);
typedef struct {
  void (*pixel_store)(uint32_t,int32_t);
  void (*bind_buffer)(uint32_t,uint32_t),(*bind_buffer_arb)(uint32_t,uint32_t);
  void (*bind_framebuffer)(uint32_t,uint32_t),(*bind_framebuffer_ext)(uint32_t,uint32_t);
  void (*read_buffer)(uint32_t);
  void (*delete_framebuffers)(int32_t,const uint32_t *),(*delete_framebuffers_ext)(int32_t,const uint32_t *);
  rb_read_fn read_pixels;
  rd_context (*create_new)(rd_display *,rd_fbconfig,int,rd_context,int);
  rd_context (*create_attribs)(rd_display *,rd_fbconfig,rd_context,int,const int *);
  int (*make_current)(rd_display *,unsigned long,rd_context);
  int (*make_context_current)(rd_display *,unsigned long,unsigned long,rd_context);
  void (*destroy_context)(rd_display *,rd_context);
  uint32_t (*get_error)(void);
  rd_proc (*get_proc)(const unsigned char *),(*get_proc_arb)(const unsigned char *);
} rd_dispatch;
typedef struct {uint32_t error,attached,bound,closed;uint64_t forwarded,events,replayed,resolvers,nonzero_errors;} rd_counts;
size_t rd_context_size(void);
int rd_install(void *,size_t,const rd_dispatch *,const char *const *safe_names,size_t count,uint32_t event_cap);
int rd_attach(void *fresh_cache);
int rd_bind_bridge(void *,size_t,const rb_config *,unsigned char *,size_t,rb_emit_fn,void *,const pb_binding *);
int rd_observe(uintptr_t,uintptr_t,rb_read_state *,void *);
int rd_invalidate(void);
int rd_finish(void);
void rd_get_stats(rd_counts *);
void rd_read_pixels(int32_t,int32_t,int32_t,int32_t,uint32_t,uint32_t,void *);
void rd_pixel_store(uint32_t,int32_t);
void rd_bind_buffer(uint32_t,uint32_t);
void rd_bind_buffer_arb(uint32_t,uint32_t);
void rd_bind_framebuffer(uint32_t,uint32_t);
void rd_bind_framebuffer_ext(uint32_t,uint32_t);
void rd_read_buffer(uint32_t);
void rd_delete_framebuffers(int32_t,const uint32_t *);
void rd_delete_framebuffers_ext(int32_t,const uint32_t *);
rd_context rd_create_new(rd_display *,rd_fbconfig,int,rd_context,int);
rd_context rd_create_attribs(rd_display *,rd_fbconfig,rd_context,int,const int *);
int rd_make_current(rd_display *,unsigned long,rd_context);
int rd_make_context_current(rd_display *,unsigned long,unsigned long,rd_context);
void rd_destroy_context(rd_display *,rd_context);
uint32_t rd_get_error(void);
rd_proc rd_get_proc(const unsigned char *);
rd_proc rd_get_proc_arb(const unsigned char *);
#endif
