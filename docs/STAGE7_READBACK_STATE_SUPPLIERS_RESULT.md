# Camera registry and command-state suppliers

Two missing CPU components now feed the inert Panda ABI bridge: a provider-owned
camera registry and a bounded original-command state cache. This is executable CPU
integration, not actual native event coverage or queried/verified driver state.
No new GPU bytes/native/provider/officialmodel/officialORT run occurred. Original
strict0/4FAIL/Stage7INCOMPLETE remain.

The Python registry retains provider/env/engine/sensor/Texture/buffer/GSG owners,
checks64bit handles and a common GSG, and fixes Road1/Wide2 independently of requester.
Registration plus12ordered guards use at most26bound getGsg calls; cheap ownership
and budget checks precede getters. Changes,wrongthread,reentry,closure and interrupted
getters poison the binding. Private native handles never enter public descriptors.
No Panda import,RAM getter,render call or image extraction occurs in the registry.

The C cache tracks2live contexts/4lifetimes,32FBOslots percontext and10000events,
with fresh unshared-context pack defaults and monotonic logical context tags.
Unknown/dead/shared/duplicate contexts reject; failed current switches retain prior
state and destroyed-handle reuse gets a new tag. Typed wrappers forward original
pixel-store/buffer/FBO/read-selector/delete calls once, unchanged, preserving caller
incoming and original returned errno on success and failure. They query no GL state.
Read/draw FBOs and per-FBO selectors remain separate; deletion snapshots input names
before the original and cannot restore stale selectors. Unpack/nonpack state does
not change read layout. NonzeroPBO,unsupported pack/selector/default-FBO coverage,
unknown mutations,thread/reentry/caps invalidate capture acceptance. Emitted valid
prefixes remain available when later failure prevents successful completion.

rc_observe supplies command-derived metadata to the unchanged assembly/core;
capturedR12 provides capacity, explicit Texture roles provide producer identity.
A sidecar retains selector/logical context/events. rc_finalize combines actual
producer return with cache failure, including OFF/corefooter0 cases; external
sink/process/window receipt transport remains independently required.

Known bits mean complete supported command history under caller delivery assumptions.
Void calls do not attest successful driver state changes or fresh GPU writes.
Context creation/current/destruction events, complete mutation coverage and original
error/return evidence still need a qualified live delivery layer. Default FBO and
unobserved color selection are rejected; no default selector is guessed. Actual
provider identities/lifetimes, mapped dispatch/code/build/environment and receipt
transport remain unqualified. No loader,GL export or native activation is added.

Pre-review verification:24focused tests PASS0.587s; whole1394tests PASS7skip95.025s.
41real compiled CPUscenarios pass ASan/UBSan with identical streams/counters, plus
Python fake64bit registry handles through Ccache→assembly→core→strictcodec. Maximum
12windows emits24records/5016B for the5×3fixture; original core image/wire caps remain
unchanged. Synthetic build1.502365051s wall excludes tests/review/CI/development and
measures no native overhead. The sole fresh review found2Important registrycallback gaps, noCritical/Minor.
One RED→GREEN fix pass checks stickyfailure after each handle descriptor read and
revalidates owners after the bounded getter pair.26focused tests PASS0.598s; final
whole1396PASS7skip92.299s;41sanitizer scenarios PASS, build1.742395934s wall. No
rereview. Pre-fix proofs remain before-fix/; exact Draft/HEAD CI closeout is recorded
in the PR body and retained output directory.

All2624base tracked files/299oldsourcepins and10original trace/graph/ZIP artifacts
are preserved. Main, old Draft102–106 and native histories stay unchanged. No merge,
Cloud/registry publication or consumed native request reuse.

See [machine result](evidence/readback-state-suppliers-01/result.json),
[proofs](evidence/readback-state-suppliers-01/proof-index.json) and
[rulings/costs](STAGE7_READBACK_STATE_SUPPLIERS_LEDGER.md).

See the [original review](evidence/READBACK_STATE_SUPPLIERS_01_REVIEW.md) and
[next execution steps](STAGE7_READBACK_STATE_SUPPLIERS_CONTINUATION.md).
