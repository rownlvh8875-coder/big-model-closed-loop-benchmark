# Readback delivery and CPU process boundary

Basec06a3a3eb8e215a8e40054433cf4c6c4c1d42bdc; feature/readback-delivery-boundary-v1.
This addition connects explicit typed originals, pre-registry command delivery,
Panda-shaped preserving read-tail, command cache and existing return core/codec.
It does not install or activate a native GL hook. Original strict0/4FAIL and
Stage7INCOMPLETE remain. No Cloud/registry publication or main/sharedbase merge.

The delivery table retains original alias identity and NULL capabilities. A bounded
bootstrap records actual context-call returns and state commands before cache
attachment. Replay uses no-op CPU callbacks and adds no original calls. Unknown
routes, pointer mismatches, shared/foreign contexts, caps, reentry and thread errors
poison metadata while original arguments/results/errno continue. The ReadPixels
assembly tail preserves Panda's returnPC, stack argument and callee-saved registers;
only successful bridge/cache binding arms it, and finalization disarms it.

The Linux code checker validates reviewed ELF64/amd64/PT_LOAD ranges against the
actual process's file SHA/dev/inode/private executable mapping/load bias/file offset
and memory bytes. It checks process starttime, executable identity, target maps and
source identity around reads. It cannot establish future immutability or an entire
process/image/driver/ABI. A short-read proc/maps regression was reproduced and fixed
with bounded reads through EOF. The positive test loads only its own compiled CPU.so.

The CPU channel uses per-message SCM_CREDENTIALS on a private SOCK_SEQPACKET pair.
It binds the actual unreaped child/PID/UID/GID, caller-fresh32Bnonce, mapped code,
post-delivery/cache/bridge/sink status, regular spool identity/size/hash before ACK
and after exit, clean process exit and channel EOF. Unexpected received FDs close.
A footer alone cannot supply producer success. This is an owned CPU session check,
not a sandbox, signature, hostile same-UID defense or native process attestation.

Evidence: docs/evidence/readback-delivery-boundary-01/proof-index.json indexes all
retained raw CPU streams/statuses/binaries/build commands and verification logs.
The78CPU scenarios comprise24standalone modes in plain and ASan/UBSan builds plus
15channel modes in both builds. Standalone bytes/status match between builds;
valid channel cases pass, badnonce/PID/mapping/status/sink/exit/extra/empty/latewrite
cases reject. Compile+link1.756446386s excludes tests/review/CI/development and is
not native instrumentation overhead. Focused18testsPASS1.654s before review.
Fullsuite1414tests/1407PASS/7skip94.729s, zero failures before review. One fresh
whole-branch review and exactDraftCI closure are next.

Remaining native gates: qualify exact live original delivery/resolver installation
and complete mutation coverage; bind actual camera/GSG/native lifetimes and process
profile/environment; qualify bounded native receipt transport; then create a fresh
reviewed ON/OFF canary allowance. Current native allowance0; no consumed request
reuse, new native/provider/model/officialORT run or observed original GPU bytes.
