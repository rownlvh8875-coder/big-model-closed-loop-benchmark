# Stage 7 continuation — camera-order versus task-count isolation

## Completed PR #15 gate

PR #15 was squash-merged after exact-HEAD CI, review and raw artifact verification.
Tested PR HEAD: `f1dc88d476942de05f913cbc828a5fa5912e78a3`.
Merged main commit: `0c678facbf72c269c2453f472e64d8192b70d675`.
All nine check runs succeeded, Codex review had no findings and no unresolved
review threads existed. Fresh local full suite: 216 passed, no skips.

Both native runs 42927840424 and 42930483265 were downloaded and independently
reaggregated: five SHA256-verified ZIPs and 32 distinct native processes each,
exact equality with both uploaded summaries. The original MD-V3 pixel run
42924910245 was also revalidated from all 96 retained raw images and its
uploaded summary. Artifact IDs, digests, match counts and all 25 initial
changed pixel RGB values are in `STAGE7_RGB_SCHEDULER_FINDINGS.md`.

Network API access now works after the user's configuration update. Do not
reapply earlier configuration proposals or publish the cloud environment.
GitHub operations use the supplied authentication; never print token values.

## Current implementation

Branch: `investigation/stage7-camera-order-ticks`, created from the merged main
commit above. `STAGE7_CAPTURE_SCHEDULE_ISOLATION.md` registers the design.
Two new opt-in diagnostic capture modes reverse sensor order or use two shared
mount task ticks. The original model camera, all original CLI/default modes,
PSSM/Chase/igLoop callbacks, ONNX input/state/action and geometry are unchanged.

The new comparator rejects wrong modes, raw frame counts/order/gaps, missing
or changed task registries, nonfinite/mismatched WORLD poses, missing positive
controls, invalid SHA series, reused process IDs and stale summaries. Matching
static images never become an original-model repeatability verdict.

New code local full suite: **232 passed**, no skips. Regression tests were run
failing before implementation. Four separate local native processes validated both new modes at seed
20261109 / s_curve_left_right. Wide-first repeats matched source Road/Wide
8/10 and 5/10, I420 8/10; paired-two-tick repeats matched source Road/Wide
8/10 and 8/10, I420 8/10. These local concurrent compatibility checks are
not the controlled four-scene CI matrix and not a renderer repair.

Read-only code review identified possible same-runner PID reuse across arms.
The regression reproduced acceptance before a case-level uniqueness guard;
it now passes, as does the full 232-test suite. Bare PID reuse across separate
CI machines is allowed. No other review findings were identified. New GitHub
CI, automated review and artifact reaggregation remain pending.

## Resume and finish this branch

```bash
cd /workspace/big-model-closed-loop-benchmark
source /workspace/.cloud-tools/onboarding/activate.sh
git status --short
git log -4 --oneline
gh pr list --head investigation/stage7-camera-order-ticks
gh run list --branch investigation/stage7-camera-order-ticks --limit 12
```

Use the existing isolated checkout; do not create a worktree or publish the
environment. Native weights remain on ephemeral CI runners only. Keep image
bytes, archives and generated outputs in ignored `output/`, never Git.

Required next checks: complete local native validation, read-only code review,
full unit CI, the 32-process order/tick native workflow and its independently
recomputed aggregate. Shared diagnostic code also triggers existing native
regression workflows; investigate failures rather than bypassing them. Download
ZIPs through GitHub API, verify their published sizes/SHA256 and safe member
paths before extraction. Recompute all scene summaries from raw process JSON
and compare to the published aggregate. Record the exact tested HEAD, Actions
URLs, artifact IDs/digests and observed numbers. Merge only after required CI
and automated review complete with no unresolved findings.

## Scientific gates still open

Original uninstrumented official MD-V3 strict repeatability remains the prior
**0/4 PASS (FAIL)**. No renderer repair or new official ONNX run has been made
in this investigation. Camera geometry, rendering determinism, real-sensor
optical equivalence and model performance are separate questions.

Use the controlled order/tick result to choose the next hypothesis. Do not
adopt paired capture, disable PSSM/Chase, reorder GPU passes, modify pixels or
model state/actions as the default without causal and rendering-semantics
validation. Only after an evidenced repair run the separate original
2 seeds × 2 S-curves × 12 steps × 2 processes official MD-V3 exact gate. Expand
scenarios and duration only after all original 4/4 conditions pass exactly.

## Xvfb cleanup-status review correction

The GitHub review identified the repository's known Xvfb cleanup exit status 5.
The new `scripts/run_native_capture_trial.py` rejects preexisting output,
launches one fresh native process, preserves other failure statuses, and
accepts status 0 or cleanup-only status 5 only after the full newly generated
native task/clock/pose/hash receipt validates. Missing or invalid receipts
still fail. Five runner tests plus the full 232-test suite passed. New exact-
HEAD native CI and automated review must be confirmed after this correction.
