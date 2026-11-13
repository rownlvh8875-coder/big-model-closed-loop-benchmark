# Provider-free sealed renderer image Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. User selected no worktrees/implementer delegation and one whole-implementation fresh review.

**Goal:** Produce and independently verify one authentic sealed renderer dependency image without invoking a renderer/model.
**Architecture:** Closed immutable inputs, pure archive/API/launch checks, isolated stdlib collector and offline installer, bounded authenticated Actions worker and separate root preflight. Exactly three files in image artifact; raw execution evidence separate.
**Tech Stack:** Python3.11stdlib/unittest, existing pure metadata helpers, Docker CLI, pinned GitHub Actions.
**Spec:** docs/superpowers/specs/2026-11-14-engine-clock-sealed-image-design.md

## Global Constraints

Preserve55oldworkflows/alloldcode/tests/consumedrequests/raw/workspaces/nativeallowance0/16nullrefs/main. Renderer53lock052b6dd9… preserves full56lockec68e4d6… and actual fullinputlockf33c2558…. No installed/imported ORT or renderer/native/model calls. SourceCI+review precede newrequest/oneworker. Image/ZIP2GiB, installed3GiB, inventory4GiB/100k/16MiB/180s, identity128KiB, file512MiB, log1MiB, download300s, freeunion16GiB; finite controller/build/save/artifact budgets; no retries/fallback or automatic cap increases.

## Review Focus

Archive/config/registry digest classes and extra tag/platform/reference payloads must reject correctly. Source/API authentication and unique activation cannot be replaced by fixture metadata or environment assertions. Collector root alias/prefix semantics and closed byte budgets must hold before reads. Offline pip/stdlib bootstrap cannot process site hooks or import installed payloads. Docker/transport metadata and error logs cannot disclose tokens/proxies/Config.Env; preserve bounded partial/failure evidence without false readiness.

---

### Task1: Streaming image/archive/API/launch verification

Create scripts/engine_clock_image_archive.py and tests/test_engine_clock_image_archive.py. Interfaces: `inspect_save_archive(path:Path,*,expected_tag:str,deadline:float)->dict`; `validate_preparation(receipt:dict,api_evidence:dict,archive:Path,*,expected:dict)->dict`; `validate_launch(actual:dict,expected:dict,nonce:str)->dict`. Archive function onlyreadsdata; API funcs authenticate semantics of externally acquired proof, no network/Docker. Return native_admissionfalse.

- [x] Write owned legacy/OCI save fixtures covering exactconfig/layerdiffID/order/tag/platform and two-image/extra member/reference/digest-class/size/truncation/path/JSONduplicate negatives; add token/proxyConfig.Env sentinels to launch fixtures.
- [x] Run focusedRED; implement bounded streaming/noextract parser and closed semantic validators; GREEN. No downloaded image or Docker call in fixtures.

### Task2: Isolated candidate inventory and verification

Create scripts/engine_clock_image_inventory.py and tests/test_engine_clock_image_inventory.py. Interfaces: `create_inventory(root:Path,*,deadline:float)->dict` (candidate-only); `verify_inventory(root:Path,expected:dict,*,deadline:float)->dict` delegates immutable publiccollector; `verify_prefix(root:Path,observation:dict,*,expected_members:dict)->dict` checks actual fixed alias/plainparents/canonical bytes without native imports. CLI inside actual qualified container only, no import-time/automatichost scan.

- [x] Write temporary owned root fixtures reproducing requiredaliases/exclusions/emptyfiles/extrafile/mutation/symlinkescape/crossroot/deadline/perfile/aggregate/entry/JSON caps; assert inherited collector globals unchanged and pure source parity/composition.
- [x] RED then per-instance subclass/prefix and typedCLI/installedmetadata absenceORT integration withTask3. Candidate alone never accepted as prepared image. Stdlib-only version evidence labels contract cv2literal vs observedPython accurately.

### Task3: Offline installer, recipe and bounded host worker/preflight

Create scripts/engine_clock_image_process.py (bounded private/recorded subprocess streams), scripts/engine_clock_image_installer.py, scripts/engine_clock_image_preparation.py, corresponding focused testfiles, docker/engine-clock-sealed-image.Dockerfile, newworkflow .github/workflows/engine-clock-image-preparation-v1.yml. Installer APIs consume verifiedexplicitinput paths and typedroot; callbacks enable fixture-only pip/venv operations. Controller `--guard-only/--run/--preflight` modes separate source/oneuse namespaces; no automaticrun.

- [x] Write RED fixtures for closedrequest/sourceclosure/soleparentdelta/exactsourceCI/currentworkflowuniqueattempt, streamtransportwronghash/redirect/authhandling/diskunion/limits/failuremarker, fakeDocker commandsequence/config/alias/mount/exit/cleanup, installer targeting/no-site/no-network/no-source/noORT/asset subtree/payloadpaths, logsentinels and distinct artifacts.
- [x] Implement guards/transports/staging/derivativeartifactinput reconstruction; source-bound offline recipe, one build/save/candidate launch and later authentic root load/verification. Keep readonly/no-network/capdrop/security/namespace/mount/env constraints explicit. No live fixture packageinstall/Docker/native/network. Run GREEN; preserve55oldworkflow bytes and immutablehelpers.

### Task4: Source qualification and single actual preparation

- [ ] FullCPU suite; inspectclosures/scopelimits; one fresh read-onlyastra/medium/forknone wholebranchreview. One Important/Critical TDDfixpass/full ifneeded/no rereview; deferMinorwithcost. Keep ignoredprogressledger current.
- [ ] Commit/pushDraft/exactheadpush+PRCI allfourPASS/artifacts0. Resolve newworkflowidentity from actual firstmatchingevent rather than fake404zero. Register/pushonlynewrequest on freshremote branch with no previousruns; immutable consumedrequest afterward.
- [ ] One bounded actualworker build/save/candidate operation; preserve exact API/run/jobs/logs/artifacts/originalZIPs and executionevidence. No old retry or model/native call. Unsupported ends consumed; do not manufacture image/digest/readiness.
- [ ] Independently authenticate actual image/execution artifacts and savearchive; new localoneusepreflight only after authentication, exactDockerload/launch/installedmatch with finite costs. Promote actual accepted data on separateevidenceDraft; source reviewed/qualified/runtimehead remain distinct. No main/Cloud/registry publication or native handoff execution.

Execution-host addendum: independent preflight is a second, separately one-use Actions workflow .github/workflows/engine-clock-image-preflight-v1.yml/branch prepare/engine-clock-image-preflight-20261114-01. Root observed healthy localDocker but cannot establish private daemon data-filesystem capacity as UID1000/no sudo; no local image load is attempted. Add pure closed tree-archive verification fixtures for pre-start code/Python copies; no host payload extraction. Preserve originalDockerconfig; owned per-command offline config only. Both roles get the same final source/CI gate and distinct live request budgets; existing55workflows remain byte-identical.
