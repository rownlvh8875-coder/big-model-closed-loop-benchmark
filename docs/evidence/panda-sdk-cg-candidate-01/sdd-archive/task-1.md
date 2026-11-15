### Task1: Closed Cg/source/provider input qualification

**Files:** Create scripts/panda_sdk_cg_inputs.py,tests/test_panda_sdk_cg_inputs.py,docs/evidence/panda-sdk-cg-candidate-01/inputs.json. Read only existing source/image authorities and docs/evidence/panda-sdk-cg-design-01/contract.json.

**Interfaces:** qualify_inputs(archive:Path,image_authority:Path,provider_data:dict[str,Path],out:Path)->dict writes a new private input tree and manifest. Returns schema/status,header/provider records,original authority hashes and explicit target_execution=False. Consumed by Task2; it cannot grant external artifact origin.

- [ ] Write test_exact_header_and_image_provider_selection: valid pinned inputs yield exactly Cg/cg.h,Cg/cgGL.h and the two image DSOs; fake parser-inc, Trace or toolkit whole-file hashes, unsafe names/links/duplicates and forged authority reject. Use small synthetic pinned fixtures for parser tests; actual pinned input acceptance is a DATA-only integration check, not mocked external provenance.
- [ ] Run `python -B -m unittest tests.test_panda_sdk_cg_inputs -v`; expected RED missing module/function.
- [ ] Implement closed TAR32MiB/inflated512MiB/20000member/1MiBselectedheader bounds and exact pins from contract; create-only out, no old tree writes. Validate existing image authority/inventory bytes and canonical provider membership. Record aliases and classify source/generated/private/host origins separately.
- [ ] Run the same tests; expected GREEN. Run actual input qualification on retained archive/provider DATA; expected pinned header digests and both current-image DSO digests, nativeFalse.
- [ ] Commit new qualifier/tests/evidence; no other runtime files change.
