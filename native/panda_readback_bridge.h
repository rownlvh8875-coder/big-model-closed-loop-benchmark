#ifndef PANDA_READBACK_BRIDGE_H
#define PANDA_READBACK_BRIDGE_H
#include "readback_return_core.h"

/* Inert Linux amd64 SysV entry transport, NOT a loader or native-admission gate.
 * Qualified caller must bind exact mapped code/returnPC and real Texture/GSG
 * identities. observe reads only cached, pre-observed GL state: no GL query/read.
 * Actual mapped ABI/allocation/state/identity/receipt transport remains unqualified.
 * The original receives the caller's incoming errno; its returned errno survives
 * both pre-call observation and post-call copying/emission.
 * Install once before invoking pb_entry; no uninstall/rebind, concurrent lifecycle
 * calls or longjmp. Caller-owned context/scratch/config/identities stay alive.
 * Use only pb_begin/end/finish for this embedded core. Final receipt must use
 * pb_finish's return plus core stats, and finalized sink/spool success; footer alone
 * cannot attest bridge errors. Data and labels have no native/GPU/frame authority.
 */
typedef int (*pb_observe_fn)(uintptr_t texture,uintptr_t gsg,rb_read_state *out,void *user);
typedef struct {
  rb_read_fn original;
  uintptr_t expected_return,gsg,texture[2]; /* Road1/Wide2, distinct live identities */
  pb_observe_fn observe;
  void *observe_user;
} pb_binding;
typedef struct {rb_stats core;uint32_t bridge_error;} pb_stats;
size_t pb_context_size(void);
int pb_install(void *storage,size_t bytes,const rb_config *,unsigned char *scratch,size_t cap,rb_emit_fn,void *user,const pb_binding *);
int pb_begin(void *,uint32_t host_call,uint32_t requested_camera);
void pb_entry(int32_t,int32_t,int32_t,int32_t,uint32_t,uint32_t,void *);
int pb_end(void *);
int pb_finish(void *);
void pb_get_stats(void *,pb_stats *);
#endif
