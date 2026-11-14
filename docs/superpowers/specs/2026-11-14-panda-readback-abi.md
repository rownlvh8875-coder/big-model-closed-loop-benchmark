# Pinned Panda readback ABI transport

Continue the original-rendering investigation at basea0e072e without rerunning old
consumed cohorts. The missing boundary is original-call returned RAM. Static
inspection now finds a concrete amd64 ABI in the pinned libpandagl ELF: method
0x62c50..0x63cd3 calls glReadPixels through PLT0x29aa0 at0x6305c, returning0x63061;
the PLT uses GOT0xcc550. At entry, rbx=Texture,rbp=GSG,r12=RAM extent,r15=RAM pointer.
For view0/z=-1, r12 is the actual RAM array end-minus-begin; other branches compute
page sizes and are excluded. Original GSG locals appear at entrySP+28(z)/+48(view).
This is file-level instruction binding; mapped runtime instructions remain unproven.

Approaches: rebuilding Panda alters the existing qualified binary and adds a large
toolchain; generic preload plus guessed RAM capacity lacks extent provenance. Use a
small register-transport entry and fail-closed dispatcher, with exact file/ELF/call
qualification. It exposes no glReadPixels/loader symbol and is not installed live.
This choice is the implementer's under persistent inline/noquestions authorization.

Create native/panda_readback_bridge.{h,c,S}: C11,pthreads,SysVamd64. No GL/Panda
linkage/load, constructor, dlsym, patcher, new query/read/render/task/heap/retry. One
immutable process binding points to a core initialized from the same rb_config.
Caller-owned aligned context/scratch and normal-return/lifetime/serialized-lifecycle
preconditions remain. Entry may only be invoked after successful install.

Assembly snapshots unchanged7GL arguments plus returnPC/rbx/rbp/r12/r15/entrySP;
preserves callee-saved registers and stack alignment. Dispatcher forwards through
the existing rb_read exactly once. Outside windows/OFF it reads no pixel/pack state;
active invalid returnPC/registry/GSG/r15/extent/view/z/thread/reentrancy is sticky and
invalidates finalization while originals still run. Only after exact returnPC and
registered identity match may it read the two qualified GSG caller stack locals.
The original return errno survives all observer work.

Two unique registered Texture identities map explicitly to Road1/Wide2, separately
from alternating requested camera. A supplied CPU-only cached-state callback gives
pre-call pack/PBO/read-FBO/context state. Dispatcher replaces capacity with captured
r12 and producer label with the registered Texture role. Callback/registry are
unqualified live suppliers, never automatic proof. OFF invokes no callback.
Core budgets24records/64MiB/12windows/1or2reads/964x604/8MiB stay unchanged.
External producer receipt must use bridge finish status as well as core stats;
core footer alone cannot attest bridge errors or sink finalization.

Create scripts/panda_readback_abi.py: bounded little-endian ELF64 reader verifies
exact file SHA, executable VA→file mapping, method/code fingerprints, direct call
target/PLT/GOT/dynamic symbol relocation. No disassembler text parsing for admission.
Pin a compact excerpt contract as data; it identifies2D register/stack transport
but never admits a loader or asserts actual mapped ABI/native allocation validity.

Verify actual assembled CPU fake caller with independent stack locals/register
sentinels, varied signed/stack arguments, source/errno preservation, extent and
identity failures, wrong caller/thread/reentrancy/OFF, both producer roles, max
budgets and real codec/producer-receipt interop. ASan/UBSan CPU scenarios; no engine
import/load/context/provider/model/ORT/native run. Mutation tests on real ELF bytes
reject code/hash/segment/call/PLT/relocation mismatches. Full suite, one fresh whole
branch review, one Important/Critical TDD fix pass, no rereview/minor polishing.

All2515base tracked files/old299pins/original evidence/main/native histories must
remain byte-identical. Same checkout/own branch, no extra worktree/implementer
delegation. Own Draft/exact source CI; no mainmerge or Cloud/registry publication.
The next live gate still requires qualified state/registry/receipt suppliers,
runtime build/maps/environment contract and fresh bounded canary allowance.
