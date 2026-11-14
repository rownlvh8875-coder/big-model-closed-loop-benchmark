# Native evidence and private cache boundary

Native03source74d3f1ae44750e9d1c373e81016a7ca092da1a87/run43539772433/
job132277351673 FAILED137.869755572s at one-native-canary. Upload then failed
EACCES scanning root-owned execution/cache/case_00/mesa_shader_cache even though
the glob excluded it. Actual original API confirms0artifacts. Native/case cause
is UNKNOWN, provider bounds[0,1], no native acceptance; do not invent results.
Original API and failed job log are retained, consumed03never rerun.

The observed failures exposed an architecture flaw: private cache shared the
artifact walk root. V4physically puts it at operation/native-cache beside
execution, not below it. Container mapping stays /work/cache; fresh cache policy,
permissions, budgets and bounded terminal inventory remain unchanged. Upload
targets execution only, with no cache exclusion glob. No chmod or cache byte
mutation to make it uploadable. All raw native payload writers use ordinary
readable files; private Xauthority stays in container /tmp. A real temporary
fixture with an inaccessible cache subtree must prove artifact root walking
cannot reach it.

V4also retains a bounded redacted failure summary in the outer result/log even
when artifact upload fails: phase status, stage, child/case errors and provider
bounds only when an available phase/case is bound to this source-qualified
request and nonce. Otherwise preserve unknown[0,1]. It is diagnosis only, never
a substitute for original image/case bytes or acceptance. Read files nofollow,
regular/single-link,<=2MiB; redact outer secret values/credential URLs before
printing. No arbitrary Config.Env or full process output. Invalid/missing files
produce a fixed unavailable code, never a new failure replacing original cause.

Image006/v1–v3/requests01–03/raws remain frozen. Newsourcev4/request04 and full
derived closure include failed03authority. Exact source4jobs/fresh sole request
addition/push and one read-only source review precede one new six-pair allowance.
No old request retry or unused allowance reuse. All v3 launch/pre/post-cv2/FIFO/
identity/native/cleanup limits unchanged. No model/ORT/weights/merge/publish.
Native04still needs original artifact+root+fresh acceptance; scientificFAIL and
Stage7INCOMPLETE remain. SN-M1/M2 deferred costs remain explicit.
