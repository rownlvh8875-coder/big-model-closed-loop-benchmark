# Original readback return-buffer core — CPU preparation

## Intent and approach

After equal CPU submissions and recorded read/resolve routes, the missing boundary
is the original readback's returned buffer. Pinned PandaGSG source passes a RAM
pointer directly to glReadPixels, then may reorder components. Its ELF exposes both
that GL import and the outer GSG method. RAM-size access is not an exported standalone
symbol. Existing sealed environment rejects added preload libraries.

Choose a small injectable C core plus strict Python wire/normalization/candidate
matcher, with compiled synthetic CPU originals. New live interposition would need
qualified ABI/span/state suppliers and a new runtime contract; source patch/rebuild
would cost more. This stage completes the reusable core and concrete admission
handoff, never pretends it observed GPU bytes or authorizes a native run.

## Core contract

Linuxamd64/C11, no GL/Panda/ORT linkage, no loader/constructor/preload symbols.
Call the supplied original read-function pointer exactly once with unchanged args;
capture only after it returns. Restore its errno even if observer/emitter fails.
No GL query,extra read,render/task call,malloc or retry inside the wrapper.

Caller supplies an immutable borrowed buffer extent and observed pack/context/FBO/
producer-label metadata. These are ABI-adapter preconditions, not authenticated by
the core. Unknown state,PBO binding,unsupported formats/overlap/overflow/short extent,
scratch alias,wrong thread,reentrancy,emitter failure and budgets fail sticky while
the original still runs. Single owner thread; other callers only forward and fail.

Supported GL_RGB/RGBA/BGR/BGRA with GL_UNSIGNED_BYTE. Width1..964,height1..604,
alignment1/2/4/8,row length/skip state bounded; source access span<=8MiB.
Copy only actual pixel columns into caller-owned private scratch, excluding padding
and skipped bytes. Preserve bottom-up original component order, including alpha.
No pointer address is serialized. Default limits24records/64MiB total wire bytes,
12windows/1or2original reads perwindow. OFF emits no data/copies, only terminalstats.

## Wire and matching

Little-endian data header160B: magic RBRET001,version1,size160,indexu64,nonce32B,
hostcallu32,requested-camera u32,producer-camera u32,readFBOu32,contexttagu64,
x/y/w/h int32,format/type u32,alignment/rowlength/skippixels/skiprows/PBO/labelbasis
u32,payloadbytes/rowstride/firstpixeloffset/borrowedcapacity u64. Tightly packed
payload follows. Producer labels are caller claims, never proof of native identity.

Terminal footer96B: RBEND001/version1/size96/nonce32B,scoped-forwards/attempts/
captured-records/data-wire-bytes/closed-windows u64,erroru32,enabledu32. Decoder
requires external expectednonce/windows/reads/mode, full footer and exact totals;
truncation at any record boundary is not successful completion.

Review correction: a complete footer cannot attest to its own emission success.
decode_stream additionally requires a trusted out-of-band producer_receipt with
schema readback-return-producer-finalization-v1,nonce(hex),stream_sha256,
stream_nbytes,finish_result,error,forwards,attempts,captured,data_wire_bytes.
The caller obtains actual post-rb_finish return/stats and successful sink/spool
finalization, then binds the stream hash/length. Never derive success from footer
status. Missing/failed/mismatched receipts reject completion. This is a trusted
caller precondition, not cryptographic process/native attestation. A future adapter
must qualify that receipt transport and process/window binding.
Per-window excess reads fail before observing metadata/copying; originals still run.

Python normalizes to top-down RGB without touching source bytes. A matcher returns
unique/no/ambiguous CPU-byte candidates only, requiring nonce/call/requester/producer
labels/context/shape. Unknown producer metadata cannot become a unique association.
All outputs deny GPUwrite success,physical-frame/native authority and Stage7 proof.
Void GL return itself does not prove a successful or fresh GPU write.

## Verification and delivery

Use TDD: real compiled C fixture with a CPU-only fake original and independent
Python wire expectations; layout,forwarding,errno,OFF,budgets,invalid metadata,
thread/reentrancy,partial emitter,complete footer and ambiguity. Run ASan/UBSan
synthetic smoke when compiler supports it; no renderer/GL context. Record compiler/
flags/source/binary/dependency hashes as synthetic build evidence, not qualified
native artifacts. Static ELF/source audit and pure environment rejection probe.

Same checkout/own branch, no new worktree/implementer delegation. Preserve every
basef8994f1 tracked file,original dataset and consumed allowance0. Full suite,one
fresh whole-branch review,oneImportant/CriticalTDDfixpass,no rereview/minorpolish.
Own Draft/exactCI; no mainmerge/Cloud/registrypublication/newnative/model/ORT run.
Source-spans/GL dispatch/camera identity and fresh runtime admission remain explicit
inactive gates for the next stage.
