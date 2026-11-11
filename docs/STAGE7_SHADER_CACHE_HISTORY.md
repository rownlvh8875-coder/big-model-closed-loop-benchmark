# Independent Mesa shader-cache history experiment

This experiment follows the four-process local pilot in
[STAGE7_SHADOW_SAMPLER_ISOLATION.md](STAGE7_SHADOW_SAMPLER_ISOLATION.md).
Shared initially-empty then populated cache gave source Road/Wide 8/10 and
6/10, I420 8/10, while two separately empty caches matched every field 10/10.
That one seed/scene result motivates this balanced CI test; it is not a repair.

## Conditions and process accounting

| Arm | First independent native process | Second independent native process |
| --- | --- | --- |
| `shared` | Empty dedicated cache | Same cache after first process |
| `isolated` | Empty dedicated cache | A separate empty dedicated cache |
| `disabled` | Empty dedicated directory, disk cache disabled | Separate empty directory, disk cache disabled |

Every child uses the existing original `sequential_road_first` launcher:
Road-first sequential perceive, original sampler/PSSM/Chase tasks, two task
ticks per pair, ten full image pairs, two-frame secondary warmup and +2 m
positive controls. No GPU observer, shader edit, task ablation, extra tick,
clock override, model inference or changes to model input bytes are inserted.
The camera source code is unchanged.

Each seed (20261109/20261110) and S-curve (left-right/right-left), fraction
0.12, has six native processes: **24 total**. Launchers and Xvfb processes do
not count as native image sequences. Across the four cases, shared versus
isolated run in ABBA twice and BAAB twice; disabled pairs run first twice and
last twice. Within shared, initially-empty always precedes populated.

Only per-child `MESA_SHADER_CACHE_DIR` and `MESA_SHADER_CACHE_DISABLE` are
controlled. Shared/isolated unset the disable variable; disabled sets `true`.
No published environment or persistent setup changes. Reference:
[Mesa cache environment variables](https://docs.mesa3d.org/envvars.html#envvar-MESA_SHADER_CACHE_DIR).

## Evidence and limits

The parent inventories cache files before launching each child and after it
exits. It records relative paths, sizes and content SHA256, and preserves an
immutable after-process snapshot. Files are read/copied only outside native
process lifetimes. This parent IO can affect OS page-cache state; it is part
of the diagnostic protocol, not an unbiased timing benchmark.

The validator requires empty initial shared/isolated/disabled caches, positive
enabled-cache population, no disabled-cache writes, and shared run 1's exact
starting manifest equal to shared run 0's ending manifest. Snapshots are
rehashed during independent aggregation. Cache roots/entries cannot be
symlinks, and each tree is bounded to 10,000 files/64 MiB. Missing disabled
empty snapshot directories after artifact packaging represent empty manifests;
populated snapshots must exist and match every recorded byte hash.

Native JSON file SHA is checked before parsing. Original task/pose/readback
controls, ten raw clock intervals and derived timestamps are validated.
All six same-runner PIDs and UUIDs must differ; all 24 cohort UUIDs must differ.
Case and final summaries are recomputed from native files and cache snapshots.
Partial native failures remain archived and cannot produce case success.
The existing child launcher alone handles Xvfb cleanup status 5, requiring a
fresh complete native receipt; the new parent requires launcher success.

Full source/warped RGB and actual I420 SHA sequences are compared without
tolerance. Cross-cache cold/cold and later/cold image comparisons are separate
observations between different conditions, not repeatability gates. File
population/availability does not prove individual disk-cache hits, identify
the earliest GPU boundary or establish unique causality. Cache controls may
change compiled renderer behavior; image equivalence is measured, not assumed.
No default change or original moving-model PASS follows from static matching.

## Reproduce

```bash
python -m unittest discover -s tests -p 'test_native_shader_cache_matrix.py' -v
python -m scripts.native_shader_cache_matrix --mode native-case \
  --root output/fresh-cache-case --seed 20261109 --scene s_curve_left_right
python -m scripts.native_shader_cache_matrix --mode aggregate \
  --root output/verified-cache-matrix --out output/cache-recomputed.json
```

The workflow pins MetaDrive 0.4.3 and official asset size/SHA, then runs four
native jobs and one independent aggregation job. Download every archive,
verify its API SHA/size/safe paths, and reproduce every case and final summary
before merging. A successful evidence job can contain image mismatches.
Original official MD-V3 strict repeatability remains the prior **0/4 PASS
(FAIL)** until a separately validated repair and actual official model test.

## Verified independent CI result (2026-11-11)

PR [#20](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/20)
merged as `465bf0c49a585fecb8ad313cac3b29e96736b8b6` after final source HEAD
`e3df7d1a74c2d7d7e6e2ac1cc3c3421da7b65eb8` passed all nine checks,
current-SHA Codex review without findings and a fresh independent read-only
review. The final local full suite passed **259 tests**. This adds an opt-in
experiment; it promotes no renderer default or repair.

[Native Actions run 42948547486](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42948547486)
completed **5/5 jobs**. All five artifact API SHA256/byte sizes and safe ZIP
paths were verified before extraction. Every retained cache snapshot was
rehashed, and the four case summaries and final aggregate were reproduced
exactly from native receipts and snapshot bytes: **24 unique native UUIDs,
six distinct same-runner native PIDs per case**. Child logs, native JSON,
cache manifests and cache snapshot bytes are preserved. Launchers/Xvfb are
not counted as native processes.

Retained independent evidence is under
`output/stage7-remote-evidence/run-42948547486/`: `recomputed.json`,
`totals.json`, `verified_archives.json` and `revalidation.log`.

| Arm | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `shared` | 23 | 23 | 23 | 29 | 19 | 12 | 0 |
| `isolated` | 34 | 38 | 34 | 40 | 34 | 27 | 3 |
| `disabled` | 37 | 35 | 37 | 35 | 32 | 25 | 2 |

No arm achieved all-field equality in all four cases. Isolated cache's
exception is **20261110 / left-right**: source Road and I420 match only 4/10,
first differ at step **2**, and I420 differs at **2, 5, 6, 7, 9, 10**. Its Wide
source matches 8/10 even though Wide warped RGB matches 10/10. Cache isolation
and disabling therefore do not constitute a strict 4/4 repeatability repair.

### Case rates and assigned process order

All counts below are exact SHA matches between the two independent native
processes of the same arm. Complete static equality requires every source,
warped and I420 field across all ten frames, including warmup frames.

| Seed | Scene | Arm | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | I420 post-warmup /8 | I420 different steps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | `shared` | 6/7 | 6/10 | 6 | 4 | 5, 7, 8, 10 |
| 20261109 | left_right | `isolated` | 10/10 | 10/10 | 10 | 8 | none |
| 20261109 | left_right | `disabled` | 10/10 | 10/10 | 10 | 8 | none |
| 20261109 | right_left | `shared` | 3/5 | 3/5 | 3 | 1 | 3, 4, 5, 6, 7, 8, 10 |
| 20261109 | right_left | `isolated` | 10/10 | 10/10 | 10 | 8 | none |
| 20261109 | right_left | `disabled` | 8/7 | 8/7 | 5 | 4 | 2, 4, 5, 6, 7 |
| 20261110 | left_right | `shared` | 6/7 | 6/10 | 6 | 4 | 5, 6, 9, 10 |
| 20261110 | left_right | `isolated` | 4/8 | 4/10 | 4 | 3 | 2, 5, 6, 7, 9, 10 |
| 20261110 | left_right | `disabled` | 10/10 | 10/10 | 10 | 8 | none |
| 20261110 | right_left | `shared` | 8/4 | 8/4 | 4 | 3 | 2, 5, 6, 7, 9, 10 |
| 20261110 | right_left | `isolated` | 10/10 | 10/10 | 10 | 8 | none |
| 20261110 | right_left | `disabled` | 9/8 | 9/8 | 7 | 5 | 5, 7, 10 |

| Seed | Scene | Native execution order |
| --- | --- | --- |
| 20261109 | left_right | shared-0 → isolated-0 → isolated-1 → shared-1 → disabled-0 → disabled-1 |
| 20261109 | right_left | disabled-0 → disabled-1 → isolated-0 → shared-0 → shared-1 → isolated-1 |
| 20261110 | left_right | isolated-0 → shared-0 → shared-1 → isolated-1 → disabled-0 → disabled-1 |
| 20261110 | right_left | disabled-0 → disabled-1 → shared-0 → isolated-0 → isolated-1 → shared-1 |

The assigned shared/isolated subsequence is ABBA twice and BAAB twice, and
disabled runs first twice and last twice. However, disabled-first occurs in
both right-left cases and disabled-last in both left-right cases. The disabled
arm fails both right-left cases and matches both left-right cases. Thus scene
and disabled position are confounded; the fixed assignments do not identify
an execution-order cause. Shared initial-empty always precedes shared later.
The rates support a cache-availability association in this cohort, without
proving individual cache hits, the earliest GPU boundary or unique causality.

All fresh enabled caches began empty and populated to 53 files, about
2.46–2.47 MB; later shared processes began with the exact previous ending
manifest and ended with 57 files, about 2.48–2.49 MB. Disabled caches remained
empty. Those validated file states prove the assigned availability control,
not that a particular shader fetched a cached entry. Parent inventory/snapshot
IO remains an OS page-cache and timing confound.

### Cross-condition image comparisons

These compare different cache conditions and are separate observations,
not within-arm repeatability gates. `shared_cold_vs_isolated_cold` compares
`shared-0` with `isolated-0`; `shared_cold_vs_disabled_cold` compares
`shared-0` with `disabled-0`; `isolated_cold_vs_disabled_cold` compares
`isolated-0` with `disabled-0`. `shared_later_vs_isolated_cold` compares
`shared-1` with the separately empty-cache `isolated-1` process.

| Seed | Scene | Comparison | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 |
| --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | `shared_cold_vs_isolated_cold` | 7/7 | 7/10 | 7 |
| 20261109 | left_right | `shared_cold_vs_disabled_cold` | 6/7 | 6/10 | 6 |
| 20261109 | left_right | `isolated_cold_vs_disabled_cold` | 7/10 | 7/10 | 7 |
| 20261109 | left_right | `shared_later_vs_isolated_cold` | 9/8 | 9/10 | 9 |
| 20261109 | right_left | `shared_cold_vs_isolated_cold` | 10/10 | 10/10 | 10 |
| 20261109 | right_left | `shared_cold_vs_disabled_cold` | 5/8 | 5/8 | 3 |
| 20261109 | right_left | `isolated_cold_vs_disabled_cold` | 5/8 | 5/8 | 3 |
| 20261109 | right_left | `shared_later_vs_isolated_cold` | 3/5 | 3/5 | 3 |
| 20261110 | left_right | `shared_cold_vs_isolated_cold` | 4/8 | 4/10 | 4 |
| 20261110 | left_right | `shared_cold_vs_disabled_cold` | 7/10 | 7/10 | 7 |
| 20261110 | left_right | `isolated_cold_vs_disabled_cold` | 7/8 | 7/10 | 7 |
| 20261110 | left_right | `shared_later_vs_isolated_cold` | 6/7 | 6/10 | 6 |
| 20261110 | right_left | `shared_cold_vs_isolated_cold` | 10/10 | 10/10 | 10 |
| 20261110 | right_left | `shared_cold_vs_disabled_cold` | 8/6 | 8/6 | 6 |
| 20261110 | right_left | `isolated_cold_vs_disabled_cold` | 8/6 | 8/6 | 6 |
| 20261110 | right_left | `shared_later_vs_isolated_cold` | 8/4 | 8/4 | 4 |

Some cold enabled processes match 10/10 across conditions, while others do
not; disabled output is also not consistently equivalent to either enabled
condition. A matching pair does not establish the renderer's intended image
semantics, and these cross-condition observations do not prove a default
cache policy is safe or causal.

### Verified archive ledger

The four raw artifacts and independent summary below retain the full
cohort. Complete SHA256/byte values matched the GitHub artifact API metadata.

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42948547486 | 13825115055 | `ea610f9b5a9dd46fd9297a6126e0cdf23d33994545ff3662a5fb305756deae71` | 2813809 |
| 42948547486 | 13824960631 | `17b86be00ce7cba74dbe3bca8f4d017d1ac12cf45ee686973a21f3dea6420b24` | 2812555 |
| 42948547486 | 13824562161 | `417aa7683f00eb6b1c18ce21e1f4e5cdd0690c2437d1142029052a7833eccc6b` | 31483 |
| 42948547486 | 13824546952 | `dbcc4131474b33131890dbb2b57f445c17f4f5f46f3580259a99ce23481e37be` | 2813293 |
| 42948547486 | 13824153006 | `635327e6a55083bfa7ce2612e5f26e3d5651d194f417c37fa746f3a0642a8a4b` | 2853121 |

### Local final-format and cancelled evidence

The final-validator local six-process case is distinct from the earlier
four-process pilot. All six native receipts passed the final validator, and
all existing summary fields reproduced exactly. Retained result:
`output/cache-matrix-local/seed-20261109/s_curve_left_right/final_validator_recomputed.json`.

| Arm | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | I420 different steps |
| --- | --- | --- | --- | --- |
| `shared` | 8/8 | 8/10 | 8 | 2, 7 |
| `isolated` | 10/10 | 10/10 | 10 | none |
| `disabled` | 8/9 | 8/10 | 8 | 4, 8 |

Its order was `shared-0 → isolated-0 → isolated-1 → shared-1 → disabled-0 →
disabled-1`. One local seed/scene is not the independent four-case CI matrix.

Superseded runs **42947832747** and **42948096573** were cancelled. All eight
partial ZIPs had their archive SHA/size and safe paths verified; neither run
has a full 24-native-process aggregate. Their retained ledgers are at
`output/stage7-remote-evidence/run-<run-id>/verified_archives.json`. No partial
native receipt count or image rate is promoted as a validated full cohort.

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42947832747 | 13824150543 | `d84e4c7b6210484f5591936b1a2d40d919b7804e6d8a2840e023dbd1c7668a1c` | 386895 |
| 42947832747 | 13824065798 | `fda94d3e9298ea1d751412b10514e1c993d7acebdd3f1326e975520d6da5b354` | 358638 |
| 42947832747 | 13824065797 | `bd340eae0e9d3f7edbd868c9b3886a5acac6e731beeb8f6fb0f209f4127f557c` | 7057 |
| 42947832747 | 13822894101 | `67f64ce63e61f3033ed1de665d9e1e5d5b6f7902ca874aba9096cf02c6c0e32e` | 1852264 |
| 42948096573 | 13824130819 | `656f910c59c7ecf32a065c19e9c10dab27e94b2d1f204f3795f5ab94343b9077` | 2519000 |
| 42948096573 | 13823647173 | `a1196fe4c724af857faaa10bb01388724f84a120f4aec28d8a081951a6c21dff` | 422963 |
| 42948096573 | 13823583445 | `3b48a947c45d6ef3f7ba5e6bd3cd9ab3614ae18dd341c31588663e27836503a7` | 1168825 |
| 42948096573 | 13822744861 | `6638b15a5d966f826aeba8cacce3294b155e9cd1d9fc1bf58bf1fcae8bf29d7b` | 6957 |

## Decision and next boundary

The balanced cache experiment is complete and still fails strict matching.
Keep original sampler, Road-first capture, PSSM/Chase, geometry and model
camera defaults. Original official MD-V3 remains the prior **0/4 PASS (FAIL)**;
no new official ONNX gate ran, and Stage 7 is incomplete.

A separate terminal-only local shadow-region probe retained four post-region
observations: a depth attachment of type `GL_TEXTURE`, object 1, mip level 0,
and active `PSSMShadowAtlas` bound to texture 1 with `use_pssm=1`; both shadow
camera initial states were empty. This is a potential feedback binding, not
a per-primitive trace, proof of an executed atlas fetch or a unique cause.
The next opt-in factorial plan separates original, linear sampler,
shadow-input guard and both: two OFF repeats plus one terminal-only ON process
per condition/case, **48 native processes** across four cases. See
[the shadow-feedback isolation plan](superpowers/plans/2026-11-11-shadow-feedback-isolation.md).
This document records no results from that next implementation.

## Automatic merged-main cache repetition

PR #20's merge started [main run 42951160118](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42951160118)
on source `465bf0c49a585fecb8ad313cac3b29e96736b8b6`. It completed 5/5 jobs.
All five archive digests/sizes, all cache snapshot bytes, 24 UUIDs/six PIDs per
case and the exact case/final summaries were independently revalidated.
Source unit run **42951159987** also passed. This is a separate repetition.

| Arm | Source Road/Wide /40 | Warped Road/Wide /40 | I420 /40 | Complete cases /4 |
| --- | --- | --- | --- | --- |
| shared | 23/23 | 23/29 | 19 | 0 |
| isolated | 34/38 | 34/40 | 34 | 3 |
| disabled | 34/33 | 34/33 | 29 | 2 |

No cache condition reached strict 4/4. This repetition must not be started
manually again merely to rediscover that negative result.

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42951160118 | 13826110055 | `ac4912e2b7bd800921c8578eefd2f69ef6f521e3b5ff5700e247154a23bb40ca` | 2853125 |
| 42951160118 | 13825915991 | `0d9c062400ba23a55458174e8433026b6c6160fa78b81d19fc24c93f2bb1a4d6` | 2813848 |
| 42951160118 | 13825566828 | `3ad6457bd2638ce95867f3fb7c9f9b916f593e1c7342a1c940c69a1e29149a3b` | 2812533 |
| 42951160118 | 13825173804 | `28f557a7d5205502783efb4ee50e87f107eade16e629b73c7586e653ea11d3dd` | 31450 |
| 42951160118 | 13824863306 | `2b8f5556b98dd09bc41579e8fb521137c6b94153b3c65464a012eaf4636bdbcb` | 2986955 |
