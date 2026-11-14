# Retained GL read/resolve command provenance

The two retained apitrace v2 ON streams have the same recorded routes for all60
original readbacks each. Their original10-frame primary source RGB timelines still
differ at3Road and8Wide positions under the inherited host schedule. No new native,
GL,provider,officialmodel or ORT execution occurred. Originalstrict0/4FAIL and
Stage7INCOMPLETE persist; this is no renderer repair or current sealed-frame proof.

## Newly measured command boundary

The earlier study compared draw inputs. This analysis adds attachment lifetimes,
read/draw framebuffer selections, recorded sampler reflection/unit dependencies,
potential write histories and resolve blits leading to originalReadPixels.

| Recorded route,30reads per camera per trace | Read attachment | RGB program | Sampled HDR texture | Resolve source→destination | Color source |
| --- | --- | ---: | ---: | --- | --- |
| Road | FBO8,texture5 | 7 | 2 | FBO3→FBO2 | renderbuffer4,requested4samples |
| Wide | FBO9,texture6 | 7 | 3 | FBO5→FBO4 | renderbuffer7,requested4samples |

Resolve rectangles are964×604,filterGL_NEAREST,mask17664(color/depth/stencil).
Both full streams include90blits,60reads,2901draws,249clear calls,336CPUupload/storage
nodes and26mipmap-family updates. Objects are separated by context,kind,name,lifetime
and storage generation; texture1 and renderbuffer1 never alias. All operations occur
on one recorded GL thread0; there are two unshared recorded contexts.

The first Road route is read8739←RGBdraw8709←texture2←resolve7843←FBO3/renderbuffer4.
All60 paired routes match selected topology/storage/scissor metadata. This excludes
geometry order, complete raster/vertex/uniform inputs, actual sampled LOD and GPU
contents. Samples above are storage-call requests, not a new measured sample query.

For the old primary host schedule, first Wide mismatch corresponds to reads37381/
37387; Road first differs at step7. These associations remain fixed-schedule evidence.
The trace records destination pointers, not returned pixel blobs or explicit host
capture nonces. It cannot be joined to the newer sealed C/ABBA by ordinal,clock or
assumed physical frame. Equal routes do not prove equal executed writes or pixels.

## Reproducibility and limits

Both original trace SHA/size pins match retained receipts:

| Trace | Bytes | SHA256 |
| --- | ---: | --- |
| ON0 | 209757595 | 9665413782cbe05d0f5460c8983643b5cdf8e6d8415ad88f2a2e85f135136e9a |
| ON1 | 209758897 | 6ddef5fc8a2c29d6f296e991fe32322b22d73a38dfd86f8764e78990622d3192 |

The pinned decoder binary SHA b41db446641250045e94645a94b507345bfcec6e5a2d7e7224348a5a80544274
matches its retained Debian package payload,package SHA0b7212fd6a0fa9ce488abec7358cdfe99aba50817eca02aa5c493e686bcec3aa.
Only offline dump/pickle commands execute, with restricted Pointer-only unpickling.
No tracer,GL context or replay starts. Full verbose thread metadata and pickle counts
agree at106555/106580calls; default dump omits6021calls inON0 and is rejected.

Decoded pickle bytes978935426/978937188 are bounded by2GiB pertrace. The largest
observed blob is507510784B; per-request cap512MiB. This can require substantial
transient memory and establishes no RSS or headroom. Each full graph is under16MiB.
Unsupported writers,shared contexts,multiple GL threads,incomplete calls and exhausted
budgets stop analysis. Possible writes keep earlier dependencies conservatively;
partial clears,feedback bindings and mipmap generation are not pixel simulation.

Successful whole-stream analysis05 took32.334334439s wall and20.660532352s parentCPU.
Pertrace wall17.463446647/14.861799933s. ParentCPU excludes decoder childCPU. These
scopes exclude earlier failed/debug analyses,tests/review/CI and are neither tracing
overhead nor end-to-end development cost. Four failed offline attempts are retained:
argument-name mismatch,64MiBcap,256MiBcap and missing verbose metadata. No native retry.

The old tracer hides program-binary formats and perturbs capabilities/timing. OFF
has no GL trace. Neither untraced equivalence, GPU completion, actual fetch execution,
unique cause nor physical runtime identity follows. Previous sampler/feedback/order
findings stand; their cohorts were not rerun. The consumed sealed allowance stays0.

Actual full graphs remain under `output/stage7-gl-read-provenance-05/`,12.7MB combined,
with exact SHA descriptors. [Evidence index](evidence/gl-read-provenance-01/proof-index.json),
[machine result](evidence/gl-read-provenance-01/result.json),original receipts,
per-read/blit records and failed analysis receipts are versioned. All299previous
source pins are independently byte-verified unchanged. These are retained local
receipt associations, not newly authenticated remote native artifacts.

Concentrated tests31PASS; full suite1316tests/7skips PASS116.057s. Whole-branch
and independent saved-route review is pending. See the [ledger](STAGE7_GL_READ_PROVENANCE_LEDGER.md)
for decisions/costs. No main merge or Cloud/registry publication.

The remaining observation gap is generated atlas/HDR contents and an explicit
capture→graphics-command→returned-pixel association in a newly qualified scope.
Design that boundary before spending another native allowance; do not reuse
consumed requests or repeat naive texture extraction.
