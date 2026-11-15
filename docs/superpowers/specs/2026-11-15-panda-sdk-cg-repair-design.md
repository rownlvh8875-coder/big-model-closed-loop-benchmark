# Cg-aware Panda SDK candidate and static layout contract

## Intent and current evidence

Repair the confirmed SDK/wheel member-layout incompatibility while retaining the installed Panda1.10.13 wheel, its model/physics modules, current image and all consumed execution receipts. The previous SIGABRT's exact cause remains unconfirmed; it may precede GSG creation. This design targets a demonstrated incompatibility, not a retrospectively proven crash fix.

Bound authority is [contract.json](../../evidence/panda-sdk-cg-design-01/contract.json), derived from the unchanged [ABI audit](../../STAGE7_PANDA_OBJECT_ABI_AUDIT_RESULT.md). SDK8d302ae2 and wheel share upstream470e352, but three same-named GSG member offsets differ by112bytes. SDK HAVE_CG is undefined; wheel Cg code and ShaderCaps conditional fields are present. Selected vtable agreement and static link success are insufficient.

Persisted user preferences are same checkout, inline execution, no repeated permission/menu questions, own Draft and no publication/merge. The implementation method remains inline; this design does not open an execution window. The current task delivers grounded design, pinned inputs and an actionable candidate-build plan. No candidate build, runtime fix or image replacement occurs in this design task.

## Approaches and choice

1. **Selected: retain wheel; build a separate Cg-aware SDK candidate and fail on layout mismatch.** This changes the narrowest artifact and preserves Python/Bullet/MetaDrive modules. It requires genuine Cg headers, authenticated current-image Cg libraries and measured tool inputs. Enabling Cg alone is not assumed sufficient; the candidate can fail the static gate. This is the executor's choice under the user's delegation, not a newly stated user preference.
2. Rebuild the entire Panda wheel and SDK from one configuration. This could eliminate mixed configuration, but changes every Panda provider/Python extension and expands model/physics compatibility work. It is a separately scoped alternative if the selected candidate cannot satisfy the contract; there is no automatic fallback.
3. A GCC14.2 OCI builder was inspected only through registry manifests/config (no layers pulled). Its mutable tag is not authority. The available local host has only about580MiB free, and an extra compiler image/tool bootstrap would add machinery without establishing compatibility. The chosen execution location is a fresh ubuntu-24.04 hosted runner using explicit gcc-13/g++-13 with a new per-build profile. It is intentionally not the prior Debian GCC14 profile or a controlled Cg-only experiment.

## Inputs and provenance

- NVIDIA HTTPS source: https://developer.download.nvidia.com/cg/Cg_3.1/Cg-3.1_April2012_x86_64.tgz ;24829131bytes; SHA256 **e8ff01e6cc38d1b3fd56a083f5860737dbd2f319a39037528fb1a74a89ae9878**. TLS/default CA validation and exact acquired digest are recorded; no independent publisher digest or signature verification is claimed.
- Only usr/include/Cg/cg.h (64961bytes/SHAfdcfeba9b8507437baad347d75c8c2b2599a845b515861bcc535d7af9941c6ed) and cgGL.h (13653bytes/SHA10711fe206ba4ede0a8949d2d91c2a828a85c5e6f60550bae1a8f16c9f102d5a) enter a **new** private sysroot. CG_VERSION_NUM=3100. Panda parser-inc/Cg files explicitly say they are not compiler headers; reject them even if they parse.
- Link providers come only from the authenticated current image: libCg.so20398129bytes/SHA942f33fe1e0935445d88e0595089fda99d20335ef089b5205d61cd6ade054018 and libCgGL.so545121bytes/SHA034f5ac079da5d56dcfe621c3ea9b6aaff553fc44ecfb630c167c91c68abe0df. Preserve their manifest paths. Do not use toolkit runtime DSOs or examples/Trace libraries. Toolkit and wheel whole files differ, while selected .text/.rodata section sizes/hashes match; that comparison does not establish complete DSO/header ABI identity.
- Retain the source revision470e352 and the current routes-v2 instrumentation/source pins. The old source, sysroot, build tree and image are read-only references. Create fresh directories; never inject Cg into the old sysroot or edit old generated headers.
- Reconstruct GL/X11 headers from the existing pinned dependency packages into the new sysroot. Replace old host-absolute linker aliases with explicitly recorded aliases to current-image provider DATA. Compiler standard libraries are measured **host toolchain** inputs, not authenticated image providers. Dependencies outside source/generated/private/measured-host roots fail.
- Use /usr/bin/gcc-13 and /usr/bin/g++-13 on ubuntu-24.04. Required Python3,binutils,bison,m4,pkg-config and compiler subtools must exist at preflight. Missing tools stop with a retained BLOCKED receipt; no implicit apt install, compiler substitution or external OCI fallback. Record resolved tool files, compiler queries, selected subtools, link inputs and host-header catalogue before build; qualify all actual .d dependencies afterward. Pre/post identities are point-in-time evidence, not continuous compiler-execution attestation or bit-for-bit reproducibility.

## Candidate build boundary

The future implementation adds separately versioned modules and one build-only workflow. No old module/workflow/request is edited. Closed source/CI/request/unique run/job/artifact/TLS acceptance must bind the actual candidate build; a static JSON claim alone grants no origin.

Build argv retains --nothing/--use-gl/--use-x11/--no-python/--no-copy-python/--optimize3 and ABI0, adding the real package name **--use-nvidiacg** (not --use-cg) plus explicit nvidiacg/cggl include and library directories. Every compile has one -D_GLIBCXX_USE_CXX11_ABI=0 and one -MD; two workers. Generated configuration must have HAVE_CG,HAVE_X11 true,HAVE_PYTHON,STDFLOAT_DOUBLE false. Capture all other generated macros and compare to the prior profile; do not call them equal to unknown wheel flags.

One build start maximum after complete input/tool preflight. Compile limit1200s, whole producer2400s, output8GiB, total owned workspace12GiB, minimum initial free16GiB, logs32MiB, carrier ZIP256MiB. Host headers≤65536nodes/1GiB. Host memory capacity is recorded; this direct-host design does not claim an aggregate cgroup memory limit or runtime sandbox certification. Compiler subprocess groups are owned and reaped; timeout cleanup affects only that group. Failed-start/compile/link/dependency/gate cases retain exact argv, preflight identities, return/signal/timing, bounded stdout/stderr and cleanup facts. No automatic rebuild/retry.

Allowed native activity is execution of measured host build tools. **No generated target/probe execution, SDK load, Panda Python import, GL call, Xvfb, Docker image load/start, image transform, model/ORT/cohort, registry/Cloud publication or main/shared-base update/merge.** A build-only slot is distinct from a runtime window and cannot replay any consumed slot. No build or slot is activated by this document.

## Compile-only descriptor and necessary static gate

A new native/panda_sdk_cg_v1/layout_contract.cxx emits a fixed uint64 little-endian descriptor in .panda_cg_layout with magic/version, pointer size8, ABI0,HAVE_CG=1,sizeof ShaderCaps/GraphicsPipe/GraphicsStateGuardian/GLGraphicsStateGuardian and offsets of _gl_vendor/_gl_version_major/_gl_version_minor. Include the real generated glgsg.h and shader.h. Use the same compiler/headers/flags as the SDK. Only this object may use -fno-access-control and -Wno-invalid-offsetof to measure protected/nonstandard-layout fields with GCC __builtin_offsetof; record these probe-only options. Compile with -c, never link/run it. Require no executable code or init-array in this data descriptor object. Descriptor values are compiler-specific measurements, not portable C++ ABI proofs.

Necessary admission to **static candidate readiness**, all required:

1. Real input/tool/source/dependency records and generated HAVE_CG verified;33existing activity/cache/command exports and exactly one source-state object retained.
2. SDK integer getter instructions independently decode member offsets major0x688,minor0x68c; vendor accessor's member address0x670. Cross-check with the compile-only descriptor. Old offsets0x618/0x61c/0x600, a forged descriptor with old code, unknown instructions, out-of-file/overflow/ambiguous symbol spans or changed pinned baseline all reject.
3. ShaderCaps descriptor must include the Cg profile fields (size≥32); retain candidate build-provider ShaderCaps::clear evidence as DATA. This is not an assertion that the candidate build's libpanda is installed or that clear executed.
4. Existing bounded ELF loader/provider audit must find zero missing strong root imports against authenticated current-image providers, with the three existing weak exceptions explicitly named from the frozen prior audit. Recompute and retain version-library diagnostics; do not promote previous105diagnostics or selected global availability to full binding/closure qualification. New Cg/CgGL bindings must select the exact pinned image DSOs.
5. Candidate public GLGraphicsStateGuardian vtable size1024 remains a necessary check. Do not reuse the ad-hoc ABI audit reader as a production boundary or interpret125previous named agreements as new runtime proof.

The success carrier has three DATA candidates (candidate/libpandagl.so.data≤4MiB,candidate/layout-contract.o.data≤1MiB,candidate/build-libpanda.so.data≤64MiB), a closed reports/ set (receipt,gate,inputs,tools-before,tools-after,host-before,used-inputs,compile-dependencies,sdk-output-manifest,source-manifest,configuration,layout,provider-audit,loader-metadata JSON; ≤16MiB each), and logs/makepanda.log,logs/host.log (combined≤32MiB). Total ZIP≤256MiB. Reject paths/links/duplicates/unlisted files and inconsistent lengths/digests. A failed carrier may omit candidates/reports not produced, and must declare omissions; a success requires every named report/candidate. The independent acceptor recomputes the selected layout/link predicates from actual carrier candidate/object bytes and separately authenticated current-image providers, rather than trusting producer success fields.

Success status is **CG_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME**. Full class-size parity with the wheel remains unknown: the wheel has no C++ configuration headers. Record measured candidate sizes without inventing wheel values. Passing these necessary checks is neither full object ABI qualification nor proof that the earlier abort is fixed. Failure is retained and stops before any image preparation. The candidate hash is learned from actual compiler output and bound to its receipt; never put the old SDK hash in a new candidate success record.

## Subsequent boundaries

A passing build artifact is only an input for a **separate** new image-preparation contract; old image03 and producers remain unchanged. A later, separately qualified runtime diagnostic must report nonce/PID/start/sequence-bound boundaries around core import, version/configuration, GraphicsEngine, module pipe, output/GSG and object identity. It must distinguish requested default-off from observed before/after stats and retain last acknowledged boundary on native abort. Design does not create those code paths or execution slots now.

## Preservation and completion

Current design branch is based on4b68ddd/Draft121; preserve all7087basefiles/modes,299pins,10originals,main,Drafts102–121,native8,image3,mapping01,dispatch01 and exactly one failed realGLX01 attempt. Existing260source identities and failure bytes remain unchanged.31sibling scratch directories/3846file hashes remain untouched. This task produces only design/plan/evidence and an own Draft against the unchanged base, with final exactHEAD CI4jobs/attempt1/artifacts0/body/preservation/clean-tree receipt outside its commit.

Scientific allowance0;strict0/4 FAIL;Stage7 INCOMPLETE. Previous default-off M1 remains deferred and unchanged. No equality/divergence/performance or runtime repair is claimed.
