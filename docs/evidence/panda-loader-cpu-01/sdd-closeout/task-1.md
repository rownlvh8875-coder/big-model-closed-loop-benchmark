# Task1: Closed CPU fixture core

**Files:** Create scripts/panda_loader_cpu_fixture.py,tests/test_panda_loader_cpu_fixture.py; new contract/frozen318 map.
**Interfaces:** build_fixture(out:Path)->dict; validate_fixture(out:Path,manifest:dict)->None; run_cases(loader:Path,fixture:Path,manifest:dict,out:Path)->dict; validate_observation(case:str,command:dict,trace:str,paths:dict)->dict. contract(),source_closure(),validate_ci() feed Task2.

- [ ] Write inert -nostdlib fixture behavior tests:hostGNUloader baseline7/merged-nondefault7,missing-library-version/wrong-target-version reject with required trace and no successful binding. All assertions refer actual CPU process effects, not mocked loader output.
- [ ] Add fixture bytes/extra files/symlinks/ELF metadata/environment guards,wrong-loader/trace/status/stream/ownership/case/budget/oldsource/CI negatives. Run `python -B -m unittest discover -s tests -p test_panda_loader_cpu_fixture.py -v`; Expected RED missing module.
- [ ] Implement exact sources/six compiler commands/closed metadata+byte manifests/private environment/bounded owned execution/case-slot ledger/trace+return validators. Add fixed contract/source322/ownCI. Run same; Expected GREEN, host-loader CPU cases separately labelled/no SDK qualification. Commit.

