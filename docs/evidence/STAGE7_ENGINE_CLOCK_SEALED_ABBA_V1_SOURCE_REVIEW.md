# New sealed C/ABBA whole-source review

One fresh gpt-6-astra/medium read-only reviewer, no inherited conversation or
subagents, reviewed all11newfiles at9d9e5d39a6df54aec3d40a3f7311de5a2ac6c676
against75bfca13ab2bea479e7a7f36f525369332a4ec2f and relevant frozen dependencies.
No mutations/native/GL/Docker/model/network/full-suite rerun. Independently checked
205unchanged prior paths/215current paths. Critical0/Important3/Minor0.

Source verdict was NOT_READY until fixes; no claim that reviewer approved later
source or actual runtime. One fix pass, no rereview. Root reproduced all3findings
as ordinary assertion failures, then20focused tests PASS1.206s. Final full suite
and exact source CI must pass before C registration; actual results in ledger.

## Important findings accepted and corrected

- SA-I1 ZIPNUL: ZipInfo.filename silently truncates at NUL while orig_filename
  retains bytes. Handcrafted local/central-name fixture reproduced acceptance.
  Require original/normalized names equal and validate original controls before
  selection or creation. Same bounded archive/CRC/hash rules remain.
- SA-I2 Inner identity: bare host/full-identity rejection lost independently
  observed differences. Indexed bounded host/identity records now retain actual
  observed fields and accepted/observed hashes/differences BEFORE gate. Fixtures
  cover parent/child host and affinity/memory mismatch; provider continuation is
  unreachable. Actual preflight routes through the same helper.
- SA-I3 Earlyphase: parent selection/admission rejection previously preceded its
  ledger. Structurally bound request/context now initializes failed phase before
  parent preflight; identity_verified startsfalse, admission_stage/error retained,
  no actual successful counts inferred. Owned selection rejection proves phase
  exists with emptylaunches/failedidentity/terminal result before provider work.

## Every declined scope, author ruling and cost

1. Actual APIs/artifact availability/host equality/Docker/load/Xvfb/GL/provider/
   OOM/cleanup timing were not executed. Ruling: exact CI/new C/original acceptance
   and strict A gate decide. Cost if wrong: new request consumed with no acceptance.
2. Root/fresh flags are attestations, not externally proven human decisions.
   Ruling: author records genuine separate root and fresh acceptance; external
   run/job/ZIP proof remains mandatory. Cost if wrong: false attestation invalidates
   dependent admission; flags alone never authenticate raw provenance.
3. Profile equality is not physical/hostile-host attestation. Ruling: preserve
   explicit trust boundary and every profile field. Cost if wrong: origin assurance
   fails outside admitted source/image/isolation trust, no forensic guarantee.
4. Rendering/science/geometry/optics/full-S/neutrality/model/ORT outcomes unjudged.
   Ruling: descriptive camera/clock only, zero model, strictFAIL/Stage7INCOMPLETE.
   Cost if wrong: unsupported sensor/scientific success claim.
5. Arbitrary malicious native-code resistance not expanded. Ruling: trust reviewed
   authenticated source/image and preserve isolation. Cost if wrong: compromised
   trust boundary invalidates observations; no arbitrary-code attestation.
6. CRC corruption/every compression variant not independently executed. Ruling:
   retain bounded stdlib CRC reader plus explicit canonical/duplicate/symlink/path/
   cap guards, corrected NUL fixture and genuine original audit. Cost if wrong:
   unsupported malformed archive/codec may reject or expose a regression.
7. No real child tested for permit reuse/cross-index substitutions. Ruling: pure
   FIFO/nonce/group/index/cache constraints plus new actual raw checks govern.
   Cost if wrong: launch/authorization defect consumes request, no retry.
8. Frozen timing/diagnostic/generated-memory/observer limits not expanded. Ruling:
   preserve source bytes and earlier costs, no stronger guarantees. Cost if wrong:
   overstated timing, source origin, diagnostics or neutral-observer assurance.
9. Whole suite not independently rerun by reviewer. Ruling: fresh author full suite
   and exact named external CI jobs govern after fixes. Cost if wrong: author
   blind spot, no independent full-suite replay claim.

No new Minor finding. Prior NS-M1/M2/SN-M1/M2/EB-M1/NM-M1/M2 retain documented
malformed-input, regression, diagnosis and earlier-watchdog limits.
