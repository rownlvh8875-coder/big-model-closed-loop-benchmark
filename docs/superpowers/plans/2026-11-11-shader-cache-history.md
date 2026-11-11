# Shader cache history isolation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test the discriminating local shared-versus-isolated cache result in balanced independent native CI.

**Architecture:** A new launcher wraps the unchanged original Road-first native trial. Three arms each use two independent processes: initially empty shared cache, separate empty caches, and disabled disk caching. Cache inventories and immutable after-process snapshots are collected by the parent outside native process intervals. Strict comparison recomputes native SHA series and snapshot manifests; four scenes produce 24 native processes.

**Tech Stack:** Python 3.11, MetaDrive 0.4.3/Panda3D/Xvfb/Mesa, GitHub Actions.

**Spec:** `docs/STAGE7_CONTINUATION.md`, `docs/STAGE7_SHADOW_SAMPLER_ISOLATION.md` local follow-up; [Mesa environment variable reference](https://docs.mesa3d.org/envvars.html#envvar-MESA_SHADER_CACHE_DIR).

## Global constraints

- Original sampler, Road-first sequential capture, PSSM.update, Chase and two task ticks per pair stay unchanged.
- Ten primary pairs, warmup two; source 964×604, model 512×256, uint8 I420 (2,6,128,256).
- Seeds 20261109/20261110 × left-right/right-left S-curves, fraction 0.12.
- Official asset size 134074203 bytes; SHA256 `4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
- No in-sequence GPU observer, model weights/ONNX, clock changes, warmup substitution, environment publication or default repair promotion.
- Cache availability and file snapshots do not prove individual cache hits. Parent-side file IO can affect OS cache state; record this limit.

## Review focus

- A preexisting case/cache/output must fail freshness checks before starting native work.
- Shared run 1 must begin with the exact state left by shared run 0; isolated/disabled runs must each start empty.
- Disabled caches must stay empty; enabled arms must populate them, or the intervention is unverified.
- Missing native receipts, modified native SHA, changed/missing snapshots, process reuse and stale summaries must fail.
- Only actual native processes count; launchers/Xvfb and cancelled partial cases are separate.

### Task 1: Complete isolated cache experiment

**Files:** Create `scripts/native_shader_cache_matrix.py`, `tests/test_native_shader_cache_matrix.py`, `.github/workflows/stage7-shader-cache.yml`, `docs/STAGE7_SHADER_CACHE_HISTORY.md`.

**Interfaces:** `execution_order(seed, scene) -> tuple[str, ...]`, `inventory(path) -> dict`, `run_case(root, seed, scene) -> dict`, `compare_case(root, seed, scene) -> dict`, `aggregate_scenes(root) -> dict`. Trial labels are `shared-0/1`, `isolated-0/1`, `disabled-0/1`. Existing `scripts.run_native_capture_trial` handles fresh receipt and Xvfb status 5, with original arm `sequential_road_first`.

- [x] Write failing tests for balanced ABBA/BAAB orders, inventory content changes, freshness, malformed native/clock/cache receipts, snapshot tampering, reused identity and stale summaries; exercise launcher success/failure with synthetic native receipts.
- [x] Run targeted tests and observe failure before implementing.
- [x] Implement three arms and 24-process strict comparison. Shared/isolated leave `MESA_SHADER_CACHE_DISABLE` unset; disabled sets `true`; all get explicit per-arm `MESA_SHADER_CACHE_DIR`. Retain native JSON/logs, outside-process inventories and after-process cache snapshots. Never change existing capture code.
- [x] Run targeted/full tests, a real local six-process case, YAML/syntax checks and an independent read-only code review. Fix findings with red regressions.
- [x] Commit/push PR; verify exact-HEAD CI/review and all five artifact hashes/sizes, then reproduce four case summaries and aggregate exactly. Preserve failed/cancelled evidence and actual mismatch counts.
- [x] Merge only after gates; update findings/continuation with facts, causal limits, current main cohorts and next commands. Original official gate remains prior 0/4 until separately retested after a validated repair.


## Completion evidence (2026-11-11)

PR #20 merged as `465bf0c49a585fecb8ad313cac3b29e96736b8b6` from final source
`e3df7d1a74c2d7d7e6e2ac1cc3c3421da7b65eb8` after nine checks, current-SHA
Codex review without findings, fresh independent review and 259 local tests.
Run 42948547486 completed 5/5 jobs; all five archive SHA/size/safe-path checks,
all cache snapshot rehashes, four case summaries and final aggregate passed
independent revalidation: 24 native UUIDs and six PIDs per case. The final
local six-process case also passed final validation with exact existing
summary fields. Cancelled runs 42947832747 and 42948096573 retain eight
verified partial ZIPs and are not full cohorts.

The experiment completed; no repair was established. Shared/isolated/disabled
I420 matched 19/40, 34/40 and 32/40, with 0/4, 3/4 and 2/4 complete static
cases. Full source/warp rates, per-case orders, cross-condition comparisons,
archive ledgers and causal limits are in
[the cache findings](../../STAGE7_SHADER_CACHE_HISTORY.md). Original official
MD-V3 remains prior 0/4 PASS (FAIL); no official ONNX retest or default switch.
The separate [shadow-feedback plan](2026-11-11-shadow-feedback-isolation.md)
is the next opt-in experiment, with no results claimed here.
