# SDK3 Renderer Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans inline; TDD; continuous all3objectives, one fresh wholebranch review at end, no implementer delegation. Checkbox tracking.

**Goal:** Trace the actual rendering boundary, implement an evidenced repair, and run the official large-model strict cohort.
**Architecture:** New C draw interposer and Python native/host adapters preserve all original producers; measured cause drives a separately recorded precise repair; uninstrumented official matrix validates result.
**Tech Stack:** C11/GCC/dl/pthread,Pythonstd/unittest/numpyexisting,frozenPanda1.10.13/MetaDrive0.4.3/SDK3/ORT1.20.1/Actions.
**Spec:** ../specs/2026-11-17-sdk3-renderer-completion-design.md

## Global Constraints
Baseae836ad09f410dd38f2503ac250863e889974c27,additionsonly;original/main/parent143 unchanged,no merge/environmentregistrypublication. Simulationonly/no realvehicles/CD210/Carrot/score. Exact sourceCI4jobs before each fresh request-only actual. Traceintervention truthfullycounted,OFFunloaded. Canary1+trace2zero-modelchildren,512draws/100000queries/2048pixelreads/16samples/8programs/16shaders/4MiBshader/32MiBtrace. Native2CPU10GiB/networknone/readonly/privateIPC/uid65534/tmpfs512MiB;canary90/120s,trace600/630s,35minjob. Causecontrasts boundedandpredeclared; official8children96inferences4conditions12steps,880s/pair1800s/60minjob, no instrumentation or tolerance. Historical3/4 remains distinct from candidate. See spec for full pinned model/image/SDK/source identities and gate limits.

## Review Focus
1. Interposer fails original ABI/errno/name-stack/alias forwarding or suppresses an original draw on observerfailure.
2. MSAA/format/pack-PBO/FBO restoration failure corrupts state or fabricates a framebuffer/owner/coordinate association.
3. Shader/program/sampler/depth/pixel identities or bounded partial observations are promoted beyond actual evidence.
4. Candidate fix changes semantics, clocks/model feeds/controller or selects outcomes while claiming original strict repair.
5. Final model cohort mixes sources/contexts, stale processes/weights/ONNX feeds/partial cases or CI success with strict matrix success.

### Task 1: exact C draw/resolver routing and CPU contracts
Files:create native/sdk3_draw_trace/trace.c,trace.h;tests/test_sdk3_draw_trace.py;tests/sdk3_draw_trace_fakes/**.
Interfaces:dt_configure(out,maxdraws),dt_begin(phase,x,y),dt_end(),dt_close(),dt_stats(out); bounded psd_lookup_begin/resolved pass-through and GLdraw wrappers.
- [ ] RED compile/run fakeSDK+fakeGL preload tests: direct/extension/instanced/alias forwarding/args/errno, nested lookupnames, OFFnoqueries, caps/failure stillforward. Expected missingtrace source/moduleFAIL.
- [ ] GREEN minimal routing/library/records,state-save-queryreadback implementation; CPUfakestate/context/buffer/pack/MSAA testsPASS; commit.

### Task 2: native tiny canary and original Road7 callback adapter
Files:create scripts/sdk3_draw_trace.py,scripts/sdk3_draw_trace_native.py,tests/test_sdk3_draw_trace_native.py.
Interfaces:guardedPythonbinding,callback scoped HDR/post only at original Road7tick; tiny8x8single/MSAAcanary, truthfulcounter/report/cleanup.
- [ ] RED CPU fake callback boundaries, borrowedcamera restoration, context identity, cold-I-S-Bhelp, noOFFhelperload, readbackMSAAerrorspartial, pixelcoordsconversion. Expected missingnativeFAIL.
- [ ] GREEN native adapter preserves original7pose/14ticks/sourceRGB retention; no extra task/render, reports intervention; namedtestsPASS; commit.

### Task 3: host authentication/workflow and first actual
Files:create scripts/run_sdk3_draw_trace.py,.github/workflows/sdk3-draw-trace-v1.yml,tests/test_sdk3_draw_trace_host.py.
Interfaces:compile/stagehelperSHA,exactsourceCI/request/mounts,immutableimageSDK/ref;nativecanary→OFF→ONhost gates,allactualartifacts.
- [ ] RED authenticating/partial/limits/counters/lifecycle/control-vs-probe negatives and source-delta tests, Expected missinghostFAIL.
- [ ] GREEN host/workflow; focusedsuite/actionlint/coldbootPASS; pushnewfeature/DraftPRparent143; exactsourceCI4jobsPASS.
- [ ] Fresh request once, tinyactualGPUcanaryaccepted before fullsceneOFF+ON. Authenticate actualrun/artifact and independently inspect/pin128MiBcarrier/source14images/probechains/staterestoration. Do not end turn; continue Task4.

### Task 4: root cause isolation and repair specification
Measured mechanism spec: ../specs/2026-11-17-sdk3-depth-mechanism-amendment.md (actual02 motivates one-pixel depth clear and bounded terrain view row; no repair claim).
Files:create docs/evidence/sdk3-renderer-completion-01/**,cause-specific spec/plan amendment beforefixcode.
- [ ] Decode originaldrawtransition/program/shader/sampler/depth/resolvedpixelchain and verify sourcepixel ownership evidence with explicitMSAAlimits. Ifinconclusive execute next measured single-variable contrast within declaredallowance; preserve allnegativecases.
- [ ] Write exact evidencedcause, invariant to restore, smallest proposedchange and REDreproductionbefore implementation. Stop speculativefixes; no request rerun or gateweakening. Continue Task5 without usercheck-in.

### Task 5: cause-specific repair and repeated renderer validation
Files:new versioned repairadapter and tests named by Task4 amendment; no originalproducer edits.
- [ ] RED reproducedcause/currentfailure; GREEN minimalrepair; CPUregressions/sourceCI.
- [ ] Bounded fresh independent repeat/contrast, original semantics/sourcepixel equivalence and +posepositive controls. Repairclaim only if cause and effect verified. ContinueTask6.

### Task 6: official MD-V3 fresh four-condition cohort
Files:new explicit candidate modelnative/hostvalidator/workflow +CPUtests; immutable officialweights only ephemeralhost.
- [ ] RED matrix/source/modelSHA/feed/state/lifecycle negatives; GREEN newvariantentry noobservers; exactsourceCI4jobsPASS.
- [ ] Fresh4casejobs×2independent children×12steps =8/96actual. Independently compare all rawsource/warp/I420/action/state/trajectory and regenerate strict4/4 verdict; failures remainFAIL. Preservebaseline3/4 separately. ContinueTask7.

### Task 7: review, final gates and full closeout
- [ ] Onefreshwholebranchreviewbase143..finalsource; ImportantoneRED→GREENpass andaffectedactualevidence revalidation; Minor defer/no rereview.
- [ ] Report each of3objectives withactualevidence and scopedroadmapgates; exactfinalHEAD4CIjobs/fullcountsPASS, Draftbody/source/parent143/main/original6filepreservation.
- [ ] Archive ownledger and exactHEAD externalreceipt; deleteonly ownscratch. Finaluserresponse after3objectivescomplete or unavoidableexternalblocker; includeallRulings/minors. No merger/publication.
