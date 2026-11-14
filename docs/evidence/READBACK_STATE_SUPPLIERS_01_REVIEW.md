# Sole fresh whole-branch source and CPU proof review

Reviewer readback_state_suppliers_01_whole_review, gpt-6-astra/medium,fresh context.
Base868f65e368bcb811bce64f61c988a27bbed612f2..0d330c32f702190ce9d4d6ead21f8b940ee08fe8.
Original verdict With fixes; Critical0,Important2,Minor0. One fix pass/no rereview.

## Strengths and independent verification

C originals run once with unchanged args and preserved returned errno despite cache
failure. Context generations/switches/localpack/read-draw/perFBO/deletion states are
bounded and fail closed. Real CPU integration uses existing assembly/core/codec and
receipt checks. Evidence consistently distinguishes commands from driver/GPU/native
authority. Reviewer independently passed24focused tests and all41fresh normal and
ASan/UBSan scenarios matching retained streams/stats/acceptance.47proofs582205B and
buildsource hashes match. Full1394suite was not independently rerun.

## Important1: final GSG handle descriptor reentry bypasses sticky rejection

scripts/readback_camera_registry.py:84,also59/71. A retained GSG.this property calls
guard, catches nested RegistryError and returns its valid handle. The pre-read error
check does not see failure caused while reading the property. native_binding
returned its complete tuple while descriptor error was RegistryError; final guard
handle reads can similarly precede success without another error check. Check
sticky error after every callback-capable handle read and before return/commit,
keeping busy through validation; test swallowed GSG descriptor reentry.

## Important2: GSG getter can change owners after the sole ownership check

scripts/readback_camera_registry.py:68–72 and init26. Wide buffer getGsg changes road
texture handle/replaces camera or buffer/provider chain then returns expected GSG.
guard succeeds/increments guards_returned with stale identities. Independent fake
hook setting roadTexture.this=123 yielded guards1/getter_attempts4/errorNone. Keep
cheap prechecks, then revalidate owner/handles after the pair without extra getGsg
calls; check sticky failures after validation callbacks. Test init/guard mutations.

## Recommendations

Fix both registry findings with RED regressions, preserving26getter cap and unchanged
success counters on failure. C supplier/proofs need no semantic changes. Regenerate
changed-source evidence. No Critical/Minor findings.

## Declined to judge (author rulings required)

1. Actual driver-state changes/GPUwrites from void calls: deferred live gate; CPU originals cannot establish them.
2. Authentic context-create/current/destroy notifications: caller-delivered command contract only.
3. Undelivered mutations/client-attribute restoration/uncovered entry points: future coverage must deliver/invalidate.
4. Real Panda/Texture/GSG/buffer/native allocation/lifetime/sameaddress reuse/liveprovider compatibility: CPU fakes only authorized.
5. DefaultFBO/shared contexts/differingGSGs: explicitly rejected by spec/rulings.
6. Invalid C storage/delete span/null/nonreturning originals/concurrent cache-storage destruction: excluded caller preconditions.
7. External process/window/sink receipt authenticity and sink-finalization transport: synthetic integration only, live transport unqualified.
8. Runtime loader/mapped dispatch/renderer/nativecanary/model/officialORT: outside task/prohibited in review.
9. Native performance/renderer overhead: timing is CPU build/test scope only.
10. Entire immutable core/assembly/codec and whole1394suite: integration/focused/all41compiledcases inspected/rerun; fullsuite not rerun.
11. PR publication/exactsourceCI/finalpostreviewpreservation: closeout work, not completed claims of reviewed snapshot.

## Assessment

With fixes. Command cache and synthetic proof chain are coherent and reproducible;
two registry rejection gaps must be fixed before suppliers are complete.
