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
