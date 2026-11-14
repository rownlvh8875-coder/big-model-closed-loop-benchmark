# Panda readback ABI ledger

Basea0e072e450cf6591b9da686711196d56eb9165a1; branchfeature/panda-readback-abi-v1.
Baseline1351tests PASS7skip121.931s; exact Draft105 push43605824432/PR43605849109 all4jobs PASS, noartifacts.
Ruling: Continue inline/samecheckout/noquestions using persistent authorization — the next missing boundary is actual binary register/extent transport — costs CPU/development, spends no native allowance.
Ruling: Use exact pinned ELF+register bridge rather than guessed-size preload or Panda rebuild — file0xf38e0734 call6305c retains R12extent/R15pointer/RBXTexture/RBPGSG — machine-specific qualification is required and runtime mapping remains unproven.
Ruling: Accept only view0/z=-1 at this bridge — other branches compute page sizes rather than actual array extent — excludes cubemap/multiview until independently qualified.
Ruling: Keep live install/state/camera/receipt transport inactive — the current environment/old source contract rejects addedpreload and CPU callers cannot qualify native state — a new runtime contract and fresh canary still cost work.
Preflight Task1→Task2: qualified returnPC/stackoffset/register contract feeds assembly+dispatcher; CPUfixture has a separately labeled synthetic returnPC, never a Panda qualification. All previous files remain immutable.
Recon: Texture upstream1.10.13h/I/cxx downloaded as data with hashes in output/stage7-readback-abi/source/download.json. PointerToArray attempted obsolete dtool path returned404; no install/load. Pinned GSGsource/ELF are existing retained data. Core original actualGPUbytes unobserved.

Task1: RED6/6missingqualifier→GREEN6/6in0.006s; syntheticELF mutations rejected. Actualpinned913073BELFstructural/hash/4227Bmethodfingerprint/call/PLT/GOT/JUMP_SLOT qualification PASS. File-levelABIonly, runtime_mapping_boundFalse. MethodSHAf2b072cf0eec59f8972329124719f328d442cea81134d6058afba4c4f7b7f90d.
Ruling: Structural ELF checks accept ordinary unused trailingpadding changes while exactqualification rejects them — physical ELF tables/spans, not artificial fixture length, determine valid structure — only exactpinnedSHA is admissible for the Panda file contract.
Task1: complete. Task2compiledCPUbridge tests next.

Task2: RED10missingbridge→GREEN10/10in1.393s; final18focusedPASS1.482s (includes6ELFtests). Assembledfakecaller checks original signedargs,stack7thpointer,6callee-saved registers and2Panda locals. Additional OFFbridgeerror/corefooter0 and outsidewindow accounting checks pass.
Task2:31CPUscenarios exactnormal/ASan/UBSanstreams+stats PASS; largest55,900,512B; finalbuild2.934881606swall excludes test/review/CI/development and is no nativeoverhead measure.
Fullsuite: python -B -m unittest discover -s tests -v →1369tests PASS7skip117.097s.
Pre-reviewpreservation: all2515baseGitblobs+299oldsourcepins+10originals match; oldDraft102/103/104/105/main/nativehistories unchanged.
Task2: complete implementation/pre-review verification. Freshwholebranchreview follows; runtime inactive and no consumedallowance reuse.

Final review: onefreshgpt-6-astra/medium wholebranch/static+syntheticdata at099fd9a;Critical0/Important1/Minor0. Reviewer independently rebuilt all31ASan/UBSan cases and verified44proofs/31rawacceptance outcomes/18focused; fullsuite log inspected only. Originalreport docs/evidence/PANDA_READBACK_ABI_01_REVIEW.md.
Final: regraded incomingerrno leak Important. Rootcause: callback changeserrno beforeoriginal; postreturn restoration cannot restore original input. Regression RED1test/2subcase failures(enabledkeep/check), OFFcontrolpassed. Onefixpass savesincomingerrno at dispatchentry and restoresimmediatelybefore allforward paths; originalreturnerrno stillpreserved. No rereview.
Final: Ruling: Runtime mapping/dispatch/preload stays unqualified — exactfileidentity doesnot establish the mappedprocess — new build/maps/environment and installation gate remain futurecost.
Final: Ruling: Native allocation lifetime stays unqualified — capturedR12transport is not a liveallocation attestation — futureinvalid lifetimes canfault untilqualified.
Final: Ruling: Cached GL state and Texture camera registration stay callertrust — CPUfixture doesnot supply realbindings/state — realcachedsuppliers remain required.
Final: Ruling: Externalreceipt dictionary consistency is not authentic native transport — caller must deliver actualbridgefinish+sinkstatus and process/window binding — fabricatedreceipts confer no nativeauthority, transport still costs qualification.
Final: Ruling: GPUcorrectness/fidelity/overhead/provider/model/Stage7 stay unobserved or inheritedFAIL — onlystaticfiles/CPUcalls executed — livecausality and officialretest remain futurework.
Final: Ruling: Install-first/validcontext+scratch/serializedlifecycle/normalreturn and nounwinding remain ABIpreconditions — violatingcalls are not supported safeintegration — unboundentrytraps and invalidlifetimes/nonlocalexits canfault.
Final: Ruling: Cubemap/multiview remain rejected — their branch computespageextent instead of theacceptedfullRAMarraylength — separateABIqualification is needed to support them.
Final: Ruling: Generic structuralELF inspection grants no admission — onlyexactpinnedfile+methodhash qualifiesfileABI — differentbinaries require newcontracts.
Final: minor (deferred): none.

Final: fixed Important1 — test_observer_cannot_change_original_incoming_or_unchanged_errno RED(enabledkeep/checkfailed;OFFcontrolpassed)→GREEN;19focusedPASS1.321s, whole1370PASS7skip118.438s.
Final:34ASan/UBSan CPUscenarios exactstreams/stats PASS; build3.408792025swall, not nativeoverhead. Onefixpass, zero rereviews/remainingImportant/Minor.
Finalpreservation: all2515baseGitblobs/299sourcepins/10originals/main/oldDrafts102–105/eightnativehistories match afterfix. ExactDraftCI follows outside immutablecommit.
