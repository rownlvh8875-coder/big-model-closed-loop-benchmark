# Retained GL read/resolve command provenance

## Intent and approach

The accepted sealed CPU pipeline still has equal sampled submissions/order with
differentRGB. Existing apitrace v2 compared draw inputs, but did not connect the
90blits pertrace to the60originalReadPixels calls. Extend analysis of those saved
bytes, not the consumed sealed cohort. Prior uniform/sampler/order studies stand.

Considered: newGLtracing would need a new qualified image/observer allowance and
perturb capabilities; GPU extraction already stopped image updates. Choose an
offline bounded command-provenance reducer. This is the executor's implementation
choice under the user's continuous inline/no-further-question preference.

## Inputs and boundaries

Use only retained on_0/on_1.trace (209757595/209758897B, SHA9665413782cbe05d0f5460c8983643b5cdf8e6d8415ad88f2a2e85f135136e9a /
6ddef5fc8a2c29d6f296e991fe32322b22d73a38dfd86f8764e78990622d3192),
original native JSON/receipts and existing pinned apitrace11.1 offline decoder.
Verify decoder binary against its retained Debian package. Permit only `dump`
thread metadata and `pickle` decoding, never replay/trace/nativeGL/provider/model/ORT.
Restricted unpickling permits only unpickle.Pointer mapped to a private int class.
Reject unknown globals, incomplete records, missing/ambiguous argument fields,
nonmonotonic calls, unsupported shared contexts/multiple GL threads and missing
context. Bound120000calls/2GiB decodedpickle/128MiB textualmetadata/1MiB textline,
20000nodes/256objects perkind-context/256reads/16MiB finalJSON/120s eachdecoder;
individual pickle read request512MiB (actual pinned CPU texture blobs include507510784B).
Preserve all original files/299sealedsourcepins/consumedrequests/main. No native
allowance is created. Same checkout, own branch, no additional worktree/delegation.

## Reducer

Track independent context namespaces, object kind+name+lifetime, 2Dtexture levels,
renderbuffer storage/samples, FBO read/draw bindings and selected color buffers,
attachment changes, original reflected sampler type/location/unit bindings and
active texture bindings. Texture1/renderbuffer1 are distinct; deletion/name reuse
must not alias prior objects. Shared contexts are explicitly unsupported.

Emit command nodes for storage/CPUuploads, potential framebuffer clears/draws,
blits and mip generation. Snapshot dependencies before updating outputs so a
texture feedback binding refers to prior command state, not a graph cycle.
Keep previous image/family dependencies conservatively: partial writes, masks,
scissor, depth tests and undefined GPU data are not simulated. Mipmap generation
does not overwrite level0. Samplers use a conservative texture-family dependency;
readback uses the selected exact attachment/aspect. Unsupported writer operations
must reject, not disappear into a complete report. Unknown pixel contents stayunknown.

Record glReadPixels source attachment and last potentially-writing command; derive
bounded RGBdraw→sampledHDRtexture→resolveblit→MSAArenderbuffer routes when present.
Preserve observed clear/scissor/masks/rectangles/filter/samples. Route equality is
not equality of all draws/uniforms/pixels or execution/completion. GPU read arguments
contain pointers, not returned pixel blobs; never hash a pointer as image contents.

## Results and acceptance

Decode both authenticated whole streams; record unsupported coverage and counts.
Compare routes per original marker/read ordinal, leaving host primary10frame mapping
explicitly inherited schedule evidence. Do not join older traced frames to the newer
sealedC/ABBA by ordinal, clock, hash or assumed GPU identity. Trace ON hides program
binary formats and changes timing; untraced equivalence/unique cause remain unproved.

Test pure reducer with real normalized synthetic events; test restricted decoder,
thread/byte/node budgets, nested namespaces/lifetimes, partial/mipmap/feedback,
unobserved pixels and unsupported calls. Full suite then one fresh whole-branch
review; one Important/Critical TDD fix pass, no rereview/minor polish. Same reviewer
also independently checks retained actual read/blit route samples, no second agent.
Retain spec/plan/ledger, code/tests, report/source/input hashes, actual data receipts
and all rulings/costs in own Draft/exact-headCI. Originalstrict0/4FAIL/Stage7INCOMPLETE;
newnative/GL/provider/model/ORT0. No main merge or Cloud/registry publication.
