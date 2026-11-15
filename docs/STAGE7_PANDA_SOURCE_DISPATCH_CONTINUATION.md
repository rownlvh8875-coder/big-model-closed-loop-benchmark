# Continue after source-integrated Panda dispatch candidate

Branchfeature/panda-source-dispatch-v1;base5aefbd5ca54557de79d00c67282c086e8a6bca61. Read RESULT/LEDGER and docs/evidence/panda-source-dispatch-01/proof-index.json. Final immutable head/Draft/exact-source CI receipts live in the PR body and output/stage7-panda-source-dispatch-01/final-verification.json after closeout. Preserve old evidence/refs; no Cloud/registry publication, main/shared-base update or consumed request reuse.

Implemented: inert C++ source hook runtime, exact4source transformation, full clean pinned source stage, constrained builder and actual minimal GL/X11/noPython SDK. Default OFF; no capture arming, loader or GL query. Candidate library and unresolved inspection ELF are DATA ONLY and must not be loaded. Existing old Panda wheel, cache/core/bridge and ABI profile remain unchanged. Actual build result is not native admission or full image parity.

Final selected implementation0071da8a47aa7648d95a02b2c93a1df960ce6b1d; SDK SHA228b2d88e91fa9c5ded10cfe8e93f9b9519de881a37765a0e8681af6e36cf96b,135.320271794s actual compile/link.23focusedPASS;1464fulltests/1457PASS/7skip140.648s;50normal/sanitizedCPU scenarios. One review0C2I1M;2Important fixed in onepass, Minor automatic receipt numbering deferred, no rereview. On a failed-build resume, copy build-receipt.json before retry: the runner retains numbered logs but overwrites that latest summary. Read selected-candidate.json for final source/build pins; before-review outputs intentionally bind the earlier source snapshot.

CPU checks:

```sh
/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m unittest tests.test_panda_source_dispatch tests.test_panda_source_dispatch_patch tests.test_panda_source_dispatch_build
```

To reproduce compilation, use a NEW source/output namespace and the retained pinned dependency sysroot. Never reuse an existing successful build output:

```sh
/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m scripts.panda_source_dispatch --upstream output/stage7-panda-source-dispatch-01/upstream --out output/panda-source-dispatch-next-source
/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m scripts.build_panda_source_dispatch --stage output/panda-source-dispatch-next-source --sysroot output/stage7-panda-source-dispatch-01/sysroot --out output/panda-source-dispatch-next-build --threads 4
```

Builder success means compile/link and static inspection only; runtime_admission_ready/native_admitted/candidate_panda_abi_qualified stayFalse. Source stage/hash/SDK output manifests are retained. Build-time CPU generators are allowed; renderer/PView/GL/provider/model/officialORT/native replay is forbidden under the existing allowance0.

Next independent plan:

1. Implement an explicit observer-to-existing-cache adapter, configured before the first temporary legacy context. Replay successful lifecycle returns and exact state commands while preserving originals. Add actual buffer-deletion invalidation support; do not infer PBO state from rc_snapshot or turn every unsupported drawable name into a context event. Qualify alias/compiled branch coverage and safe256budget for this actual new build, retaining unknown-name fail-closed behavior.
2. Produce a complete Python/MetaDrive image candidate under separate authorization, pin dependencies/build/environment and actual mapped dispatch origins. Qualify new method/callsite/register/returnPC/allocation spans and camera/GSG/Texture identities/lifetimes. The old ABI profile deliberately rejects this rebuilt library; never reuse its registers or returnPC.
3. Bind receipts/sink/process/windows and complete runtime/driver/read freshness gates before creating any fresh ON/OFF canary contract/allowance. Preserve PSSM/Chase/render/read counts. Remaining allowance0, strict0/4FAIL/Stage7INCOMPLETE; no native run or official large-model test follows merely from this SDK build.
