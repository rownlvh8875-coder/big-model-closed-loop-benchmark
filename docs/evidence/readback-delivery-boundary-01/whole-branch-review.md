# Whole-branch review: readback delivery/process boundary

Reviewed base `c06a3a3eb8e215a8e40054433cf4c6c4c1d42bdc` through HEAD `bcb8e11e4183b2c6f50ebd48dcad357181b77a6a` in `/workspace/big-model-closed-loop-benchmark`. This is the single fresh whole-branch review. No checkout/index/HEAD/branch mutation, subagents, remote actions or native runs were performed. Repros and report are under `/tmp`.

## Scope and verification

Read the spec, implementation plan (all five Review Focus items), ledger, result and continuation; all nine added production/test source files; existing cache/bridge interfaces and implementation needed to assess integration; evidence generation and preservation scripts, indexed evidence and verification logs. The diff consists of 191 additions, with no changed/deleted base files. Independently verified SHA256 and sizes for all 176 proof-index entries and all 14 current source pins. Inspected the retained full-suite result: 1414 tests, 7 skipped, success in 94.729 seconds. This is retained evidence, not a new full-suite run.

Fresh authorized verification: `python -B -m unittest tests.test_readback_call_delivery tests.test_readback_process_mapping tests.test_readback_producer_channel` passed all 18 tests in 1.583 seconds. These compile/run only the CPU originals/caller or the tiny locally compiled CPU library. Reviewed 78 retained plain/sanitized scenario results, build commands, and executable/symbol/tail-disassembly evidence through their integrity-checked index. No GL/Panda/MetaDrive/provider/model/ORT/native replay was imported or executed.

## Strengths

- Typed dispatch preserves each original alias and optional resolver NULL, with actual original return-dependent context events and deliberate errno restoration. Bootstrap applications use no-op callbacks, keeping replay distinct from original execution.
- The read entry is a real tail jump; arming requires successful bridge installation and matching original/observer, and finish disarms it. CPU caller checks exercise the prior register/stack/returnPC contract.
- Mapping validation combines reviewed ELF spans, private executable mapping identity, offset/load-bias agreement, actual process bytes and before/after identity checks, with bounded parsing and reads.
- The channel uses per-message kernel credentials, an actual owned unreaped child, fresh caller nonce, held-code inspection, same-spool snapshots, clean EOF and exit, then the existing strict decoder. Unexpected received descriptors close even on rejection.
- Documentation consistently retains the CPU-only evidence boundary and original strict 0/4 FAIL / Stage7 INCOMPLETE. Evidence is reproducible and source-pinned; no base source was altered.

## Findings

### Critical: 0

### Important: 1

**I1 — Known unsupported direct-state-access mutation can be classified as safe and bypass metadata invalidation.**

Location: `native/readback_call_delivery.c:63-66` (`unsafe_name`), used at line 76 and bypassed through the safe-name return at line 174.

The denylist rejects traditional capture-state mutators such as `glReadBuffer` and `glBindFramebuffer`, but accepts `glNamedFramebufferReadBuffer` (and its EXT form). That operation directly changes the read selector of a framebuffer whose selector is cached by the existing command supplier. It is a known unsupported capture-state mutation, exactly the category the spec says the safe-name allowlist excludes. An explicitly allowlisted name currently returns its unwrapped original with no error, so a subsequent call can change that framebuffer's selector without updating or invalidating the cache. A later read can therefore continue using the earlier cached selector and close successfully. This does not require hostile same-UID behavior, pointer spoofing, or a real installed hook; it is an input-validation hole in the reusable delivery component's advertised boundary.

Reproduction performed entirely with CPU code: copied `tests/fixtures/readback_delivery_fixture.c` to `/tmp/readback-review-unsafe-name.c`, replaced both occurrences of `glDrawArrays` with `glNamedFramebufferReadBuffer`, and compiled it with unchanged production delivery/cache/core/bridge sources and the existing CPU caller (tail target substituted as in `compile_delivery`). Running `/tmp/readback-review-unsafe-name safe` succeeds. `/tmp/readback-review-unsafe-name.json` records `delivery_error=0`, `finish=0`, `captured=2`, all argument/errno/register checks equal 1. Thus installation and resolution accept this known unsupported mutator. The repro demonstrates the missing admission rejection; it does not claim execution of GL or driver-state proof.

Recommendation: in the one authorized TDD fix pass, add CPU regression cases requiring installation rejection for known unsupported selector/context-state mutation names, including core/EXT `glNamedFramebufferReadBuffer` and `glXCopyContext` (which can copy pixel-store state). Extend the explicit unsupported-name classification accordingly, while preserving the documented limitation that this is not complete real-Panda coverage. Test rejected safe-name installation and an ordinary safe-name positive case. Do not broaden this into live installation or GL validation.

Severity rationale: Important, because the advertised fail-closed treatment of known unsupported mutations can silently become successful stale command metadata. Not Critical: the branch remains inert, explicit dispatch/allowlist profiles require qualification, and no native authority or deployment is granted.

### Minor: 0

## Review Focus conclusions

1. Alias/proc/NULL/mismatch/unknown forwarding and errno behavior are covered by implementation and positive/negative CPU scenarios; I1 is the unsupported safe-name classification gap.
2. Bootstrap ordering and actual-return context semantics are retained; original calls are not replayed. Delete reads are bounded to 32 names and occur only for an armed valid span under the documented input-extent precondition. Sticky errors prevent recovery into successful metadata.
3. Tail assembly preserves the caller stack/register frame; matching delivery binding and successful bridge install precede arming. The existing bridge performs the actual callsite/identity/extent checks. Finish combines bridge/cache/delivery outcomes, while fixture status additionally includes sink flush/fsync.
4. Exact reviewed file ranges cannot be replaced with anonymous/foreign/writable/wrong-offset or wrong-byte memory through the checked interface. PID starttime, executable/file identity and target mappings are checked around reads. Full process atomicity is explicitly outside the guarantee.
5. Actual kernel sender identity, nonce, typed packet, status, code ranges, regular spool contents, EOF and exit are combined before the old decoder can accept. The retained negative cases and fresh focused tests reject the supplied partial/forged/extra/failed-finalization cases.

## Behaviors considered but declined as outside scope (before verdict)

- Live GL interposition, exports, constructors, loader/preload/resolver installation and symbol coverage across real Panda: explicitly deferred; this branch is inert typed delivery.
- Actual Panda ABI/camera/GSG/buffer/lifetime qualification beyond the CPU-shaped caller: requires a new native contract and is not claimed here.
- GL driver acceptance of void state commands, GPU write freshness, camera image semantics and original GPU bytes: command-derived CPU metadata does not establish these facts.
- Official model/ORT/provider success and completing Stage 7 or increasing strict score: excluded and no allowance remains.
- Hostile same-UID/root modification, forged code by a privileged sender, or cryptographic attestation: explicitly not the threat model.
- Whole process/image/dependency/environment identity and executable behavior outside the reviewed named code ranges: profiles deliberately select bounded ranges rather than attest the full runtime.
- Atomic snapshot against mapping/exec changes that occur and revert between observations, or future code immutability: the documented guarantee is point-in-time observed consistency, not freezing the process.
- Proving that an explicitly supplied code profile/address table describes the intended ABI and executed functions: reviewed profiles and original addresses are caller trust boundaries.
- Enforcing nonce uniqueness across independent runs with a persistent replay database: caller-generated fresh nonce is an explicit precondition.
- Arbitrary executable sandboxing or malicious subprocess descendant/resource containment: `run_cpu_probe` requires a reviewed CPU-only fixture and says it is not a sandbox.
- Direct invocation of optional NULL originals, invalid string/delete memory spans, calls before installation, prematurely freed installed storage, nonreturning originals, or concurrent installation/lifecycle: these violate the documented caller capability, valid-input, lifetime and serialized-lifecycle requirements.
- Complete discovery of every possible OpenGL mutator or every future extension: real coverage is deferred; I1 concerns familiar concrete unsupported state mutations the current explicit guard purports to exclude.
- Revalidating remote main/Drafts/native histories or rerunning prior native evidence: this read-only review inspects retained preservation evidence and local diff only; no remote or native work was authorized.
- Re-running the entire historical test suite: reviewed its retained log and independently ran the three new CPU modules; unrestricted historical imports/runs were not authorized for this reviewer.

## Assessment

**Ready with fixes:** resolve I1 in the single authorized Important/Critical TDD fix pass before proceeding. No rereview or minor-polishing round is requested. Current native allowance remains 0; original strict 0/4 FAIL and Stage7 INCOMPLETE persist. This assessment grants no native admission, merge, push or publication authority.
