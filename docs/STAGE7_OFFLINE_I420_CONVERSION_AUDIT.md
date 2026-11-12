# Offline same-canvas RGB conversion measurement

This CPU-only measurement extends the earlier [source-contract audit](STAGE7_INTEGRATION_VERIFICATION.md#rgb-and-i420-source-contract-audit). On all128 preserved V3 model-canvas PNGs, the unchanged repository RGB→I420 conversion and the pinned official **simulator surrogate** RGB→NV12 arithmetic produce different logical six-plane values. **This does not select a correct converter for MD-V3 or explain its tracking error.** No application converter, historical image or model input was changed.

## Frozen input and execution scope

The input is all128 existing512×256 RGB warped PNGs from the16 completed local [V3 paint-holdout processes](STAGE7_INTEGRATION_VERIFICATION.md#v3-execution-complete-whole-cohort-geometry-not-confirmed). Selection was fixed by the [prospective plan](superpowers/plans/2026-11-11-offline-i420-conversion-audit.md) before numerical execution. Ledger SHA256 is `f1f2a9ffe80d85c98078ffc0e83460b92c7608cca12f65b4cc938ee61cf75e3f`; protocol SHA256 is `dfae8e79795a7890be78793603592afdc6074f2d4447a7a7004cb9e3de33c3ad`. All128 encoded PNG sizes/SHA256s, chunk CRCs, dimensions, top-left RGB orientation and decoded-RGB hashes match the frozen ledger. All128 consumed PNGs, ledger/protocol and repository dependencies were checked again after calculation.

These are **128 retained reads,42 unique decoded RGB hashes**, not128 independent statistical trials. Equal RGB duplicates remain in the saved-read aggregation; a separate unique-RGB aggregation reports each hash once. Their16 native processes are historical dataset provenance. This study created **0 native processes,0 camera/GPU reads,0 model calls** and has no Actions run/artifact ID. The main pass made128 existing `rgb_frame_to_six` calls and128 isolated `rgb_to_nv12` calls; tests, example calculation and independent CPU replays are separate computation, never model inference counts.

Only the inspected AST definitions `rgb_to_nv12`, `align` and `get_nv12_info` are compiled into a NumPy-only namespace. No official module imports, publisher, VisionIPC, MetaDrive, Panda, ONNX, controller or weights are executed. The source functions are exercised on the **same already-warped512×256 canvas** as the existing adapter, then only active Y/U/V are extracted from padded NV12 and packed in `Y00,Y10,Y01,Y11,U,V` order. Storage padding/interleave are not compared as pixel values.

Pinned official source is `ajouatom/openpilot@e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42`:

| Executed source text | SHA256 |
| --- | --- |
| `openpilot/tools/sim/lib/camerad.py` | `fa1855507de6b6543fa7159690bb3c0126c5da20a4429f934dd1c243c8d7010b` |
| `openpilot/system/camerad/cameras/nv12_info.py` | `3a16d167e489b6862d67641bdbe681a1e751a90edf7e60e2eb6d9743000863be` |

The20-source manifest SHA256 is `e4558054128c57eb66ba93d5713ddeb0c2aecec552a3700027b243277ccae068`. Thirteen frozen diagnostic/ModelSpec files plus actual `camera.py`/`image_adapter.py` bytes were checked. Local runtime is Python3.11.17, NumPy1.26.4, OpenCV4.11.0, x86_64; build-information SHA256 is `f3f58b60f58039df358dceb98f617583025ea7b080b4b3b5c84cc15ef13edf09`. This records the current local calculation, not historical CI wheel/HAL or physical-camera runtime identity.

## Descriptive results; no new acceptance threshold

Difference direction is **isolated simulator arithmetic minus existing repository conversion**, signed before aggregation to avoid uint8 wrap. The full saved-read denominator is25,165,824 plane-byte values. **23,227,322 differ (92.29708512624105%)**; absolute-difference sum48,543,420, MAE1.9289422035217285, squared-difference sum313,521,900 and RMS3.5296233490091207. Signed range is−34..75. All128 whole six-plane hashes differ; this is a cross-converter observation, not a failed native repeatability gate.

| Plane | Differing/total values | Differing fraction | Mean absolute difference | Signed range |
| --- | ---: | ---: | ---: | ---: |
| Y00 | 4,080,654/4,194,304 | 97.290373% | 1.192485809 | 0..2 |
| Y10 | 4,068,494/4,194,304 | 97.000456% | 1.187022686 | 0..2 |
| Y01 | 4,080,198/4,194,304 | 97.279501% | 1.192124844 | 0..2 |
| Y11 | 4,068,480/4,194,304 | 97.000122% | 1.187813282 | 0..2 |
| U | 3,812,790/4,194,304 | 90.903997% | 4.966431141 | -34..75 |
| V | 3,116,706/4,194,304 | 74.308062% | 1.847775459 | -16..13 |

Counting42 unique RGB hashes once gives7,557,462/8,257,536 differing values (91.521998814%), MAE1.937407236250620, RMS3.576296532635181, with the same maximum75. No confidence interval, independence, quality/ranking or preferred preprocessing claim follows from either weighting.

The first selected canvas is `s_curve_left_right/original_0/read_00_road_warp.png`, PNG SHA256 `130ea10af97ed84e91416c8c9257cd4d596e684cf4631222a91c91feb96fc824`. Its first conversion difference is logical Y00 row0/column0: repository146, simulator147. This is an array-coordinate difference between two CPU formulas, not a newly observed native first-mismatch step.

### Descriptive maximum example

The first maximum in frozen ledger order is `out_ramp/original_0/read_02_road_warp.png`, PNG SHA256 `7561854bc7de9f31f2494523bc363a879d544efe8372bf188e6ac6eb5aa76ffe`. U(row65,column111) covers full-RGB rows130–131/columns222–223:

```text
(199,188,  0)  (145,141,149)
(142,137,146)  (165,162,169)
```

The simulator's rounded2×2 RGB mean is(163,157,116), yielding U119 from `(-19*Rmean-37*Gmean+56*Bmean+32896)>>8`. The pinned OpenCV4.11 CPU scalar formula on top-left(199,188,0), `(-155188*R-305135*G+460324*B+(1<<19)+(128<<20))>>20`, gives44, matching this actual local OpenCV result. The measured difference is119−44=75. This directly reproduces this pixel's arithmetic difference; it does not separately estimate coefficient versus sampling contributions or attribute a driving deviation. The example was selected descriptively after the fixed full-data calculation; no image, threshold or decision was tuned.

## Limits and unchanged gates

The pinned full simulator starts with1928×1208 RGB and converts source RGB to padded NV12 **before** its selected plane warp. This study starts from the repository's already-warped512×256 canvas. It deliberately measures same-input color arithmetic only; it does not reproduce source resolution, full warp/conversion order, interpolation, border/grid behavior, deployed warp artifacts, production NV12/ISP, exposure or training preprocessing. Matching the simulator surrogate would not establish physical-camera correctness. Existing I420 dtype/shape/packing remains valid within its separate contract.

No corrected tensor was fed to a model. Model state/action, tracking causality, physical optics, full-S and model ranking were not tested. Original strict0/4FAIL, corrected expansion12/12, V3 original2/4/candidate1/4 geometry and all renderer/default limits remain unchanged. Stage7 is incomplete. PR33 optical/model/merge HOLD remains until its existing CI conclusion/raw artifact and current-HEAD review gates are actually accepted. No Cloud publication/reconfiguration occurred.

## Verification and retained evidence

Nine CPU tests pass, covering literal colors, asymmetric2×2 rounded mean/six-plane order, an independent scalar oracle, NV12 padding, signed±255 differences, identical arrays, PNG CRC/truncation/decoded identity, source-file digest rejection and function-only extraction. The initial missing-helper RED, final GREEN and main-run output are preserved. Primary calculation wall time is2.131062695000s including input/source validation, conversion, aggregation and report/provenance work up to execution-receipt construction; it is not camera or model timing. Fresh independent source/results review is **CLEAR/root-accepted**. Its nine-test suite passes and its full128-image replay produces byte-identical analysis SHA256 `937a1986a88f92ffbd7c9af810cf38d476603aef63333be8a3ccf60df7e32026`. The reviewer checked all14 frozen members and independently recomputed all six values of the maximum example.

Local proof root is `output/stage7-offline-i420-conversion-audit/`:

| File | SHA256 |
| --- | --- |
| `analysis.json` (all128 per-image records, exact integer histograms, saved/unique aggregates) | `937a1986a88f92ffbd7c9af810cf38d476603aef63333be8a3ccf60df7e32026` |
| `provenance/offline_i420_audit.py` | `403a00f272cbdb53f248a6d340babde439e079aac48b8b10ab83dbc6aca815b0` |
| `provenance/test_offline_i420_audit.py` | `9c432a9f652dd442c9b1e2967d7d5968204fb014a518eb32604f73e4ccd3eede` |
| `provenance/frozen-manifest.json` (14 original provenance/result members) | `497ec77e5b97ba6411283e4f273cf2d4cfaada94a1a516a5364a8c22d821ede5` |
| `independent-review.json` (separate later source/result review) | `d74065f0221d72a3990ebfef6738087e4662cf93033169750e075931690200b1` |
| `maximum-difference-example.json` (separate later descriptive derivation) | `43de5d8e103b7070a610d7963b1ac9861e61947a3c5a998ff941880abfc254e8` |

Reproduction uses the frozen helper/test copies and original source/data roots; it writes to a **new** analysis output directory. The original14-member manifest excludes the later example and independent review; those are retained separately, never silently added to the original manifest. Raw input data/provenance stay local and are not GitHub artifacts or committed large binaries.
