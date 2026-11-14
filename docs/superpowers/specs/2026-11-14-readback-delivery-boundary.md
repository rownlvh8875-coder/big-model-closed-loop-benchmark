# Readback delivery and process-bound proof boundary

Basec06a3a3 has an inert register bridge and command-state supplier, but no original
dispatch, pre-registry event delivery, mapped-code check or authenticated producer
channel. Implement those as reusable components tested with real CPU processes,
without loading Panda/GL or activating an old/new native renderer workflow.

Choose explicit typed original-function injection, bounded bootstrap replay and a
tail-jump read entry. Ambient dlsym/preload would introduce an unqualified loader;
installing after camera creation loses context/state history. The implementer uses
the persistent inline/noquestions choice. This stage has no GL symbol exports,
constructor, resolver lookup, patcher or environment change; live installation still
needs a new reviewed native contract and fresh bounded canary.

C delivery owns one immutable per-process typed dispatch. Supported state calls are
pixelStorei,bindBuffer(+ARB),bindFramebuffer/deleteFramebuffers(+EXT),readBuffer;
context calls are GLXCreateNewContext/CreateContextAttribsARB,MakeCurrent/
MakeContextCurrent,DestroyContext; original GetError and GetProcAddress/ARB returns
are observed without extra calls. Exact proc routes preserve the alias's original
target. A nullable optional entry preserves NULL capabilities. Unexpected pointer
results/unknown unclassified names/unsupported mutations fail metadata but return
the original resolver result. Explicit safe-name allowlist<=256names/63B excludes
known unsupported capture-state mutations. No claim that the list covers real Panda.

Caller-owned aligned storage holds<=10000ordered bootstrap records, including up to
32delete names. Before actual Texture/GSG binding, originals run once and records
retain only required state/return values. Attach once to a fresh initialized cache;
replay uses local no-op forwarders to apply previously observed commands, creating
zero additional GL calls. Recorded calls and cache-replay applications have distinct
counters. First error is sticky; unsupported/overflow/thread/reentry paths continue
original forwarding with unchanged args and incoming/returned errno. Context events
derive only from the actual original's return. One display/unshared context profile.

An amd64 tail entry jumps through an aligned atomic read target, initially original
ReadPixels, then existing pb_entry only after successful bridge install with matching
original and delivery callback. It preserves the Panda returnPC/stack/callee-saved
registers; a normal C wrapper would break that ABI. Delivery callback checks owner,
phase/error/reentry before rc_observe. Finalization folds delivery+bridge+cache
results, disarms the tail, then host must finalize the actual sink. No success from
footer alone. Source known bits still describe commands, not verified driver state.

Python mapped-code checker: bounded Linux proc maps/stat + ELF64LE/PT_LOAD parsing,
exact file SHA/dev/inode/private r-x permissions and load-bias/offset association,
bounded pread of target process bytes matching file. Stable PID starttime/maps before
and after, reject deleted/foreign/writable/anonymous/overlapping/wrong-offset/wrong-
byte mappings. Profile supplies reviewed ELF virtual ranges; this does not prove
function signatures or full process/image/driver/environment identity. CPU self/child
mapping proof must never become Panda runtime admission.

Producer transport uses private AF_UNIX SOCK_SEQPACKET with SO_PASSCRED. Validate
SCM_CREDENTIALS PID/UID/GID against the actual unreaped Popen child, fresh32Bnonce,
exact typed record, bounded packet<=16KiB, no truncation/extra/rights; close any
received unexpected FDs. Child emits actual post-producer/cache/delivery/sink status
after fflush/fsync, then holds for parent mapping inspection. Parent pins executable,
stream regular-file identity/<=64MiB/hash and process exit, checks no extra packet,
constructs old codec receipt from actual status+spool, and decodes full stream.
Kernel sender identity and code bytes are evidence at this instant, not a signature,
malicious-same-UID defense, native admission or future mapping/lifetime guarantee.

Tests: compiled CPU originals/aliases/failed context calls/bootstrap attach/tail
registers/errno/NULL/unknown resolver/errors/caps/thread/reentry/OFF/finalize; actual
child proc/memory checks and SCM packet spoof/truncate/extra/FD/status/nonce/sink/
exit/stream tamper. ASan/UBSan CPU scenarios and fullsuite. One fresh whole-branch
review; one Important/Critical TDDfixpass/no rereview/minorpolish. Preserve all2734
basefiles/299oldpins/originals/main/nativehistory. Own Draft/exactsource CI only;
no sharedbase/mainmerge,Cloud/registry publication,native/provider/model/officialORT
run or consumed request reuse. Original strict0/4FAIL/Stage7INCOMPLETE remain.
