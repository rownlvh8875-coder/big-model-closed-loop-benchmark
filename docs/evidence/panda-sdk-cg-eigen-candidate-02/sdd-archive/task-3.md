Plan docs/superpowers/plans/2026-11-16-panda-sdk-cg-eigen-candidate-v2.md
### Task3: Complete CET-aware necessary static gate

**Files:** Create scripts/panda_sdk_cg_eigen_gate.py,tests/test_panda_sdk_cg_eigen_gate.py. Read frozen libpandagl/build-libpanda/parent DATA from build01 and old reference/provider authorities; edit none.

**Interfaces:** audit_candidate(candidate:Path,parent:Path,descriptor:Path,build:dict,providers:dict[str,Path])->dict. Exact success status CG_EIGEN_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME, otherwise STATIC_CG_EIGEN_CANDIDATE_REJECTED with observed facts/reasons and no runtime/fullABI/crash/install authority.

- [ ] Write test_cet_complete_getters_and_consumed_candidate_rejects: optional exactlyone f30f1efa then exact mov-disp32/ret; both known complete vendor copy bodies and validated import call targets. Extra/truncated prefix,suffix,IFUNC,overlapping/W+X/unbacked symbols,decoy expected then old loads or arbitrary call target reject. Actual build01 supports observation but retains0x678/0x67c/0x660 mismatch; matching descriptor cannot override code.
- [ ] Write test_literal_code_config_link_all_required: byte parent/raw equivalence plus actual build facts/effective Eigen/alignment, offsets0x688/0x68c/0x670,vtable1024,33exports/one state and exact current-image imports/Cg pair/original3weak exceptions are all required. Missing/changed provider,strong import,API/state or unknown feature rejects. Equal offsets/revision/vtable never assert complete ABI/runtime binding/abort fix/image installation; wheel sizes remain unknown.
- [ ] Run `python -B -m unittest discover -s tests -p test_panda_sdk_cg_eigen_gate.py -v`; expected RED.
- [ ] Implement bounded whole-function byte templates and PLT/loader association, independent128B parent extraction plus fixed descriptor validation and existing static provider/API checks. Keep origin separate. Do not use ad-hoc forensic recipes as admission parsers.
- [ ] Run same tests; expected GREEN. DATA-only negative integration on consumed build01 must still reject; this does not revalidate or reopen its request. Commit.
