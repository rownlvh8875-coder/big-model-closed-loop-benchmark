# Panda dispatch coverage implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans. Inline; one fresh whole-branch review; no implementer delegation.

**Goal:** Produce a pinned-source/image dispatch coverage gate with concrete missing installation work.
**Architecture:** PT_DYNAMIC ELF import reader plus conservative source lexer and fail-closed planning assessor. CLI combines exact Panda/read-ABI and current delivery pins; no loading or patching.
**Tech Stack:** Python3.11 stdlib, existing cc/readelf for CPU-only ELF tests.
**Spec:** ../specs/2026-11-14-panda-dispatch-coverage.md

## Global Constraints

Preserve3083basefiles/299pins/10originals/main/Drafts102–108/8nativehistories. No realGL/Panda/MetaDrive/provider/model/ORT/native replay/import, oldrequest reuse, sharedbase/main push/merge or Cloudregistry publication. Nativeallowance0; strict0/4FAIL/Stage7INCOMPLETE. Samecheckout/noquestions; onefreshreview/oneCritical-ImportantTDDfixpass/no rereview/minorpolish. Caps ELF64MiB,64PHDR,65536symbols,262144relocs,4MiBstrings,512Bnames,1MiBdynamic;4sources×1MiB,500000tokens,20000observations;safe256×63B. Name/source/image consistency never runtime/compiled-path/driver/GPU authority.

## Review Focus

1. Loader imports must come from validated PT_DYNAMIC ranges, including address-taken GLOB_DAT; forged/truncated/overlapping tables or misleading sections cannot hide required routes.
2. Comments, strings, declarations, computed/concatenated/conditional source calls cannot silently disappear or become executed-path claims.
3. Legacy context/delete-buffer/unsafe mutator aliases and allowlist caps must block incomplete classification, even when other names are routed.
4. GOT-only coverage cannot bypass private GLX/POSIX or compiled-table resolution; source-integrated candidate also stays uninstalled/unqualified.
5. Source/delivery/image pin or CLI input/output failures must preserve prior evidence and never produce readiness, including supplied booleans/profiles.

### Task1: Loader-backed ELF imports

**Create:** scripts/readback_elf_imports.py;tests/test_readback_elf_imports.py;tests/fixtures/readback_import_fixture.c.
**Interface:** inspect_imports(blob:bytes)->dict with schema,imports(list name/symbol_index/type/binding/slot_vaddr/relocation_type),needed_libraries,elf_sha256. No section-header dependency, no loading.

- [x] RED tests: compiled CPU ELF requires literal glReadPixels/glXCreateContext/address-taken glPixelStorei imports; independent readelf slots agree; zero section headers still work. Corrupted ELF/machine/dynamic tags/strtab/symtab/entrysize/RELA/JMPREL/duplicates/overlap/termination/budgets reject.
- [x] Implement bounded unique PT_LOAD/actual dynamic table reader; focused tests PASS; commit with ledger evidence.

### Task2: Pinned coverage scanner/assessor/CLI

**Create:** scripts/panda_dispatch_coverage.py;tests/test_panda_dispatch_coverage.py;docs/evidence/panda-dispatch-coverage-01/{source,source-pins.json,...};RESULT/LEDGER/CONTINUATION docs.
**Interfaces:** scan_source(data:bytes,filename:str)->dict literal_lookups/computed_lookups/direct_calls/member_calls;delivery_routes(data:bytes)->tuple names;assess_coverage(imports:dict,sources:list,routes:tuple,safe_names:tuple,mechanism:str)->dict;qualify(image:bytes,sources:dict,delivery:bytes,safe_names=(),mechanism='got-only')->dict. CLI --image,--source-dir,--delivery,--safe-names,--mechanism,--out reads bounded canonical files and creates a new directory.

- [x] RED parser/coverage/CLI tests: literal line identities, comments/unrelated strings, concatenation, computed calls, definitions/declarations, conditionals/malformed lexical forms; legacy glXCreateContext and glDeleteBuffers missing; unsafe/duplicate/oversized names reject; private resolver/GOT-only and source-integrated native readiness remainFalse; image/source/delivery mutation rejects; CLI invalid input/output preserves inputs/no success.
- [x] Implement scanner, explicit existing17route profile and planning gate, exact source/image/readABI binding and CLI. Actual pinned audit emits concrete gaps, not guessed allowlist/activebranch coverage; focusedPASS; commit.
- [ ] Run pinned audit/environment guard/fullsuite; retain CPU ELF/source/raw reports, commands/logs/preservation. Onefreshwholebranchreview,oneCritical/ImportantRED→GREENfixpass+suite; all rulings/declined behavior/costs ledgered; no rereview.
- [ ] Prepare ownDraft/exactHEADCI and final preserved originals/refs/history proof; copy/remove only thisplan scratch after fixes committed. ImmutableHEAD final receipt goes to PR body and retained output.
