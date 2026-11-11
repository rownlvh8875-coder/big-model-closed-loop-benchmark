# Public ONNX applied-action binding implementation plan

> **For agentic workers:** Use `superpowers:executing-plans` only after separate parent authorization and the gates below. These checkboxes describe future work. **This draft authorizes no implementation, tests, native/model execution, CI, Git or source edits.**

**Goal:** Correct the confirmed MD-V3 model-FRD → world-FLU applied-action boundary at five live public constructor sites, without altering the nine frozen diagnostic dependencies or legacy evidence producers.
**Architecture:** A new public composition factory identifies the verified model/spec or requires an explicit parent-action frame declaration, constructs the unchanged bare policy once, and uses existing `WorldFramePolicyAdapter` once for FRD. Migrated callers pass its policy to their unchanged loop and save a separate frame-binding receipt. Renderer selection remains untouched.
**Tech stack:** Existing Python/dataclasses/hashlib/argparse; existing ONNX policy/adapter, CPU test doubles and existing tiny synthetic test graphs. No new package/workflow/model.
**Spec:** Parent dispatch plus the tracked [generic live action-consumer inventory](../../STAGE7_INTEGRATION_VERIFICATION.md#generic-live-action-consumers-remain-legacy). Original read-only inventory SHA256 is `92de7a27c8ea00e242b489822465b5cf0c86fd05fe956d2d294c86b25bdab7e0`; reviewed prospective-plan SHA256 before tracked preservation is `bfc7ef56d3d617d1bea428814281499617ac7f548d35133dc76914e208a31b1a`. Corrected expansion run43012480495 is independently accepted12/12 and PR #31 source `48bf4309cabe9d2e6e8b2fef952b9fb6f945b28a` merged as `cb1e7bfe698fe3bc3df9540eeb7dc2557e671300`. The current completed-results documentation has not merged; public binding implementation remains HOLD until that gate clears.

## Gates and scope

- This prospective plan has completed parent review and is preserved for the next session. It records no public-binding implementation or test execution; the remaining publication gate below still holds. The separate V3 paint schedule/root replay and fresh full evidence review are complete/CLEAR and root-accepted; current results-documentation final review/checks/Codex/no threads/actual merge remain pending. Its original2/4/candidate1/4 geometry gates do not become a factory or renderer-default acceptance claim.
- **Before tracked implementation/migration/integration:** require independently accepted corrected-expansion evidence and its reviewed source/results merge. Evidence/source acceptance is fulfilled by run43012480495/PR #31; **the current results-documentation PR must still pass its applicable CI/Codex/no unresolved threads/fresh review and actually merge**. No implementation before that merge, no diagnostic binding changes and no future PR number presumed. Root owns gate confirmation and integration; this plan does not request a native/model/heavy CI repeat.
- Preserve bytes of `OnnxBigModelPolicy`, `ModelAction`/`step_ideal`, native camera/public loop, legacy audited producers/readers, adapter, pinned factory and **all ModelSpecs**. Do not globally negate a common policy/kinematics value.
- Only the four unpinned live entrypoint files below migrate. Frozen-RGB isolation, legacy AuditedOfficialOnnx/candidate/expansion and protected diagnostic pipelines stay explicitly legacy; acceleration-only and synthetic policies stay unchanged.
- The factory is action-contract composition only: no sampler/bin/renderer choice, PSSM/task/camera setting, image preprocessing, controller, GT, extra inference, reset, observation/state/raw mutation, real vehicle/CAN, ranking or default promotion.
- Existing renderer defaults remain exactly as today: schematic dual camera for CLI, original native provider for the generic native scripts. Corrected diagnostic Both+unsorted results do not become a canonical renderer default or a new reproducibility/optics result.

## Exact files and migration seams

| Future action | File / current call site |
|---|---|
| Create | `bigbench/public_action_frame.py`: identity resolution, factory and receipt export; no renderer imports |
| Create | `tests/test_public_action_frame.py`: CPU unit and entrypoint-regression contracts |
| Create | `docs/PUBLIC_ONNX_ACTION_FRAME.md`: public flags/API, trace/applied semantics and legacy exclusions |
| Modify | `bigbench/cli.py:44–49`: one `run-onnx` constructor; leave smoke/smoke-compare/inspect branches unchanged |
| Modify | `scripts/compare_native_onnx.py:42,72`: two constructor sites; retain first/second/repeat-first behavior |
| Modify | `scripts/run_same_model_repeat.py:37–40`: fresh binding per repeat; existing camera options unchanged |
| Modify | `scripts/metadrive_optical_check.py:45–48`: optional model branch only; no-model RGB probe unchanged |

No `__init__.py`, packaging dependency, `DrivingPolicy`, shared runner/validator or workflow change is needed. `scripts/metadrive_longitudinal_check.py` remains unchanged: its consumer uses only `ModelAction(0., accel)` (`bigbench/native_longitudinal.py:97–103`). `CameraLaneMock` already emits a synthetic world action; its paths must not be wrapped. `scripts/frozen_camera_model_repeat.py` and all legacy audited/renderer diagnostics remain untouched, including historical pose conventions.

## Frame resolution and public controls

New API: `create_public_onnx_policy(model_path, spec_path, *, model_action_frame='auto', traffic_is_rhd=False, lat_action_t_s=.175, long_action_t_s=.175) -> PublicActionFrameBinding`.
`PublicActionFrameBinding` exposes `.policy`, immutable `.resolution` and `.receipt() -> dict`. Callers explicitly pass `.policy` to the existing loop. No public `session`, fake-policy, factory or identity-verification bypass is added.

- `model_action_frame` accepts only **`auto`, `model-frd`, `world-flu`**. It describes the convention of the **returned parent ModelAction**, not images, world axes, traffic side, raw plans or all graph outputs.
- Known official MD-V3 is recognized by **all three actual identities**: weight SHA256 `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`, bytes **768750198**, and spec-file SHA256 `689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2`.
- For that exact triplet: `auto` or explicit `model-frd` resolves `MODEL_BODY_FRD`; explicit `world-flu` is a conflict and fails **before policy/session construction**. An official weight/spec anchor that only partly matches the triplet fails as an identity conflict, never becomes an unknown override route.
- Other verified model/spec identities: `auto` fails with an actionable declaration-required error **before construction**. Explicit `model-frd` or `world-flu` is accepted as a **user declaration, not source-verified basis**. No basis is guessed from name, hash prefix, shape, model family, traffic flag or action sign.
- `model-frd` constructs the existing `WorldFramePolicyAdapter(inner, source_action_frame='MODEL_BODY_FRD')` once. It negates applied curvature, preserves acceleration and leaves parent actions/raw outputs/plans/states untouched. Both bases are right-handed; no global Y/image flip.
- `world-flu` passes through the unchanged parent's already-world-by-declaration action without a rotation. Never wrap synthetic policies as a shortcut; the public factory constructs the bare ONNX class, not an arbitrary supplied policy.
- Private binding logic rejects an existing adapter marker or already-world/incompatible applied-action marker before binding. Do not make double wrapping idempotent or silently “fix” a declaration conflict. Existing adapter safeguards remain unchanged.

New CLI flags:
- `bigbench run-onnx`, `scripts.run_same_model_repeat`, and the optional model branch of `scripts.metadrive_optical_check`: `--model-action-frame {auto,model-frd,world-flu}`, default `auto`.
- `scripts.compare_native_onnx`: **separate** `--first-model-action-frame` and `--second-model-action-frame`; `--repeat-first` reuses the first declaration. Perform pure identity/frame preflight for BOTH inputs before constructing ORT policies, providers or running either episode. A valid A plus initially invalid/unknown/conflicting B must execute zero constructors/providers/loops. After both preflights pass, construct and run A/B sequentially as before; each factory still performs full current file/identity verification, with no trust/skip bypass from the preflight. Both resolved applied actions must be world-FLU before comparison, but different source bases remain distinct in receipts.
- Keep existing `--rhd`, action-time, integrated/fixed-speed and camera flags unchanged and independent. The no-model optical branch accepts its existing default invocation; a non-auto model-action flag without model/spec is rejected before provider construction.
- Intentional compatibility change: unknown-model CLI calls that formerly omitted basis now require an explicit declaration. Do not add a “legacy” fallback to the migrated live commands. Lower-level bare/legacy APIs remain available and documented as unconverted, with no historical relabeling.

## Identity, construction and receipt contract

Resolve/verify identity before constructing policy/ORT; optical model-mode failure must also precede native provider creation. Verify actual full spec bytes, actual model length/full streaming SHA and manifest weight identity, not just a catalog claim. Existing constructor then performs its unchanged complete ModelContract/file validation again. Repeated file hashing is setup cost, not extra inference or “free” overhead; no trust flag bypasses it.

Keep the new module import-light: stdlib identity/decision types at import, lazy policy/adapter imports only when constructing. No import from native diagnostic scripts to obtain constants, no package-root re-export, and no import of CLI/runner/renderer modules. Known hashes above have existing official MD-V3 provenance; they are not a new model/spec inference.

Factory construction adds **zero resets**; existing bare constructor/loop reset behavior is preserved. Each bound step calls the parent exactly once on the identical observation. Frame tags cover the parent/applied action boundary only. Preserve `name`, `is_mock`, `needs_dual_camera`, contract/session flags, state, trace and raw output identity through existing forwarding; do not overwrite classification or injected/mock flags.

`binding.receipt()` records protocol `public-onnx-action-frame-v1`, actual model/spec identities, requested/resolved frame, identity-vs-user-declaration provenance, rotation-applied flag, parent-action frame and applied `INTEGRATOR_BODY_FLU_WORLD_CCW`. FRD binding exports the adapter's separate actual bridge receipts unchanged. World-declared binding records no conversion and references its parent returned-action/trace convention; do not invent a measured bridge or a corrected-source proof.

Keep `ModelTiming` class/schema and `model_inference.csv` values **unchanged**: `curvature_1pm` is parent-model FRD in the FRD branch, while run-loop frame/action fields describe the applied world action. Store the separate binding/bridge receipt in each newly produced report and CLI summary, and document the distinction. Do not rename old CSV columns, negate parent timing/raw fields, relabel forwarded plans or recalculate old evidence. Preserve parent/bridge count differences and errors after failed/incomplete episodes; export must not truncate dangling records or claim a completed trajectory.

## Transitive compatibility with frozen diagnostics

The nine pinned modules import old core modules and each other; they do not import the four migration seams. `bigbench/__init__.py` currently only declares the version. New imports must point **from the live seams into the new helper**, with no back-edge from pinned/shared modules. Do not add helper imports or global registration to `__init__`, `policies`, `runner`, `onnx_policy`, native core or diagnostic scripts.

CPU regression must check the local source import graph and clean-process imports of both corrected diagnostic modules: no new public factory reachable from their pinned paths, no eager ORT/Panda/native initialization, no symbol replacement and all nine byte pins identical. Legacy validation formulas and FRD audit fields remain unchanged; public migration cannot force pinned diagnostics to adopt a different label/frame or a second bridge.

## Review focus

1. Unknown/partial/conflicting identity must fail before model/session/provider construction, not quietly default to FRD; declaration provenance must remain explicit.
2. A known model's trace/raw values must remain parent FRD while applied curvature changes exactly once; world-declared/synthetic/acceleration-only actions must not be negated.
3. Constructor/reset/step counts, identical observations, all inner state/image/output objects and mock/injected flags must survive composition.
4. Optional/no-model CLI and two-model/repeat-first flags must route independently without changing renderer/defaults or legacy diagnostics.
5. New module dependencies and receipt serialization must not break pure diagnostic imports, source bindings, incomplete evidence or existing CSV/API fields.

## Future tasks and meaningful CPU regression

### Task 1: Identity resolution and public composition
- [ ] Write RED tests for the pure resolution table: full known triplet, each partial anchor mismatch, conflicting known `world-flu`, unknown-auto rejection and both explicit unknown declarations. Use clearly synthetic identity fixtures; never claim a test verified real official bytes.
- [ ] Test actual streaming/file/manifest checks with tiny temporary synthetic files; no official local weights/download. Assert failure before a counted constructor/provider and invalid declaration/type rejection.
- [ ] Implement the new factory/binding module. Private test seams may supply fake inner constructors; native/public CLI has no bypass. Test exact one adapter for FRD, no adapter for declared world, rejection of prior adapter/world markers and no mutation of the parent.
- [ ] Test zero additional constructor resets, one forwarded reset/step, same observation object, signed/zero/nonzero-heading actions, unchanged acceleration, raw four values/state/image/trace identity and honest runtime flags. Preserve/serialize partial parent and bridge records without inferring unknown execution counts.

### Task 2: Migrate only the five live constructor sites
- [ ] CPU-test each parser/default/forwarded argument, separate first/second frames and repeat-first reuse; unknown-auto fails before construction, no-model optical branch remains unchanged. Add valid-A/invalid-B cases asserting both-input preflight fails with zero constructor/provider/loop calls. Prove actual construction remains sequential after two valid preflights and still rechecks full identities; file changes after preflight must not be trusted. Implement the four-file migration and separate receipt outputs.
- [ ] Fake the existing public loops/providers at the **unpinned entrypoint boundary** to inspect the bound returned actions, call/reset/step counts and renderer arguments without native/model execution. Test that no sampler/bin/PSSM/camera/convergence setting changes.
- [ ] Assert `ModelTiming`/CSV parent values remain FRD while applied loop fields/bridge are world; summaries include binding protocol/provenance and do not mislabel declared unknown models as official or newly validated.
- [ ] Regression-check smoke/inspect, CameraLaneMock, acceleration-only and frozen-RGB/legacy audited source paths remain untouched. Do not modify their old tests to expect a new sign.

### Task 3: Isolation, documentation and gated integration
- [ ] Verify all nine pins and ModelSpecs bytes before/after; statically inspect import closure and import diagnostic modules in a clean CPU subprocess with native/model constructors forbidden. Existing legacy/corrected pure fixture regressions must still pass without source/schema updates.
- [ ] Write the public guide with the exact flags/decision table, unknown-model compatibility change, parent-vs-applied receipt distinction, untouched legacy exclusions and renderer/optics/repeatability limits. This migration alone supplies no new official native gate.
- [ ] After the current expansion's evidence/source acceptance and current results-documentation merge prerequisite, run targeted CPU regressions then the full existing suite with required dependencies/no unexplained skips, using existing tiny/fake graphs only. No official local weights, native run or automatic rerun of completed heavy CI is part of this plan.
- [ ] Require fresh whole-change API/scientific/code review, exact-HEAD applicable CI/Codex/no unresolved threads and unchanged pinned-source proof before merging this separate public API change. A new native/model protocol, if later desired, needs separate review/authorization; no future PR number is presumed.

Future targeted check after authorization: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_public_action_frame.py' -v`, followed by the repository's existing full-suite command. Tests must first fail for the missing binding behavior, then pass; no result is claimed by this plan.

## Nine frozen diagnostic dependency pins

| File | SHA256 |
|---|---|
| `bigbench/onnx_policy.py` | `d983d5950296620a6ae89c88993829b4d2cebd35a6fd0e9046a980f75c9142da` |
| `scripts/native_mdv3_repeat_trial.py` | `ddaf0510a775c3a44c908bb4dedf4879ae88bfcb80e1f2d022a8b513a4f42427` |
| `scripts/native_mdv3_renderer_candidate.py` | `5a9058102004e2f5eaa4c9dcab4c24d97a9d42702b7a9e7c248c4f576a30d22e` |
| `scripts/native_mdv3_candidate_expansion.py` | `d86b3be67c8ac3dee31f0bf9928014d3880c8c55a6cd829bb3c46c464d16b42c` |
| `bigbench/kinematics.py` | `58c92e9a5b584932cfe73ebbf7de888f2595e88ceacdabe9a457a78fa77bb70a` |
| `bigbench/native_model_campaign.py` | `0bcb4ca73e1404a7164be1c879a200eeff5ca41e47e3035301d40fd173000bad` |
| `bigbench/metadrive_camera.py` | `1c5661e6c9eea6445ebe55cb246e6b48d3384dd5a731353ba3f1a45599e338f9` |
| `bigbench/model_world_frame.py` | `275f5359a975d9e152f61df74cd57803e1322e1f9618784f0993e780516ec092` |
| `scripts/native_mdv3_world_frame.py` | `cd57c4d407e96459921ca61c78eb81ef55851cd4fafa92ca917bbc7f494a3e38` |

## Self-review / current outcome

The file list, five constructors, frame controls/identity conflicts, transparent composition, receipt compatibility, transitive-import safeguards and sequential integration gates are specified. Existing tests directly exercise the bare ONNX executor/adapter and generic loops; they remain valid low-level contracts rather than being silently migrated. Only new tests cover the new public binding.

This tracked document preserves the reviewed prospective design; no public-binding implementation or tests have run. Corrected expansion evidence and PR #31 source acceptance are complete, while current results-documentation review/checks/merge remain HOLD gates. After that actual merge, follow root's approved sequence for CPU-only implementation in the seven future files above; preserve all nine pins and unchanged source/spec contracts. No native/model execution, completed heavy-cohort repeat, real-vehicle/controller scope, renderer default or performance-rank authority is added.
