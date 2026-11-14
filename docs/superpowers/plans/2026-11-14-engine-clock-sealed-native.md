# Sealed native canary implementation plan

> Execute inline, sequentially, without worktrees or implementer delegation.
> User already delegated routine choices and requested continuous execution.

**Goal:** execute and independently authenticate one new sealed-image native
camera/clock canary with zero official-model calls.

**Spec:** [sealed native design](../specs/2026-11-14-engine-clock-sealed-native-design.md).

**Architecture:** a new pure/source admission module, outer authenticated image
controller and isolated in-container parent/child harness. Reuse immutable image
transport/archive/Docker primitives and offline camera case validator. No old
native gate, request, producer or scientific result changes.

**Global constraints:** baseb895800a0a1a3bc399e6ec5d47ffe05106f53127;
source diagnostic/engine-clock-sealed-native-v1; new operation sealed-native-20261114-01.
No main merge, publish, model download or ORT. Actual source closure must be
derived; all failures/raws retained. One fresh whole-source review before request.

## Task1: Pure protocol and boundary tests

Files: scripts/engine_clock_sealed_native.py,
tests/test_engine_clock_sealed_native.py, new workflow and this spec/plan.
Interfaces: source_paths, validate_request, validate_activation, validate_source_ci,
validate_live, environment_profile, validate_launch, validate_permit, make_identity.

- [ ] Write RED tests for request scope/one-use activation, exact CI/run, native
  env/mount injection, permit ancestry/group/binding, and strict host/core identity.
- [ ] Run `python -m unittest discover -s tests -p test_engine_clock_sealed_native.py -v`.
  Expected: assertion failures naming absent implementation, no native/network.
- [ ] Implement minimum pure logic; targeted command GREEN.

## Task2: Actual outer controller and isolated native harness

Files: scripts/engine_clock_sealed_native_run.py and
scripts/engine_clock_sealed_native_container.py; extend owned tests only.
Interfaces: new controller authenticates source/image and freezes binding;
container parent/child consume exact binding, two inventories and one-use FIFO.

- [ ] RED transport/launch/composition and refusal-before-provider fixtures.
- [ ] Implement bounded controller, prestart copies, exact inspected launch,
  parent/child native lifecycle and offline validation. Do not call native locally.
- [ ] Targeted GREEN then full unittest discover with existing CPU interpreter.
  Expected: green suite, baseline skip reasons retained.
- [ ] Commit source and use one fresh whole-branch reviewer; one Important fix
  pass if needed. Ledger all findings/declined rulings and costs; no rereview.

## Task3: Exact-head CI and one new canary

- [ ] Push source/Draft PR based on accepted evidence; authenticate exact push/PR
  synthetic-unit and generated ONNX interface jobs, attempt1/artifacts0.
- [ ] Prove operation branch absent/runs0; register sole new request from qualified
  source, push once. Preserve API originals and all failed/partial evidence.
- [ ] Observe terminal run once; download original artifact once and verify ZIP,
  API/source/image/identity/launch/cleanup/case payloads independently.
- [ ] Fresh read-only raw acceptance, ledger real results and limitations; no
  automatic native retry or ABBA. Persist exact continuation and Draft evidence.

## Review focus

Read actual producer-to-new-source bindings separately, source closure completeness,
prestart proof versus running Python, exact Docker inspection including writable
mounts/environment, FIFO EOF/deadline/parent/group, no legacy gate invocation,
hashing/native shared deadlines and cleanup reserve, complete failure evidence and
provider-attempt uncertainty. No tests imply actual GL/inference or future C/A host
equivalence. Check code composition beyond pure fixture coverage.
