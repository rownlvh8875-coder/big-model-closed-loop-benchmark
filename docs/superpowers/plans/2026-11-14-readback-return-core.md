# Readback return core implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline, one fresh whole-branch review; no implementer delegation.

**Goal:** Build and CPU-verify the bounded original-call return-buffer capture core and inactive runtime handoff.
**Architecture:** Header-only ABI declarations plus standalone C implementation; Python strict160/96Bwire codec and candidate matcher. Static source/ELF audit identifies the future adapter gates.
**Tech Stack:** C11/pthreads, existing cc, Python3.11 stdlib. No GL/Panda/ORT linkage.
**Spec:** ../specs/2026-11-14-readback-return-core.md

## Global Constraints

Preserve allbasef8994f1 files/old299pins/originals/consumedallowance0. Samecheckout,
ownbranch,noadditionalworktree/delegation. No realGL/provider/model/ORT/replay/newnative
workflow. Caps:24records/64MiBwire/12windows/2reads/window/964x604/8MiBsource-span.
No heap allocation/query/retry in readwrapper; supplied original runs once unchanged.
Synthetic artifacts do not satisfy native ABI/runtime/source-span/camera admission.

## Review Focus

1. Original forwarding/errno remain correct on OFF,error,thread,reentrant and cap paths.
2. Pack/PBO/extent/overflow/alias validation prevents reading unbounded or unobserved memory.
3. Wire totals/footer reject truncation,partial writes and undeclared scope/camera state.
4. Normalization and matching distinguish component order/row direction/ambiguous labels.
5. CPU fake/ELF/source metadata never becomes GPU/native/frame authority or loader permission.

### Task1: C core and compiled synthetic harness

**Files:** native/readback_return_core.{h,c}; tests/fixtures/readback_return_fixture.c;
tests/test_readback_return_core.py.
**Interfaces:** storage-size/init/begin/read/end/finish/stats; Cread pointer has the
original seven GL ABI arguments. Immutable rb_read_state supplies pack/context/labels/
borrowedcapacity. Emitter accepts constheader+payload only.

- [ ] Write compiledfixture/independent wire tests RED (missingcore); implement minimal
core preserving oneforward/errno and stickyfailure. Focused unittest expectedPASS.
- [ ] Verify layouts,OFF/no data,unsupported/PBO/short/alias/thread/reentrant/caps/emit
failure,window/terminalcounts. CPU-only compilation/harness; commit with ledger.

### Task2: Python codec, source audit and synthetic handoff

**Files:** scripts/readback_return_codec.py,scripts/audit_readback_return_source.py;
tests/test_readback_return_codec.py; docs/evidence/readback-return-core-01/,result/ledger.
**Interfaces:** decode_stream(blob,expected_nonce,expected_windows,reads_per_window,
enabled); normalize_rgb(record); match_cpu_candidate(...). No native authorization.

- [ ] RED codec malformed/truncated/footer/layout/nonces/scopes/normalization/ambiguity
tests; implement bounded decoder/matcher, focused expectedPASS; interop realCfixture.
- [ ] Static pinned wheel/source/ELF audit, existingenvironment+LD_PRELOAD pureguard
rejection; generate syntheticcompiler/flags/binary/harness/dependency/sanitizerreceipt,
inactive actualruntime/ABI/span-supplier handoff. Native/GL/model/ORT0.
- [ ] Fullsuite expectedPASS. Onefreshwholebranchreview,allrulings/costs ledgered;
oneImportant/Critical RED→GREEN fixpass/fullsuite,no rereview. OwnDraft/exactpush+PRCI.
- [ ] Finalbasefiles/source299/originals/main/nativehistoryunchanged audit, progress
and explicitnext qualification gates. No publication or consumedrequest retry.
