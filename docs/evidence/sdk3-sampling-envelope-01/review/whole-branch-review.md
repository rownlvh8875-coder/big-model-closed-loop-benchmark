# Whole-branch review — SDK3 conditional sampling envelope

Review range: `d6eb529d52364117a01d446652f2e938089625c2..baf6ff0bc96c3b5a35219f42c3cb65ac4312c3b5`.
Read-only checkout: `/dev/shm/stage7-sdk3-runtime-20261116/repo`.
Reviewed own review-package, spec, plan, progress ledger and both Ruling lines, added numerical/driver code, tests, report and evidence; inspected unchanged prepared-boundary receiver integration. No agents, native renderer, SDK/Panda/GLX, model/inference, install, or checkout writes were used.

## Strengths

- Exact index SHA and all eleven byte hashes authenticate a small fixed input set. The driver reauthenticates the snapshot before modeling and checks the final digest/identity chain. Input and identity mutations are covered by integration negatives.
- The report and result distinguish conditional CPU models and prior prepared-boundary revalidation from fresh image/native validation. Every hardware/format/coordinate/ownership/cause/repair/Stage7 promotion flag stays false.
- The recorded result independently reproduces byte-for-byte: 81,130 bytes; SHA256 `3aa26b56ea04a3364ab77837bcb1801834c4e993d45d3582c71575521228f37b`; 135 modeled / 135 yellow. My 70-digit Decimal recomputation at the recorded fractions checked all 135 values and predicates, maximum absolute scalar error `2.18473029009837593533985539172282046098926000521345258E-18`.
- All 26 newly added tests pass. All 20 changes in the supplied range are additions. The documented existing 172-test receipt was inspected; it was not represented as a new reviewer execution.

## Issues

### Critical

None found.

### Important

1. **The advertised single-round float32 FMA model can double-round.**
   - Location: `scripts/sdk3_sampling_envelope.py:33`; coverage gap at `tests/test_sdk3_sampling_envelope.py:40`.
   - Input: `attribute_uv([1.4904742329235887e-08, 0.], 1.9995194673538208, 'f32_fma_model')` returns first coordinate `0.5`; correctly rounding the exact float32-input product plus 0.5 once to float32 yields `0.5000000596046448`.
   - Both inputs are exactly representable float32 values within accepted bounds, and this ratio takes the multiply/add branch. Exact `Fraction` distances prove that the upper float32 value is nearer. Python first rounds the sum to binary64, erasing the small excess above the float32 midpoint; the final conversion then chooses the even lower float32 value.
   - Effect: a scenario labeled FMA can use the wrong UV, fraction, footprint and potentially predicate. The current test reproduces the implementation expression, so it cannot detect this failure. The fixed 135-case dataset is unaffected by this counterexample, but the numerical interface promises this arithmetic model for its accepted inputs.
   - Fix: perform exact product-plus-add and correct round-to-nearest-even float32 conversion (stdlib rational/integer arithmetic is sufficient), or otherwise implement a demonstrably single-rounded FMA. Add this literal expected-value test rather than calculating the expected result with the same double-rounded expression.

2. **Conflicting bytes for the same captured texel offset are accepted.**
   - Location: `scripts/sdk3_sampling_envelope.py:78` through the digest/return at line 83.
   - Input: a 1×1 clamp window with four entries all at `xy=[0,0]`, `offset=0`, but raw float32 corner values `[0.,0.,.075,0.]`, and a correctly recomputed concatenated sample SHA. At `uv=[0.,0.]`, `scenario(...,'recorded_float32',None)` returns `MODELED`, value `0.01875000074505806`, `yellow=True`.
   - Effect: one physical texel cannot simultaneously contain those four values. The helper turns contradictory sparse evidence into a plausible yellow result. Duplicated corners naturally occur with clamp/mirror or unit extents, so digest validation alone is insufficient. This is not an attack on the fixed-index loader; it is a missing invariant in the separately exposed window validator and model helper.
   - Fix: bind each unique texel offset/coordinate to exactly one raw byte value and reject conflicts before interpolation. Continue accepting consistent duplicate corners. Add a negative conflict case plus a positive consistent clamp/mirror duplicate case.

3. **Cancellation in the axis solve both loses valid endpoint roots and admits roots outside the cell.**
   - Location: `scripts/sdk3_sampling_envelope.py:51`–56.
   - Missing valid root: `threshold_roots([.01,.03,.01,.03],[.5,.5])` returns `[]`, although axis 0 at fraction 0 is exactly the lower threshold.
   - False in-cell root: let `lo=math.nextafter(.01,math.inf)`. `threshold_roots([lo,.03,lo,.03],[1.,.5])` returns a lower-threshold axis-0 root at fraction 0 and delta -1. Every value in this cell is strictly above .01; the mathematical root is outside the cell.
   - Effect: the `old + (threshold-current)/slope` cancellation followed by a raw `[0,1]` test can fabricate or suppress branch-boundary displacements. The latter can become a meaningless proxy-world distance. Exact equality and out-of-domain roots are explicit requirements; widening/clamping with an arbitrary epsilon would also admit the second example.
   - Fix: form each one-axis affine function from its endpoint values, explicitly establish whether the threshold is between those endpoints, handle exact endpoint equality, and solve within that established domain with adequate numerical robustness. Add both literals and preserve flat-slope and truly outside-cell rejection.

4. **Nearest-code normalization has an unadvertised binary64 intermediate rounding boundary.**
   - Location: `scripts/sdk3_sampling_envelope.py:21`; related misleading midpoint construction at `tests/test_sdk3_sampling_envelope.py:16`.
   - Additional targeted cases supplied by the executor and independently verified by this reviewer: `normalize([0.011811023622047244], 'snorm8_nearest_even')` returns code 2/127 although the supplied binary64 value is strictly nearer code 1/127. `normalize([0.0058823529411764705], 'unorm8_nearest_even')` similarly returns code 2/255 although code 1/255 is nearer. Exact `Fraction(value)*scale` rounds to integer 1 in both cases; the binary64 product first rounds to 1.5 and then chooses even integer 2.
   - Effect: the accepted generic finite-number interface does not implement the stated nearest-code model at these boundaries. This does not change the fixed float32 evidence: multiplying a decoded float32 mantissa by 127 or 255 fits exactly in binary64. It does matter for other accepted binary64 helper inputs, which the literal unit tests themselves exercise.
   - Fix: either implement exact nearest-even code selection for the admitted numeric values, or explicitly restrict the API/model to exactly representable float32 inputs with a corresponding contract. For the generic interface, exact rational comparison is appropriate. Replace approximate `1.5/127` midpoint constructions with genuinely representable ties such as +/-0.5 and add these just-below-midpoint cases; the existing expectation for an approximate midpoint must not silently dictate a different rounding model.
   - Grade: Important, for the same accepted-input mathematical-model correctness reason as finding 1. This was a targeted supplemental probe only, not a second whole-branch review.

### Minor

None separately raised.

## Recommendations

- Address all four Important findings in the single authorized RED→GREEN pass, with the four regression cases below, the two normalization cases, and a consistent duplicated-corner positive case. No reviewer rerun is requested.
- Recompute the authenticated actual result after the fix, update numerical provenance if changed, and run the appropriate focused regression suite. Preserve the distinction between the fixed dataset remaining yellow and the broader helper contracts being corrected.
- Exact final push/PR canonical four CI jobs, attempt 1, zero artifacts, complete test counts, Draft PR and closeout remain required **inside-plan executor gates**. They were pending at this review, not excluded or waived. Finalize report/PR links and claims against the actual final HEAD before closeout.

## Declined to judge

None. No considered behavior was silently set aside as outside scope. In particular, the accepted helper inputs above were judged by numerical effect despite not occurring in the fixed eleven-file dataset. Existing CPU-only evidence boundaries were reviewed as claim/provenance requirements; no new native validation was undertaken.

## Assessment

**Ready to merge? With fixes.** The fixed evidence result and provenance are sound for the inspected dataset, but the advertised FMA, nearest-code normalization, sparse-window consistency and strict root-domain contracts have reproducible correctness failures. Complete the single Important fix pass and the remaining final executor gates before proceeding; the authorized integration remains a Draft PR, not a merge.

## Exact commands and results

Every command ran from `/dev/shm/stage7-sdk3-runtime-20261116/repo`, using `sandbox_permissions=require_escalated` with a routine Korean justification. Python used `-B`; subprocess CLI tests also use `-B`. Every shell invocation had `TMPDIR=/dev/shm/stage7-sdk3-runtime-20261116/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`. Only this external report was written by the reviewer; unit-test temporary output stayed in that TMPDIR.

New tests:

```bash
TMPDIR=/dev/shm/stage7-sdk3-runtime-20261116/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m unittest tests.test_sdk3_sampling_envelope tests.test_sdk3_sampling_envelope_host
```

Result: exit 0; `Ran 26 tests in 0.461s`, `OK`.

Independent in-memory reproduction / Decimal check:

```bash
TMPDIR=/dev/shm/stage7-sdk3-runtime-20261116/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B - <<'PYCODE'
from scripts import run_sdk3_sampling_envelope as h
from pathlib import Path
from decimal import Decimal as D,localcontext,ROUND_FLOOR,ROUND_HALF_EVEN
import json,hashlib,struct
r=h.analyze(h.load_inputs());raw=(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();committed=(Path('docs/evidence/sdk3-sampling-envelope-01/result.json')).read_bytes()
assert raw==committed
print('recomputed_result',len(raw),hashlib.sha256(raw).hexdigest(),r['scenario_count'],r['modeled_yellow_count'])
count=0;err=D(0)
with localcontext() as ctx:
 ctx.prec=70
 for p in r['points']:
  corners=[D.from_float(v) for v in p['raw_float32_values']]
  for s in p['scenarios']:
   v=corners
   if s['format_model']!='recorded_float32':
    n=127 if s['format_model']=='snorm8_nearest_even' else 255;minimum=-1 if n==127 else 0
    v=[(min(D(1),max(D(minimum),q))*n).to_integral_value(rounding=ROUND_HALF_EVEN)/n for q in v]
   a,b=map(D.from_float,s['fraction'])
   if s['weight_bits'] is not None:
    n=2**s['weight_bits'];a,b=[(z*n).to_integral_value(rounding=ROUND_HALF_EVEN)/n for z in (a,b)]
   value=v[0]*(1-a)*(1-b)+v[1]*a*(1-b)+v[2]*(1-a)*b+v[3]*a*b
   error=abs(value-D.from_float(s['value']));err=max(err,error);assert error<D('1e-15');assert s['yellow']==(D('.01')<value<D('.11'));count+=1
print('independent_recorded_fraction_decimal',count,'max_absolute_error',err)
print('flags', {k:r[k] for k in h.FALSE_FLAGS})
PYCODE
```

Result: exit 0; reproduced byte count/hash and 135/135 as above; all eleven FALSE_FLAGS were false. This independent check covers interpolation and predicates at recorded fractions; it does not overclaim a fresh independent coordinate/root/image verification.

Four new reviewer regression probes, executed without adding files:

```bash
TMPDIR=/dev/shm/stage7-sdk3-runtime-20261116/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B - <<'PYCODE'
import hashlib, math, unittest
from fractions import Fraction as F
from scripts import sdk3_sampling_envelope as h
from tests.test_sdk3_sampling_envelope import window
class ReviewRegression(unittest.TestCase):
 def test_true_single_round_fma(self):
  uv=1.4904742329235887e-08; ratio=1.9995194673538208
  exact=F(uv)*F(ratio)+F(1,2); expected=.5000000596046448
  self.assertLess(abs(exact-F(expected)),abs(exact-F(.5)))
  self.assertEqual(h.attribute_uv([uv,0.],ratio,'f32_fma_model')[0],expected)
 def test_conflicting_duplicate_bytes_reject(self):
  w=window();w.update(size_xy=[1,1],expected_nbytes=4,uv=[0.,0.],wrap_codes=[0,0],wrap_modes=['clamp','clamp'])
  for row in w['texels']:row.update(xy=[0,0],offset=0)
  w['sample_sha256']=hashlib.sha256(b''.join(bytes.fromhex(row['raw_hex']) for row in w['texels'])).hexdigest()
  with self.assertRaises(ValueError):h.scenario(w,[0.,0.],'recorded_float32',None)
 def test_exact_endpoint_retained(self):
  roots=h.threshold_roots([.01,.03,.01,.03],[.5,.5])
  self.assertTrue(any(r['axis']==0 and r['threshold']==.01 and r['fraction']==0. for r in roots))
 def test_outside_root_not_rounded_into_cell(self):
  lo=math.nextafter(.01,math.inf)
  self.assertEqual(h.threshold_roots([lo,.03,lo,.03],[1.,.5]),[])
unittest.main()
PYCODE
```

Result: exit 1; `Ran 4 tests in 0.002s`, `FAILED (failures=4)`. Respectively: conflicting duplicate raises no ValueError; exact endpoint missing; outside root incorrectly returned at 0; FMA `0.5 != 0.5000000596046448`. These failures corroborate the three findings rather than indicating a failed fixed-input reproduction.

Read-only range checks:

```bash
TMPDIR=/dev/shm/stage7-sdk3-runtime-20261116/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 git diff --stat d6eb529d52364117a01d446652f2e938089625c2 baf6ff0bc96c3b5a35219f42c3cb65ac4312c3b5
TMPDIR=/dev/shm/stage7-sdk3-runtime-20261116/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 git diff --name-status d6eb529d52364117a01d446652f2e938089625c2 baf6ff0bc96c3b5a35219f42c3cb65ac4312c3b5
```

Results: 20 files / 3,878 insertions; every listed path status `A`. `git rev-parse HEAD` during review matched the requested head. `git status --short` showed only the executor-owned untracked `docs/evidence/sdk3-sampling-envelope-01/original-preservation.json` at inspection time; it was not modified or included in the requested review range.

Supplemental exact-code normalization command (executor-supplied cases, independently verified; no broad rerun):

```bash
TMPDIR=/dev/shm/stage7-sdk3-runtime-20261116/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B - <<'PYCODE'
from fractions import Fraction
from scripts import sdk3_sampling_envelope as h
for mode,scale,value in [('snorm8_nearest_even',127,0.011811023622047244),('unorm8_nearest_even',255,0.0058823529411764705)]:
 exact=round(Fraction(value)*scale)
 actual=h.normalize([value],mode)[0]
 print(mode,repr(value),'exact_nearest_code',exact,'actual_code',actual*scale,'closer_to_code_1',abs(Fraction(value)-Fraction(1,scale))<abs(Fraction(value)-Fraction(2,scale)))
PYCODE
```

Result: exit 0; for both modes, `exact_nearest_code 1 actual_code 2.0 closer_to_code_1 True`. These are two additional confirmed counterexamples, not passing correctness assertions.
