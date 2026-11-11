# Stage 7 continuation — PR #15 evidence gate

## Scope and current decision

The 2026-11-11 user instruction requires verifying PR #15 and all 32 native
process receipts before merging, then investigating sparse original RGB drift.
Never publish the cloud environment or repeat its prior setup changes.

Initial main: `20f0faaa1110ead55a4213cf84303e61c50eb61d`.
PR #15 initial HEAD: `8a69c334dd6ca1dff20b13e5873368383c2b8da2`.
Local branch: `review/stage7-pr15-evidence`, based on that PR HEAD.

## Evidence validation implementation plan

**Goal:** Reject fixed-pose cross-process receipts that do not preserve the
original Chase task or do not prove that the experimental arm removed only
`PSSM.update`. This changes evidence validation, not rendering or model inputs.

**Approach:** Extend the existing comparator and its tests. Changing simulator
task scheduling would change experimental semantics and is outside this fix.
The user explicitly requested autonomous implementation and testing; proceed
inline without another design or execution-method confirmation.

- [x] Read PR source, tests, workflow, and installed upstream MetaDrive 0.4.3.
- [x] Reproduce acceptance of a receipt missing `update main chase camera`.
- [x] Add failing regression tests in `tests/test_native_pssm_cross_process.py`
  for missing/duplicate required tasks and incomplete or inconsistent removal
  ledgers; use the actual `remove_visual_scene_task` receipt structure.
- [x] Update `scripts/compare_native_pssm_cross_process.py::validate_trial`
  to require exactly one Chase and igLoop task, correct PSSM multiplicity,
  and an experimental ledger removing exactly one PSSM task and nothing else.
- [x] Run the targeted contract tests and full unittest suite.
- [x] Exercise the comparator against actual separately produced native JSON.
- [ ] Download all five original PR #15 artifacts, verify archive digests,
  rerun the four-scene aggregator, and record exact image matches and IDs.
- [ ] Commit the fix/results, update PR #15, verify the new HEAD's CI and
  automated review, and merge only after every required gate is confirmed.

## Remote access prerequisite

Git fetch/ls-remote and public github.com pages work. GitHub REST/GraphQL API
requests to `api.github.com` are rejected at CONNECT with HTTP 403; GH_TOKEN
is present (value was not inspected). No new token has been requested.
Only `api.github.com` was added to the current environment draft's custom
network allowlist, preserving its preset domains and existing setup scripts.
The user must save this new network change in environment settings before
API access can be rechecked. Do not publish the environment.

Public run page observation (not raw-artifact verification):
https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42927840424
shows Success, four matrix jobs, one independent aggregate, and five artifacts.
The public PR page contains a completed Codex review for the initial HEAD with
no findings. Neither observation verifies all raw process receipts locally.
Baseline local full suite on the initial PR HEAD: 213 tests passed, no skips.

## Completed validation fix and current-instance checks

Fix commit: `c14935ee9bab258c7dbd0a2f669643e27cefaf55`.
The regression run before the fix produced 21 assertion failures across the
new subcases (9 test methods total). After the fix: targeted **9/9 PASS**;
full suite **216/216 PASS**, no skips. A fresh independent read-only reviewer
reported no Critical, Important, or Minor findings and independently passed
the comparator + task-ablation suites (13 tests). This is code review, not
verification of GitHub's original artifacts or permission to merge.

The published development environment restored successfully. The official
MetaDrive archive size and SHA256 were freshly reverified. Three new local,
sequentially executed, separate Python/Panda/Xvfb processes all returned
`OBSERVED_NATIVE_PIXEL_CLOCK` and passed the strengthened validator:

| Seed / scene | Arm | Independent processes | Source Road / Wide match | Warped Road / Wide match | I420 match |
| --- | --- | ---: | --- | --- | --- |
| 20261109 / s_curve_left_right | sequential_original | 2 | 10/10, 10/10 | 10/10, 10/10 | 10/10 |
| 20261109 / s_curve_left_right | paired_pssm_task_removed | 1 | Not compared | Not compared | Not compared |

Both original processes retained one each of PSSM.update, Chase and igLoop.
The experimental process's actual removal ledger proved that only PSSM.update
was removed. CPU repeat-read and +2m image positive controls passed in all
three processes. Each captured 10 frame pairs, with the first two retained
as warmup. There was no ONNX inference in any of these processes.

Local JSON, SHA256 manifest and comparison:
`output/pr15-local-verification/local_validation.json`.
These files are ignored local outputs, not uploaded CI artifacts. This is
one static-scene compatibility check on this Debian/Python/CPU OpenGL machine,
not a reproduction of GitHub's Ubuntu environment or the full 32-process
matrix. A 10/10 local pair does not improve or replace the official moving
MD-V3 strict-repeatability gate. The fix does not alter any renderer callback,
camera capture scheduling, RGB pixels, ONNX input, state or action.

### Exact resume commands

From the existing checkout after saving the `api.github.com` network rule:

```bash
source /workspace/.cloud-tools/onboarding/activate.sh
gh pr view 15 --repo rownlvh8875-coder/big-model-closed-loop-benchmark \
  --json headRefOid,headRefName,state,reviews,comments,files,statusCheckRollup
gh run view 42927840424 --repo rownlvh8875-coder/big-model-closed-loop-benchmark \
  --json headSha,status,conclusion,jobs,url
gh api repos/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42927840424/artifacts \
  > output/pr15-original-artifacts.json
gh run download 42927840424 --repo rownlvh8875-coder/big-model-closed-loop-benchmark \
  --pattern 'stage7-pssm-crossprocess-*' --dir output/pr15-original-download
```

Inspect each artifact's paths before combining: each native artifact has a
different `seed-*/scene/` subtree, whereas the final summary artifact contains
`aggregate_summary.json`. Preserve every original download and reject path
traversal, unexpected overlapping members or mismatched API archive digests.
For digest verification, download each artifact ZIP through its API endpoint,
compare its SHA256 to the API `digest`, then extract validated members. Build
a clean combined root containing the four original scene subtrees. Run:

```bash
python -m scripts.compare_native_pssm_cross_process --mode aggregate \
  --root output/pr15-original-combined \
  --out output/pr15-original-recomputed.json
```

Compare the recomputed JSON to the original final summary; record artifact
IDs/digests, per-arm Road/Wide/model-RGB/I420 exact matches and first differences.
If the validation fix has been pushed to PR #15, also verify all required CI
and automated review on the **new** exact HEAD; old-HEAD success is insufficient.
Do not merge while any result, review or raw artifact verification is unknown.

## Remaining scientific gates

Original uninstrumented official MD-V3 strict repeatability remains the prior
**0/4 PASS (FAIL)**. No new official ONNX run has been performed in this session.
No causal renderer fix is justified yet. PSSM removal is an experimental
renderer change, not a valid default or proof of official model determinism.

Once PR #15 is fully verified and merged, start the next branch from latest
main. Revalidate PR #14's compressed RGB artifacts and exact first changed
pixel/channel values, then run hypothesis-specific independent A/B experiments.
Preserve original controls, task callbacks, camera geometry, GPU-readback
interference controls, model state and actions. Download official MD-V3 weights
only on ephemeral CI runners and verify the required SHA256. Execute the
2 seeds × 2 S-curves × 12 steps × 2 independent process strict gate only after
a causal fix is justified; expand scenarios only after an exact 4/4 pass.
