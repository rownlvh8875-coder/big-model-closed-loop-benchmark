#ifndef PANDA_SOURCE_ACTIVITY_H
#define PANDA_SOURCE_ACTIVITY_H
#include "panda_source_dispatch.h"
/* Read-only activity signal from the SAME source-runtime translation unit.
 * Exact observer/user binding and an idle owner are required. No counters, GL
 * calls, resolver calls, capture arming or source state are changed. An older
 * SDK without this additive symbol is incompatible, never assumed idle.
 */
extern "C" PSD_API int psd_source_idle(psd_observer expected,void *user);
#endif
