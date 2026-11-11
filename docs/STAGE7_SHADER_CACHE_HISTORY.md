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
