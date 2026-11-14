# Native v5 explicit-memory source review

One fresh gpt-6-astra/medium read-only reviewer; no inherited conversation,
mutations, subagents, native, Docker, network or actual cgroup scan. All9files
from8e1d0399d72fb5e303155274b7d0a56a330d8091 through842439ea47d1a5c27e63d9a6e36850a641297514
read. Critical0/Important0/Minor2 plus existing deferred costs. No fix pass or
rereview. Root read full1101tests/7existing skips PASS106.185s;4new RED→GREEN
fixtures PASS0.009s. Source suitable for exactCI and new05, not runtime acceptance.

Reviewer confirmed exact4GiB/CPU2/PID128/privateCG limits and identity binding,
host qualification before load,4bounded nofollow snapshots, zeroOOM gates,
peak-as-aggregate/notRSS/non-atomic semantics. State wrapper adds no commands,
preserves original returns/errors on diagnostic failures. Full v4comparison
shows renderer/capture/FIFO/env/clock/cleanup unchanged.195existing paths and
request05absent; retained04admissions agree and process-log hash matches.

## Deferred minors

- NM-M1: pure state projection is tested, wrapper dispatch/cleanup forwarding/
  repeated filename/write-error/backend-error composition lacks direct mock
  integration fixtures. Cost: reduced regression coverage of that diagnostic
  hook; source inspection confirms one existing call, unchanged return/errors.
- NM-M2: rejected preflight snapshot is not persisted before zeroOOM assertion.
  Cost: less precise diagnosis if a prior OOM counter blocks admission; no provider
  allowed. A surviving parent can preserve later counters.
- Existing SN-M1 inventory-prefix loss, SN-M2 narrower timer and EB-M1 uploader
  fixture fidelity remain with previously recorded costs; no newly Important
  regression. Physical cache separation has actual04upload success evidence.

## All declined judgments and rulings

1. Actual05CGavailability/peak/OOM/constructor/captures/closure need execution.
   Ruling: new original runtime data and independent acceptance decide. Cost if
   wrong: consumed failed05request, no accepted native canary.
2. Remote04API/ZIP authenticity not independently rechecked by reviewer. Ruling:
   preserve root-authenticated original acquisition/CRC/source bindings; failed04
   cannot be promoted. Cost if wrong: upstream diagnosis invalid, no guarantee.
3. Old04OOM cause is unproved by137. Ruling: retain UNKNOWN and never infer
   constructor return/captures from init logs; new measured experiment is separate.
   Cost if wrong: misleading causal/scientific conclusion.
4. Whole1101test result not rerun by reviewer. Ruling: root fresh log and exact
   four external named jobs/attempt1/artifacts0 govern qualification. Cost if
   wrong: author-side blind spot, requiring independent externalCI gate.
5. Existing SN-M1/M2/EB-M1 not resolved as fixture improvements. Ruling: retain
   all deferred costs and actual04upload fact separately. Cost if wrong: overstates
   diagnosis/timer/test coverage; none is a scientific guarantee.
6. Arbitrary hostile ancestor replacement in supplied fixture root not reviewed.
   Ruling: deployed root is fixed inside admitted private-cgroup container with
   dropped caps; metadata API alone grants no authorization. Cost if assumption
   wrong: cgroup-origin assurance fails; do not generalize to hostile-root APIs.
