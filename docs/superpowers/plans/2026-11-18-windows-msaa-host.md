# Windows MSAA host correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement inline. Steps use checkbox syntax.

**Goal:** Correct hostless WGL allocation, prove ownership, and deliver scoped retest guidance plus retrospective full-S observations.
**Architecture:** One private allocator using caller-owned ExitStack; original challenge/validator path retained. Fake WGL failures and separate hosted Linux API smoke; no model reruns.
**Tech Stack:** Python3.11stdlib, stockPanda1.10.13, existing CPU unittest/Windows CI, optional hosted Mesa/Xvfb only.
**Spec:** docs/superpowers/specs/2026-11-18-windows-msaa-host-design.md

## Global Constraints
Base14297e2 and previous evidence immutable except narrow GPU allocator/callback cleanup, GPU tests, laptop docs and CI additions. No local native/Panda/SDK/officialmodel loads. No mainmerge/environmentpublication/registrypublish. Targetrequested2..64samples unchanged; four original renders, exactpixels and MSAA enabled/disabled edge discrimination. Newoutputsowned and removed reverseorder; originalcallback restored first. No realWindows qualification fromfakes/Linuxsmoke/handoffsummary. No duplicateofficialmodelrun; retrospective source54e2510 only.

## Review Focus
1. Valid host output with null/invalid GSG, or target allocation failure, must remove owned outputs and preserve original requested samples.
2. Draw/callback/disposal exceptions must restore callback, attempt removal of both outputs, and destroy ShowBase without a false cleanup PASS.
3. A zero-sample host must remain inactive while target keeps actual-MSAA gates; no hidden render or lower-sample target fallback.
4. Hosted Linux allocation or synthetic Windows contracts must not become actual RTX/WGL/model-camera qualification; missing resources stay explicit.
5. Old full-S traces and local handoff metadata must not be relabeled as new cloud/model outcomes or causal optical/model conclusions.

### Task 1: owned host/GSG allocation
Files: bigbench/laptop_gpu.py; tests/test_laptop_gpu_host_allocation.py (new); existing GPU coldhelp test if needed.
Interfaces: consumes existing GPU challenge and actual WGL verifier; produces `_allocate_msaa_output(base,core,requested_samples,owners)->GraphicsOutput`, usingcallerExitStack and no optionalimports at module scope; post-review return is(output,observedallocationmetadata).
- [ ] Write fake WGL run_gpu_probe regressions: originalrender reached only after valid0samplehost, sameGSG+host passedto4sampletarget; initialization/gsg/target/draw/callback/removal failures cleanup and no targetdowngrade.
- [ ] Run new module; ExpectedRED atoriginalhostlessallocation, before fake drawboundary.
- [ ] Implement allocator, resourceownership and nestedcallback/output/basecleanup; record newattemptconstruction marker, preserve all challenge/validator behavior.
- [ ] Run hostregressions+portable58baseline; ExpectedPASS,noactualPanda/ORT. Commit.

### Task 2: native API smoke, evidence and local retest
Files: scripts/smoke_gpu_host_allocation.py; .github/workflows/gpu-host-allocation.yml; laptop-portable.yml branchscope; docs/LAPTOP_FOUR_VALIDATIONS.md; docs/evidence/windows-msaa-host-20261118/*.
Interfaces: consumesTask1allocator; produces zero-model software API smoke report and corrected Windows kit/retest instructions; retrospective JSON binds oldsource54run44176109300.
- [ ] Coldhelp regression RED→GREEN for smoke CLI; actual imports lazy.
- [ ] Add hosted Ubuntu stockPanda1.10.13/Xvfb/Mesa smoke: allocate0samplehost/request4target, one no-scene software render, report actualdriver/framework samples and ownedcleanup; flag hardware/model/physical qualificationFalse.
- [ ] Read and independently verify saved native trajectories; derive fourcondition tracking observations with exact inputfile hashes; no newmodels or causalclaims. Compare pairedsummary results.
- [ ] Update Windowsinstructions with freshoutputpath and host-fix scope; workflowonlynewfeaturebranch/pullrequests. Run focusedtests/actionlint/diffcheck; ExpectedPASS.

### Task 3: final review and delivery
- [ ] Singlefreshwholebranchreviewbase142..HEAD, regrade; oneCritical/ImportantRED→GREENpass, Minordefer/no rereview.
- [ ] ExactfinalHEADcanonicalpush+PR4jobs, Windowspush+PR and Linuxsoftwarepush+PR checksPASS; freshDraftPRagainstparentfeature, preserveparent142/source54/main/originalartifacts.
- [ ] Build source-pinned Windowskit, coldinventorysmoke. Archiveownledger/rulings/minors, deleteonlyownscratch; preserveworktree and previousarchives. ReportactualWindowstestpending and externalfullSresultsnotobserved.

Post-review one-pass additions: actualtargetTypeHandle/GSG-sharing must be recorded without unconditional FBO claim; validalternate-output regression. Nativeownership check must run beforeBase.destroy; fault-injected missinghost/canarycallback mustFAIL evenwhenBasefallbackworks. ExactfinalCI receipts must use software-api-smoke-v2 and pre-Baseownership fields. One wrapper-error docMinor deferred.
