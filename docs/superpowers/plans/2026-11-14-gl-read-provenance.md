# Retained GL read provenance implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline; one fresh whole-branch/source+actual-saved-data review, no implementer delegation.

**Goal:** Reconstruct original read→RGBdraw→HDRresolve command routes from retained traces.
**Architecture:** Inert stdlib event reducer and bounded pinned offline decoder; separate actual comparison runner/report. No replay or native authority.
**Tech Stack:** Python3.11 stdlib; existing pinned apitrace11.1 CPU data decoder.
**Spec:** ../specs/2026-11-14-gl-read-provenance.md

## Global Constraints

Preserve299oldsourcepins/alloriginals/consumedrequests/main. Samecheckout/ownbranch,
noadditionalworktree/delegation. No native/GL/provider/model/ORT or replay. Bounds:
120000calls/2GiBpickle/128MiBtext/1MiBline/20000nodes/256objectskind-context/
256reads/16MiBJSON/120sdecoder. No returned-pixel/sharedframe/GPUcause/neutrality claim.

## Review Focus

1. Object namespaces/lifetime/context and FBO read versus draw bindings cannot alias.
2. Conservative possible writes/partial clears/mipmaps never masquerade as pixel contents.
3. Shader-sampler dependencies come from original reflection/location/unit, not all ints.
4. Unsupported operations/thread/global/truncation or exhausted budgets cannot complete.
5. Old traced-frame markers cannot be promoted to new sealed physical-frame association.

### Task1: Pure command reducer

**Files:** scripts/gl_read_provenance.py; tests/test_gl_read_provenance.py.
**Interfaces:** `analyze(events,*,max_calls=120000,max_nodes=20000,max_reads=256)`;
events tuple(call,fn,args-pairs,return,flags), `Pointer` typed int; report nodes/reads/
routes/counters/limitations. Each node records call/kind/context/outputs/dependencies.

- [ ] RED tests: selected readbuffer/bindtargets; texture/renderbuffer namespace;
context separation/shared rejection; deletion/reuse; actual sampler reflection+unit;
MSAAblit route; partialclearpreviousdependency; mipmap preserveslevel0; feedback
acyclic; pointer-only readbytes unobserved; unsupportedwriter/malformed/budget fail.
- [ ] Run focusedunittest, expectedFAIL missinganalyzer; implementboundedreducer;
same command expectedPASS. Commit code/tests with ledger.

### Task2: Bounded data decoder and actual retained analysis

**Files:** scripts/gl_trace_reader.py, scripts/analyze_saved_gl_reads.py;
tests/test_gl_trace_reader.py; docs/evidence/GL_READ_PROVENANCE_01.json, result/ledger.
**Interfaces:** `decode(tool,trace,*,thread_ids=...)` yields reducer tuples from
restrictedpickle after threadscan; pinnedinput/tool receipts feed actualrunner.

- [ ] RED restrictedglobal/truncatedpickle/bytecap/threadscan/no-shell-command tests;
implementdecoder/cleanup/toolpin verification, expectedfocusedPASS.
- [ ] Authenticate package/tool/trace/nativeJSONreceipt bytes; run fullactualstreams
once into freshignoredoutput; native/GL0. Preserve source/data/CPUcost receipts and
bounded actual route report, no synthetic substitute.
- [ ] Fullsuite expectedPASS. Onefreshreview of wholebranch and actualsaved routes;
record all findings/declinedscope/cost rulings; oneCritical/ImportantTDDfixpass/fullsuite,
no rereview. Commit result/rulings, ownDraft/exactpush+PRCISUCCESS/artifacts0.
- [ ] Final old299/source/originalsha/main/oldworkflowcountsunchanged audit; preserve
continuation and consumedallowance0. No newnativeworkflow. Finalresult only.
