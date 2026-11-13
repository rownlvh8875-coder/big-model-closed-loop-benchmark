# Engine-clock local real-wheel verification and derivation

## Scope and authorization

Base `de30d68027162b4058e029b9687c5a198f1339b2` / Draft PR44. The user continued the explicitly stated next step: bounded actual official wheel verification/derivation. This operation uses the existing source-reviewed transform, its completed R1/R2 TDD correction and final726-test/4job evidence. No product code changes or package installation/import are required. The operation is a separate local package-input gate; it does not activate the inactive image/native proposal.

One new request authorizes at most one local attempt, four source fetches (release JSON, simple index JSON, PEP658 sidecar, wheel payload), one wheel payload download and one transform invocation. Claim a fresh output directory and attempt journal before the first fetch. Existing directory/attempt rejects; failures consume this request, retain bounded prefixes/receipts and terminate without retry, fallback, cap change or source adaptation. This is not reuse of any native allowance.

## Frozen inputs and source

Request schema `engine-clock-local-wheel-request-v1` binds exact constants: metadrive-simulator0.4.3, original filename `metadrive_simulator-0.4.3-py3-none-any.whl`, published size55128766, wheel SHA256 `c6f8a42baac939a0af53a8e1cd9d48ec2bf0051917e7c19083e156a6506493d9`, metadata SHA256 `4fb69fa54bb0e8118315aecdc482597af69798e17e47df3c57fbca50d4e7bcf6`. Fixed HTTPS URLs come from the saved PyPI binding; never follow URLs extracted from README/error text. Release and simple-index exact wheel fields must agree with each other and these pins before fetching the payload.

Bind transform/test/policy/saved metadata file SHA256 to the de30d68 Git objects and working bytes; record actual execution HEAD and request-file SHA separately. Any intervening tracked changes may be this increment's documentation/request only; no preexisting source/test/workflow/registry/proposal changes. The active execution HEAD is committed before network execution and differs from later evidence-only HEAD. The existing transform is imported only after source checks; package code remains opaque data. Record actual Python/curl versions, not proposed image Python3.11.18.

## Transport and storage

Use installed curl8.14.1 with inherited proxy/CA settings and TLS verification, `--proto =https`, no redirects, no retry, connect timeout10s, metadata max-time30s/file1MiB, payload max-time120s/file64MiB. Require exit0, HTTP200, redirect count0 and ssl_verify_result0. Persist only these selected transport fields, URLs, sizes and hashes; no headers/env/credential/exception dumps. Exact-size/SHA checks follow every fetch; metadata files are public response data treated as untrusted. Curl operation limits are client controls, not host/network attestation.

Require >=1GiB actual free space on the output filesystem before claim; this package-only storage minimum does not replace the future image16GiB requirement. Source<=64MiB, derived<=512MiB and metadata<=3MiB plus bounded receipts fit within that package reservation. Outer GNU timeout360s/kill-after10s bounds the controller process group; transform uses the unchanged cooperative180s cap and existing64MiB/256MiB/member64MiB/metadata1MiB/20000member/output-read512MiB policy. No larger input or hidden retry is allowed. Record actual source/derived file hashes, bytes, phase timings, self-process peak RSS on Linux and final retained file sizes. These measurements do not establish image feasibility or neutrality.

Download to new `.part` paths. Rename to verified original filename only after pin checks. Retain the source and derived files on success and partial bytes on failure. Write derived bytes only after transform success, using exclusive creation, flush/fsync and bounded hash verification of stored bytes. Do not extract/install/import the wheel. The transform's metadata/RECORD/CRC/raw compressed stream/payload preservation checks must succeed unchanged; unsupported actual WHEEL/layout is an authentic terminal failure for this request.

## Evidence and acceptance

The receipt identifies `CODEX_CLOUD_LOCAL_PACKAGE_INPUT`, actual source HEAD, request SHA, source-byte map, request/attempt IDs, transport fields and measured hashes. Distinguish locally measured wheel SHA from advertised metadata hash, policy-data hash and transform-source hash. Published-pin matching over the configured TLS route is not a publisher signature, upstream endorsement, independent host attestation or an Actions artifact/run association. No package/image/native artifact ID is fabricated. The transformer still reports source_origin_authenticated/implementation_authenticated/native_admission/execution_authorizedFalse.

Root verifies retained source/derived records and preserved-member counts/aggregate; a fresh independent whole-branch/raw-byte review accepts or terminates this local input checkpoint. No duplicate broad CPU suite is needed because product code is unchanged; final baseline CI remains required. Never change source/metadata/caps to repair an authentic one-shot failure during this request.

## Preservation and next gate

Keep producer70/workflows44/registry8, Task1/2/derivative code/tests/policy/proposal, prior evidence and all raw/controller workspaces fixed. No worktree, native engine/Xvfb/provider/GPU/clock/official model/ORT/image build-pull-load-run/Cloud publication/main merge. Existing generated SMALL ONNX CI is separate. All16 image preparation refs remain null/nativeallowance0; Task3 remains incomplete. Old ABBA terminalFAIL/7null/4cases6comparisonsNOT_RUN and strictFAIL/expandedNOT_RUN/geometry-optics-fullS limits/Stage7INCOMPLETE remain.

If accepted, next is complete genuine transitive Python/base/deb/asset input resolution and inactive image adapter design. A local derived wheel alone is not a complete lock, supported installed runtime, prepared image, launch proof or native admission. Any actual image preparation and native protocol retain their separate future gates.
