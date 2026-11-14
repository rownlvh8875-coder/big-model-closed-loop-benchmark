# Retained GL read/resolve provenance ledger

Base3555a133ed3ae999cdcb86ab3867fe3f5005530e; feature/gl-read-provenance-v1.
Plan: superpowers/plans/2026-11-14-gl-read-provenance.md.

Ruling: Continue inline/no extra worktree/questions using persistent user choice —
new scope is CPU-only retained-data analysis — wrong scope spends development/CPU
effort but creates no new native/provider/getter/model allowance.
Ruling: Analyze resolve/read routes instead of another live trace or GPU extraction —
old draw inputs are already analyzed and extraction disturbed image updates — old
trace capability/timing perturbation and no current sealed-frame association remain.
Ruling: Treat writer commands/dependencies conservatively, never simulate exact GPU
contents — scissor/masks/undefined data/conditional fetches prevent inference — routes
can contain earlier possible producers and cannot select a unique cause.
Pre-flight: reducer tuples come from bounded decoder; original reflection supplies
samplers; actual runner requires pinned traces/tool/receipts and never executes them.
Baseline: clean3555a13 with full1285tests/7skip and exactsource/evidenceCIgreen from
prior completed task; no old source changes or dependency installation.
Task1:13tests RED missingreducer→GREEN; bound renderbuffer deletion test exposed
missing detachment RED→GREEN. Focused14PASS0.007s. Fullsuite gate remains Task2.
Ruling: Support only unshared contexts and 2Dlevel0 framebuffer attachments — actual
traces fit this scope; unsupported commands reject — future broader traces require
explicit extension, not a false full-GL reconstruction.
Ruling: Add64MiB individual pickle-read request cap — the whole2GiB budget alone
does not bound a malicious declared allocation — larger valid blob records stop
analysis rather than allocating unbounded memory; pinned actual traces checked later.
Actual saved-data failure01 is retained: originalglDrawBuffer argument ismode,notbuf.
Corrected fixture/consumer RED→GREEN; decoder closure on reducer failure RED→GREEN.
Failure02 is retained: pinned originalCPUupload atcall6785 requests201326592B.
Ruling: Raise per-request cap64→256MiB under unchanged2GiBstreamcap — authenticated
192MiB originalblob cannot fit64MiB; validrequest regression RED→GREEN — transient
CPU allocation can be hundreds of MiB, not memory-headroom proof. No new native run.
Failure03 retained: a later originalCPUupload atcall12606 requests507510784B.
Ruling: Final per-request cap512MiB under unchanged2GiBstreamcap — actual pinned
484MiB upload exceeds256MiB, regression RED→GREEN — transient decoder/Python memory
can approach/exceed1GiB across copies; no RSS/headroom claim or live graphics work.
Failure04 retained: defaultdump omits6021verbosecalls (100534vs106555pickle).
Fullthreadscan with --verbose independently yields106555/oneGLthread0/22547015textB.
Decoder command regression RED→GREEN; strict count equality is retained rather than
relaxed. Failure receipts now include current decoder receipt, even if incomplete.
Task2 actualanalysis05: completewhole106555/106580calls,60reads+90blitseach,
all60pairedreadroutesmatch. ON0/ON1 fullgraphs6354660/6354686B, retainedoriginaloutputs;
decodedpickle978935426/978937188B;thread0/2unsharedcontexts. Originaltrace/input/tool
SHAverified including packagedbinary. Source299pins independentlyhashcheckedunchanged.
Wholeanalysiswall32.334334439s,parentCPU20.660532352s excludingdecoderchildCPU,
failed/debuganalyses,tests/review/CI. No native/GL/model/ORT/newprovider/allowance.
Focused31PASS0.159s; full1316tests/7skipPASS116.057s. Freshwholebranch+saveddatareviewpending.
Ruling: Treat samples4 as recorded storage-request metadata — no new or interpreted
actual sample-count query — physical allocation/effect is not established by thisfield.
Ruling: Keep existing primary10-frame read mapping labeled schedule-only — original
read arguments contain no returned pixel bytes or capture nonce — matching routes
cannot prove same physical camera/GPUframe or associate newer sealed counterexamples.
Fresh wholebranch+saveddatareview689b89cb: Critical0/Important4/Minor0. Independent
trace/fullgraph/evidence/old299SHA and actualRoad/Wide command samples all passed.
Singlefixpass: I1 full active-count/index reflection gate plus pre-reflection integer
assignments retained; I2 default FRONT/BACK/NONE separated; I3 read/source/texture/FBO
lifetime endpoints enter route comparison; I4 current299sourcebytes actually hashed
against pinnedqualifiedreceipt before any affirmative preservation count.
Each finding reproduced RED (10failures across6regressions)→GREEN; focused37PASS0.166s.
Fullsuite and actualoffline06reanalysis running; no second reviewer/minor polish.

Final: Ruling1: Judge issued possible-write/dependency commands, not executed writes,
pixelvalues,samplefetch/LOD,complete shader/raster/vertex behavior or completion —
conservative dependencies preserve uncertainty — a GPU content/cause claim remains absent.
Final: Ruling2: Keep requested samples distinct from actual multisample allocation
or resolvedpixel equality — no new query occurred — matching storage requests alone
cannot establish effective GPU storage or pixel contents.
Final: Ruling3: Retain inherited host schedule only — destination pointers contain
no returned bytes/capture nonce — physical host/camera/GPUframe association staysunproved.
Final: Ruling4: Do not join this older traced cohort to newer sealedC/A, untraced
execution,neutrality,repair,official model input or Stage7 — evidence does not support
those extensions — the original0/4FAIL/INCOMPLETE and consumed allowance0 stand.
Final: Ruling5: Fresh reviewer did not repeat full~2GiB decode/fullsuite — root ran
both and reviewer independently hashed original/fullgraph/source/evidence and sampled
actual commands; after fixes root repeats fullanalysis/tests with no rereview — shared
source/parser blind spots remain possible, not erased by two independent roles.
Final: Ruling6: No exactRSS/headroom/decoderchildCPU/failed-debug-total/end-to-endcost
estimate — only successful parent/wall scopes are measured — real CPU/I/O/memory and
latency costs exceed those scopes and transient copied blobs can exceed1GiB.
Final: Ruling7: Read-only review grants no live captures/replay/native/provider/model/
ORT/package install/merge/publication — root proceeds only with already-authorized own
Draft/exactCI, no newnativeworkflow — external CI success requires separate evidence.
Final: Ruling8: Keep scoped2D/unshared command support with explicit rejection of
unsupported writers/reflection/default selectors — no fullOpenGL model is promised —
broader traces stop instead of silently acquiring complete route authority.
Final: Ruling9: Assume retained local inputs/decoder remain immutable between checks
and reads — privileged concurrent mutation/compromised dependencies are outside this
scope — hashes do not create new remote or physical runtime trust.
Deferred minors: none. All four Important findings enter this single fix pass.
Final: fixedI1 test_missing_or_partial_active_reflection_cannot_complete and
test_integer_assignment_before_reflection_retains_sampler_unit RED→GREEN;
fixedI2 defaultFRONT/BACK/NONE tests RED→GREEN;fixedI3 changedreadendpoint/lifetime
test RED→GREEN;fixedI4 changedsourcepreservationtest RED→GREEN. Focused37PASS;
finalfull1322tests/7skipPASS125.086s. Single fix pass complete; no rereview.
Actual06reanalysis still106555/106580calls,60reads/90blitseach/all60routesmatch,
with endpoint/lifetime/reflection/source-validation fixes active. Source299preflight
verifiedbythisrun. Wall45.402455962s,parentCPU28.602519559s,sourcepreflight0.057838852s;
pertracewall26.335314337/19.061084480s. Fullsuite ran concurrently; neither comparison
to05 nor these scopes estimate instrumentation overhead. Both05/06 originals retained.
Finalcurrentresult after-fix/result.json;24proofs1642018B,full06graphs13247714B retained.
