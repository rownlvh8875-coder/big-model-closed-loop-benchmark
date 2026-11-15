# Whole-branch review: Panda dispatch coverage

Reviewed base `93475a36e8a68889aa632182dccd4cdc3dde39c0` through HEAD `1c3077021f4fe05764a2a78ae14f681ca7158ab7` on `feature/panda-dispatch-coverage-v1`.

Counts: **0 Critical, 4 Important, 0 Minor.**

## Strengths

- The production path never loads an ELF or calls GL. Exact Panda image/read-ABI, four source identities and the existing delivery source pin are checked before publishing reports. Both mechanisms retain explicit installation, compiled-path, runtime, driver and GPU blockers.
- Loader imports come from program headers and PT_DYNAMIC, independent of section headers; ordinary JUMP_SLOT and address-taken GLOB_DAT cases have independent readelf comparison. The source inventory keeps conditional branches as possibilities and separates computed lookups from literal names.
- Evidence is unusually clear about its limits: spelling presence does not establish an executed branch; broad GLX prohibitions do not establish that every drawable operation mutates capture state; compilation timing excludes native overhead. Existing evidence is preserved on ordinary output reuse.
- All 78 changed paths are additions. I read both production modules, both test modules, fixture, specification, plan, all ledger Rulings, result/continuation documents and evidence helpers. Generated reports/logs and vendored audit inputs were examined through their declared schemas, relevant contents and integrity checks. All 67 indexed proofs (4,071,070 bytes), seven retained failed-helper inputs, nine source pins and five upstream SHA256/Git-blob identities verified.

## Critical

None. No finding below bypasses the unconditional native/runtime authority false values, and exact input pins protect the currently recorded Panda audit from mutated ELF/source inputs.

## Important

### I1. A forged symbol-table range can silently erase all imports

**Location:** `scripts/readback_elf_imports.py:102` (also lines 56–59 and 105–106).

Only individual symbol records' containment in a PT_LOAD is validated. The parser does not establish a valid, non-overlapping dynamic symbol-table extent or validate the null symbol before interpreting records. In particular, the dynamic string table can be reused as the symbol table; arbitrary string bytes then look like non-undefined/non-function symbols and are silently skipped.

**Repro:** Read the committed CPU-only `before-review-final/cpu-imports.so` as bytes; use the existing `changed_tag(blob, 6, tags[5])` test helper to replace DT_SYMTAB with DT_STRTAB, then call `inspect_imports`. The original yields eight imports including `glReadPixels`, `glXCreateContext`, and `glPixelStorei`. The modified input is accepted with `imports=[]`, rather than rejected. No ELF was loaded or executed.

**Effect:** The reusable reader reports a successful but empty inventory for a malformed overlapping loader table, hiding the required routes from downstream planning. This violates the explicitly required malformed/overlapping-table rejection. The pinned CLI rejects the changed image hash first, so this is an import-reader correctness defect, not a pinned-image native-admission exploit.

**Recommendation:** Establish and validate the loader-backed symbol table's bounded extent and table relationships before filtering symbols. At minimum reject symbol/string/dynamic/relocation table aliasing and invalid null-symbol metadata; where symbol count is derived from dynamic hash metadata, validate that metadata and referenced indexes too. Add RED cases for DT_SYMTAB=DT_STRTAB and a relocation index escaping the validated symbol extent. Preserve section-header independence and the actual Panda/CPU cases.

### I2. Valid C/C++ line splices silently discard route observations

**Location:** `scripts/panda_dispatch_coverage.py:64`–69.

The splice guard only recognizes LF and uses `isalnum()` for identifier boundaries, omitting underscore. It also removes the splice after tokenization has already split the first identifier piece. Thus a legal splice after underscore passes the guard and becomes two identifiers. A CRLF splice is not recognized at all and inserts punctuation between a callee and its argument list.

**Repro:** `scan_source(b'get_\\\nextension_func("glDeleteBuffers");', 'case.cxx')` returns all four observation lists empty. So does `scan_source(b'glDeleteBuffers\\\r\n(1, buffers);', 'case.cxx')`. The equivalent unspliced lookup is reported normally. The first byte expression contains a backslash followed by LF; the second contains backslash followed by CRLF. Exact runnable byte expressions are in the companion repro script.

**Effect:** Both are valid source spellings of calls. Required lookup/direct-call names silently disappear, so the lexical inventory can understate the conservative union. The unchanged pinned sources are not claimed to contain these examples; this is a defect in the new reusable scanner's explicit fail-closed lexical contract.

**Recommendation:** Handle phase-two splicing consistently before lexical decisions while preserving physical line locations, or explicitly reject unsupported splice forms, including underscore boundaries and CRLF. Include comment-boundary/continued-comment cases when choosing the implementation so moving this logic does not manufacture observations from comments. Add isolated regression cases for both demonstrated losses.

### I3. Known capture-state restoration/reset functions can be marked safe

**Location:** `scripts/panda_dispatch_coverage.py:31`–34 (`_UNSAFE`) and `scripts/panda_dispatch_coverage.py:222`.

The prohibited-prefix set misses `glPopAttrib` and `glClientAttribDefaultEXT`. `glPopAttrib` can restore the read-buffer state saved by the pixel-mode attribute group; `glClientAttribDefaultEXT(GL_CLIENT_PIXEL_STORE_BIT)` resets pixel pack/unpack state. They are therefore known state-changing operations for the gate's read-buffer/pixel-store model, even though they are not named `glReadBuffer` or `glPixelStore*`.

**Repro:** Scan `glPopAttrib(); glClientAttribDefaultEXT(1);`, assess it with an empty loader import list and empty routes, and pass both names as `safe_names`. The result has `name_classification_complete=True`, `missing_required_routes=[]` and no missing-capture-state blocker. The argument `1` in this lexical repro is immaterial: the gate classifies names, and the same accepted function permits GL_CLIENT_PIXEL_STORE_BIT.

**Effect:** A caller can explicitly classify actual capture-state mutators as harmless. This does not elevate runtime authority and does not change the current pinned 445-name audit, but undermines the new assessor's promised prohibition of known state mutators and produces an incorrect future routing plan. The existing native delivery file need not be changed to correct the new planning boundary.

**Recommendation:** Extend the new assessor's prohibited names/prefixes to these state restoration/reset paths and test both rejection when supplied as safe and actionable missing-route classification when encountered without an adapter. Keep the delivery pin immutable and do not imply that adding prohibitions implements the missing adapters.

### I4. FIFO input hangs before regular-file validation

**Location:** `scripts/panda_dispatch_coverage.py:278`–281.

`read_input` performs a blocking `os.open(..., O_RDONLY)` before checking `S_ISREG`. A canonical FIFO with no writer therefore never reaches the validation that is supposed to reject it.

**Repro:** Create a FIFO under a temporary `/tmp` directory; run the actual CLI with that FIFO as `--image`, the valid pinned source directory and a new output path. The subprocess remained blocked until a two-second timeout killed it. It emitted no rejection and created no output. The companion script performs this bounded repro and cleans up its FIFO.

**Effect:** An unsupported input can hang an automated offline audit indefinitely instead of returning the specified exit 2. This is an availability/CLI-contract issue; no prior evidence was overwritten and no readiness was produced.

**Recommendation:** Open with nonblocking semantics suitable for inspecting the descriptor, then reject nonregular files using `fstat` before reading. Retain the descriptor identity checks and add a subprocess timeout regression proving FIFO rejection exits 2 promptly without a success directory.

## Verification and reproducibility

- Reviewer command: `python -B -m unittest tests.test_readback_elf_imports tests.test_panda_dispatch_coverage` — **21 passed in 0.374s**. The test ELF was compiled and inspected only, never loaded/called.
- Existing integrity-verified full-suite log records **1,436 tests, 1,429 passed, 7 skipped, 92.646s**. I did not independently rerun the full suite or any native/workflow command.
- Runnable pure-data/CLI repros: `/tmp/panda_dispatch_coverage_review_repros.py`; captured results: `/tmp/panda_dispatch_coverage_review_repros.txt`. Run with `python -B /tmp/panda_dispatch_coverage_review_repros.py` from this environment. Its subprocess timeout prevents an indefinite FIFO hang.
- HEAD remained the reviewed commit and `git status --porcelain` remained empty. No index/HEAD/branch/checkout mutation, push, remote message, workflow dispatch or subagent dispatch occurred. Repro/report artifacts were written only under `/tmp`.

## Recommendations

Use the single authorized Important/Critical fix pass for I1–I4, with regression tests failing first. Refresh changed production source pins and affected evidence after the fixes; preserve the original before-review evidence and all authority-false statements. Do not use these fixes to implement or qualify a native installer. The existing full-suite and pinned CLI evidence establish the current inputs' behavior but do not cover the demonstrated counterexamples.

## Behaviors considered but declined as outside this review's implementation scope

- Running or loading Panda/GL/MetaDrive/provider/model/ORT/replay, including loading the CPU fixture: explicitly prohibited; all inspection was data-only.
- Implementing/qualifying an actual GOT or source-integrated installer and proving driver/GPU/native lifetimes: the task explicitly leaves both candidates uninstalled and unqualified.
- Determining active preprocessor branches, full upstream build configuration or complete installed-image behavior from spelling presence: explicitly not established by this static inventory.
- Auditing renderer correctness throughout the vendored upstream C++ files: these are pinned audit input data; their integrity and relevant lexical/resolver cases were checked instead.
- Adding ELF32, non-amd64, REL, or other relocation classes such as R_X86_64_64 function-pointer initializer coverage: the declared reader profile is ELF64LE/amd64 with RELA JUMP_SLOT/GLOB_DAT, and broader runtime/full-call-path coverage is not claimed. This does not excuse malformed supported tables in I1.
- Replacing the broad GLX drawable prohibitions with a newly researched safe classification: the ledger explicitly leaves those names prohibited pending future classification and does not assert they are all context mutators.
- Modifying the pre-existing native delivery implementation or adding missing context/buffer adapters: base files are required immutable; the present task must expose gaps and keep installation blocked.
- Publishing the final Draft/CI receipts or rechecking remote histories: closeout belongs to the parent task; no network/remote actions were taken by this reviewer.

No demonstrated parser, known-mutator classification, or ordinary input-rejection behavior above was dismissed merely because it does not bypass the final native-ready flag. Those are the product of this static gate and require correct behavior in their own right.

## Assessment

**Ready with fixes, not ready as-is.** The architecture and evidence preserve the native boundary, but the four Important issues prevent accepting the reusable offline gate's fail-closed claims. No rereview is requested; use the authorized single fix pass and its verification evidence.
