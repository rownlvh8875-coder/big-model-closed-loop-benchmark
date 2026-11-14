# Continue after the pinned Panda ABI bridge

Branch feature/panda-readback-abi-v1, basea0e072e450cf6591b9da686711196d56eb9165a1.
Exact final HEAD/PR/CI lives in that Draft body and retained
output/stage7-panda-readback-abi-01/final-verification.json. Do not reapply the old
consumed native request. Main/old Drafts102–105/native histories remain unchanged.

Completed: pinned file-level ELF/call/PLT/GOT qualification and inert SysV bridge,
R12extent/R15pointer/RBXTexture/RBPGSG transport, view0/z=-1 guard, exact original
argument/register/incoming+returnederrno preservation, CPU core/receipt interop.
Full1370PASS7skip118.438s;19focusedPASS;34ASan/UBSan CPU scenarios PASS. Sole review
found1Important incomingerrno leak, one RED→GREEN fix pass; no rereview/minors.
No actual GPU bytes/native/provider/model/officialORT executed. Strict0/4FAIL and
Stage7INCOMPLETE remain; no renderer cause/fix is established by this transport.

Verify current checkout and CPU boundary before edits:

```sh
git status --short --branch
git rev-parse HEAD
/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m unittest tests.test_panda_readback_abi tests.test_panda_readback_bridge
```

Read result/ledger and docs/evidence/panda-readback-abi-01/{static-abi,result,
synthetic-build,proof-index}.json. Exact ELF bytes remain data at
output/stage7-readback-return-core/source-audit/libpandagl.so; do not load them on
the local preparation machine. The source and qualified baseline are immutable.

Next implement and qualify the missing live suppliers under a fresh namespace:

1. Actual Texture/GSG registration from provider-owned objects with identity/lifetime,
   distinct Road/Wide roles and no inference from requester/ordinal or cached frame.
2. Actual cached pack/PBO/read-FBO/context state observed from original calls, with
   explicit initial-state completeness and no observer GL queries/readbacks.
3. Same-process nonce/host-window binding and external bridge/sink-finalization
   receipt transport, independently checked against raw records and process status.
4. Reproducible native build, exact mapped ELF/instructions/original dispatch and
   reviewed runtime source/maps/environment contract. The old environment rejects
   arbitrary preload; do not relax it or treat file-level qualification as admission.
5. Only after those mechanical gates, a fresh bounded ON/OFF native canary allowance
   and raw evidence review. Keep original PSSM/Chase/render/read counts and preserve
   originals/failed results. No expanded cohort or official model run before canary.

No loader/patcher/workflow activation is present in this branch. Unqualified live
state, camera registration, allocation lifetime and receipt dictionaries cannot
establish native/GPU/frame authority. Cubemap/multiview need separate ABI contracts.
