# Bounded renderer task callbacks linked to camera calls

The accepted03 clock/Texture signatures do not distinguish RGB. Older PSSM/Chase
profilers already measured actual callbacks, but are unbounded, are not linked to
the sealed03 camera call ledger, and do not establish normal return on exception.
Do not repeat those old experiments or infer a unique PSSM cause.

Build a separate CPU-tested observer, preserving all261 frozen producer files.
Compose with engine_clock_boundaries.camera_clock_scope: install the callback
step wrapper first, then the clock scope; obtain explicit active call/camera
association from that clock trace. Install sys.setprofile only around each
original taskMgr.step. Match exact bound Python code AND self identity for
PSSM.update/MainCamera._chase_task. Observe call and return, pose and two-split
MVP. Require the known task.cont return; profile return events alone also occur
on exception and are insufficient. Preserve first failure even if Panda catches
it. Missing, duplicate, nested, foreign, thread-crossing, malformed or over-budget
events cannot produce complete evidence. Preserve original arguments, return
identity, exceptions, step count, callback methods and task registration.

OFF uses the same step association wrapper, no callback binding, profile install
or renderer snapshot. Its events are null/unobserved, never empty measured data.
ON has exactly two nonoverlapping callbacks/four boundary snapshots per step,
at most12steps/48snapshots. No file I/O, native imports, shader changes, task
removal, extra frame/tick, RAM/GPU readback or clock getter inside this observer.
All original steps return through their existing path; callbacks may occur in
either order, which is measured. Snapshot observations are non-atomic and intrusive.

Add a structural engine adapter using already-admitted supplied classes, never
importing Panda/MetaDrive locally. Verify exact engine.pssm/engine.main_camera and
camera ownership; copy existing two-split MVP to private aligned matrices and read
WORLD position/HPR. The adapter names35 getter-method calls per snapshot (2pose,
1MVP-array,32cells), with2private matrix allocations/assignments and vector/array
indexing accounted separately; this is not an exhaustive C++ API-call count.
Existing clock and Texture observers would be common to both future arms.

Authenticate target Python source as data from the retained headless wheel against
its pinned SHA and accepted image006 installed manifest, including base_engine,
main_camera,pssm,base_camera. Record AST callback ranges/source hashes without
executing downloaded code. Synthetic tests remain synthetic, not native admission.

This increment completes the observer, structural binding and pinned source audit.
Actual sealed runtime composition, new source closure/allowance and native canary
remain required before any native execution; no new request/workflow activation
is introduced here. Strict0/4FAIL/Stage7INCOMPLETE remain. User authorized continuous
inline execution and own Drafts, no additional worktrees/main merge/publication.
