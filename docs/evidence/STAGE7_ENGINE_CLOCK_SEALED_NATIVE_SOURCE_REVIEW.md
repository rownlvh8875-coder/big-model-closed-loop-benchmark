# Sealed native source review

Review range b895800a0a1a3bc399e6ec5d47ffe05106f53127 through
924c46dd8d0b5bc49771ed630bac97da56529082. One fresh read-only reviewer,
gpt-6-astra/medium, no inherited conversation, no subagents, native, Docker or
network. Relevant existing interfaces inspected. Verdict before fixes: do not
activate. Critical0/Important2/Minor2. No rereview is requested.

## Important findings and the one fix pass

- SN-I1: runner-owned0700 binding/output/cache cannot be traversed/written by
  UID0 with all capabilities dropped. Fixed by explicit755 binding and777 fresh
  output/cache directories,644 public immutable binding files, with read-only
  source/binding mounts preserved. Real temporary-directory permission fixture
  failed755-vs700 before fix and passed afterward. No credential enters these
  mounts. Runner can read uploaded644 case evidence; root-owned600 Mesa cache
  binary files are excluded from upload, with bounded terminal inventory retained.
- SN-I2: successful collector returns the full8,339,196-byte manifest, which
  cannot fit the2MiB parent or child admission ledger. Fixed by checking actual
  inventory canonical bytes against the bound original before retaining its
  explicit path/size/hash reference and complete bounded verification metadata.
  Real accepted44,232-entry manifest plus public result-shape/counters fixture
  failed before implementation; parent/child serializations pass below2MiB after
  fix. A changed manifest entry is rejected. The older CLI summary is explicitly
  not misrepresented as a retained full collector return.

Targeted fix suite15/15 PASS1.923s. Final whole-suite result is recorded in the
continuation ledger before source qualification and one-use activation.

## Deferred minors

- SN-M1: a failed installed collector's detailed bounded prefix/stage/counters
  are not persisted before the completeness assertion. Generic failure remains;
  no provider is admitted. Cost: the consumed run can require more manual
  diagnosis and less precise filesystem failure localization.
- SN-M2: source/manifest/prefix work precedes the collector's own180s SIGALRM.
  The elapsed allowance is passed onward, and the enclosing child420s/container
  780s/total1800s watchdogs bound the operation. Cost: a stalled prefix read can
  exceed the narrower preflight allowance before rejection. Do not describe
  the180s allowance as an encompassing watchdog over all earlier byte reads.

## Rulings on all declined judgments

1. Actual Xvfb/GL/Mesa/Panda/MetaDrive startup, cache population and mapping
   acceptance were outside this read-only review. Ruling: only the new registered
   canary's actual raw run can decide these; unit tests make no runtime-success
   claim. Cost if wrong: the sole canary is consumed and remains failed.
2. Docker-injected environment and shell exports were not observed by reviewer.
   Ruling: exact inspected/actual profiles and declared DISPLAY/XAUTHORITY/PWD
   checks remain fail-closed in the new canary. Cost if wrong: startup rejects
   before provider admission, with no retry of this request.
3. Fresh installed equality, actual host/engine identity and performance require
   execution. Ruling: compare both actual inventories and strict identity cores
   with outer observations, then independently authenticate raw evidence. Cost
   if wrong: no accepted native result or future ABBA authorization.
4. Previously accepted image internals were reviewed at new call sites only.
   Ruling: retain image006's independent byte acceptance and authenticate its
   original producer against old1af source separately from the new source. Cost
   if wrong: an upstream defect can invalidate this dependent canary; no broader
   new transport acceptance is claimed.
5. Scientific repeatability, inference, GPU freshness, optical equivalence and
   future C/A host equality are outside source/fixture proof. Ruling: retain
   strictFAIL/expandedNOT_RUN/Stage7INCOMPLETE and zero model/ORT calls; a successful
   canary is only a model-free camera/clock record. Cost if wrong: overstating
   the canary would mislead later scientific decisions; those promotions are
   explicitly prohibited.

Reviewer strengths: separate old/new source authentication; derived closure;
stopped copies before the sole start; exact env/mount validation; EOF/deadline/
live-ancestor/group/nonce/hash FIFO admission; unchanged six-pose semantics and
offline validator; conservative unknown provider bounds and separate cleanup.
