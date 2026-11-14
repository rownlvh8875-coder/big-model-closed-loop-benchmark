# Native process environment implementation plan

> Execute inline continuously, without worktrees or implementer delegation.

**Goal:** execute one fresh canary using verified original launch snapshots and
explicitly observed/bound cv2 environment mutation.
**Spec:** [process environment](../specs/2026-11-14-engine-clock-native-process-environment-design.md).
**Base:**f6bedb3d8d8da977b283401c7745429928940e2e; source diagnostic/engine-clock-sealed-native-v3.
**Global constraints:** freeze v1/v2/image006/consumed requests and raw failures;
new03request only; no inherited LD at exec, silent stripping, model or publication.

## Task1: Snapshot boundary and explicit environment identity

- [x] RED fixtures from real02post-import environment: initial LD rejected,
  exact expected mutation accepted only after import, wrong/missing/extra values
  rejected; child built from immutable validated launch snapshot and original
  actual parent remains unchanged; identity commits to both profiles/policy.
- [x] Implement v3 entry modules/workflow and derived full source closure with
  failed02authority. Preserve every other gate and finite budget.
- [x] Targeted GREEN and full unittest discover. Expected green/7existing skips.
  One fresh whole-source review, one Critical/Important TDD pass if needed, retain
  all Minor/declined costs; no rereview.

## Task2: Qualified one-use native03 and independent evidence

- [ ] Draft source PR, exact push/PR4successful named jobs/attempt1/artifacts0.
  Fresh03branch absent/runs0, sole request-only activation/push from source.
- [ ] Terminal original API/ZIP acquisition, root source/image/installed/pre/post
  snapshots/identity/FIFO/cleanup/case byte validation. Never retry01/02/03.
- [ ] Fresh raw acceptance if actually successful. Persist exact result and next
  steps; native success cannot promote original strictFAIL or Stage7INCOMPLETE.

## Review focus

Verify immutable pre-import snapshot supplies actual Popen env, while both actual
post-import mutations remain recorded and validated before identity acceptance.
No arbitrary LD override, parent environment deletion, source equality filtering
or weakened child initial profile. Hash commits to both exact profiles/policy.
Check new namespace/source/request/workflow closure and frozen v2 equivalence.
Actual runtime remains unproved until the new raw canary and independent review.
