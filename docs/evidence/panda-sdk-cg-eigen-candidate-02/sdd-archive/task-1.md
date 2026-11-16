Plan docs/superpowers/plans/2026-11-16-panda-sdk-cg-eigen-candidate-v2.md
### Task1: Exact Eigen header qualification

**Files:** Create scripts/panda_sdk_cg_eigen_inputs.py,tests/test_panda_sdk_cg_eigen_inputs.py; reuse frozen docs/evidence/panda-sdk-cg-residual-01/libeigen3-dev_3.4.0-4_all.deb.data,eigen-input.json,eigen-header-manifest.json,contract.json. Read old panda_sdk_cg_inputs helpers without editing them.

**Interfaces:** qualify_eigen(package:Path,private_root:Path)->dict stages exactly530files/8669561B under a fresh qualified Cg private root, returns schema/status/package pin/version/file records/staged root/target_execution=False. Task2 consumes this alongside the genuine Cg/current-provider manifest.

- [ ] Write test_exact_pinned_eigen_headers: exact archive1040780B/SHA1a167bb381acb90c1d8450a8f3e66a09d216dbc64b33ac8a082a0912513ef939,530exact header names/digests/version3.4.0; lapacke.h1058369B accepted under2MiB, no CMake/pkgconfig/runtime/package-script files staged. Synthetic parser negatives cover >4MiB package/>32MiBinflation/>2048members/>2MiBheader,links/traversal/duplicates/missing header/wrong version/host aliases and existing-output collisions; no old root writes.
- [ ] Run `python -B -m unittest discover -s tests -p test_panda_sdk_cg_eigen_inputs.py -v`; expected RED missing module.
- [ ] Implement closed ar/data.tar.xz parsing and manifest-bound membership, create-only owned header writes; verify generated effective expectations are future measurements, never asserted from the archive alone.
- [ ] Run same test; expected GREEN. Run actual archive qualification into a new DATA-only root; expected530matches and no installation/execution. Commit.
