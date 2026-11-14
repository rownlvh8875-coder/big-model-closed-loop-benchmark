# Sole fresh whole-branch source and synthetic-data review

Reviewer: readback_return_core_01_whole_review, gpt-6-astra/medium, fresh context.
Basef8994f1d6c0f4cb6c6348d50c8c6f25d6b4628c0..20f0d7e52dc3b253b22cb36607321572972cc67c.
Original verdict below. Critical0, Important2, Minor0. One authorized fix pass; no rereview.

## Strengths

- The C wrapper preserves unchanged original arguments and post-call errno, snapshots metadata before the original runs, and keeps copying bounded by validated layout, source extent, scratch capacity, and total wire budgets.
- The codec independently validates layout arithmetic, record order, external nonce/window expectations, and terminal totals. Normalization correctly handles bottom-up RGB/RGBA/BGR/BGRA, and unknown producer labels cannot produce a unique match.
- Static source/ELF evidence and CPU fixtures consistently deny native admission, GPU-write proof, and physical-frame authority. No live adapter or loader permission was introduced.
- Reviewer reran all26focused tests successfully, verified32indexed files and4retained artifact hashes, checked decoder outcomes against all22recorded CPU scenarios, and confirmed all45changed paths are additions. Reported full-suite/sanitizer results were inspected, not independently rerun.

## Important1: per-window cap is enforced after excess capture

native/readback_return_core.c:86–103,124. Configure2reads/window and invoke3valid
reads before end. A temporary compiled CPU fixture produced original_calls3,
captured3,attempts3,wire_bytes615. Only end set RB_SEQUENCE. Decoder rejection does
not undo copying/emission beyond a window's declared1or2read limit. Detect excess
scoped forwards before observation/copying, fail sticky, forward once; test1and2read
windows, unchanged args/errno and no additional capture.

## Important2: failed terminal emission leaves accepted stream

native/readback_return_core.c:139–140; scripts/readback_return_codec.py:100–107.
Emitter writes complete footer then returns failure (e.g. sink finalization/flush
failure). Temporary CPU fixture returned finish=-1,error=RB_EMIT but decoder accepted
cpu_window_closed=True with footer error0. Status precedes the operation that can
invalidate it. Require an external successful-finalization receipt bound to the
capture, or distinguish byte completeness and producer success and require both.
Regression must cover complete-footer-write then failure as well as partial writes.

## Recommendations and declined to judge

Address both boundary cases in one fix pass, preserving forwarding/native denials;
document how terminal emitter success reaches the consumer. Each set-aside item
requires an author ruling:

1. Actual GL dispatch ABI/compiled instruction binding: no live adapter; imports/relocations cannot establish this.
2. Real Texture/view extent/producer identity: caller preconditions requiring adapter qualification.
3. GPU-write success/freshness/physical frame: CPU equality/void return cannot establish them.
4. Live concurrency/overhead: synthetic fixtures do not establish scheduling/races/production cost.
5. Invalid context/storage lifetimes,inaccessible metadata,concurrent lifecycle,longjmp originals: violate documented C API preconditions.
6. Runtime admission/fresh allowance/deployment: explicitly inactive; no native execution authorized/performed in review.

## Assessment

Ready to merge: With fixes. Credible bounded CPU preparation with strong wire
validation and limited evidence claims; both findings must be corrected before
the capture/completion contract is fulfilled. No Critical or Minor findings.
