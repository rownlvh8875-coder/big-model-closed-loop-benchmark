# Native evidence boundary implementation plan

> Inline continuous execution; no worktrees or implementer delegation.

**Goal:** preserve actual case/failure evidence independently of private Mesa
cache permissions and obtain one fresh bounded native observation.
**Spec:** [evidence boundary](../specs/2026-11-14-engine-clock-native-evidence-boundary-design.md).
**Base:**f5422390b1e222b098d1b1886e33ffd5d582c8a7; source diagnostic/engine-clock-sealed-native-v4.
**Constraints:** freeze01–03sources/requests/data, no inference about missing03raw;
no permission changes to private caches, no gate relaxation or model/publication.

## Task1: Physical artifact boundary and safe failure summary

- [x] RED real fixture: cache beside execution, unreadable nested cache cannot
  enter any artifact-root walk; container still mounts exact /work/cache route.
- [x] RED failure fixtures: bound partial/case summary, unknown bounds when
  absent/mismatched/malformed/oversized/symlink, redaction of secret and URL values.
- [x] Implement v4modules/workflow/full closure and new evidence policy. Targeted
  GREEN/full unittest discover, expected green with7existing skips. One fresh
  read-only whole-source review; one Important/Critical fix pass, no rereview;
  retain all Minor/declined costs.

## Task2: One qualified native04 and independent raw proof

- [ ] Draft source/exact push+PR4jobs/attempt1/artifacts0; prove remote04absent/
  runs0, register sole new request from source, push once.
- [ ] Original terminal API/log/artifact acquisition with zero-artifact failures
  retained explicitly. If artifact exists, independently verify image/installed
  identities, both env snapshots, case payloads, exact observers and cleanup.
- [ ] Fresh raw acceptance only after genuine success. Persist actual outcome,
  original failures, deferred costs and next phase; no scientific promotion.

## Review focus

Artifact walker must never traverse private cache, including root-owned0700
subdirectories. No recursive chmod/chown, no broad mounts, no weakened admission.
Summary must preserve unknown bounds when binding absent and never leak secret
values from malformed/hostile metadata. Compare v3/v4 runtime/controller changes,
new namespace closure and actual workflow paths. Missing03raw remains unknown.
