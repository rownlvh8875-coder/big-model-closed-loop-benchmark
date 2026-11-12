# Public ONNX action-frame binding

The live ONNX commands bind the **parent returned `ModelAction`** to the world integrator's action convention. For the verified MD-V3 identity, the parent action uses model-body FRD (forward, right, down); the integrator uses body FLU (forward, left, up), with positive curvature turning counterclockwise in world coordinates. The binding applies `ModelAction(-parent.curvature_1pm, parent.acceleration_mps2)` exactly once. Both bases are right-handed; their constant body rotation is `diag(1, -1, -1)`.

The bare ONNX executor's numeric conversion remains unchanged. The binding preserves raw outputs, all four raw action values, plans, recurrent states, images, timing rows, mock/session flags and the parent's returned action. It adds no inference, reset, smoothing, clipping, controller or ground-truth input. The existing loop consumes the separately applied world action.

## Identity and declarations

`--model-action-frame` accepts `auto` (the default), `model-frd`, or `world-flu`. The flag describes the convention of the **parent returned action**, independently of traffic handedness, image coordinates and action-time settings.

| Actual verified files | Requested frame | Result |
|---|---|---|
| Exact official MD-V3 identity below | `auto` or `model-frd` | Source basis verified as model FRD; apply the existing world adapter once |
| Exact official MD-V3 identity | `world-flu` | Conflict; fail before policy/session construction |
| Official model SHA or spec SHA matches, but the full triplet differs | Any | Identity conflict; an explicit declaration cannot override it |
| Other verified model/spec identity | `auto` | Fail; an explicit declaration is required |
| Other verified model/spec identity | `model-frd` | Apply the adapter using `USER_DECLARATION` provenance |
| Other verified model/spec identity | `world-flu` | Pass the parent action through using `USER_DECLARATION` provenance |

The recognized official identity requires all three actual values:

| Field | Value |
|---|---|
| Model SHA256 | `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199` |
| Model bytes | `768750198` |
| Spec-file SHA256 | `689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2` |

A coincident byte count alone is not an official identity anchor. A filename, model family, tensor shape, sign or hash prefix never establishes a basis. An explicit declaration for an unknown identity records the caller's assertion; it supplies no source-verified basis or official execution claim.

Preflight reads the complete spec and checks the actual model's length, streaming SHA256 and manifest contract. The factory repeats these checks even after a caller preflight, and the unchanged bare constructor performs its own contract/file validation. This repeated hashing is setup overhead, not inference.

**Compatibility change:** unknown models that previously ran without a basis declaration now fail in these migrated commands. Declare their parent action convention explicitly after establishing it independently. There is no implicit legacy fallback.

## Commands and API

The following commands accept `--model-action-frame`:

- `bigbench run-onnx`
- `python -m scripts.run_same_model_repeat`
- `python -m scripts.metadrive_optical_check`, when `--model` and `--spec` are supplied

`python -m scripts.compare_native_onnx` instead accepts independent `--first-model-action-frame` and `--second-model-action-frame` flags. `--repeat-first` reuses the first declaration. Both inputs must pass identity/frame preflight before either policy, provider or episode is constructed; policies still construct and run sequentially, with a fresh full-file check each time.

The no-model optical invocation keeps its existing RGB probe. Supplying a non-`auto` frame without model/spec is rejected before provider creation. Existing `--rhd`, action-time, fixed/integrated-speed, camera and convergence controls retain their meanings.

```python
from pathlib import Path
from bigbench.public_action_frame import create_public_onnx_policy

binding = create_public_onnx_policy(
    Path("/private/model.onnx"), Path("model_specs/md-v3.json"),
    model_action_frame="auto",
)
policy = binding.policy  # Pass this to the existing loop.
receipt = binding.receipt()
```

`preflight_public_onnx_policy(model_path, spec_path, *, model_action_frame="auto")` returns an immutable resolution without creating a policy/session. `create_public_onnx_policy` returns `PublicActionFrameBinding`, exposing `.policy`, immutable `.resolution` and `.receipt()`. Its only optional construction settings are `model_action_frame`, `traffic_is_rhd`, `lat_action_t_s`, and `long_action_t_s`; it accepts no supplied policy/session or verification bypass. Importing the new module requires only the standard library; policy/adapter imports are lazy.

## Evidence and failures

Reports and the schematic CLI summary include `public_action_frame`, using protocol `public-onnx-action-frame-v1`. It records actual identities, requested/resolved frames, identity versus declaration provenance, rotation status, the world-applied convention and the adapter's separate bridge receipts. A declared world policy has no conversion or measured bridge invented for it.

`ModelTiming` and `model_inference.csv` retain their existing schemas and values. In the FRD branch, CSV `curvature_1pm` remains **parent model FRD**, while loop frame/action fields contain **applied world FLU**. Raw lateral acceleration and parent plans are not relabeled or negated.

Each migrated command also writes a frame-binding sidecar in a `finally` block:

| Command | Sidecar |
|---|---|
| Schematic `run-onnx` / optical model probe | `action_frame_binding.json` |
| Native comparison | `model_a_action_frame_binding.json`, `model_b_action_frame_binding.json` |
| Comparison's repeat-first run | `repeat_model_a_action_frame_binding.json` |
| Same-model repeat | `run_0_action_frame_binding.json`, `run_1_action_frame_binding.json` |

Sidecars preserve committed parent timing rows and every completed bridge, including dangling records after an episode failure. Raised errors and their exception chain are retained there; returned incomplete native reports retain their existing status/error fields. Records are not truncated to completed trajectory rows. `parent_trace_count` and `bridge_receipt_count` describe different commit boundaries. `total_executed_model_calls` remains unknown (`null`), because a failed inference can execute without committing a timing row. Existing `model_inference_steps` fields remain counts of committed parent timing rows, not proof of all executed calls after failure. Neither a binding receipt nor a trace count claims episode completion.

## Existing workflow callers

The workflow operator explicitly declares `model-frd` for Light Speed and
Light Speed 2 using the pinned shared catalog/parser/publisher body-frame
contract. These remain `USER_DECLARATION`, with `source_basis_verified=false`;
they are not added to the MD-V3 `auto` identity rule. The full source proof,
all six existing callers and the bounded integration budget are in the
[reviewed CI amendment](superpowers/plans/2026-11-11-public-onnx-action-frame.md#ci-integration-amendment-accepted-before-first-push).

Existing triggers and failure criteria are preserved. Four automatic native
jobs plan65 model calls per feature push; a separate main budget65 applies only
after accepted merge. Dormant matrices are not manually dispatched. These are
planned regression counts, not completed inference or repeatability claims.
A strict repeat failure leaves the public integration PR unmerged.

## Unchanged scope

The schematic CLI still uses its schematic dual camera. Generic native commands retain the original native renderer and their existing camera defaults. This binding selects no sampler/bin, changes no optics or image processing, and promotes no diagnostic renderer to a default. CPU binding tests supply no new native reproducibility, optical-fidelity or driving-quality gate, ranking, or real-vehicle result.

Lower-level `OnnxBigModelPolicy` remains available with its original parent-action convention. Frozen-RGB isolation, historical audited/candidate/expansion producers and readers, corrected diagnostic factories, and their nine dependency pins remain unchanged. They keep their own historical labels and frame contracts; this migration does not retrofit old poses or add a second adapter. Acceleration-only longitudinal checks and synthetic `CameraLaneMock` actions are unchanged.
