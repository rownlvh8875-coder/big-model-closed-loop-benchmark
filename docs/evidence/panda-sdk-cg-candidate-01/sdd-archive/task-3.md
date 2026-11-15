### Task3: Necessary static member-layout and link gate

**Files:** Create scripts/panda_sdk_cg_static_gate.py,tests/test_panda_sdk_cg_static_gate.py. Reuse scripts/panda_sdk_link_elf.py/readback_process_mapping.py and image-provider selection without altering them.

**Interfaces:** audit_candidate(candidate:Path,layout_object:Path,build:dict,reference:Path,providers:dict[str,Path])->dict. Returns status CG_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME only after all spec predicates; otherwise STATIC_CG_CANDIDATE_REJECTED with reasons and native_admitted=False. Task4binds this output to authenticated compiler/carrier origin.

- [ ] Write test_old_and_forged_offsets_reject: old0x618/0x61c/0x600 reject; new0x688/0x68c/0x670 plus matching descriptor accepted only with all other supplied facts. Changed descriptor with old getter bytes, unknown machine instruction, truncated/overflow/ambiguous dynamic symbol spans and executable/init-array layout objects reject.
- [ ] Write test_no_runtime_promotion: candidate status never asserts full ABI/crash fix/installed image/runtime admission, even with equal revision/vtable1024 and all strong imports available. Changed Cg provider, missing API/state duplicate, unlisted weak exception or unqualified dependencies reject.
- [ ] Run `python -B -m unittest tests.test_panda_sdk_cg_static_gate -v`; expected RED missing gate.
- [ ] Implement bounded ELF-backed getters/descriptor checks and all spec static predicates. Existing ad-hoc .py.data investigation recipes are references only. Retain candidate sizes/macros/version diagnostics and unknown wheel configuration facts; infer no absent wheel sizes.
- [ ] Run the same tests; expected GREEN. Run gate against retained OLD SDK/reference as DATA; expected rejection with the three known offset mismatches. Commit gate/tests/negative evidence.
