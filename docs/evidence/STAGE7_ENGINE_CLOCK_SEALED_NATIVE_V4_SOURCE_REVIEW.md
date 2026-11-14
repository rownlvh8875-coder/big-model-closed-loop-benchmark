# Native v4 evidence-boundary source review

One fresh gpt-6-astra/medium read-only reviewer, no inherited conversation,
mutations, subagents, network, Docker or native execution. All9files from
f5422390b1e222b098d1b1886e33ffd5d582c8a7 to6b253d002957040c7fac7714e0a67d300cf929c4
read. Critical0/Important1/Minor1, plus existing SN-M1/M2 costs. Root's authorized
single Important fix pass: RED→GREEN6fixtures0.022s, full1097tests/7existing
skips PASS104.517s. No rereview.

## Important fixed

EB-I1 (reviewer's SN-I1 for this scope): frozen helper redacts only lowercase
HTTP(S) and ignores known values<8chars. Bound malicious error strings could
expose uppercase/mixed-case credential URLs or short tokens in printed results.
New local v4 redactor, without changing frozen helpers, redacts nonempty known
credential values regardless of length and case-insensitive HTTP(S) auth/query
parts BEFORE truncation. Mixed-case/short-token fixture failed with a visible
dummy CasePassword before fix, then passed. Malformed hostile metadata remains
non-echoed/unknown. No real v4 execution occurred before this fix.

Reviewer confirmed physical cache separation from exact execution upload root,
no chmod/chown or weakened mounts/admission, summary acceptedFalse/unknown[0,1]
until context/nonce/parent/request-bound,187-file closure and request04absent.
Runtime is namespace-only v3copy; only controller topology/summary changes.

## Deferred minors

- EB-M1: topology fixture uses chmod0/rglob, not actual unprivileged/root-owned
  uploader integration. Its claim is physical exclusion only. Cost: future
  permission/uploader regressions have reduced direct fixture coverage; actual
  new workflow upload remains mandatory evidence.
- SN-M1: failed inventory detail omitted before assertion; cost less precise
  diagnosis, no provider admission.
- SN-M2: prefix reads use enclosing watchdogs, not one encompassing180s timer;
  cost delayed rejection on stalled prefix IO.

## All declined judgments and rulings

1. Native03cause/captures/closure/acceptance lack original artifacts. Ruling:
   retain UNKNOWN and provider[0,1], no six-pair inference. Cost if wrong:
   invented scientific evidence; promotion remains prohibited.
2. Native04/upload outcome was not executed in review. Ruling: sole fresh run
   and original bytes decide; source review supplies no acceptance. Cost if
   wrong: another consumed failed request, no accepted native canary.
3. Reviewer did not rerun whole suite. Ruling: root ran6targeted fixes and fresh
   full1097/7skip suite after RED→GREEN. Cost if wrong: author-side blind spot;
   exact external4job CI is still required before activation.
4. Complete original03 API/log authenticity not rechecked by reviewer. Ruling:
   root retains original API and masked job log/hash, with0artifacts explicitly.
   Cost if wrong: dependent diagnosis invalid, never evidence of native success.
5. SN-M1/M2 not resolved by change. Ruling: retain their deferred costs and do
   not label the summary as full inventory-failure or encompassing-timer proof.
   Cost if wrong: misleading diagnostics/timing assurance.
6. Universal payload readability unproved by static xvfb source. Ruling: actual
   original artifact membership/CRC/bytes must be checked before acceptance.
   Cost if wrong: upload/root verification fails; no accepted canary.
