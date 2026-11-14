# Native process environment boundary

Native02 at source69ed28ef0d61af6e4bf6629dc2cbf0bbbbc85f07 passed actual Docker
admission (HostConfig-only tmpfs), parent installed verification1,670,492,280bytes
and prefix verification. Run43537981048/job132271502357/artifact14090408074
failed at child entry before provider. Original322,512,132-byte ZIP SHA
f8c73f702a2025da56dfa474a589929e9b9599a15ecbc22ca6975f1f01aa8854 is retained.
Parent post-import environment proves cv2 added LD_LIBRARY_PATH exactly
`/opt/venv/lib/python3.11/site-packages/cv2/../../lib64:`; parent copied that into
the child, whose initial strict launch profile correctly rejected it. No engine,
provider or model ran. Consumed01/02 and all their sources/evidence stay frozen.

New sourcev3/requestsealed-native-20261114-03 captures the complete validated
launch environment BEFORE native imports. It validates and records the complete
post-cv2 environment, allowing only that exact pinned-image bootstrap side effect.
The actual parent environment is never stripped or restored to conceal it.
The child starts from the immutable validated pre-import snapshot, with only
its declared FD/cache and xvfb-run routes. No LD variable enters exec. The child
performs its own byte/prefix/host verification, then validates/records the same
observed cv2 mutation. Any other native selector, value, missing/extra change or
injected initial LD rejects. Do not edit installed cv2 or image006 bytes.

The installed-identity configuration environment hash now explicitly commits to
both the complete launch profile and expected post-cv2 profile, plus the fresh
validated-snapshot child launch policy. Both actual snapshots must match before
identity acceptance. This is a separately source-qualified new protocol; it
does not filter or relabel native02's failed identity/evidence. Parent/child cores
remain exactly equal, and future C/A equality is still required separately.

All other v2 limits, one-use admission, same namespace FIFO/live ancestry/group,
six-pair original camera/clock semantics, maps/module observations and finite
cleanup remain unchanged. New03native budget is explicit and never borrowed
from failed01/02. No weights, ORT, official-model calls, old scientific gate edits,
main merge or publication. Source/fixture review and exact4CIjobs precede sole
fresh request addition/push. Actual canary bytes need root+fresh acceptance.
SN-M1/M2 remain deferred with their recorded costs; no source review rereview.
