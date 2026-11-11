# Public ONNX applied-action binding implementation plan

> **For agentic workers:** Parent authorization and prerequisite source/results merges are confirmed below. Use `superpowers:executing-plans` for the authorized implementation. Unchecked items remain unverified. Only the bounded existing-workflow CI regression in the accepted amendment below is planned; no local official-model or renderer-default authority is added. Root owns Git, CI and integration.

**Goal:** Correct the confirmed MD-V3 model-FRD → world-FLU applied-action boundary at five live public constructor sites, without altering the nine frozen diagnostic dependencies or legacy evidence producers.
**Architecture:** A new public composition factory identifies the verified model/spec or requires an explicit parent-action frame declaration, constructs the unchanged bare policy once, and uses existing `WorldFramePolicyAdapter` once for FRD. Migrated callers pass its policy to their unchanged loop and save a separate frame-binding receipt. Renderer selection remains untouched.
**Tech stack:** Existing Python/dataclasses/hashlib/argparse; existing ONNX policy/adapter, CPU test doubles and existing tiny synthetic test graphs. No new package, workflow file or model architecture; existing workflow invocation compatibility is covered by the accepted CI amendment below.
**Spec:** Parent dispatch plus the tracked [generic live action-consumer inventory](../../STAGE7_INTEGRATION_VERIFICATION.md#generic-live-action-consumers-remain-legacy). Original read-only inventory SHA256 is `92de7a27c8ea00e242b489822465b5cf0c86fd05fe956d2d294c86b25bdab7e0`; reviewed prospective-plan SHA256 before tracked preservation is `bfc7ef56d3d617d1bea428814281499617ac7f548d35133dc76914e208a31b1a`. Corrected expansion run43012480495 is independently accepted12/12 and PR #31 source `48bf4309cabe9d2e6e8b2fef952b9fb6f945b28a` merged as `cb1e7bfe698fe3bc3df9540eeb7dc2557e671300`. Completed-results PR #32 subsequently merged as `48e79a7ed5aedf6daa5a62ff68d2225af7955ef1`; the execution checkpoint below records fulfilled prerequisites and parent authorization.

## Gates and scope

**Execution checkpoint:** results PR #32 actually merged as
`48e79a7ed5aedf6daa5a62ff68d2225af7955ef1` from
`8e847da753d2c50af8ec5b6cbdba40bce774ed3d`, after four successful checks,
current-HEAD Codex without findings/no unresolved threads and fresh final
ten-document review (diff SHA256
`08f2f4093aa78d2862b3efaf8ec3b8eaf50fd7df54a7a1e7c4f29ba3f47e2f09`).
Main unit43032709728 passed. Root authorized the specified implementation on
`fix/public-onnx-action-frame` based on that merge. The original HOLD checkpoints
are historical; their source/results prerequisites are now fulfilled.
Implementation and22 targeted/383 full CPU tests are complete without skips;
seven-file code/API review is CLEAR. Whole-change review, CI/Codex and the new
change's integration remain pending. The API/source boundary and nine diagnostic
dependency pins remain unchanged; five workflow edits are scoped below.

- This plan completed parent review before implementation. Its original results-draft HOLD checkpoint is historical: V3 evidence review and final results-documentation review/checks/Codex/no threads/actual PR #32 merge are complete. Original2/4/candidate1/4 paint geometry does not become a factory or renderer-default acceptance claim. Public binding implementation/CPU tests are complete; whole-change review and CI/integration remain pending.
- **Prerequisite fulfilled before tracked implementation:** corrected-expansion evidence was independently accepted, PR #31 merged its reviewed source and PR #32 passed applicable CI/Codex/no unresolved threads/fresh review and actually merged its results. Root confirmed both merges before authorizing this branch. No diagnostic binding change or future PR number is presumed; root owns integration. The accepted CI amendment below permits only the bounded new public-entrypoint regression through existing triggers, with no manual replay of completed scientific cohorts.
- Preserve bytes of `OnnxBigModelPolicy`, `ModelAction`/`step_ideal`, native camera/public loop, legacy audited producers/readers, adapter, pinned factory and **all ModelSpecs**. Do not globally negate a common policy/kinematics value.
- Only the four unpinned live entrypoint files below migrate. Frozen-RGB isolation, legacy AuditedOfficialOnnx/candidate/expansion and protected diagnostic pipelines stay explicitly legacy; acceleration-only and synthetic policies stay unchanged.
- The factory is action-contract composition only: no sampler/bin/renderer choice, PSSM/task/camera setting, image preprocessing, controller, GT, extra inference, reset, observation/state/raw mutation, real vehicle/CAN, ranking or default promotion.
- Existing renderer defaults remain exactly as today: schematic dual camera for CLI, original native provider for the generic native scripts. Corrected diagnostic Both+unsorted results do not become a canonical renderer default or a new reproducibility/optics result.


**CI scope correction:** the initial CPU-only integration assumption below was
superseded before the first push. Existing workflow callers require five YAML
compatibility/receipt/asset-verification edits and four existing automatic
native jobs, under the accepted amendment appended below. Its 65 model steps
are a planned budget; no native/model result is claimed yet. Official weights
stay on ephemeral CI runners; triggers, failure criteria and renderer defaults
are unchanged. A strict repeat failure blocks merge.

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

No `__init__.py`, packaging dependency, `DrivingPolicy` or shared runner/validator change is needed. Five existing workflow invocation/receipt/asset-check changes are specified in the accepted CI amendment below. `scripts/metadrive_longitudinal_check.py` remains unchanged: its consumer uses only `ModelAction(0., accel)` (`bigbench/native_longitudinal.py:97–103`). `CameraLaneMock` already emits a synthetic world action; its paths must not be wrapped. `scripts/frozen_camera_model_repeat.py` and all legacy audited/renderer diagnostics remain untouched, including historical pose conventions.

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

## Implementation tasks and meaningful CPU regression

### Task 1: Identity resolution and public composition
- [x] Write RED tests for the pure resolution table: full known triplet, each partial anchor mismatch, conflicting known `world-flu`, unknown-auto rejection and both explicit unknown declarations. Use clearly synthetic identity fixtures; never claim a test verified real official bytes.
- [x] Test actual streaming/file/manifest checks with tiny temporary synthetic files; no official local weights/download. Assert failure before a counted constructor/provider and invalid declaration/type rejection.
- [x] Implement the new factory/binding module. Private test seams may supply fake inner constructors; native/public CLI has no bypass. Test exact one adapter for FRD, no adapter for declared world, rejection of prior adapter/world markers and no mutation of the parent.
- [x] Test zero additional constructor resets, one forwarded reset/step, same observation object, signed/zero/nonzero-heading actions, unchanged acceleration, raw four values/state/image/trace identity and honest runtime flags. Preserve/serialize partial parent and bridge records without inferring unknown execution counts.

### Task 2: Migrate only the five live constructor sites
- [x] CPU-test each parser/default/forwarded argument, separate first/second frames and repeat-first reuse; unknown-auto fails before construction, no-model optical branch remains unchanged. Add valid-A/invalid-B cases asserting both-input preflight fails with zero constructor/provider/loop calls. Prove actual construction remains sequential after two valid preflights and still rechecks full identities; file changes after preflight must not be trusted. Implement the four-file migration and separate receipt outputs.
- [x] Fake the existing public loops/providers at the **unpinned entrypoint boundary** to inspect the bound returned actions, call/reset/step counts and renderer arguments without native/model execution. Test that no sampler/bin/PSSM/camera/convergence setting changes.
- [x] Assert `ModelTiming`/CSV parent values remain FRD while applied loop fields/bridge are world; summaries include binding protocol/provenance and do not mislabel declared unknown models as official or newly validated.
- [x] Regression-check smoke/inspect, CameraLaneMock, acceleration-only and frozen-RGB/legacy audited source paths remain untouched. Do not modify their old tests to expect a new sign.

### Task 3: Isolation, documentation and gated integration
- [x] Verify all nine pins and ModelSpecs bytes before/after; statically inspect import closure and import diagnostic modules in a clean CPU subprocess with native/model constructors forbidden. Existing legacy/corrected pure fixture regressions must still pass without source/schema updates.
- [x] Write the public guide with the exact flags/decision table, unknown-model compatibility change, parent-vs-applied receipt distinction, untouched legacy exclusions and renderer/optics/repeatability limits. This migration alone supplies no new official native gate.
- [x] After the current expansion's evidence/source acceptance and current results-documentation merge prerequisite, run targeted CPU regressions then the full existing suite with required dependencies/no unexplained skips, using existing tiny/fake graphs only. No official local weights or manual repeat of completed heavy cohorts is permitted; the separately specified existing-workflow CI regression is the only planned native/model work.
- [ ] Require fresh whole-change API/scientific/code review, exact-HEAD applicable CI/Codex/no unresolved threads and unchanged pinned-source proof before merging this separate public API change. Only the separately reviewed existing-workflow regression below is included; no extra native/model protocol or future PR number is presumed.

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

This tracked document preserves the reviewed design. Corrected expansion evidence, PR #31 source acceptance and PR #32 results-documentation review/checks/actual merge are complete. Root authorized implementation in the seven specified files and accepted the five-workflow integration amendment below. After the lifetime fix,22 targeted and383 full CPU tests pass without skips, and seven-file code/API review is CLEAR. Whole-change/workflow review and CI/integration remain pending. Preserve all nine pins and unchanged source/spec contracts. Only the existing-workflow CI regression below is planned; no local official-model execution, manual completed-cohort repeat, real-vehicle/controller scope, renderer default or performance-rank authority is added.


## CI integration amendment accepted before first push

Root reviewed and accepted source amendment SHA256 `7d7688712e85f8208146c92495bc8001f6782cc3ffab3be7ffa06149ebde8a12` before editing workflows or pushing `fix/public-onnx-action-frame`. This source review executed no official weights/models/native/CI. Actual source/workflow/checkpoint diffs require fresh whole-change review before push; CI results remain pending.

The previously reviewed seven-file implementation remains CPU TDD work. Its former CPU-only integration assumption is incomplete: changing existing public entrypoints matches existing `push.paths` filters. Keep those triggers and check criteria. Predeclare their new public-boundary regression instead of removing triggers, substituting fixtures for native jobs, using skip-CI, canceling required checks or replaying completed Stage 7 scientific cohorts.

### Exact scope amendment

Retain the seven implementation files (new public factory, new CPU tests, new public guide, four migrated public entrypoints). Root owns the three tracked documentation updates: the public implementation plan, continuation checkpoint and integration record. Permit changes to these five existing workflow YAML files only for the following concrete integration needs:

| Workflow | Proposed change | Trigger policy |
|---|---|---|
| `two-model-native.yml` | Add `--second-model-action-frame model-frd`, with source-supported operator-declaration provenance; first MD-V3 remains `auto`. | Keep dispatch and all current push paths, flags, assertions and failure semantics. |
| `light-speed-native.yml` | Add `--model-action-frame model-frd`, with the same explicit operator-declaration scope for Light Speed. | Keep its existing self-YAML push path. This necessary command repair adds one automatic five-step job. |
| `real-mdv3-one-step.yml` | Give its existing matrix an action-frame field (`auto` for MD-V3, `model-frd` for Light Speed 2), and forward that field to `run-onnx`. | Keep its docs-only push filter; this YAML edit does not trigger the old five-step matrix. Do not dispatch that matrix manually. |
| `metadrive-optical.yml` | In the existing asset preparation block, assert SHA256 `4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9` in addition to existing byte size `134074203`, before extraction/native startup. | Keep no-model invocation, two poses, captures and current push paths. |
| `model-camera-repeat.yml` | Add a CPU inspection of the newly produced successful MD-V3 binding receipts, after the existing strict repeat command succeeds. Check actual identity, verified provenance, parent/applied frames and per-row once-only curvature conversion/unchanged acceleration against the existing run reports. | Preserve the original command's nonzero exit on mismatch/incomplete run. Do not use `continue-on-error`, replace the gate, change tolerances or change artifact-on-failure preservation. |

The binding-receipt inspection must use the actual factory/adapter schema, not infer successful execution from labels alone. For a successful twelve-row run, each saved binding must agree with the embedded report binding, have twelve committed parent trace rows and twelve bridge receipts, and its applied actions must agree with the existing twelve episode rows. Preserve raw parent values. Keep the public receipt's conservative total-execution-unknown field; a failed job's partial trace is not proof of all attempted ORT calls. This inspection adds no model/capture call and supplies no renderer repeatability or quality claim.

No factory auto allowlist entry, ModelSpec, nine frozen diagnostic dependency, shared policy/kinematics/adapter/native-loop implementation, renderer/default, camera/sampler/bin/task/PSSM setting, image preprocessing, controller or performance-ranking criterion changes. Other heavy workflows stay byte unchanged. Any extra runtime or workflow change needs a separately reviewed amendment before it can trigger CI.

### All six existing workflow callers

All six have `workflow_dispatch` and a path-filtered `push`, without a branch filter or pull-request event. Counts below describe benchmark Python invocations and sequential fresh policy/provider instances, not every setup/download/helper process spawned by a CI job.

| Caller | Current relevant command arguments | Automatic after amended feature push? | Successful planned model work |
|---|---|---|---|
| `model-camera-repeat.yml:58–63` | MD-V3; LR seed `20261109`; `--steps 12 --speed 8 --camera-convergence 6 --camera-pixel-tolerance 16 --camera-channel-delta 10`; original native renderer. | Yes: existing script path and the proposed YAML edit. | One benchmark Python invocation; two fresh MD-V3 policy sessions/provider worlds; `2×12=24` calls. |
| `two-model-native.yml:62–68` | MD-V3 A, Light Speed 2 B; LR seed `20261109`; `--steps 12 --speed 8 --repeat-first --full-s-route`; original native renderer. | Yes: existing script path and proposed YAML edit. | One benchmark Python invocation; sequential fresh A/B/A sessions/worlds; `24` MD-V3 plus `12` Light Speed 2 calls. |
| `metadrive-optical.yml:55` | `--steps 2`, no model/spec. The no-model branch captures its two fixed baseline/shifted poses. | Yes: existing script path and asset-check YAML edit. | One benchmark Python invocation/provider world; zero ORT sessions/calls; two rig captures, four sensor RGB reads. |
| `light-speed-native.yml:54–57` | Light Speed, `model_specs/light-speed.json`, `--steps 5`; optional optical model branch. | Yes, because the necessary declaration repair changes its self-triggering YAML. | One benchmark Python invocation; one fresh Light Speed policy session/provider world; five calls. |
| `real-mdv3-one-step.yml:17–24,41–47` | Existing schematic `run-onnx` matrix: MD-V3 and Light Speed 2, five steps each, `--accept-uncalibrated-vision`. | No. Its push paths contain only `docs/REAL_MODEL_SMOKE_TRIGGER.md`, which is not changed. | Zero added calls in this amendment. An independent dispatch would be ten calls; it is not authorized/planned here. |
| `metadrive-mdv3-inference.yml:58–61` | Exact MD-V3, optical model branch, `--steps 3`, default `auto`. | No. Its push paths contain only its own unchanged YAML. MD-V3 `auto` remains supported. | Zero added calls. Do not dispatch/replay its old three-step cohort. |

The first three workflows alone would plan sixty calls. Correctly repairing the additional self-triggering Light Speed invocation makes the actual amended per-push budget **four benchmark Python invocations, seven provider worlds, six fresh ORT policy sessions and sixty-five planned calls: 48 MD-V3 + 12 Light Speed 2 + 5 Light Speed**. The no-model optical job additionally plans four sensor reads. Convergence can perform additional RGB captures; do not invent a fixed sensor/render/readback total from the inference budget, and exclude unmeasured environment startup activity from claimed capture counts.

Only if all source acceptance gates pass and the PR actually merges, that main push changes the same paths and automatically triggers the same four existing jobs again. Predeclare this possible main-integration budget separately at the same size, not as a manual rerun of an accepted scientific cohort. Across one fully completed frozen feature push and that conditional main merge the planned ceiling is 130 model steps, twelve policy sessions, fourteen provider worlds and eight benchmark Python invocations, plus eight no-model optical sensor reads. Earlier failure can reduce completed work and leave total attempted execution unknown. Do not label planned numbers as observed results.

### Source basis and explicit declaration provenance

Pinned source commit: `e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42`. The source bodies below were read without execution; their Git blob IDs and byte sizes were checked against the cached official source tree, whose SHA256 is `930d4fa83ab88d6e3f77014c4336c6c57c78cb0c3924a51ff859427d366cf49c`.

| Source / local identity | Full SHA256 | Relevant fact |
|---|---|---|
| [Pinned catalog.json](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/model_catalog/catalog.json) | `2a6f3f16b3d7741355465769304100fbf52db86d40cbdfb7ac509773a5e4cde0` | 2929 bytes; blob `fa8af488ea81f7e23d45b7cd2f6806fc20aefba3`; maps MD-V3, Light Speed and Light Speed 2 to their respective `jetson_spec` files in the shared model catalog. |
| [Pinned Light Speed 2 spec](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/model_catalog/light-speed-2.json) | `de56c423af3e953ed5618404dde8550ea276ee81116d67d798e059f929aa7a8f` | 1662 bytes; blob `8487b5051e8a3e2d109825ef01fe61ba9e2edb4e`; every source JSON value equals the local spec after removing local `source`/`catalog_commit` annotations. Action slice `[2062,2066]`. |
| Local `model_specs/light-speed-2.json` | `2ce9b7caaa50649612d8323c66d9bc193b4c89d39fb399ec00553055d3f87afa` | Official weight SHA256 `909a140019050a9d7f00db22dd4f4085928d2af9474a82244672ddab964f95a8`, byte size `768749892`. No weight was downloaded for this audit. |
| [Pinned Light Speed spec](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/model_catalog/light-speed.json) | `9b73940c2a10a0af5c54c7b95e105b00b8dbf4459f6e83745fddab52a40a78d0` | 1668 bytes; blob `8124d9d32321399656c9f62e846e1d3dbc1569dd`; every source JSON value equals local after removing those annotations. Action slice `[2062,2066]`. |
| Local `model_specs/light-speed.json` | `f25bd9ef91503831b64de47be68c65a6a336e2f9fd348894e1c67902998ebe5a` | Official weight SHA256 `6274eb4a3f3eb7ad1ab341d222bbba2ba709b06645dbbd15ac4971d6cb22ab21`, byte size `792305602`. No weight was downloaded for this audit. |
| [Pinned shared modeld.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/modeld.py#L94-L128) | `19633776d15cbe2b2b25cbc115b088c5f4ed3bde42583eb5c196bad00f0246d0` | Lines114–115 use `action[0]/max(2.5,v_ego)**2` and `action[1]`; no family-specific sign transform. Lines155–157 slice outputs by metadata; line223 uses the common Parser. |
| [Pinned Parser](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/parse_model_outputs.py#L112-L120) | `45b38da9f929bd59ca28ff9e19f64e8718286ae3ccbeccddb7868ffbcd88fc85` | Shared parse path transforms plan/other outputs and passes action values through; no per-family action-axis conversion. |
| [Pinned publisher](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/fill_model_msg.py#L89-L100) | `dc9a3be34d38f37bab7062bcfea90f18d209e415b867559b5149a0a71080cb22` | Publishes body-plan values and the shared action without an intervening family-specific rotation. |
| [Pinned camera coordinate source](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/common/transformations/camera.py#L73-L85) | `3ac87fd236aa9c9e284059c47c9eb96a7c6e0be5106f514a95e6ec06e1060fb5` | Explicit device `forward/right/down` and road `forward/left/up` basis definitions; the accepted coordinate proof supplies the shared model-to-integrator body rotation. |

This shared catalog/parser/publisher/frame contract is the documented basis for the workflow operator's explicit `model-frd` declaration for Light Speed and Light Speed 2. It is not direct validation of every weight's learned action convention, a new model inference result or automatic identity-to-basis certification. Both remain unknown under public `auto`; their receipts must say `USER_DECLARATION`, `source_basis_verified=false`, requested `model-frd`, parent `MODEL_BODY_FRD`, applied `INTEGRATOR_BODY_FLU_WORLD_CCW`, rotation applied once. Never infer a convention merely from names, equal shapes, model family or observed sign.

MD-V3 alone retains the factory's exact verified triplet: weight SHA256 `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`, size `768750198`, local spec SHA256 `689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2`. Its `auto` provenance is `VERIFIED_OFFICIAL_IDENTITY`. Existing workflow SHA-pinned downloads stay on ephemeral official CI runners; no local official model run is added.

### Gates, failure handling and scope of any new result

1. Complete CPU TDD and full applicable CPU checks, the source-only basis audit above and fresh review of the frozen whole change before any push. Independently verify all nine frozen byte pins and all unchanged ModelSpecs. Review all actual workflow argument/receipt diffs against this amendment. Root owns the push and integration.
2. Preserve intended sequential model lifetime: after exporting receipts, release both `policy` and `binding` before garbage collection and the next large constructor. A retained `binding.policy` would otherwise keep the preceding large ORT session alive during the next constructor. Cover the lifetime with a CPU weak-reference regression; no extra model execution is needed.
3. Existing strict repeat remains the same original-renderer/convergence experiment. `run_same_model_repeat` compares both camera hashes and world-position repeatability; mismatch returns1, incomplete diagnostics return2. Its recent historical failures are not repaired or overridden by the accepted Both+unsorted corrected diagnostic results. A new failure leaves this public integration PR unmerged; retain receipts/logs and report it honestly. Do not tune renderer, tolerance or gate criteria to green.
4. Existing paired workflow remains a technical diagnostic. It requires complete comparable episodes and first **Road** camera equality; its repeat-first mismatch is recorded without a match assertion, as before. Do not relabel that existing technical success as a strict repeated-model match. `--full-s-route` selects/validates the route, while twelve steps at8m/s cover only nominal0.6s/4.8m; they do not demonstrate full S traversal or tracking quality.
5. The no-model optical workflow validates its existing RGB-to-input plumbing at two poses, not real-camera optics, photometry, action basis or model performance. Keep existing raw outputs/artifacts on failure; weights stay outside upload paths.
6. Inspect actual CI statuses, each completed/failed report, binding provenance/actions/counts, logs and uploaded artifacts before making any result claim. Failed or incomplete execution can leave parent/bridge counts different and total attempted ORT calls unknown; never replace those with the planned65 count. No arbitrary retry-to-green, cancellation or nonrequired override is authorized. A necessary runtime fix needs review of the new behavior and a newly stated regression scope.
7. Require current-HEAD applicable checks/Codex/no unresolved threads, fresh whole-change review and source-binding proof before merge. Main's automatically triggered integration jobs are a separate current-main result. Any failure stays a failure; no corrected scientific cohort, original0/4, renderer-default, Stage7-complete, optical-equivalence or performance-ranking claim changes.

**Review disposition:** the amendment is concrete and suitable for root review. Seven-file-only/CPU-only integration is insufficient: incorporate the caller declarations and asset assertion, confirm the frozen model-lifetime fix, and review the actual plan/workflow/whole-source diffs before push. No new test or CI result is claimed by this document.
