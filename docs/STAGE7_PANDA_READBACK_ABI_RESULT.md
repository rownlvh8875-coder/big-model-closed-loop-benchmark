# Pinned Panda readback ABI transport

The exact retained libpandagl ELF now has a verified file-level read-call route:
GSGmethod0x62c50,size4227 → call0x6305c → PLT0x29aa0 → GL JUMP_SLOT0xcc550;
returnPC0x63061. A bounded ELF64LE parser checks executable VA/file mapping,
symbols/relocation/directcall/PLT targets and exact file/method SHA256. Generic
structural validity alone never qualifies foreign bytes.

Disassembly identifies saved registers at the call: RBXTexture,RBPGSG,R12RAMextent,
R15RAMpointer. The accepted view0/z=-1 path loads extent from RAM-array end-minus-
begin. Other paths compute page sizes and are rejected. Z/view are at original
GLentrySP+28/+48. These are instructions in an exact file, not observed mapped
runtime code, live allocation validity or actual GPU bytes.

The new inert assembly/C bridge preserves the7original GL-shaped arguments,
callee-saved registers and original return errno, then uses the existing bounded
CPU core. It exposes no GL/loader symbol and installs no interposer. Exact expected
returnPC/registeredTexture/GSG checks precede reading qualified caller stack slots.
Wrong identity/extent/view/state/thread/reentrancy fails sticky while originals run.
The copied extent comes from capturedR12, replacing the cached-state callback's
capacity. Producer role comes from two explicit Texture registrations, independent
of requester alternation. OFF calls no state callback and reads no pixels. Unscoped
calls only forward. Core limits remain24records/64MiB/12windows/2reads/964×604/8MiB.

The binding, actual Texture identities, cached GL pack/PBO/FBO/context state and
mapped original dispatch remain caller-supplied live preconditions requiring new
qualification. Entry-before-install is invalid; context/storage/lifetimes and
serialized lifecycle/normal original return remain API preconditions. The external
producer receipt uses bridge finish status and core stats plus finalized spool
identity. Even OFF bridge failure invalidates a core footer reporting error0.
Neither synthetic labels nor manufactured receipt data provides native authority.

Before independent review,18focused tests and1369whole-suite tests pass,7skip,
117.097s. The actual assembled CPU caller independently sets the two stack locals,
checks all6callee-saved registers, and validates signed/scalar/stack arguments.
31scenarios pass ASan/UBSan with exact normal/sanitized streams/counters, including
bad callers/identity/span,thread/reentrancy,OFF,pack padding,emitter failures and
max24record55,900,512B. Build smoke2.934881606s wall excludes tests/review/CI/development
and measures no live GL overhead. Review/CI closeout is pending.

All2515base files/299oldsourcepins and10original trace/graph/ZIP artifacts are
byte-preserved. Main, old Drafts102–105 and native histories are unchanged. No new
native/GL/provider/officialmodel/officialORT execution, no old request reuse,
mainmerge or Cloud/registry publication. Original strict0/4FAIL/Stage7INCOMPLETE stand.

The next gates are actual mapped-code/dispatch/build/environment admission, live
Texture/allocation and cached-state suppliers, process/window/receipt transport,
then a fresh bounded native canary with OFF control and raw evidence review. No
native collection is activated by these file-level and CPU checks.

See [machine result](evidence/panda-readback-abi-01/result.json),
[proof index](evidence/panda-readback-abi-01/proof-index.json) and
[decisions/costs](STAGE7_PANDA_READBACK_ABI_LEDGER.md).
