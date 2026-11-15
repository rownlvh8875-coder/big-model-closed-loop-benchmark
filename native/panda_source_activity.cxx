#include "panda_source_activity.h"
// Compile the immutable runtime once with this additive activity boundary.
// A future Panda integration includes this TU instead of including the old TU
// directly, preserving its PSD_PANDA_BUILD/PSD_ORIGINAL_READ configuration.
#include "panda_source_dispatch.cxx"
extern "C" int psd_source_idle(psd_observer expected,void *user){
 int saved=errno;
 bool idle=active() && owner() && !load(&S.error) && !S.busy && !S.lookup && expected && S.observer==expected && S.user==user;
 errno=saved;return idle?0:-1;
}
