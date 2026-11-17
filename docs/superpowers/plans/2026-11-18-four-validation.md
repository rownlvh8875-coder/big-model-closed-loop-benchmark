# Four validation and laptop execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Execute four scoped validation tracks when resources exist and provide a truthful laptop-ready path for externally blocked tracks.
**Architecture:** Shared fail-closed resource/evidence contracts, an independent full-S loop preserving original policy/camera plus existing action bridge, and bounded authenticated hosted adapters. Additions only to frozenPR144base.
**Tech Stack:** Python3.11stdlib/NumPy/OpenCV, existingMetaDrive0.4.3/Panda1.10.13/SDK3, ORT1.20.1, frozenDocker, GitHubActions.
**Spec:** docs/superpowers/specs/2026-11-18-four-validation-design.md

## Global Constraints
Base8380e8a immutable/additionsonly; no mainmerge/environment/registrypublish/realvehicle/CAN/CD210/Carrottuning/rankings. Models ephemeralhosted or explicitlyinvokedlaptoponly; nolocalPanda/SDK/model loads. OfficialweightsSHA35976/768750198B, imageb9d6/SDK27cd/core8b03 andterrainadapter16aafa unchanged. Fixed8m/s/.05s/.12/.9m/max600;8freshmodels/max4800inferences. llvmpipe2worker issoftwareonly. 3600child/3630launcher/7320pair/7380container/150minjobs,10GiB2CPUpids128. Exact4sourceCIjobs before request-onlyactivation. Missing externalresources remainblocked.

## Review Focus
1. Missing/inaccessible laptop devices, endpoint or physicaldata silently treated as a passed verification; exercise allfourstate aggregation.
2. Fullroute terminal overshoot, reversed/ambiguous native joins, lane departure or empty/prefix result fabricates completion; test boundary and invalid path.
3. Parentmodel FRD outputs altered, bridge applied twice, truth entersmodel/control or recurrentstate resets across segments; test exactfeed/action/step traces.
4. Timeout/lostchild/mid-inference failure produces falsezero/exactcounts or failsownedXvfb/containercleanup; testtruthfulbounds andownership.
5. Mixedsource/driver/weights/case/artifact or requestedMSAA/sourcepinhole values promoted to actualhardware/physical/CARLA completion; testcounterfeit/incompleteevidence.

### Task 1: resource contracts and laptop preflight
Files:new bigbench/validation_resources.py, scripts/validate_laptop_environment.py, tests/test_validation_resources.py.
Interfaces:collect_resources()->dict observations; resource_gates(report)->dict fourtrack readiness; aggregate_validation(reports)->dict actualcomplete states. No actualsim/model atpreflight.
- [ ] RED tests:softwareGPUvsdevicepresence, missing/inaccessibleCARLA/calibration, malformedcounterfeitpass, Windows/macOS/Linux safecommandvectors, noautomaticinstallation.
- [ ] GREEN stdlib read-onlycollector/CLI; coldhelp/preflight workswithoutPanda/ORT andwritesJSON requestedpath; preserveprivacy. ExpectedfocusedtestsPASS.
- [ ] Run actualCloudpreflight, retain rawmetadata/deviceabsence/GitHub403distinction; commit Task1.

### Task 2: full-S protocol and original policy boundary
Files:new bigbench/full_s_validation.py, tests/test_full_s_validation.py.
Interfaces:run_full_s(policy,camera,lanes,*,seed,scene,max_steps=600)->dict fulltruthfultrial; route_state(lanes,index,state)->dict exactprogress/truth/terminal; compare_full_s(a,b)->dict strictrepeat separatefromtraversal.
- [ ] RED purefake-lane/model tests:twobends+connector complete, terminalovershoot, firstlane/prefix/stepbudget/departure FAIL, ambiguous/discontinuous/repeatedlanes reject, rawmodel/bridge/clock/feed preserved, uncertain inferencefailure bounds.
- [ ] GREEN independentfixedspeedloop usingoriginalcamera/policyinterface andexistingWorldFramePolicyAdapter; captureoriginalhashes/audit/bridge/progress; noGTcontroller. ExpectedfocusedtestsPASS; commit.

### Task 3: native geometry/virtual optical and full-S adapters
Files:new scripts/sdk3_four_validation_native.py, scripts/sdk3_four_validation_runtime.py, scripts/run_sdk3_four_validation.py, corresponding3testmodules.
Interfaces:owned nativechild/pair modes; immutableimage/SDK stage; nativeprobe rawreports/geometry/sourceRGB; fullSreports; hostvalidate_geometry_optics()/validate_full_case() consumecontracts and regenerategates.
- [ ] RED coldhelp/importfences, exactcommands/resources/driver/modelSHA/actionbridge, rawpixel/lens/coverage/source/context negatives, processownership/counttimeout tests.
- [ ] GREEN ownedzero-modelnativeprobe4cases/twoposes; newownedfullS2children, lifecyclebounds; hostsource/artifact authenticators andindependentreceivers; nooriginalproducerchanges. Expectedtests/actionlintPASS.
- [ ] New workflow .github/workflows/sdk3-four-validation-v1.yml:probejob, gated4fullScases; alwaysrawupload, fixedrequestactivation path. Commit/pushfeature/DraftPR; requirecanonicalpush+PR4jobsPASS.
- [ ] Freshactualrequest; independentlyreceiveactualzero-modelprobe. Ifqualifiedrate, runfreshfullS4cases; otherwise recordblockedwith0actualmodels. Savealloutcomes withoutretry/outcomeselection.

### Task 4: laptop orchestration and external tracks
Files:new scripts/run_laptop_validation.py, docs/LAPTOP_FOUR_VALIDATIONS.md, tests/test_laptop_validation.py; externalinputschemas asneeded.
Interfaces:explicituserexecution paths resourceprobe/full-S/physicalcalibration/CARLA/hardware; commonmachine-readablereports. OS-specificinstructions baseduseranswer, noautomaticresourcepurchase.
- [ ] RED externalinputsabsent blocked;softwareGPU/MSAArequestnotactual reject; invaliddatasetprovenance/holdout/missingCARLAowner notPASS; nohiddenmodeldownload orworldmutation inpreflight.
- [ ] GREEN runnableexplicitcommands foravailablebackends, strictmissingrequirements forunavailable ones, privatecalibrationdata stayslocal. Executeactualsupportedchecks; neverlabelruntimechecker asfullvalidationPASS.

### Task 5: independent review and closeout
- [ ] Rootindependentlyregeneratesactualfourtrackstate/traversal/repeatgates anddistinguishesblockedresources; preserveprevious3taskevidence.
- [ ] Singlefreshwholebranchreviewbase838..HEAD withReviewFocus/spec/ledger; oneImportantRED→GREENfixpass, Minordefer/no rereview.
- [ ] FinalHEAD4canonicalCIjobs/fullcounts/DraftPR/sourceparent/main/originalpreservation; archiveledger/allrulings/exactexternalreceipt, deleteonlyownscratch. Preserveworktree andstateforlaptop followup. FinalhonestactualPASS/FAIL/BLOCKED pertrack withprecise nextrequirements.
