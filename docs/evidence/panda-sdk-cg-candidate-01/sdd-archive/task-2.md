### Task2: Measured isolated-output build and compile-only descriptor

**Files:** Create scripts/build_panda_sdk_cg.py,native/panda_sdk_cg_v1/layout_contract.cxx,tests/test_build_panda_sdk_cg.py. Reuse unchanged source staging/ELF/dependency parsing primitives; never call the old GCC14-pinned build/profile entrypoint.

**Interfaces:** build(stage:Path,inputs:dict,out:Path,tool_profile:dict)->dict; compile_layout(sdk_include:Path,inputs:dict,out:Path,tool_profile:dict)->dict. Both preserve structured failed receipts. Task4supplies verified hosted context; Task3consumes candidate/descriptor paths and build manifest.

- [ ] Write test_cg_command_and_dependency_closure asserting --use-nvidiacg plus all four custom nvidiacg/cggl path options, ABI0/MD exactlyonce,2workers and originalsource identities; silent Cg disable, wrongcompiler, injected MAKEPANDA/RPM flags, host-header drift, missing tool, failed spawn and timeout reject with argv/preflight/return-or-exception/timing/log/owned-cleanup fields.
- [ ] Run `python -B -m unittest tests.test_build_panda_sdk_cg -v`; expected RED missing builder.
- [ ] Implement new gcc13/profile discovery and allowlisted environment. Capture source/private/tool/subtool/header inputs before; validate actual dependency files and used-input identities afterward. Use create-only output, recorded before-start latch and owned subprocess group; no implicit package install/fallback/rebuild.
- [ ] Add compile-only .panda_cg_layout descriptor per spec, using real generated glgsg.h/shader.h and probe-only -fno-access-control/-Wno-invalid-offsetof. Emit only data; -c only. Tests use a handwritten CPU layout type to verify capture/never-execute behavior. Do not load real SDK in tests.
- [ ] Run the same tests; expected GREEN, including every negative structured receipt. Commit builder/probe/tests; actual full target build remains deferred to Task4's authenticated slot.
