# Engine-clock Task3 input compatibility gate

## Intent and observed outcome

Task1 and Task2 are complete at `d54d43757eabc60d4f3f5b3d7e51f665bcc9f23e` / Draft PR42. This increment executes Task3's mandatory first input-resolution gate from the [parent plan](../plans/2026-11-12-engine-clock-runtime-contract.md). It does not declare Task3 complete. Status: **BLOCKED_INPUT_COMPATIBILITY** before a complete lock/recipe/adapter or preparation execution.

All five requested release endpoints returned HTTP200: Python3.11.18, NumPy2.4.6, OpenCVheadless5.0.0.93, Panda1.10.13, MetaDrive0.4.3. Version existence is therefore not the blocker. These are upstream metadata observations, not downloaded/installed binary verification.

MetaDrive's genuine `metadrive_simulator-0.4.3-py3-none-any.whl` has an unconditional `Requires-Dist: opencv-python`. The PyPI simple index advertises the wheel SHA256 `c6f8a42baac939a0af53a8e1cd9d48ec2bf0051917e7c19083e156a6506493d9` and PEP658 core-metadata SHA256 `4fb69fa54bb0e8118315aecdc482597af69798e17e47df3c57fbca50d4e7bcf6`. The11,315-byte metadata sidecar was fetched and its SHA verified. Its exact bytes are retained in the [public evidence](../../evidence/engine-clock-image-inputs/metadrive-0.4.3.METADATA).

The existing contract independently fixes `opencv-python-headless==5.0.0.93`. OpenCV's release description instructs users to select only one package because all variants share `cv2`. See the [verbatim guidance](../../evidence/engine-clock-image-inputs/opencv-package-guidance.txt). The full `opencv-python==5.0.0.93` endpoint also returns200; choosing its exact matching version would not remove the namespace overlap.

This is an upstream-supported packaging compatibility blocker, **not a claim that pip's dependency solver is unsatisfiable**. Pip can install both distribution names. Installation order could overwrite shared files; no new overlapping install or import was performed. These observations also do not establish what files were loaded by historical jobs or explain their pixel differences.

## Constraints and boundaries

Keep producer70/workflows44/consumed registries8, Task1+2 code/tests and inactive proposal byte-identical. No old failure retry, record projection, default/converter/clock/render change or reuse of four unused ABBA cases. Raw archives, extractions and controller histories remain. No worktree or cleanup.

No model/weights/ORT/provider/native import, engine/Xvfb, GPU/clock access, Docker build/pull/load/run, image layer/wheel/deb/asset download, Cloud publication or main merge. The eight bounded HTTP requests retrieve release/index/core metadata only; no automatic retry. Existing generated SMALL ONNX baseline CI is separate.

All16 preparation references stay null; image/native readinessFalse and native allowance0. No `inputs.lock.json`, Dockerfile, active preparation workflow or `engine_clock_image_preflight.py` is emitted as though inputs were resolved. Base manifest, Python archive content digest, complete wheel/deb graph, actual installed inventory, config/diffIDs, sanitized launch proof and resource feasibility remain unresolved. Published wheel SHA values are advertised object hashes, not locally measured payload hashes.

The parent plan explicitly requires genuine complete input locks and stopping unsupported resolution. Consequently its first checkbox remains incomplete and downstream preparation work is blocked. It is safer to review a concrete support-policy revision than silently add two cv2 providers or hide the transitive dependency with `--no-deps`.

## Approaches for the next policy revision

These are root proposals under the standing delegated design choices; none has been executed or selected by the user in this increment.

| Approach | Assessment |
| --- | --- |
| Lock and install both OpenCV distributions | Rejected for the present supported-image design: contradicts publisher guidance and introduces overlapping cv2 ownership, even if installation order is pinned. Closed inventory alone does not establish supported package compatibility. |
| Remove headless or ignore MetaDrive's requirement using `--no-deps` | Rejected under the unchanged contract: removes a fixed input or leaves a declared dependency unsatisfied. No silent fallback or pip-check exemption. |
| Define a reproducible, source-bound MetaDrive metadata-only derivative requiring the fixed headless package | Recommended for a separately reviewed next increment. Preserve every original runtime/asset payload byte, label the derivative honestly, and bind original wheel, transform source and derived wheel hashes. This is a proposed package-policy revision, not an existing official headless wheel or current full lock. |

## Required work before a derivative can unblock resolution

The next design must define the exact permissible METADATA change, distribution identity/label and upstream license handling, remove or preserve signatures honestly, and rebuild wheel RECORD correctly. It must prove that every non-metadata member is byte-identical, reject unexpected/duplicate/traversal/symlink/encrypted/oversized members, and preserve failed input verification. Original wheel bytes must match the advertised official hash before transformation. The derived wheel hash must be measured from an actual bounded output; do not invent it.

Use small synthetic wheels for RED/GREEN before any real package preparation. A fresh source/quality review must inspect the transform and its policy. The real wheel has not been downloaded in this increment. The transform is not an image build, but it still requires honest provenance and cannot be treated as upstream-official bytes. Keep Task1/2 validators/proposal unchanged; a future lock/adapter must explicitly bind the derivative's provenance and report unsupported policy instead of accepting bare version strings.

After that separate input-policy gate, resolve the entire Python and OS graph, base/platform manifest and Python archive digests. Only a genuinely complete reviewed lock/recipe permits continuing Task3 adapter integration and the still-separate bounded preparation gate. A derivative alone proves no image, package compatibility at runtime, loaded driver, deterministic pixels, observer neutrality or scientific PASS.

## Verification and scientific status

Evidence records exact request URLs, status, time, bytes and SHA256; raw responses remain in the existing plan workspace. Core metadata SHA, dependency lines, official guidance, null/zero semantics and frozen file maps are checked without installing or importing packages. This documentation-only gate adds no product code or implementation-mirroring tests. Independent review and existing basic CI bind reviewed/final HEAD separately.

Strict FAIL, expanded NOT_RUN, geometry/physical-optics/production-ISP/full-S limits, Stage7 INCOMPLETE and main official calls0 remain. The authentic old ABBA runtime failure has7null aggregates and4cases/6comparisons NOT_RUN; consumed allowance cannot be reused.
