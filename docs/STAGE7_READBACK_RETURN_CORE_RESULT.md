# Readback return-buffer CPU preparation

The standalone C core forwards a supplied original read function once, then copies
bounded returned RAM into private scratch. It does not load/interpose Panda or GL.
This closes the reusable CPU implementation step; actual original GPU bytes have
not been observed. Original strict0/4FAIL and Stage7INCOMPLETE remain unchanged.

The core snapshots supplied pre-call pack/context/FBO/camera metadata, rejects
PBOs, unknown/unsupported state, short/overlapping spans and scratch aliases, and
preserves the original post-call errno. OFF does not inspect metadata/pixels.
Wrong-thread, reentrant, cap and emitter failures stop acceptance while forwarding
the original. Calls outside explicit windows only forward. No allocation, GL query,
extra read/render/task or retry runs inside the wrapper.

Data records use independent160B little-endian headers plus tightly packed original
component bytes, retaining bottom-up RGB/RGBA/BGR/BGRA order. Padding/skipped bytes
and pointers are not serialized. A96Bterminal footer is mandatory. The Python
decoder requires external nonce/window/read/mode expectations, exact sequence and
counter totals and a trusted out-of-band producer-finalization receipt. The caller
obtains actual post-rb_finish return/stats and finalized sink/spool success, then
binds nonce, whole-stream SHA256 and size. Footer bytes alone cannot attest their
own emission result. Missing/failed/mismatched receipts reject completion; receipt
transport remains a caller trust boundary, not native/process attestation. It normalizes to top-down RGB and reports unique, absent, ambiguous
or insufficient-label CPU-byte candidates. None implies native/frame/GPU authority.

Limits are24records,64MiBwire including footer,12windows,1or2reads/window,
964×604pixels and8MiBborrowed source span. The largest synthetic fixture emits
55,900,512B. Caller-provided capacity and labels are preconditions; this core cannot
authenticate a real allocation, camera or GL state. Void return does not establish
a successful or fresh GPU write, even when memory equals a later source image.

Pinned wheel bytes match two installed Panda ELF identities. Static readelf finds
glReadPixels import/JUMP_SLOT and three outer GSG method relocations; no standalone
RAM-size export. Pinned1.10.13source calls glReadPixels directly into RAM at line7477,
then may reorder components. Versioned source is not an instruction-level ABI proof.
The existing sealed environment accepts its baseline dictionary and rejects added
LD_PRELOAD. It was not changed. The local compiled core is not qualified for that
native image and is not loaded into it.

Before independent review,26focused tests and1348whole-suite tests passed,7skip,
120.285s before review. The final C CPU fake covers25scenarios; each also passes ASan/UBSan with
the same stream and counters, including negative paths/max size. Initial build smoke took
3.627116568s wall; final build wall time is in the active receipt. This excludes fullsuite/review/CI/development and measures no
runtime GL overhead. Compiler flags, executable/source hashes, ELF dependencies,
raw small synthetic streams and max-stream identity are retained in the
[proof index](evidence/readback-return-core-01/proof-index.json).

All2431base tracked files and299old source pins are byte-preserved, along with both
original trace streams, four before/after route graphs and original sealedC/ABBA
ZIPs. Main, old Drafts and native workflow histories are unchanged. New native,
GL, provider, official model and official ORT execution counts are0. No main merge
or Cloud/registry publication. The sole fresh review found2Important issues and noCritical/Minor. One fix pass
limits capture before excess per-window reads and requires the external completion
receipt, including full-footer-write/emitter-failure rejection.29focused tests pass;
final whole suite1351tests PASS7skip121.931s. Exact Draft/head CI closeout
is recorded separately in the PR and retained `output/stage7-readback-return-core/ci-closeout/`. The reviewed pre-fix proofs remain in
`before-fix/` with relocated index; the original review is
[retained](evidence/READBACK_RETURN_CORE_01_REVIEW.md). No rereview.

The next gate is a qualified adapter: original GL dispatch/instruction ABI, actual
Texture/view RAM extent, observed pack/PBO/context/read-FBO state and camera identity,
same-process nonce/host-call binding, and a newly reviewed source/build/maps/
environment contract. Only a fresh bounded native canary allowance can then test
real return-buffer capture with ON/OFF control and raw evidence review. Old consumed
requests remain closed. Full inactive gates are in the
[machine result](evidence/readback-return-core-01/result.json), with decisions and
costs in the [ledger](STAGE7_READBACK_RETURN_CORE_LEDGER.md).
