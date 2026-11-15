# Eigen-aligned Cg SDK v2: grounded design

## Intent and current task

Retain the installed wheel/image and recover necessary SDK layout compatibility. Build01 compiled successfully, but remains rejected and consumed. This task is DATA-only forensic analysis, pinned Eigen input acquisition and a future implementation plan: no new SDK compilation, target execution, image preparation, workflow activation, merge or publication. Same checkout/inline/no repeated questions/own Draft preference persists. Choices below are the executor's under that delegation.

Authority: `docs/evidence/panda-sdk-cg-residual-01/contract.json`; base912c50b/Draft123;7325existing files/modes;282closed source identities,299older pins,10originals,31sibling scratch directories/3846hashes,main,Drafts102–123,native8/image3/mapping01/dispatch01/realGLX01/Cgbuild01 remain immutable.

## Evidence, uncertainty and root cause

Build01 workflow419500017/run43764042768/job132965048079/attempt1, activationffc6d918c4b07605a32d22073827fc2241737b2d; independently authenticated output origin, static rejection. Candidate SHA5f466f01b7eb11345658910e6108f073b1bd68b7f04ebdf791e3df90b223269e,1056664B. It has Cg/X11, ABI0 and float32; no Python. Real getters major0x678/minor0x67c/vendor0x660 are16bytes earlier than required0x688/0x68c/0x670.

The residual starts in the base GSG before Cg fields. Candidate/wheel `_internal_coordinate_system` both0xdc; `reset()` stores four16B vectors at candidate0xf0/0x108/0x11c/0x12c versus wheel0xf0/0x110/0x130/0x140. Source-order layout with vector alignment4 versus16 predicts these exact stores, incomplete-render0x148 versus0x15c (20B), then loader/prepared-object pointer alignment reduces the difference to16B (prepared0x158 versus0x168). Subsequent gamma/engine and derived getters retain16B difference. Disassembly, literal descriptor and authenticated source tree identities are retained.

Candidate generated config says LINMATH_ALIGN=1 but HAVE_EIGEN is undefined. Pinned `dtoolbase.h` explicitly undefines LINMATH_ALIGN without HAVE_EIGEN; `lsimpleMatrix.h` then removes ALIGN_LINMATH and uses plain float arrays. Thus the candidate's effective vector alignment differs from observed wheel layout. **Enabling pinned Eigen is a source-consistent proposed correction, not a demonstrated v2 build or proof of the wheel's original Eigen version/full flags.** Wheel class sizes, complete ABI and the previous SIGABRT cause remain unknown. Do not pad members, force offsets, patch the wheel or merely change expected offsets.

Two independent gate issues were localized: integer functions start with CET `f3 0f 1e fa`, unsupported by the old7-byte decoder; descriptor includes collision-mask `lower_on(20)`/`bit(20)` initialization and a Panda version-check body. The .panda_cg_layout constant section itself has no targeting relocations. A separately derived section-only object passes the old literal parser, but correctly still fails member offsets. Neither observation changes the consumed verdict or grants readiness.

## Approaches and choice

1. **Selected:** new versioned Eigen-aware builder, CET-complete gate and section-scoped descriptor contract. It directly addresses the observed source/layout differences while preserving the wheel/image. Costs: new pinned header input and one future qualified compile-only request; it may still fail.
2. Rebuild the whole wheel+SDK together: broader ABI control, but replaces Python/Bullet/model providers and expands compatibility work. Separate future project, no automatic fallback.
3. Artificial padding or lowering the gate: would conceal unmeasured base-class differences; rejected. No native experiment is needed to distinguish the current offsets.

## Closed inputs and effective configuration

Retain source470e352/routes-v2 instrumentation, current image/Cg providers and genuine NVIDIA headers from the frozen b11e85da328bd4f68627fdd957b14f1aa4e2f0c898282404402405dd1f4d3630 contract. Old source/sysroot/generated headers/builds remain read-only.

New `libeigen3-dev_3.4.0-4_all.deb`:1040780B/SHA2561a167bb381acb90c1d8450a8f3e66a09d216dbc64b33ac8a082a0912513ef939, retained as DATA under docs/evidence/panda-sdk-cg-residual-01. HTTPS Debian bookworm Packages metadata's exact paragraph/digest match the archive; Release GPG verification is **not** claimed. It contains530 selected regular usr/include/eigen3 files/8669561B, version macros3/4/0. Retain copyright. No dpkg/apt/package scripts/CMake/pkgconfig/runtime files are installed or run.

Stage only those530 names/lengths/hashes into a fresh private root; archive4MiB/inflated32MiB/2048members/2MiBindividual header bounds. Authentic lapacke.h is1058369B, so1MiB is insufficient. Reject traversal, duplicate names, links/special selected files, version/pin substitution, or host Eigen fallback. Stage existing GL/X11/NVIDIA inputs unchanged into that fresh root. No toolkit/Trace provider substitution.

New builder uses explicit gcc-13/g++-13/ABI0/float32/two workers and --use-nvidiacg plus --use-eigen and --eigen-incdir=<private>/usr/include/eigen3. Empty private pkgconfig and verified .d origins prohibit host Eigen headers. Require generated HAVE_CG,HAVE_EIGEN,HAVE_X11 true and HAVE_PYTHON,STDFLOAT_DOUBLE false; descriptor compile-time guards require effective LINMATH_ALIGN, alignof(LVecBase4f)=16 and MEMORY_HOOK_ALIGNMENT=16. Capture generated AND effective macro reports and old/new generated delta; do not equate these with unknown wheel flags. Fresh measured tool/subtool selection and pre/post input checks remain mandatory; do not reuse an old guarded build entrypoint whose branch/descriptor/flags are frozen.

## Descriptor v2 and necessary static checks

Compile native/panda_sdk_cg_v2/layout_contract.cxx with real generated headers, ABI0,-MD,-c and probe-only -fno-access-control/-Wno-invalid-offsetof. Never link/load/run it. Fixed .panda_cg_layout_v2 is16uint64LE/128B: magic0x50414e4441434732,version2,ptr8,ABI0,Cg1,ShaderCaps/GraphicsPipe/GSG/GLGSG sizes,vendor/major/minor offsets,Eigen1,effective-LINMATH1,LVecBase4f-alignment16,memory-alignment16. Candidate sizes are recorded without inventing wheel sizes.

The complete parent ET_REL object may contain unrelated header-generated initializer code, retained as DATA only. The new extraction contract requires a unique read-only SHF_ALLOC/SHT_PROGBITS descriptor section, exact128B, bounded ELF64LE/AMD64 ET_REL≤1MiB/256sections, consistent nonoverlapping file extents/name bounds, and **no REL/RELA section targeting the descriptor**, including forged sh_info associations. Reject writable/executable descriptor flags, duplicates, out-of-file extents or relocatable descriptor values. Other parent sections are inspected as DATA and never executed. Copy the exact128bytes to layout-descriptor.data; no rebuilding values from JSON. Retain parent object, parent/section/raw hashes and extraction report. Independent consumer re-extracts parent bytes and requires exact equality with the raw descriptor.

Gate v2 accepts exactly one optional CET ENDBR64 prefix followed by the complete known integer mov-disp32/ret body. Reject extra/truncated prefixes, trailing instructions, IFUNC or ambiguous/W+X/unbacked symbols. Support complete authenticated GCC13 and previous known vendor string-copy bodies, including branch layout; bind calls to the expected ABI0 string-copy/clone import through validated PLT/loader relocations. No first-matching-load or arbitrary suffix acceptance. Old offsets, decoy expected loads overwritten by old loads and unrecognized forms reject.

Only all predicates together may yield CG_EIGEN_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME: actual source/tool/dependency/configuration facts; code and descriptor offsets major0x688/minor0x68c/vendor0x670; Eigen/effective alignment facts; vtable1024;33required exports/one state; selected strong root imports against exact current-image Cg/CgGL/providers with the original three weak exceptions and retained version diagnostics. Keep origin authentication separate. No full ABI/runtime mapping/crash repair/image installation promotion; unknown wheel facts stay unknown. Build01 must still reject even when recognized and diagnostically extracted by v2.

## Future one-use authority and carrier

This design grants no build slot. Future implementation uses new feature/panda-sdk-cg-eigen-candidate-v2 source, prepare/panda-sdk-cg-eigen-build-20261116-02 branch, .github/workflows/panda-sdk-cg-eigen-build-v2.yml and docs/requests/panda-sdk-cg-eigen-build-20261116-02.json; artifact name matches request id. Preserve all282old source identities and extend the new closure with new code/descriptor/Eigen DATA. Never reinterpret build01 under a changed source or replay its request.

After TDD/full tests/one fresh wholebranch review/one Critical-Important fix pass/exact reviewed-source CI4jobs, create one request-only child and new ref once. Exact owner/repository/source/two canonical CI events/four jobs/attempt1/artifacts0, unique build run/job/attempt1, bounded TLS artifact and closed carrier must authenticate. No retry or implicit compiler/package fallback.

ubuntu-24.04,contents/actions read-only,pinned checkout/upload,45minute job. One SDK build start;compile1200s/whole2400s,two workers,output8GiB/workspace12GiB/initialfree16GiB/logs32MiB/carrier256MiB. Point-in-time tool selection checks, not continuous execution/reproducibility/cgroup claims. Owned groups reaped; partial failed spawn/compile/extraction/gate/deadline retains argv/return/timing/log/truncation/omission evidence. Unknown default-off observation is None.

Carrier: four DATA files: libpandagl≤4MiB,build-libpanda≤64MiB,parent layout-contract.o≤1MiB,raw layout-descriptor.data exactly128B. Closed reports receipt/gate/inputs/tools-before/tools-after/host-before/used-inputs/compile-dependencies/sdk-output-manifest/source-manifest/configuration/effective-configuration/configuration-delta/layout-extraction/layout/provider-audit/loader-metadata JSON≤16MiB each; two logs combined≤32MiB. Exactly23files on success; failure declares omissions and preserves bounded diagnostics before optional candidates. Links/unknown/duplicate/truncated ZIP members reject. Every success predicate is recomputed from received bytes/current provider DATA; receipt claims alone cannot qualify.

SDK/Panda/GL/Xvfb/target/model/officialORT/cohort execution0,image operations0,scientific allowance0,strict0/4FAIL,Stage7INCOMPLETE. A static pass only feeds a separate image/runtime contract. Failure closes the new request without retry. Current task ends with forensic/design/plan/pinned input evidence and own Draft, exactHEAD CI4jobs and outside-commit receipt; it does not implement or activate the future builder.
