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
