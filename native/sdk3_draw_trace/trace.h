#ifndef SDK3_DRAW_TRACE_H
#define SDK3_DRAW_TRACE_H
#include <stdint.h>
struct dt_stats {uint32_t version,error,active,restored;uint64_t lookups,forwards,draws,queries,readbacks,blits;};
int dt_configure(const char *path,unsigned max_draws);
int dt_begin(int phase,int x,int y);
int dt_end(void);
int dt_close(void);
int dt_get_stats(struct dt_stats *out);
#endif
