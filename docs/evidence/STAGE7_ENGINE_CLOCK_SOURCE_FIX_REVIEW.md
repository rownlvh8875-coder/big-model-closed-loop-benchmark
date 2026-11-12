# Task 1 fix round 1 — scoped independent re-review

Reviewed HEAD: `30dcc5b4075dd2cfaf25b3e8d90e324386a278af`.
Fix base: `9bb9ebbbf2ca67da0e12705b9ec20ac843ab8c8c`.

**All findings addressed. Spec: PASS. Task quality: ready for the pre-native source gate when combined with the prior source review.** No new Critical, Important, or Minor issue was found in this fix diff. The deterministic ABBA CPU-test blocker is closed. This review supplies source readiness for root's one-shot canary decision; it does not establish native feasibility, accept raw evidence, or authorize a retry or ABBA activation.

## Scope and method

Read `task-1-brief.md`, including its root-ruling addendum; the full prior `task-1-source-review.md`; the fix append and `fix_rounds[0]` machine report; and the complete supplied `fix-1-review-package-30dcc5b4075d.md` diff once. Inspected the changed test locations and the covering harness/recorded outputs. This was a finding-and-fix review: unchanged production logic and Git admission implementations were not re-reviewed. The prior source review remains the production/spec review for the unchanged runner and workflow.

Read-only Git confirmed the exact HEAD, clean tracked status, and a one-file fix: `tests/test_engine_clock_native.py`, 66 insertions and 26 deletions. The runner, workflow, and mutable request have no fix-diff changes. `git diff --check FIX_BASE HEAD` returned exit 0.

## Prior finding disposition

**Important I1 — ADDRESSED.** CI CPU tests must work after a valid ABBA request activation, while their individual injected failure scenarios must reach their intended stages.

- `tests/test_engine_clock_native.py:16` builds independently schema-checked synthetic canary or ABBA request bytes, with the exact ABBA acceptance members. `tests/test_engine_clock_native.py:28` overlays only the exact repository request's `Path.read_bytes` in memory and delegates all other reads to the saved reader. The context manager restores the reader, and nested covering/scenario overlays remain compatible.
- `tests/test_engine_clock_native.py:436` isolates the launch-stop scenario to its canary fixture. It still requires exactly one case invocation and now requires `failure_stage == 'case_00'` and the injected `stop` error at line 439. An earlier phase mismatch cannot satisfy it.
- `tests/test_engine_clock_native.py:449` isolates the malformed candidate test; its line 452 assertion requires `dataset_validation`, preventing the prior unrelated-gate false positive.
- `tests/test_engine_clock_native.py:580` isolates the subreaper case and line 583 requires `subreaper`, preserving the injected error check.
- `tests/test_engine_clock_native.py:639` isolates the incomplete-phase null-count fixture. Its existing count assertions remain unchanged.
- `tests/test_engine_clock_native.py:989` derives the preflight fixture request and digest from explicit canary bytes and overlays those same bytes. Existing assertions at lines 992–999 still require no Popen or provider construction, each intended `context`/`runtime`/`unique_run` failure stage, persisted ledger identity, truthful nullable fields, and null aggregates.
- `tests/test_engine_clock_native.py:757` runs the actual extracted registered-phase shell step for both registered modes. The temporary `sitecustomize.py` reader supplies only that subprocess's working-tree request read; a separate fake Git executable verifies exact `git show SHA:REQUEST` argv and supplies its blob bytes. Line 784 asserts actual output bytes `mode=canary\n` and `mode=abba\n`. Lines 789–793 change the Git blob to whitespace-different, valid same-mode JSON, then require nonzero exit, the specific unchanged Git-byte mismatch error, and no output file in both modes.

The production request parser and workflow Git-byte check execute in that integration test. Their implementation is not replaced, and neither CPU test invocation nor any admission/source/runtime/acceptance gate is skipped or weakened. The workflow and production runner are byte-identical to the previously reviewed base.

## Verification evidence checked

No suite was repeated: root explicitly limited this pass to retained covering evidence unless a narrowly identified doubt required a test. Direct inspection resolved the fixture/step questions, and independent hash/output checks found no such gap. The evidence below is from the actor's retained executions, not new reviewer test runs.

The covering driver `fix-1-verify-mode.py` extracts and asserts the unchanged workflow command, runs it under `bash -e`, selects the existing CPU interpreter through PATH, overlays request bytes only in memory, and asserts unchanged on-disk request bytes afterward. Its temporary startup guards reject real API/provider calls and report their counts on stderr without corrupting CLI JSON stdout. Inner workflow-step subprocesses install their own narrow reader and fake Git; their extracted code only reads/parses the request and writes the registered mode.

| Retained execution | Confirmed output | SHA256 |
| --- | --- | --- |
| `fix-1-red.log` | 1 test, 0.007s, expected `0 != 1` launch-count failure before repair | `ec3506ecc6cb2fd91ec724f09f35a1a5db9e228a9171f656559a6cd29c1970d4` |
| `fix-1-targeted-green.log` | 9 intended regression tests, 1.097s, OK | `39328e8cba5bf7baa52808bf4a9fee56beef6bd35ccb8e0f0c56963ab8fc5fdd` |
| `fix-1-workflow-canary.log` | 82 tests, 9.667s, OK, no skips, command exit 0 | `ca8ba4f8d28644bdc62c43478c76dd45ad3ced1e06f29150575833800b32def7` |
| `fix-1-workflow-abba.log` | 82 tests, 9.349s, OK, no skips, command exit 0 | `50950e098537fafaa970736fcf37eb27c05291f863973101acc674fd75ab0282` |

Both covering logs identify exactly `python -m unittest tests.test_engine_clock_native tests.test_engine_clock_boundaries -v\n`, contain 82 individual `... ok` results, report `real_api_calls: 0` and `real_provider_calls: 0`, and finish with `ON_DISK_REQUEST_UNCHANGED True`. The registered-step test is included in both. Both modes and both byte-mismatch branches are enforced by its loop/assertions, not inferred from a constant grep.

Independently recomputed all ten fix-round artifact/log hashes and sizes in `fix_rounds[0].verification_logs`, including the covering driver, RED/GREEN logs, source map, and four preserved failed covering logs. All match. Inspected the retained failure summaries: the initial environment attempts fail before the corrected CPU PATH, and the guard-output attempts fail the CLI JSON test; the final logs are complete successful replacements. These are disclosed verification harness corrections, not hidden production changes or native retries.

## Preservation and binding

Independently recomputed all 67 `before-source67.json` entries and all 43 `before-workflows43.json` entries: no differences. All four current file digests match both the fix machine report and the exact reviewed HEAD's blobs. The initial report copies and old `source70-final.json` hash remain intact. The current snapshot wrapper's source map equals the machine report map; all 70 current producer file hashes and the compact sorted-JSON aggregate hash match:

`6f8dcc2fc4aa7b1896a74d43ea4e030f89729b4b7851825cd0bbd444c6acab04`.

Current mutable request SHA256 remains `2b10f4cba178afb3e73581bcde2b44275f3875a13233552f4f0dfff0fe8d7800` (initial canary). The source snapshot wrapper records capture-time `actual_head` equal to the pre-commit fix base; current HEAD binding was checked independently against `30dcc5b4075dd2cfaf25b3e8d90e324386a278af`, so that historical metadata is not treated as the reviewed commit identity. The prior review file hash also matches the actor's referenced review hash.

No old workflow/request/history changes appear in the fix commit. Historical full-suite evidence (644 tests, 7 optional skips) remains historical and was not relabeled as a run of this revision. This pass performed no source, Git/index/HEAD, request, CI, dependency, network, native/Panda/Xvfb/ORT/model, or raw-history mutation; only this review report was written.

## New issues and residual limits

New Critical: none. New Important: none. New Minor: none. Open prior findings: none. Out-of-scope observations: none requiring action.

Actual Actions authentication/status timing, pinned installation, bootstrap, Xvfb collision behavior, Panda/MetaDrive compatibility, cache population, engine cleanup, and native resource behavior remain unexecuted in this review, as already recorded by the prior source review. Fake CPU evidence does not resolve those expected native uncertainties. Raw canary acceptance and any direct-parent ABBA admission remain later root-controlled gates. The prior scientific limitations and official-call accounting are unchanged.
