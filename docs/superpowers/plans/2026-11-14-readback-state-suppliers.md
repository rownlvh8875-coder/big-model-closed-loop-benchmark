# Readback state suppliers implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline; one fresh whole-branch review, no implementer delegation.

**Goal:** Supply guarded camera object identities and command-derived GL pack/context/FBO state to the inert ABI bridge.
**Architecture:** Python owner registry plus bounded C callback/cache and original-call forwarding wrappers. Compiled CPU fixture uses the unchanged prior assemblybridge/core/codec.
**Tech Stack:** Python3.11 stdlib,C11/pthreads,existing cc; no GL/Panda imports/linkage.
**Spec:** ../specs/2026-11-14-readback-state-suppliers.md

## Global Constraints

Base868f65e368bcb811bce64f61c988a27bbed612f2/all2624basefiles/299oldpins/originals/main/native histories unchanged. No new worktree/implementer delegation/loader/GLquery/native/model/officialORT run/publication. Contexts2live/4lifetimes,FBOslots32,events10000,hostwindows12. Existing core caps24records/64MiB/964x604/8MiB unchanged. Command state never implies driver/native/GPU authority.

## Review Focus

1. Unknown,failed,current,destroyed/reused/shared contexts and uncovered mutations never become guessed complete state.
2. Per-FBO read selection/deletion and read/draw/PBO/pack separation remain correct across context switches.
3. Invalid/cachefailed wrapper calls still forward once unchanged with both incoming and returned errno preserved.
4. Provider owner/handle/GSG changes, wrongthread/reentry and getter budgets cannot yield a fresh valid registry.
5. Supplier/cache success and receipts never claim driver state, native event coverage, GPU freshness or runtime admission.

### Task1: Provider-owned camera registry

**Files:** scripts/readback_camera_registry.py; tests/test_readback_camera_registry.py.
**Interfaces:** CameraRegistry(provider,nonce,max_windows=12),guard(host_call,requested_camera),native_binding()->(road_texture,wide_texture,gsg),descriptor(),close(). No native imports. Handles private; guards cheapchecks before exact2bound getGsg calls. Budget26getter attempts/returns maximum including init.

- [ ] Write RED tests for complete owners/handles/commonGSG,role/requester independence,mutation/reentry/thread/closed/budget and no addresses in descriptors; missingregistry expectedFAIL.
- [ ] Implement minimal registry; focused PASS; commit with ledger.

### Task2: Bounded C command cache and bridge callback

**Files:** native/readback_command_state.{h,c}; tests/fixtures/readback_state_fixture.c; tests/test_readback_command_state.py.
**Interfaces:** rc_context_size/init; rc_context_new/current/destroy/invalidate; rc_pixel_store/bind_buffer/bind_framebuffer/read_buffer/delete_framebuffers; rc_observe(Texture,GSG,state,user);rc_snapshot/stats. Observe callback directly feeds unchanged pb_binding. Post-return event functions grant only command coverage, not real state authority.

- [ ] RED compiled CPUfixture covers spec/focus input classes, proper original args/errno/counts and raw Ccache→bridge→codec records. MissingCmodule expectedFAIL.
- [ ] Minimal cache/context/FBO transitions and typed forwarding; focused PASS; ASan/UBSan allscenario streams/counters; preserve compiler/source/binary/dependency evidence and command-only limitations.
- [ ] Fullsuite PASS; one fresh wholebranch/source+syntheticreview; one Important/Critical TDDfixpass+greensuite, no rereview. Ledger everyruling/declined item/cost.
- [ ] OwnDraft/exact push+PRCI and finalallbase/source299/original/main/nativehistory audit; continuation with remaining real delivery/mapping/receipt/canary gates. Copy progress and delete only thisplan scratch.
