# Held-host v2: bounded live API visibility

User requested continued sequential execution; earlier questions, inline execution,
own Draft/CI and new source-qualified requests were delegated. No worktree,
implementer delegation, main merge, Cloud/registry publication or old request replay.
Base f06c23199df8d2772615692965c3610e97544bbb; preserve all235producer files.

## Evidence and choice

Campaign01 source5ab516c/C01ca6198/run43563102068 genuinely failed in both jobs:
HTTP200 live-run snapshots said queued, validate_live demanded in_progress.
Only an in-memory status change passed that pure gate; backend/cache cause was
not proved. Original bytes and consumed authority remain immutable.
Chosen implementer approach: new static v2 derivatives observe successful pending
run/caller-job API snapshots within predeclared limits, then require actual
in_progress. Accepting queued weakens authority; sleeping blindly cannot prove
visibility; mutating old source/request violates preservation. No alternative fleet.

## New authority and unchanged native contract

ID held-abba-20261114-02; source fix/engine-clock-held-abba-visibility-v2;
operation diagnostic/engine-clock-held-abba-20261114-02; workflow
.github/workflows/engine-clock-held-abba-v2.yml. C adds sole new -canary.json;
direct-child A adds sole separate -abba.json; C-only workflow path filter.
Actual checkout/producer head remains C. Acontrol head/data distinct. All v1
lease6000s/control900s/181snapshots/256GETs, attestor1500s/256GETs/512MiBZIP,
phase2400/start1800/child420/native120/inventory180/cleanup12/64GETs/3GiB,
4GiB/CPU2/PID128/privateIPC+CG/readonly/networknone/capdrop, genuine image006,
six poses, OFF0/ON0/ON1/OFF1, provider5/capture30/getter528 limits remain exact.
No model/ORT; strict0of4FAIL/Stage7INCOMPLETE. No scientific promotion.

Run visibility: maximum60seconds/13snapshots/5seconds cadence; only queued with
null conclusion may wait. Every snapshot must bind runID/Chead/branch/event/
attempt1/workflowpath/repository and stable positive workflowID. Any changed
identity/status/conclusion or HTTPerror fails immediately. Only actual in_progress
with null conclusion can return. Preserve each original numbered body and HTTP
event; live-run.json is an exact-byte alias of the admitted original body.
Run visibility does not claim completed C/workflow/attestor or later gate success.
Clamp shared client deadline to min(original, visibilitystop) per observation and
restore original without extending it. Reject results arriving at/after deadline.

Caller job: max30seconds/7snapshots/5seconds, validate complete bounded named-job
list and target run/head/attempt; queued/null may wait, in_progress/null required,
terminal or other status/conclusion rejects. Same transport deadline clamping.
Known absent target retains existing finite visibility behavior. Other peer job
may have completed successfully when A reauthenticates its still-running host.
Worst control metadata GETs251<=256 (auth35 + control181+peer31 + delta4).

All235prior source bytes plus6v2modules/3v2tests/workflow/spec/plan/originalqueuedfixture form248pins.
No global mutation, dynamic source rewriting, checkout override or native local run.
Completed native C/upload steps + distinct terminalSUCCESS metadataattestor +
genuine root/fresh original CPUacceptance remain mandatory before Acontrol.
Retained actual full identity/lease and original C raw replay required before A.

## Verification and completion

Real original queued body drives CPU tests; active copies explicitly synthetic.
Test queued→active, persistentqueued, changedprovenance, completed/cancelled,
HTTPfailure, latearrival/shareddeadline, targetjobqueued→active, failedjob and
malformed list. Existing derivative tests cover all new request/source/binding/
lease/archive/attestation/workflow/prestart boundaries. All old source preserved.
Fullsuite, one fresh whole-source review, one Important/Critical RED→GREEN pass,
no rereview; defer Minors with costs. Exact source push+PR four namedjobs/attempt1/
zeroartifacts before unique Crequest. Genuine original C+terminalattestor+root/fresh
before separate Acontrol, same actual host A, final raw review or honest terminal
failure and versioned evidence/Draft/CI. No auto rerun after consumed failure.
