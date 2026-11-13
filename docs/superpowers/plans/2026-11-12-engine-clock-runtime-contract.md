# Engine-clock provider-free runtime contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. This is a future provider-free implementation roadmap, not a native/image-preparation activation.

**Goal:** Implement and verify a pure metadata identity contract, then a separately reviewable installed-file collector and image-evidence adapter without constructing a provider.

**Architecture:** Keep consumed source70/runtime gates immutable. A new namespace separates installed image content and strict host execution profile from provenance. Authenticated Docker-save image artifacts avoid a registry publication requirement; the metadata tool alone proves neither actual preparation nor execution.

**Tech Stack:** Python3.11 standard library/unittest for the first two tasks; Docker/GitHub read-only API adapters only in the later separately gated preparation task. No native-library imports in provider-free tools.

**Spec:** `docs/superpowers/specs/2026-11-12-engine-clock-runtime-contract-design.md`

## Global Constraints

Preserve all70 producer files, all44 existing workflows, all8 consumed request/acceptance files, protected13/baseline43, raw archives/extracts and controller histories.

No worktrees, local MetaDrive/Panda engine/Xvfb, new render/step/RAM/GPU/clock getter/setter, official weights/inference/ORT, Cloud settings/publication or main merge. Baseline generated SMALL ONNX CI is separate.

The current design's native/model allowance is0; image/build/lock/launch references are null. No old retry, fallback, source rewriting, registry reinterpretation or reuse of four unexecuted cases. Each later task remains provider-free; a native protocol requires its own later design/source/canary/acceptance/budgets.

Identity schema `engine-clock-installed-identity-v1`: exact core objects `image`, `versions`, `host`, `engine`, `configuration` and fields/literals/types from the spec. SHA256 canonicalization uses UTF-8 sorted compact ensure_ascii JSON, no newline, allow_nan=False. New installed-profile equality never modifies the old full ImageVersion comparison.

Installed manifest limits:<=100000entries/16MiB JSON/4GiB total read/512MiB per file/180s, identity<=128KiB. Image archive/outer ZIP each<=2GiB, expanded installed content<=3GiB, image download<=300s with1MiB chunks; actual preparation requires>=16GiB genuinely free storage. These are future caps, not measured feasibility or a native deadline extension.

## Review Focus

- Matching hashes on synthetic metadata must not be reported as authentic container/build/provider admission; tests assert separate limited statuses.
- Host ImageVersion-only differences can pass only the new complete-identity comparison; legacy/partial/version-only inputs must fail, and kernel/CPU/engine changes must reject.
- Closed filesystem inventory must detect missing/extra files, modes, symlink escapes/cycles and bounded failure without importing native packages or executing ldd.
- Docker-managed `/etc` metadata and legitimate aliases must not cause either an always-failing inventory or broad exclusions that hide native content.
- Sanitized host/container API evidence must reject forged env-only claims while preventing token/proxy/Config.Env disclosure; old in-memory192MiB transport cannot handle the new image archive.

---

## Current increment completion

The initial design-only checkpoint is preserved at04c91d1 and Task1 at2cc22c0. The previous increment implemented **Task2 caller-root fixture verification** inline with TDD and a fresh whole-branch review. The current continuation inspects Task3 mandatory input compatibility and records its blocked first gate. [Task2 addendum](../specs/2026-11-12-engine-clock-runtime-inventory-design.md) fixes concrete alias/exclusion/deadline/two-pass rules. Task3 remains unimplemented with separate later gates; no image/native allowance is added.

### Task 1: Pure identity/proposal parser and comparator

**Files:** create `scripts/engine_clock_runtime_contract.py`, `tests/test_engine_clock_runtime_contract.py`; update only the new runtime-contract docs. Do not edit/import consumed `scripts.engine_clock_native` or its helpers for validation. Use saved dictionary fixtures for tests; no filesystem inventory, API, Docker or native imports.

**Interfaces:**

- `validate_proposal(document: dict) -> dict`: accepts the inactive companion proposal only with its exact schema/status, null unprepared references and zero allowances; returns `status=INACTIVE_PROPOSAL_VALIDATED`, `execution_authorized=False`.
- `validate_identity(document: dict) -> dict`: validates exactly the spec's identity schema/core and recomputes core_sha256; returns the validated identity without claiming external authenticity.
- `compare_identity(left: dict, right: dict) -> dict`: validates both, returns `status=INSTALLED_PROFILE_MATCH` or `INSTALLED_PROFILE_MISMATCH`, `differences` sorted by JSON field path (at most64), `truncated` bool, `native_admission=False`. Ordered rootfs diffIDs are not sorted away.
- `main(argv: list[str] | None=None) -> int`: subcommands `validate-proposal --proposal PATH` and `compare-identity --left PATH --right PATH`; bounded JSON stdout,exit0 for valid inactive proposal or matching metadata,exit1 for mismatch/invalid input. Nonzero output includes bounded original cause, no rewritten source/extra IO.

- [x] Write `test_inactive_proposal_never_authorizes_execution`: assert status and explicit execution_authorizedFalse; every non-null preparation reference, nonzero allowance or ready/native flag rejects. Use the committed proposal as the genuine inactive input, never as an actual identity.
- [x] Write `test_matching_synthetic_identity_is_metadata_only`: fixture core has real-shaped synthetic digests and exact required fields; assert recomputed hash/status/native_admissionFalse and no external action. Patch API/Docker/process constructors and native import paths to raise if touched.
- [x] Write `test_every_core_leaf_is_bound_or_rejected` and `test_diff_id_order_is_not_sorted_away`: mutate each core leaf and recompute that fixture's digest; valid variable-field alternatives must mismatch, while invalid changes to fixed literals/pins must reject. Neither may match. Reordered CPU flags normalize only by rejecting unsorted input; reordered diffIDs remain changed content.
- [x] Write `test_missing_extra_legacy_and_provenance_fields_reject` plus digest/type/CLI negative tests: old C/A version dictionaries are invalid new identities, mutable tags or invalid prefix/length/placement reject; a well-formed same-shaped index/config/archive digest may parse but must not authenticate an object, and comparison detects a changed expected field value, bool is not an integer, duplicate JSON keys reject at CLI boundary. Preserve old raw records untouched.
- [x] Verify `test_missing_extra_legacy_and_provenance_fields_reject` rejects provenance envelopes/unknown identity fields. Separately, `test_matching_synthetic_identity_is_metadata_only` compares standalone identity records with native_admissionFalse. No adjacent non-input provenance fixture or ignored-field behavior is claimed.
- [x] Write `test_more_than_64_differences_truncate_in_sorted_path_order` plus CLI status/error tests: >64 valid leaf differences truncate deterministically; long errors/oversized128KiB inputs reject; valid inactive input exits0 with execution_authorizedFalse,invalid/legacy inputs exit1.
- [x] Run `/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -m unittest tests.test_engine_clock_runtime_contract -v` before implementation; retain the meaningful missing-feature RED.
- [x] Implement only the interfaces above from the exact spec/proposal. The tool never imports Panda/MetaDrive/CV/NumPy/ORT, mutates env/modules or scans installed packages. Standard-library `json`, `hashlib`, `pathlib`, `argparse` are sufficient.
- [x] Run the targeted command to GREEN. Run one complete CPU suite only after integration changes justify it; retain exact source/test hashes and meaningful skip reasons. Add no implementation-mirroring tests for ordinary documentation.
- [x] Independent spec+quality review, source70/workflow44/registry8 preservation, own feature branch/Draft based on this design; current sequential Task1 is included in design/engine-clock-runtime-contract. Existing baseline CI only. Commit exact reviewed code; no native/image-preparation workflow is created or run.

### Task 2: Bounded installed-file collector (current separate increment)

**Files:** create `scripts/engine_clock_runtime_inventory.py`, `tests/test_engine_clock_runtime_inventory.py`; consume Task1 `validate_identity` only where its input is genuinely an identity. Do not put new collectors inside a consumed producer module.

**Interfaces:** `collect_inventory(root: Path, expected: dict, *, deadline: float) -> dict` reads a caller-supplied fixture/sealed root and verifies expected `installed-files-v1`; `validate_inventory(document: dict) -> dict` is pure metadata. Production absolute paths are mapped under `root`; no host machine scan is run as an automatic import/test side effect. Root/entry/runtime-exclusion schemas and limits follow the spec.

- [x] Write RED tests with small temporary file trees: exact byte/mode preservation; changed/missing/extra/empty files; overlapping root deduplication; valid cross-root symlink and expected `/etc/mtab`; escape/cycle/device/FIFO rejection; unexpected broad exclusions reject; file/entry/byte/JSON/deadline caps preserve a bounded partial stage without claiming a complete inventory.
- [x] Pin provider-free behavior: no `ldd`, subprocess, native import, GL context, provider, task or GPU invocation; hashing a file named like a native library is byte IO only. Synthetic caps can be lower in fixtures; production constants remain exact spec values.
- [x] Run targeted RED, implement collector, run targeted GREEN, then independently review pure-tool/collector boundary and installed-vs-actual-loaded assurance statements. Record hashing timing as preflight overhead; do not call it neutral.
- [x] Keep image/native readiness false. Commit/test/Draft only on a new provider-free branch. Any missing concrete filesystem/alias compatibility blocks preparation rather than changing old runtime rules.

### Task 3: Image inputs, preparation adapter and provider-free evidence (real local wheel measured; full lock pending)

Current local package evidence: [real wheel operation](2026-11-13-engine-clock-real-wheel-preparation.md) measured original55128766B/c6f8... and derivative72968610B/f949... with1428preservedmembers; independent input review is pending. This addresses the first package-policy candidate only. Complete Python/base/deb/asset locks, runtime compatibility and image/adapter/preparation gates remain unresolved; the first Task3 checkbox below stays unchecked. Do not replay the consumed local package request.

Follow-up: [metadata derivative plan](2026-11-13-engine-clock-wheel-derivative.md) implements the explicit policy on synthetic bytes only. It does not resolve actual original/derived wheel provenance, full locks or preparation; all Task3 checkboxes below remain unchecked.

Current input-gate result: **BLOCKED_INPUT_COMPATIBILITY**, not Task3 complete. All requested releases exist, but MetaDrive0.4.3 requires opencv-python while the fixed contract requires opencv-python-headless; publisher guidance rejects shared cv2 providers. See [Task3 gate addendum](../specs/2026-11-12-engine-clock-image-inputs-design.md). No complete lock/recipe/adapter/workflow or preparation is created. The first checkbox remains unchecked; proposed metadata-only derivative policy requires a separate source/fixture review before resolution can continue. This is not a pip unsatisfiability or historical-cause claim.

**Planned files:** create `containers/engine-clock-runtime/Dockerfile`, `containers/engine-clock-runtime/inputs.lock.json`, `scripts/engine_clock_image_preflight.py`, `tests/test_engine_clock_image_preflight.py`, and an inactive workflow example under `docs/proposals/engine-clock-image-preparation.workflow.json`. None exists or is active in the current increment.

**Interfaces:** `validate_preparation(receipt: dict, api_evidence: dict, archive: Path) -> dict` authenticates the three-member artifact; `validate_launch(host_view: dict, expected_identity: dict, nonce: str) -> dict` accepts sanitized actual image/mount/config evidence, not an environment's own digest assertion. Task1 validates core; Task2 verifies the actual installed tree. Separate bounded streaming archive transport, not old model/dataset downloader reuse.

- [ ] Resolve genuine base/Python/wheel/deb/asset digests and complete dependency locks using provider-free metadata/package preparation; no illustrative hashes. Preserve failed resolutions and stop when unsupported. Review actual lock/recipe/version compatibility before a build or workflow activation.
- [ ] Test authentic run/workflow/head/attempt/artifact binding, wrong ZIP/tar/config/diffID/hash classes, duplicate/missing/extra ZIP members, truncated/oversized streaming data, hostile paths, insufficient/shared disk accounting, env-only forged identity, wrong actual container ID/mounts, native library/device/display injection and bounded cleanup. Fake Docker/API fixtures must not imply a real prepared image.
- [ ] Test log/error sanitization with secret-looking token/proxy Config.Env sentinels; none may appear in persisted output, command argv or artifact metadata. Only credential routing/presence is recorded; no full inspect dump or credentials baked in image layers.
- [ ] Implement the inactive adapter/example, then source/CPU review before a separately authorized preparation run. Fix authentic source issues before first execution, never as a native retry.
- [ ] Only after that separate gate, one bounded provider-free preparation/preflight run may produce real image/config/inventory/lock/launch evidence. No provider/native engine/GL probe/model/ORT invocation. Independent API/archive/installed-content review accepts or terminates it; null references remain until real accepted data is recorded.
- [ ] Check measured disk/load/hash feasibility against caps. Missing actual evidence or a cap failure does not permit another native attempt, fallback, extra jobs or automatic budget increase.

## Native handoff — out of this plan

After provider-free image/preflight evidence is accepted, write a separate new native protocol/source/request/workflow and budget design. Include all imported new tools/locks/image bindings in its actual producer closure; determine the closure's real count rather than guessing70 or borrowing the old canary. Parent/child identity checks must account for hashing time, finite cleanup and same-namespace one-use FD/PID/group semantics. A new source canary and authentic root+fresh acceptance are required before any direct-child ABBA. The old four unexecuted cases are not available. This plan creates no native allowance and promises no scientific PASS.
