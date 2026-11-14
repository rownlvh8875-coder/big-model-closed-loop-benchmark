# Native memory experiment implementation plan

> Inline continuous execution, no worktrees or implementer delegation.

**Goal:** test explicit4GiB budget while preserving cgroup/OOM evidence and
obtain one genuine native camera canary.
**Spec:** [memory design](../specs/2026-11-14-engine-clock-native-memory-design.md).
**Base:**8e1d0399d72fb5e303155274b7d0a56a330d8091; source diagnostic/engine-clock-sealed-native-v5.
**Constraints:** old137is not definiteOOM; frozen image/v1–v4/requests/raws;
new05budget only, no fallback, resized cameras, GL override, model or publication.

## Task1: Explicit resource binding and bounded observations

- [ ] RED temporary cgroup fixtures:4GiB cap required; finite counters/peak;
  missing/malformed/oversize/symlink/FIFO reject; OOM delta blocks acceptance.
- [ ] RED host-memory minimum, exact4GiB Docker admission and safe state projection;
  secret Error/Env fields never persisted; identity binds resources.
- [ ] Implement v5modules/workflow/derived closure and4snapshots without new
  Docker state calls or cleanup-budget changes. Targeted GREEN/full unittest
  discover with7existing skips. One fresh source review; one Important/Critical
  TDD fix pass, no rereview; retain Minor/declined costs.

## Task2: Qualified05experiment and original raw acceptance

- [ ] Draft/exact push+PR4jobs/attempt1/artifacts0, remote05absent/runs0, sole
  request from source, push once.
- [ ] Terminal actual API/ZIP/cgroup/state/image/both inventories/env/identity/
  case bytes and cleanup independently checked. No old137OOM inference.
- [ ] Fresh raw acceptance only if genuine successful canary; persist exact
  resource facts, failures and continuation; scientificFAIL/INCOMPLETE remain.

## Review focus

No automatic budget growth or hidden change to renderer/input/clock semantics.
Exact resource limits bound into identity and source-qualified request. Cgroup
reads bounded/nofollow/fixture-rooted; peak notRSS, metadata non-atomic. Same-PID
namespace/FIFO and finite cleanup preserved; state projections reuse existing
calls and cannot leak arbitrary fields or override original return/errors.
Old04OOM remains unproven; actual new runtime/bytes require independent evidence.
