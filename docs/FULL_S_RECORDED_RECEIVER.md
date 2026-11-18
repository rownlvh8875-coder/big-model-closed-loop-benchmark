# Recorded official diagnostic receiver

The new reader completes the next independent step after the actual camera/
recorder canary. It does not start a model, renderer, SDK or CARLA. The separate
private official-model task remains UNKNOWN until its actual link/result/state
is available. No model activation is included here.

`python -I -S -B scripts/full_s_recorded_receiver.py plan` is stdlib-only.
`python -I -B scripts/full_s_recorded_receiver.py verify --trial-dir TRIAL --out OUT`
uses the pinned CPU NumPy/OpenCV readers. OUT must be fresh and outside TRIAL.
There is no `run` command. Archive extraction uses a separate 384MiB immutable
ZIP/512MiB expanded/16MiB-member/512-entry ordinary ZIP profile; the old camera
canary's64MiB/128MiB limits remain unchanged.

- COMPLETE_DIAGNOSTIC means a locally consistent completed body, recording and
  cleanup. Original LANE_INTRUSION is a completed diagnostic, not full-S success.
- PARTIAL_DIAGNOSTIC preserves a failed original inference, audited-without-frame,
  observer/storage/cleanup error and every available snapshot. Reported inference
  bounds remain distinct from frames, and the original error stays primary.
- INCOMPLETE_EVIDENCE preserves reported lifecycle bounds when final receipts,
  report or manifest are missing. It does not invent verified inferences.

An accepted local structure does not authenticate the producer's session/calls,
actual native execution, model camera, RTX, physical optics, CARLA, model quality,
repeatability, private-job completion or all stage7 tracks. Those flags stay
false. Synthetic/mock/injected-session receipts, nonce/PID/source/case swaps,
changed report/manifest/UUID binding and contradictory lifecycle/error/cleanup
records are rejected. CPU tests relabel external metadata only to exercise
parser contracts; they supply no actual official model inference evidence.

Scientific producers, the capture helper, recorded worker and completed canary
reader remain unchanged. Existing full-S0/4 and strict-repeat4/4 remain unchanged.

Read-only source/pixel continuity:
`python -I -B scripts/full_s_recorded_receiver.py continuity --canary-zip ZIP --historical-dir COHORT --out OUT`
authenticates the known actual 5,012,494B canary artifact SHA/run/source, exports
the full499-file approved Git source map for hashing only, and reuses the frozen
receiver with only its byte-root scoped to that export. Current frozen Python
readers must have the approved hashes; exported or downloaded code is never
imported. Historical metadata must match trusted Git bytes before all five old
artifact snapshots and original eight first graph-feed inputs are replayed.
The new first camera RGB/canvas/I420 is compared to the two old same-case first
graph audits. A match proves same first input bytes for this condition, with
zero new model calls; it does not prove a graph feed for the synthetic policy or
later-step fidelity. Original full-S0/4/strict-repeat4/4 remain unchanged.

Review refinements: lifecycle checkpoints and final trial receipts are validated
individually. Older checkpoint bounds/cleanup remain separate from later trial
progress. Missing fingerprints/runtime records with a reported failure and
partial `abort.json` metadata are retained as INCOMPLETE_EVIDENCE, with unknown
verified calls where no original report is available. Every surviving report
still receives typed PID/UUID/case/model/error and trajectory checks. A verified
source callback requires the producer's observer request. Local results expose
tri-state `producer_reported_body_success`; they never emit an actual execution
success claim. Original long errors use the frozen worker's bounded serialization.
Historical replay and selected-case authentication consume private staged copies
of the same six verified metadata snapshots, including nested replay functions.
The larger ZIP profile also rejects aliases of implicit directory components and
DOS directory/volume-label attributes. Source-pinned Cloud receipt continuity
uses Linux; the trial/archive and metadata-scoping helpers remain portable.
