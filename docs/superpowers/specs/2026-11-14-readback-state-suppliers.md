# Readback object registry and command-state suppliers

Build the two missing suppliers for the pinned Panda ABI bridge at868f65e, without
loading a renderer or reusing consumed requests. Existing provider ownership is
env.engine.sensors['bigbench_road'/'bigbench_wide'].copy_texture and .buffer; each
buffer exposes getGsg(). Texture/GSG handles are private uintptr values, never
inferred from requester or serialized as native proof.

Approaches: querying GL on each read adds new driver calls; manually filling state
cannot detect unknown contexts/state transitions. Choose a bounded C command cache
and owner/lifetime-checked Python registry. This is the implementer's choice under
persistent noquestions/inline authorization. These suppliers are executable CPU
components, not proof that live event delivery or native identities are qualified.

Python registry: capture provider/env/engine/sensors/two camera/buffer/texture owners,
strongly retain them, validate distinct nonzero64bit handles and one common GSG.
Only initial registration and at most12ordered host-window guards call each buffer's
bound getGsg once. Validate all cheap owner/handle checks before getters; failures
are sticky. Guard sequence1..12 with requester1odd/2even; role1Road/2Wide stays fixed.
Wrong-thread/reentry, closed/replaced owner/handle/GSG, extra guard or duplicate native
identity reject. Close invalidates binding; actual bridge must finish first. Return
handles only via a private binding method; public descriptors contain nonce/roles/
counts/denials, no addresses. Import no Panda/GL and call no RAM/render/texture getter.

C cache: caller-owned aligned storage, one lifecycle/event owner thread, no heap,
GL linkage/query, constructor, resolver, loader or runtime interposition exports.
At most2live contexts/4context lifetimes/32FBO slots percontext/10000events. Fresh
unshared-context events seed only GL-specified pack defaults; successful make-current
events select known contexts, failed switches keep old state, unbind/destroy/reuse
never retain stale identity. Assign monotonic logical context tags, not raw pointers.
Unknown/shared/duplicate/dead context, wrongthread, unsupported state/event/cap and
observation failure are sticky. Fresh-context/switch events are untrusted delivery
inputs until a real wrapper/coverage/runtime contract qualifies them.

Typed wrappers for original glPixelStorei,glBindBuffer,glBindFramebuffer,glReadBuffer,
glDeleteFramebuffers preserve unchanged arguments and incoming/returned errno and
invoke original exactly once on every cachefailure. Record after original returns;
snapshot bounded delete names before call. Pack alignment1/2/4/8, rowlength/skips
0..4096; PBO binding tracked, nonpack buffer/unpack calls ignored for read layout.
Nonzero swap/LSB flags and unsupported enums reject. Track read/draw FBO separately,
read-selector per FBO and deletion/unbinding; draw-only changes do not change read
source. Observe only a known nonzero FBO with explicitly observed color attachment
selector; no guessed default framebuffer selector. glPush/PopClientAttrib and any
uncovered mutation must explicitly invalidate the cache in a future delivery layer.

rc_observe has the existing pb_observe_fn signature and validates registered
Texture/GSG identity/current context, then emits rb_read_state from cache with
capacity/producer left0 (bridge supplies actual savedR12/registered role). A sidecar
snapshot carries read-selector, logical context generation and event counts.
This is COMMAND-DERIVED state, not queried/verified driver state: void calls do not
attest successful state changes, errors or GPU writes. Live mutation coverage,
original error/return receipts, mapped dispatch, registration and process/window/
sink receipt transport remain inactive mechanical gates. No native authority from
known-bit masks or synthetic context creation events.

Verify registry against complete provider-shaped fakes and explicit getter budgets;
real compiled C originals/cache→existing assemblybridge/core→strictcodec/producer
receipt interop, errno/arguments/forwarding, ON/OFF, context lifetimes/switchfailures,
pack/PBO/FBO/deletion/caps/unsupported events/thread failures and RGB bytes. Run
ASan/UBSan CPU scenarios, full suite, one fresh whole-branch review, one Important/
Critical RED→GREEN fix pass, no rereview/minorpolish. Retain originals/failed output.

Same checkout/ownbranch, preserve all2624base tracked files/299oldpins/old originals,
main and native histories. Own Draft/exact source CI only; no mainmerge/Cloud/registry
publication, new native/provider/model/officialORT run or old allowance reuse.
