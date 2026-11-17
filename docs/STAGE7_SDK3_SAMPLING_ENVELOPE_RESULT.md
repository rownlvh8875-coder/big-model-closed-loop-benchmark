# SDK3 conditional sampling envelope result

Checked 2026-11-17T20:40:07.747058+09:00; based on unchanged PR142/d6eb529d52364117a01d446652f2e938089625c2. **Original official matrix remains3/4 PASS,overallFAIL,Stage7=false.**

## Finding

All **135/135 modeled scenarios** remain inside the yellow predicate at the five captured mip1 CPU candidates. All10adjacent-SNORM8/fraction-box conditional intervals also remain yellow. Within these explicit models and recorded four-texel cells, scalar quantization, float32 coordinate arithmetic and modeled8/12-bit weight precision alone do not explain the captured gray Road7 pixel. This does not rule out other GPU behavior: actual internal format, sampler, procedural terrain coordinates and pixel ownership remain unmeasured.

The central unquantized candidate is0.01687556688432301; hypothetical SNORM8 nearest-even gives0.017717129883200268. With adjacent SNORM8 codes and +/-1/256fraction error, its conditional interval is[0.015613318640467009,0.018088530902566895], above the strict0.01lower threshold and below0.11. This is a model, **not a bound guaranteed by the driver**.

## Candidate comparison

|CPU proxy ray|Recorded mip1 value|Hypothetical SNORM8 value|Conditional8-bit interval|Nearest one-axis threshold delta in mip texels|Proxy world displacement mm|
|---|---|---|---|---|---|
|center|0.016875566884|0.017717129883|[0.015613318640,0.018088530903]|-0.094301863381|8.572897|
|top_left|0.017166276122|0.018022336420|[0.015909125131,0.018370270098]|-0.110890141361|10.080922|
|top_right|0.016021417879|0.016692432929|[0.014904649865,0.017215196152]|-0.074178247502|6.743477|
|bottom_right|0.016021417879|0.016692432929|[0.014904649865,0.017215196152]|-0.074178247502|6.743477|
|bottom_left|0.017166276122|0.018022336420|[0.015909125131,0.018370270098]|-0.110890141361|10.080922|

Each nearest root reaches the lower0.01threshold by reducing the second coordinate while holding the first fixed; equality is not yellow. The center root moves attribute UV by[0,-8.37196940525e-06],or -0.094301863381mip1texels. Through the recorded affine transform/elevation ratio this is a **proxy** world displacementapproximately0.008572897m. Across the five points, the corresponding one-axis distances are6.743477–10.080922mm. These are not screen-pixel offsets, minimum2Ddistances, measured terrain motion, or evidence of an actual terrain intersection. A nearer crossing in an unrecorded neighboring cell is outside this calculation.

## Models and evidence boundaries

- Three scalar models: recorded raw float32; hypothetical SNORM8 nearest-even code/127 with[-1,1]clamp; hypothetical UNORM8 nearest-even code/255 with[0,1]clamp. The pinned desktop Panda source's F_red/T_float→GL_R8_SNORM path motivates the signed model but does not attest the runtime internal format.
- Three coordinate models: recorded float64; float32 inputs with separate multiply/add; float32 inputs with one rounded multiply/add (FMA model). These model the frozen shader's ratio branch, not measured terrain fragment coordinates.
- Three weight models: unquantized, hypothetical nearest-even8fractionbits and12fractionbits.5points×3formats×3coordinates×3weights=135scenarios. Every actual input remained within its captured footprint; the implementation returns explicit unavailable if a modeled coordinate would leave it.
- Conditional intervals combine floor/ceil adjacent SNORM8 codes with a fraction box+/-1/256or+/-1/4096,clipped to the same cell. Nonnegative bilinear weights let the evaluator bound this **assumed** box by its corners. No hardware precision guarantee is inferred.
- Axis roots use recorded unquantized corners, hold the other fraction fixed, and retain only[0,1]roots. No neighboring texels are generated or extrapolated. All points originate from the prior nearest GeomNode hit on triangle606, not procedural terrain raster intersections.

## Authentication and independent validation

[Input index](evidence/sdk3-sampling-envelope-01/input-index.json) pins11committed files/1016892B with per-file SHA/size,1MiB/file2MiBtotal. IndexSHA `6543dc462cf3af472af77ad481566cfdfc947ec321b8cf46b98f23d02f9c3e54`. Prior native run44067526874/attempt1,artifact14320743853,`sha256:f5bbd810ad6369c64cece2e5c828b33b4eb43356b2069ca7136338c235144aad`; prior executed sourceb759849d911190a2d3376b0f90daa330d8192c1c,activation051b0f33ca2684d072363b42a4cba84a517cb2e3.

The driver rechecks the final prepared→terrain/material→shader digest chain,pid/nonce/target/archive and the unchanged prior prepared-boundary receiver result. That revalidation covers the prepared boundary only. The14prior source images and full raw receiver validation remain prior evidence; this step creates **zero native renderer/model processes and zero ONNX inferences** and performs no fresh image capture/verification, GPU query/readback or install.

A separate50-digit Decimal evaluator independently verified all135scenario values/coordinates,10conditional intervals and axis roots. Maximum scalar discrepancy 9.531072878547926e-14, tolerance2e-12. Strict root comparisons use independently checked recorded float64 fractions; evaluating UV products in exact Decimal instead changes a root by at most 2.829485629664833e-12,below1e-9. The first diagnostic mismatch came from comparing exact Decimal UV products with the helper's rounded float64 fractions; the independent checker now separates those domains. No production correction was needed.

[Full result](evidence/sdk3-sampling-envelope-01/result.json),[independent analysis](evidence/sdk3-sampling-envelope-01/input-analysis.json),[result hashes](evidence/sdk3-sampling-envelope-01/result-index.json). CPU code commit `53cad9de110ef3162a9d876ca9e314344fe2a270`; executed resultSHA `3aa26b56ea04a3364ab77837bcb1801834c4e993d45d3582c71575521228f37b`. CLI: `python -I -B scripts/run_sdk3_sampling_envelope.py --out output/stage7-sdk3-sampling-envelope-01/actual` (fresh output only).

## Verification and remaining question

33newtests cover literal quantization/ties/clamps/strict thresholds/f32ratio/FMA/roots/cellescape/rawintegrity, actual135cases, input tampering, identity/falseproof flags, cold-I-S-B help and immutable output.179focusedtestsPASS. Sole fresh review found4Important/0Critical/0Minor numerical issues. One fix pass corrected exactfloat32FMA, duplicate-offset bytes, endpoint/domain roots and exactnormalized-code selection/outward intervals;6regressionsRED→GREEN plusconsistentduplicatepositive,179testsPASS. No rereview. ExactfinalHEAD canonical push+PR fourjobs/fullcounts are final executor gates; their receipts are linked in the new DraftPR and retained in `output/stage7-sdk3-sampling-envelope-01/final-closeout/verification.json`. Original checkout/sixfiles/main/parentPR142 remain preserved; additionsonly/no runtimecode changes/no mainmerge/environmentregistrypublication.

Remaining evidence must address actual procedural terrain surface/cull/draw coordinates and sampler state. The modeled precision changes tested here keep the branch yellow; this result does not prove a renderer repair or move Stage7 to complete.
