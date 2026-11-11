# Official MD-V3 model-to-world action basis bridge

> Required workflow: writing-plans, TDD, executing-plans and fresh scientific/code review.
> Delegate isolated implementation and evidence documentation. No worktree/environment publication.

## Confirmed problem and boundaries

Legacy source e84369c9f7f461a59c8d506b8b9efb2312297c03 and its current PR27
study stay frozen. All twelve completed cases establish legacy repeatability only;
the four160-step cases visit only their first route lane and have
39–41m maximum virtual lateral deviation. No correct tracking/full-S claim
follows. The completed legacy cohort must be independently accepted
before PR27 merge; never retrofit old actions, poses, labels or JSON.

Independent pinned-source and pure-math review confirms a missing action-basis
conversion, not an error in the numeric raw_lat/max(2.5,v)^2 formula. Model
body/device FRD is forward/right/down. The virtual yaw integrator expects
body FLU forward/left/up; its positive curvature increases CCW world heading.
These are BOTH right-handed. R=diag(1,-1,-1), determinant+1, rotates the body
basis180degrees about forward. Thus k_world_ccw=-k_model_right; longitudinal
acceleration is unchanged. The global world axes are fixed; step_ideal already
rotates body-forward displacement using current heading. Do not globally flip
world Y or camera/image coordinates.

Pinned catalog commit e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42 supports the full
chain: camera.py73–88 declares FRD/FLU; modeld114–115 computes model curvature;
parser112–120 does not change action; fill_model_msg100 copies Action directly;
controlsd217/225,227,262–265 preserves its sign; angle23 and torque171/174/306
negate at the model-to-left-positive steering boundary. These files were read
as text only. No Carrot controller/params, vehicle plant or real car is run.

Pure current math with raw+8,v8,dt.05 produces legacy heading+.05/leftward
motion and basis-mapped heading-.05/rightward motion. Nine signed/zero/nonzero-
heading cases and source hashes are retained under
output/stage7-coordinate-contract-audit/. This establishes the sign mismatch,
not its sole responsibility for all tracking errors, optical equivalence or
model quality. Fixed coordinate conversion is not controller tuning, smoothing,
clipping, seed-specific correction or a change to the raw model output.

## Five new files and isolation

Implementation owns only these initially untracked files:
- bigbench/model_world_frame.py
- scripts/native_mdv3_world_frame.py
- tests/test_native_mdv3_world_frame.py
- .github/workflows/stage7-mdv3-world-frame.yml
- docs/STAGE7_MDV3_WORLD_FRAME.md

Root owns this plan, continuation and legacy/integration documentation.
Keep EVERY existing core, producer, reader, spec, test and workflow byte-identical.
This first implementation is an explicit opt-in corrected-world diagnostic;
legacy bare-policy consumers/defaults are not silently migrated or endorsed.
No candidate renderer default is adopted. Broader canonical API integration
requires its own explicit review after the corrected contract is validated.

## Pure adapter

WorldFramePolicyAdapter COMPOSES the exact audited policy returned by the
unchanged official pinned factory. Its constructor does NOT reset. Require an
explicit FRD applied-action declaration; reject wrong declarations, an existing
adapter marker or an already-world/FLU applied-action convention to prevent
repeated conversion. Scope tags to the APPLIED ACTION; forwarded model plans,
raw outputs and states remain in their original convention.

reset() calls inner.reset exactly once and clears only bridge receipts.
step(observation) passes the SAME observation to inner.step exactly once,
then returns ModelAction(-parent.curvature_1pm,parent.acceleration_mps2).
Use only the returned parent action. Never run inference again or repack I420.
Do not modify inner audit_rows or parent_converted_action: those remain the
numeric model-FRD action. Add a SEPARATE bridge_receipts list with sequence,
source/target applied-action conventions, constant rotation, parent action,
applied world action and measured CPU bridge-audit time.

Forward actual contract/session/is_mock/_injected_session/state/trace/raw
audit/input/output properties using __getattr__; never shadow/falsify them.
Preserve all four raw float32 values and their exact SHA, actual image-feed
SHA, ModelTiming and every typed recurrent state. No GT, route, scene, seed,
controller or tuning parameter enters the adapter. No image/world-axis flip.

The official runner verifies reviewed source bytes BEFORE factory/ORT creation
to avoid a later parent-side sign change silently causing a second conversion.
Pin the seven current source files in the table below, actual specSHA689f4d80...
and official768750198-byte modelSHA35976b11.... Use full existing spec/model
constants and fail on a changed source binding. Require the exact expected
inner audited-policy class. Unit factories/fakes remain explicitly non-official;
there is no public model-file or injected-session bypass.

## First corrected native gate only

Use a new protocol stage7-mdv3-world-frame-v1 and distinct corrected-frame
evidence/gate labels. Run only the original2seeds x2nativeS x12steps x2fresh
processes, fraction.12/speed8/dt.05:8processes96actual model steps. Do NOT
implement corrected ramps/camera/160 expansion until this corrected4/4 is
independently verified. Historical original0/4 and all legacy candidate passes
are separate records with unconverted action binding; no relabeling.

Reuse actual provider, NativeWorldCamera, CPU capture audit, opaque1 before
provider and feedback_both after initialization. Original PSSM/Chase, ego
visibility, Road-first order, two ticks and public run_target_lane_episode
remain unchanged. Small setup only; no copied loop or supported-module monkeypatch.
Pass the wrapper to the public loop once. No extra capture/render/PSSM/tick,
GPU query/depth/HDR, retention observer, warmup/convergence/replay or state reset.

Reuse only genuinely generic legacy helper checks: parent audit validation
returns FRD action, capture validation checks actual pose/clocks/hashes. Build
new identity/control/bridge/full-trial validation. Never forge a legacy group,
scenario, label or parent action to invoke a fixed old validator. Each completed
row's desired action and kinematics must use the APPLIED WORLD action, while
its parent receipt retains model FRD. Compare all source/warp/I420/raw4actions,
aggregate+named states, entry/post-world pose/time and bridge fields exactly.
Exclude measured wall times from across-process equality; validate them finite.

This initial corrected gate is complete-only. Save all raw frame/capture/parent/
bridge audits and errors before JSON wire validation, including any dangling
records. Every incomplete requested episode fails. Native0/cleanup5 requires
fresh complete nonce-matched receipts; all other statuses remain failures.
Two distinct same-runner PIDs/case and8globalUUIDs/nonces; exact case/final
regeneration; never import the old expansion's valid-partial acceptance here.

A separately labeled offline first-step comparison may use immutable legacy
raw records to check unchanged source/warp/feed/raw-output/state evidence for
the identical initial observation. This is NOT input replay and executes no
extra model calls. Applied world action/post-pose intentionally differ. Report
any unmatched initial-condition control as inconclusive; never tune or weaken
the corrected repeat gate to force agreement with the legacy cohort.

## Predeclared tests and execution gates

- [ ] Meaningful RED before implementation: positive-model turns world-right,
  negative turns left, signed zero/nonzero headings and unchanged acceleration.
- [ ] Constructor/reset/step counts and original observation identity; true
  forwarded runtime flags; all inner raw/audit/state objects/bytes preserved;
  separate bridge fields; wrong declaration/double wrap/source pins fail.
- [ ] Camera remains heading=degrees(world_heading)-90 and uses unchanged
  rectifier; CPU-only Panda NodePath or independent analytic projection tests
  may prove image-right/body-right without native GL, controllers or weights.
- [ ] Fresh raw-first failures/nonces/statuses/12fullrows/2ticks/initialstates/
  all named receipts/bridge/action/pose/case/final mismatches fail strictly.
- [ ] Dedicated four-native-job/independent-aggregate workflow, maxparallel2;
  pinned MetaDrive0.4.3/Panda1.10.13/assets/model; weights ONLY ephemeralCI;
  five scoped JSON/log artifacts, strict pipeline failure propagation.
- [ ] Full local suite, pure NumPy aggregation dependency check, legacy
  fingerprints, fresh whole-change scientific/code/workflow/doc review.
- [ ] Legacy PR27 full artifact/evidence acceptance and gated merge BEFORE
  triggering corrected workflow. Source/model outputs from current study stay
  frozen and historical. No source push while its prerequisite is unresolved.
- [ ] Corrected source gate: all4cases/full96steps exact; current-HEADCI/Codex/
  no open threads, all5APIarchiveSHA/size/safepaths and independent raw exact
  regeneration before acceptance/merge. Tracking is reported separately.

The NEW corrected-world workflow may predeclare one automatic merged-main repeat as a
SEPARATE additional cohort; do not manually repeat completed runs. No corrected
expansion before corrected4/4. All renderer-equivalence, physical optics,
tracking/quality, full-S and Stage7-completion claims stay unproven unless
separately supported. No real vehicle, CAN, CD210 or Carrot controller enters.

## Reviewed repository dependency bindings

| File | SHA256 |
| --- | --- |
| `bigbench/onnx_policy.py` | `d983d5950296620a6ae89c88993829b4d2cebd35a6fd0e9046a980f75c9142da` |
| `scripts/native_mdv3_repeat_trial.py` | `ddaf0510a775c3a44c908bb4dedf4879ae88bfcb80e1f2d022a8b513a4f42427` |
| `scripts/native_mdv3_renderer_candidate.py` | `5a9058102004e2f5eaa4c9dcab4c24d97a9d42702b7a9e7c248c4f576a30d22e` |
| `scripts/native_mdv3_candidate_expansion.py` | `d86b3be67c8ac3dee31f0bf9928014d3880c8c55a6cd829bb3c46c464d16b42c` |
| `bigbench/kinematics.py` | `58c92e9a5b584932cfe73ebbf7de888f2595e88ceacdabe9a457a78fa77bb70a` |
| `bigbench/native_model_campaign.py` | `0bcb4ca73e1404a7164be1c879a200eeff5ca41e47e3035301d40fd173000bad` |
| `bigbench/metadrive_camera.py` | `1c5661e6c9eea6445ebe55cb246e6b48d3384dd5a731353ba3f1a45599e338f9` |


## Prerequisite checkpoint after legacy merge

PR #27 merged as `bdcf91e4d3a98399503a0ba215b66920b0436c08` after final
documentation-only HEAD `46a77106e1bdceaa11e9001c32100250d1a82306` passed
four applicable checks, completed current-HEAD Codex review without findings,
no unresolved threads and fresh three-document review. Frozen executable
source e84369c9 had its own17 checks and full independent13-archive evidence
acceptance; these are not mislabeled as checks on the later docs commit.
Main unit run43003435159 passed. All seven source bindings above remain exact.
The corrected adapter is in TDD implementation, not complete, and no corrected
native/model gate has executed. The numerical/scientific plan and pure proof
received clear fresh independent review before implementation began.


## Pinned read-only action-frame proof sources

The model catalog identifies repository `ajouatom/openpilot` at the pinned
commit below. These are source-text provenance links, not runtime dependencies
or authorization to import/execute its controllers/vehicle plant. The full
source SHA256 values verify the retained text; no controller code is copied
into the benchmark.

| Pinned source text | SHA256 |
| --- | --- |
| [openpilot/common/transformations/camera.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/common/transformations/camera.py) | `3ac87fd236aa9c9e284059c47c9eb96a7c6e0be5106f514a95e6ec06e1060fb5` |
| [openpilot/selfdrive/modeld/modeld.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/modeld.py) | `19633776d15cbe2b2b25cbc115b088c5f4ed3bde42583eb5c196bad00f0246d0` |
| [openpilot/selfdrive/modeld/parse_model_outputs.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/parse_model_outputs.py) | `45b38da9f929bd59ca28ff9e19f64e8718286ae3ccbeccddb7868ffbcd88fc85` |
| [openpilot/selfdrive/modeld/fill_model_msg.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/fill_model_msg.py) | `dc9a3be34d38f37bab7062bcfea90f18d209e415b867559b5149a0a71080cb22` |
| [openpilot/selfdrive/controls/controlsd.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/controls/controlsd.py) | `e81a6f7dc25507d8052cf3c12aec062759c9e6feafcad76a90814258f2eb6c7a` |
| [openpilot/selfdrive/controls/lib/latcontrol_angle.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/controls/lib/latcontrol_angle.py) | `d01c571d063538f18d47c74b0e8ba6c444fe7c8dff2bb7d8a01d492f48c57dad` |
| [openpilot/selfdrive/controls/lib/latcontrol_torque.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/controls/lib/latcontrol_torque.py) | `67fb6ecafc4d0ce999e2bbf1b729b5f6cf58a5f787c054e770162e7f2f3629cc` |
| [opendbc_repo/opendbc/car/vehicle_model.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/opendbc_repo/opendbc/car/vehicle_model.py) | `00fbe6da9b17723932988e5b3be5e29a2302296e0bcdaf914154906c6162489b` |


## Local implementation checkpoint before first corrected execution

Five new files implement this opt-in protocol. The adapter/runner/test received
clear independent code review after13 new pure tests and342 full local tests
passed without skips (18.169s, `/tmp/stage7-world-frame-full-1.log`). Initial
RED9 missing-feature failures and a later nonzero wrong-map RED→GREEN record
are retained; unit data is explicitly synthetic, never official execution.
A guarded NumPy-only aggregate succeeds with Panda/MetaDrive/ORT imports
forbidden. Every seven-file legacy source binding still matches; no legacy
core, reader, producer, spec, test or workflow byte changed.
The workflow and guide require their own final review before a triggering
push. No corrected native/model gate has executed. Legacy PR #27 and the
historical-integration documentation PR #28 are merged; the latter is
`e0e220688e8d3c0254d04f8fc28dca02e1824796`, exact reviewed docs source
`09b799fda7d894a9ab6340435bd6b80f3b31d44d` with4 successful checks,
current-HEAD Codex without findings/no unresolved threads and fresh7doc review.
These local results do not substitute for the complete fresh corrected4/4 gate.
