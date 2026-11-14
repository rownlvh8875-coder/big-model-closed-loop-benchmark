# Native launch diagnostic implementation plan

> Execute inline and continuously; no worktrees or implementer delegation.

**Goal:** preserve exact safe failure predicates and run one separately registered
v2 canary with exact admission security properties. Handle proven Docker28 tmpfs
projection compatibility; do not infer the sole old rejection cause.
**Spec:** [launch evidence design](../specs/2026-11-14-engine-clock-native-launch-diagnostics-design.md).
**Base:**428e7fc44996807fcc3442b41049d99d53b331a5, source diagnostic/engine-clock-sealed-native-v2.
**Global constraints:** immutable v1 and old image/scientific sources, no old
request rerun, no broader native allowance or relaxed predicate, no publication.

## Task1: Source and safe evidence

- [x] RED tests: absent diagnostic projection; accepted fixture has no failed
  predicates; changed host/mount/env/label/config produces exact safe field codes;
  token/proxy/argv/path sentinels absent; v2 scope rejects old request identity.
- [x] Implement v2 entry files and safe pre-gate evidence. Derived source closure
  includes v1 closure, all new files, failed01authority and genuine preflight
  tmpfs carrier evidence. Keep gate semantics except explicit new entry/request
  and optional redundant /tmp Mounts projection; HostConfig.Tmpfs remains exact.
- [x] Run targeted GREEN then full unittest discover. Expected all green,7 existing
  skips; no native/Docker/network in tests. Commit, one fresh whole-source review;
  fix Important/Critical once with RED→GREEN, ledger minors/declined costs.

## Task2: Qualified one-use observation and raw result

- [ ] Source Draft PR, exact push/PR4jobs/attempt1/artifacts0. Prove operation
  branch absent/runs0, register only new02request from qualified source, push once.
- [ ] Preserve terminal original API/ZIP and all CRC/hash/membership evidence.
  If rejected, identify exact actual predicate without guessing; if native runs,
  independently validate all case bytes, installed/host identity and cleanup.
- [ ] Fresh raw acceptance only for an actually successful native canary. Persist
  actual results and precise continuation, leaving strictFAIL/Stage7INCOMPLETE.

## Review focus

Ensure diagnostic output precedes rejection but never leaks unvalidated Env,
labels, argv, mount paths or credentials; no start on gate failure. Compare v1/v2
gate semantics rather than treating copy provenance as automatic proof. Verify
new entry/module/source/request/workflow closure, old and new source bindings,
and two fixed permission/ledger compositions. Previously deferred failure-prefix
and preflight-wide timer issues stay explicit. No claim about unknown old cause.
