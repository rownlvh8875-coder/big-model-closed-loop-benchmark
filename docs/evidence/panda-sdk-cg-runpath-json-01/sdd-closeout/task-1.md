# Task1: Narrow JSON semantic comparison

**Files:** Create scripts/panda_sdk_cg_runpath_json.py,tests/test_panda_sdk_cg_runpath_json.py.
**Interfaces:** canonical_metadata(metadata:dict)->dict; validate_reported_gate(claimed:dict,recomputed:dict,providers:dict,metadata:dict)->None. Export contract()/source_closure(root)/validate_audit_ci(source,registrations,proofs) for Task2 using hardpinned contract and original310map.

- [ ] Write actual handwritten CPU shared-library/version-script fixture; inspect_elf emits integer version keys, JSON round trip makes strings. New comparison must accept equal metadata while old receiver still rejects. Never load/execute fixtures.
- [ ] Write type/order/value/version/missing-row/unknown-field/advisory-path/numeric-key collision/bool/nonfinite/depth/node/string bound negatives. All ordinary scalar types preserved, only canonical table indices0..32767 normalize; reject duplicate raw JSON with existing strict parser.
- [ ] Run `python -B -m unittest discover -s tests -p test_panda_sdk_cg_runpath_json.py -v`; Expected RED missing module. Implement narrow canonicalization and original selected gate field checks, typed deep equality and sole scoped provider-record data_path exception. Add closed contract/source314 and exact own-sourceCI2events/4jobs/attempt1/artifacts0 checks.
- [ ] Run same; Expected GREEN. Commit tests/code/ledger.
