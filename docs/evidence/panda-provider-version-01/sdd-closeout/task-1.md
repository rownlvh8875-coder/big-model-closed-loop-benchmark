# Task1: Pure bounded version witnesses

**Files:** Create scripts/panda_provider_version_witness.py,tests/test_panda_provider_version_witness.py; new closed contract/frozen314map.
**Interfaces:** audit_graph(nodes:dict,edges:list,policy:dict)->dict; contract(root=ROOT)->dict; source_closure(root=ROOT)->dict; validate_ci(source:str,registrations:list,proofs:list)->None. Report contains original strict rows,explicit per-row requirement/stub/target witnesses,count summary and false authority flags; no origin authority.

- [ ] Write real -nostdlib CPU graph fixture:root→consumer→legacy-stub→merged-target. Consumer linked to original legacy exporter before stub replacement; same ABI_1 remains in stub's version table and merged export. Old checker must still miss the consumer row; new report must witness it without loading any ELF.
- [ ] Add wrong/missing stub/target/version/name/type/SHA/edge,unrelated/disconnected exports,IFUNC,weak/default distinction,duplicate edges,JSON key collision/type/bounds/population/source/CI negatives. Run `python -B -m unittest discover -s tests -p test_panda_provider_version_witness.py -v`; Expected RED missing module.
- [ ] Implement bounded graph/policy validation and narrow dual-obligation witness model; fixed own contract/source318/CI validator. Run same; Expected GREEN with observed counts. Commit code/tests/spec/plan/ledger.

