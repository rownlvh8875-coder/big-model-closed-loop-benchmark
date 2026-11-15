# New SDK Actions image authentication implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans. Inline same checkout; one fresh wholebranch review; no implementer delegation.

**Goal:** Produce and authenticate a NEW full SDK image without starting native payloads.
**Architecture:** exact reviewed-source/request-only activation; portable COPY-only/stopped Docker producer; external authenticated API transport and byte/layer/inventory acceptance. Preserve old modules/evidence and all runtime restrictions.
**Tech Stack:** Python stdlib,GitHub REST/TLS,GitHub Actions,Docker data operations,existing guarded tar/inventory parsers.
**Spec:** ../specs/2026-11-15-panda-sdk-image-auth-v1.md

## Global Constraints

Base16c690c0bfc586acf089ff15cb95431eb1412ca8;5798basefiles/299pins/10originals/main/Drafts102–114/8native histories unchanged. No native/SDK/GL/MetaDrive/model/provider/officialORT loading or container starts. No main/shared-base update/registry/Cloud publication/request reuse. Source branchfeature/panda-sdk-image-auth-v1; activationprepare/panda-sdk-image-20261115-01; requestonlydelta; workflowattempt1unique. Budgets/immutable input pins and inherited metadata limits exactly as spec; preserve failures/newoutputs, no shared cleanup.

## Review Focus

1. A self-consistent forged receipt/request/API dictionary must not grant external origin or native readiness; consumer expected source/run/activation comes from caller and live API.
2. Source activation changes or rerun/foreign/ambiguous workflows/artifacts must reject before any Docker operation/download.
3. Docker children cannot inherit credentials/loader endpoint injection or perform activation/publication; failed attempts retain output and cleanup stays owned/stopped.
4. ZIP/tar/decompression/metadata budgets and symlink/path/CRC/duplicate checks must hold before large allocations, including remote outputs.
5. SDK-only layer and full inherited file/link manifest bind actual candidate, while directory/runtime/host/driver/native authority remain absent.

### Task1: Closed policy and input/lineage validators
**Create:** scripts/panda_sdk_image_auth.py;tests/test_panda_sdk_image_auth.py.
**Interfaces:** request_template(source,ci,root)->dict;validate_request(r,root);validate_activation(r,head,commit,compare);validate_ci(r,proofs);validate_run(r,context,run,workflow,listing,completed=False);validate_artifacts(run,listing)->dict;expected_inventory(root)->dict.
- [x] RED changed SDK/base/hash/closure/permissions, bool-as-int, wrong/multiple CI/activation/foreign/rerun/workflow/artifact cases reject; real tiny fixture metadata, no native.
- [x] Implement exact pinned metadata policy and current source closure,record focused result,commit.

### Task2: Portable producer and authenticated consumer
**Create:** scripts/produce_panda_sdk_image.py;scripts/accept_panda_sdk_image.py;.github/workflows/panda-sdk-image-production-v1.yml;tests/test_panda_sdk_image_producer.py;tests/test_panda_sdk_image_acceptance.py.
**Interfaces:** production --run;accept(source_sha,activation_sha,run_id,out)->receipt;DockerData.run(args)->bounded record. Uses Task1 live validators and existing Client/guarded archive/export/SDK layer helpers.
- [ ] RED CPU child/pinned tool/env/timeout/forbidden verbs, closed3carrier ZIP + mismatched image/manifest/receipt/authority and failure preservation; real synthetic tar/ZIP fixtures.
- [ ] Implement only declared read/COPY/STOPPED actions, source-bound workflow/artifact upload, independent API acceptance; focused/fullsuite/static checks and preservation,commit.

### Task3: Review, actual one-use production and final closeout
**Create:** docs/STAGE7_PANDA_SDK_IMAGE_AUTH_{RESULT,LEDGER,CONTINUATION}.md;docs/evidence/panda-sdk-image-auth-01/;new activation request on separate branch only.
- [ ] Sole fresh most-capable wholebranch review, regrade,ONE Important/Critical TDDfixpass/fullsuite; ledger all rulings/minors, no rereview.
- [ ] OwnDraft/sourceCI exact source gates; new request-only activation; actual bounded producer attempt1; external run/artifact download/SDK/layer/inventory acceptance; retain all APIs/bytes/failures,never native.
- [ ] Commit final evidence/docs; ownDraft exact finalHEAD CI4jobs/attempt1/artifacts0/body/fresh preservation/finalreceipt; cleanup own scratch only. Report actual producer and remaining runtime/scientific gates.
