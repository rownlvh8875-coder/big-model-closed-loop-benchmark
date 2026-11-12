# Retained raw pixel neighborhood and CPU intervention analysis

## Intent and authority

User requests sequential autonomous continuation without repeated technical
questions. Accepted study source582cc594d127e9cde5ff3525e50c143f60285f75,
run43149053427/artifact13912454399 records retention A/A first raw difference
at step2: Road3pixels/Wide1pixel, followed by13packed I420 values. The next task
is CPU analysis of existing evidence, with ZERO new native/GPU/ORT/model calls
inside the forensic tool/archive replay. Unchanged baseline tests may execute
their generated SMALL ONNX fixture, counted separately; no official inference.

## Approach

Root selects a standalone CPU tool plus human/machine report. Manual location
inspection alone cannot establish influence through resampling; a new native
probe would add observation effects before existing evidence is exhausted.
Use retained actual intrinsics and unchanged production warp/I420 to enumerate
all subsets of the four raw pixel changes IN MEMORY. These are CPU transform
interventions, never altered model feeds or model counterfactual experiments.

## Data contract

`scripts/first_divergence_pixel_forensics.py` imports only CPU capture/optics/
adapter utilities and starts no providers or sessions. Required APIs:
`pixel_locations(lhs, rhs) -> list[dict]`, `analyze_pair(raw_a, raw_b,
intrinsics) -> dict`, `verify_archive(root, archive) -> dict`,
`run(root, archive, out) -> dict`, plus CLI `--root --archive --out`.

Images are uint8 HWC RGB, pair keys exactly road/wide. Pixel neighborhoods
are radius2 with clipped bounds and literal top-left coordinates. At most4
changed pixels total are admitted, ordered Road then Wide and row-major.
Every one of2^N subsets starts from immutable A copies and substitutes all3
channels of selected pixels from B. Save packed SHA/checksum, changed byte
indices/coordinates/values relative to A, camera counts, and minimal subsets
that exactly reconstruct B. Compare the joint signed-byte delta to the sum of
singleton deltas; do not assume linearity through interpolation/quantization.
Endpoint0/all must exactly reconstruct saved A/B canvas and packed NEW_IMG SHA.
Unchanged pixels produce the one empty subset and exact endpoints.

Archival `run` requires NumPy2.4.6/OpenCV5.0.0.93, the existing original ZIP
27428724bytes/SHA370ef36862e3da5bf39064acc732ff1728b0a0a549b6fba77045ce7380a8c748,
141safe unique regular members/187115633uncompressedbytes. Verify every member
against existing extraction without writing/extracting; reject links/extra files,
duplicate paths, unsafe members, altered source map or failed/mismatched trials.
Check both retained trials/step1+2 and62producer Git blobs/current bytes, saved
pose/intrinsics/prestate/fixedfeed equality at step2, and raw/canvas/packed SHA.
Tool establishes offline pinned-byte provenance, not live API authentication.
Root refreshes actual API metadata separately before running the archived data.

Write only an exclusive fresh output JSON <=1MiB, outside the original input
root; reject existing/symlink output paths before allocation. New script/test
are not native producer paths; all62existing producer bytes/protected13/
baseline43/all42workflows/consumed requests stay unchanged. No local official
weights/native/Xvfb/ORT, no new CI native workflow, no renderer/converter/action/
6-16-10/default changes, no Cloud publication/main merge/worktree or raw deletion.

## Completion

Meaningful CPU tests cover signed arithmetic/locations/clipped patches, invalid
images, no-op and cropped pixels, camera independence, subset cap, immutable
inputs, and no-overwrite/source/runtime/archive rejection. One full CPU suite,
actual archive analysis with recorded versions, source/history inspection and
fresh whole-branch review precede draft PR push. Runtime import guard applies
to explicit archival CLI/run, not generic math helpers inside a mixed unit suite.
Publish code, source/ZIP/report digests, exact neighborhoods/subset influences,
human limitations and a concrete next observation boundary; preserve original
strict FAIL/geometry-optics-fullS limits/Stage7 incomplete. Pixel RGB alone
cannot identify a shadow/lane/triangle or a unique GPU mechanism.
