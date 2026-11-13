# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과

이번 연속 작업은 source 구현·독립 검토·실제 준비 작업·원본 검증·추가 FD 결함 수정까지 진행했다. 실제 준비는 격리 네트워크 loopback 설정의 RTM_NEWADDR/EPERM으로 종료돼 대상 입력 전송과 Python/bootstrap/progressbar build/smoke가 미실행이다. 요청01은 소비됐고 재실행하지 않았다. **Stage7은 INCOMPLETE**이며 source-only 시험 통과를 실제 빌드 성공으로 바꾸지 않는다.

## A. 저장소·변경·검토 대상

저장소 `rownlvh8875-coder/big-model-closed-loop-benchmark`.

| 대상 | 실제 HEAD / branch | 검토 위치 |
|---|---|---|
| 승인된 원본 builder source |b0bfc46a8fb151897cec8f9db47965a39af66944 / feature/engine-clock-builder-staging|[Draft PR50](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/50)|
| 실제 준비 producer |78deaec1a3158889f0f90ede159b9466bfc9b194 / prepare/engine-clock-builder-20261113-01|한 번 push 후 불변, 새 요청01|
| 원본 실패 evidence |a103c1ebe4611bb859336c4bb7dbe3f88e485aa9 / evidence/engine-clock-builder-preparation|[Draft PR51](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/51)|
| FD 수정의 실제 독립 검토 |31578499df046fb6c27a0d69cc2ef4ad7b2af48f / fix/engine-clock-builder-probe-fd|이후 최종 metadata HEAD/실제 Draft·CI는 해당 branch PR 본문과 최종 응답에 기록|

구현은 nofollow/FD filesystem staging·검증, 닫힌 namespace 실행·output 처리, offline driver와 source-before/source-after manifest, 엄격한 wheel 검증, quota-bound tmpfs와 원본/부분 workspace 보존이다. 파일별 내용과 범위는 [source 결과](STAGE7_ENGINE_CLOCK_BUILDER_STAGING.md), [실제 준비 결과](STAGE7_ENGINE_CLOCK_BUILDER_PREPARATION.md), [FD 수정 결과](STAGE7_ENGINE_CLOCK_BUILDER_PROBE_FD.md)에 있다. 마지막 수정은 `scripts/engine_clock_builder_preparation.py:382`의 intended root/build FD 전달과 실제 trusted-child fstat 회귀다.

Source 전체 독립 검토96e97dc는 C0/I5/M2였고, root의 단일 Important TDD pass9aaca760/843fb749로5건을 닫았다(독립 재검토 없음). 별도 FD delta 검토31578499는 C0/I0/M1이며 이전 pass의 재검토가 아니다.

## B. 실제 검증·Actions·artifact

로컬 최종 FD 회귀1/0.029s, builder 집중90/1.355s, 전체816/69.171s PASS(선택 의존성7skip). 실제 자식의 device/inode를 확인한 source-only 결과이며 namespace나 다운로드한 target 도구를 실행하지 않았다.

| 구간 | 실제 run | 실제 작업·결과 |
|---|---|---|
| 예비 source3ee2954 |push43385193041 /PR43385200004|각814unit/7skip+1generatedSMALL,4jobsPASS,attempt1,artifacts0; 과거 기록|
| 최종 승인 sourceb0bfc46 |push43386207237 /PR43386214092|각815unit/7skip+1SMALL,4jobsPASS,attempt1,artifacts0|
| 활성화78deaec basic CI |43389231245|unit131764894624:815/69.020s/7skip; SMALL131764894028:1/0.058s,2jobsPASS/artifacts0|
| 실제 preparation |[43389231348](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43389231348)|workflow417016407/job131764894606/attempt1,FAIL,artifact1|
| evidencea103c1e |push43393226827 /PR43393234067|unit131777887936:815/67.041s/7skip +SMALL131777888507:1/0.081s; PR unit131777912028:815/45.962s/7skip +SMALL131777912444:1/0.068s;4jobsPASS/artifacts0|
| FD 최종 metadata HEAD |commit 후 해당 Draft에서 실제 관측|본 파일의 사전 commit 시점에는 CI를 선기입하지 않음; 최종 응답/PR의 실제 run·job·count가 기준|

Preparation은16:55:25~16:55:46 KST(21초 run metadata 구간). guard·pinned helper setup·tmpfs/disk checks는 통과했으나 trusted-host true preflight가 실패했다. 보존/upload는 성공했다. Artifact14019513519는582689B/SHA977a9e8c3432e51ef0696b3793aa447f72be6ab41b19e58a37de237ba133ce62로 원본 API digest/size와 일치한다.

5개 ZIP 파일, 단일 gzip EOF/CRC와 zero-only TAR tail,120항목(91files/27dirs/2links/1241638regularB)을 모두 검증했다. 내부 gzip527425B/SHAafca2bf16d2afcbc4c94207a823ee16f18b824ce372f55cfe576248996b9fc5d; physical TAR1331200B/SHA18381b66fc67ec80a971491278356e80cefce9f570a2a851d4697801a099a09d. 원본 API/log/ZIP/decoded TAR/top-level extraction은 `output/stage7-builder-preparation-evidence/43389231348/`에 보존했다. Source/CI log 원본은 `output/stage7-builder-source-ci/`에 있다.

## C. 확인한 사실·미확정 사항

Source28파일과 원본 request가 승인 b0bfc46, 실제 producer78deaec 및 원본 GitHub tree와 일치했다. 실제 helper0.12.0 binary SHA c09c5c5d549cb18ddf3e6f780a718d0a4b1e15039be1a1e220f8c82300521730, source archive126452B/SHA9760d007, 빈256MiBtmpfs와 available disk91974352896B를 확인했다.

stderr61B/SHAed3471f7900377f86150471417911309833a36d664cb5af7409e139103f67ddf는 보존된 공개 network.c182 literal+C-locale errno1 메시지와 정확히 일치했다. 실패 지점은 loopback RTM_NEWADDR/EPERM이다. 정확한 host/kernel/LSM/capability 정책 원인은 미확정이며 user namespace 전체의 지원 여부를 일반화하지 않는다. 실제 probe를 재실행하거나 raw stderr를 다시 수집한 결과가 아니다.

추가로 발견한 PF1 FD 누락은 별도 source-only 수정했다. 관측 network 오류보다 나중의 bind 처리 문제이므로 이번 실패의 원인이나 해결로 바꾸지 않았다. Fixture와 source delta 검토는 실제 backend/Python/bootstrap/build 성공 증거가 아니다.51개 component 입력109285137B는 등록값이며 이번 실제 전송은0B/0건, target launch0, staging/build/smoke NOT_RUN, wheel SHA null이다. 명시적 receipt와 검증된 code flow/workspace로 확인했으며 기록 부재만으로 수치를 만들지 않았다.

## D. 보존한 gate·제한

기존 producer70/old44workflow bytes/consumed registry8/legacy tools·tests·policies·proposal과 모든 기존 raw/controller/review workspace를 유지했다. 새 provider-free workflow를 포함한45개 workflow의 byte도 FD 수정에서 그대로다. 활성화 branch는78deaec에서 불변이다. 기존 canary/ABBA/unused4cases/native/model/ORT/default/render/clock 실험을 재실행하지 않았다. Generated SMALL baseline CI는 별도 허용 범위다.

old16image refsnull/nativeallowance0, strictFAIL/expandedNOT_RUN/ABBA authentic terminalFAIL/geometry-optics-fullS/Stage7INCOMPLETE가 유지된다. Main merge와 Cloud 게시를 하지 않았다. Component 실패 기록은 full-lock/image/native admission을 열지 않는다. 새 실제 실행에는 지원되는 격리 전제와 별도로 검토한 새 프로토콜/요청이 필요하다.

## E. 판단·비용·유예 기록

아래46개는 이 연속 작업의 source→operation→source-only FD ledger 순서다. 각 항목의 cost는 판단이 틀렸을 때의 비용이며, source-only 검증을 runtime 인증으로 바꾸지 않는다. 유예 Minor는 M6(controller review-SHA 외부 binding), M7(reusable deadline 최대값), FD-M1(과거 검토 시점의 완료 문구)이다. 실제 source/CI 기록을 후속 audit/PR에 남겼으며 과거 checkpoint를 재작성하지 않았다.

1. [source] User explicitly requests continuous work and final-only review; proceed inline without choice/approval menus, with only concise mandatory progress updates — existing authorization covers own Draft/basic CI — cost if wrong: more work may need later scope review.

2. [source] Current checkout/new branch and all original/partial workspaces preserved — user preference overrides worktree/cleanup defaults — cost if wrong: reduced isolation and disk retention.

3. [source] Local trusted-true namespace discovery failed readonly UID mapping; select a separately reviewed remote provider-free job instead of local downloaded-code execution — mandatory isolation cannot be relaxed — cost if wrong: remote setup/provenance work and possible separate backend failure.

4. [source] Normalize builder-only ownership/modes and generated files explicitly, retaining all source bytes and old main inventory rules — single-user readonly sandbox needs a concrete recipe — cost if wrong: normalized permissions or generated config can change behavior and must fail/revise before admission.

5. [source] Keep bounded untrusted logs only as byte counts/hashes/fixed errors — environment/secret sentinels must never persist — cost if wrong: terminal failures provide less textual diagnosis.

6. [source] Old44workflows remain byte-identical; inactive template now, later separately registered narrowly gated new provider-free workflow allowed — latest continuous authorization and original GitHub Actions scope support necessary remote preparation — cost if wrong: an extra ephemeral job/host dependency setup may be unnecessary; no main/Cloud publication is granted.

7. [source] Increase new builder per-file write limit from1MiB to4MiB, retaining wheel1MiB and tmpfs256MiB — authenticated ensurepip source copies its bundled pip wheel2110226B to temporary storage before installation;1MiB would guarantee a false bootstrap failure — cost if wrong: each writable file can consume3MiB more within the unchanged aggregate tmpfs quota. Static tar read only; no execution.

8. [source] Remote primary host setup builds pinned bubblewrap0.12.0 from official release archive126452B/SHA9760d007363e3abba7c747489910f9f82d9fca53ba3bd3282e396fa3c97a3314 and installs it at the standard ephemeral /usr/bin/bwrap path before any target input/source execution — Ubuntu24.04 bubblewrap0.9 source demonstrably lacks mandatory --ro-bind-fd; knowingly choosing it would waste the one-use operation — cost if wrong: extra trusted host build dependencies and setup work; no local downloaded-code execution or post-failure fallback. Host build source is a separate pinned setup input, not target runtime/library provenance.

9. [source] Accept I1/I2/I4 as one coherent build-protocol repair: exact pip wheel supported options plus an owned unpack hook before source metadata/build, with bounded per-file before/after evidence — pinned CLI/layout inspection proves current commands fail and snapshots are incomplete — cost if wrong: tighter coupling to pinned pip internals; fail unsupported layouts rather than silently continue.

10. [source] Accept I3 with conservative rejection of nonleading parent components and canonical output-chain validation — POSIX link semantics differ from lexical cancellation — cost if wrong: some otherwise valid POSIX link layouts are unsupported; all real52source metadata must still compile.

11. [source] Accept I5 with a sole predeclared host tmpfs256MiB, verified and bound by FD as /build, plus bounded retained archive/inventory for raw inputs, partial roots/build and host-helper workspace on success/failure — an internal-only tmpfs cannot survive namespace exit — cost if wrong: privileged primary host mount setup and larger evidence storage; no local mount or post-failure fallback.

12. [source] Raise new outer evidence budget from16MiB metadata-only to1GiB, with retained gzip<=900MiB/decoded<=800MiB/40000nodes/file128MiB — preserving actual352MiBroot+110MiBinputs+256MiBbuild requires a concrete bounded package — cost if wrong: additional transfer/storage; artifact cap failure stays terminal/incomplete, never claims full preservation.

13. [source] Defer M6: controller reviewed_source_sha remains informational unless independently established; preregistration/external consumer must bind reviewed/qualified source commits and exact closure before activation/admission claims — source execution HEAD/closure still gated — cost if wrong: readers may overinterpret a syntactically valid review SHA.

14. [source] Defer M7: public staging guard maximum is not enforced internally beyond finite deadlines; controlled operation supplies180s and bounded job runtime — minor reusable-API issue is outside this Important-only pass — cost if wrong: an uncontrolled future caller could request a longer staging deadline.

15. [source] Review decline — Actual namespace/quota/startup: accept bounded scope because must be proven by the separately registered remote capability/target run — cost if wrong: unsupported backend may terminate without a wheel.

16. [source] Review decline — Actual build/smoke success: accept bounded scope because source fixtures cannot certify downloaded target execution — cost if wrong: a genuine runtime/build failure may remain.

17. [source] Review decline — Complete bubblewrap/kernel security: accept bounded scope because review covers the fixed recipe and pins, not an exploit-resistance certificate — cost if wrong: unknown host/kernel weaknesses remain outside assurance.

18. [source] Review decline — Aggregate memory/PIDs/same-user interference: accept bounded scope because claims stay per-process plus tmpfs quota, with trusted ephemeral host — cost if wrong: shared-user interference or aggregate pressure can still fail the job.

19. [source] Review decline — Administrator-proof global replay: accept bounded scope because history-deletion resistance is explicitly excluded; unique run/attempt checks are bounded — cost if wrong: an administrator can invalidate assumptions outside this protocol.

20. [source] Review decline — Publisher/build attestation: accept bounded scope because pinned bytes/API digest agreement are not cryptographic build/publisher attestation — cost if wrong: supply-chain trust remains in the selected origins.

21. [source] Review decline — Future full lock/image/native/model/science: accept bounded scope because these gates remain separate and false/incomplete — cost if wrong: component success cannot imply benchmark correctness or native admission.

22. [source] Review decline — Legacy scientific re-execution: accept bounded scope because prohibited consumed protocols remain unchanged; CPU fixture evidence is sufficient for this source review — cost if wrong: old scientific uncertainty remains unresolved.

23. [source] Retention certifies available workspace contents at postflight, not every transient file ever created or survival after abrupt runner loss — upstream ensurepip/build tools may clean internal temporary copies while authenticated originals and before/after source manifests are retained — cost if wrong: a sudden runner loss or upstream transient state can remain unavailable; mark missing/incomplete evidence rather than infer success.

24. [source] Complete I5 disk-capacity precondition with measured host available bytes>=1GiB before any component input transport; preserve insufficient-capacity facts — the immutable build policy explicitly requires this minimum and retention needs real disk capacity — cost if wrong: the preliminary source CI becomes historical and exact-final-source checks must run again; no target request was consumed.

25. [operation] Continue inline through the separate operation under the user's explicit continuous/final-only instruction, overriding skill plan-review/choice handoff — execution method and authorization persist — cost if wrong: additional reversible work/ephemeral job must be reviewed later.

26. [operation] External preregistration binds actual reviewed96e97dc, qualified9aaca760/843fb749 and approvedb0bfc46 source/code/CI closure before activation and independent consumption — deferred M6 is informational inside the controller — cost if wrong: an inaccurate external binding could undermine source provenance; no native/image admission follows.

27. [operation] One exact preparation-branch push adds the45th workflow while old44bytes remain fixed; all later evidence uses a separate branch — reviewed template plus prior Actions/continuous authorization cover this provider-free job — cost if wrong: one extra host setup/build/storage operation, never main/Cloud publication.

28. [operation] Retain original APIs/log/result archives and bounded available-workspace data once; stream nested archives without following links or executing payloads — source-mode inventory alone cannot replace actual evidence — cost if wrong: transfer/disk consumption up to declared1GiB and terminal incomplete evidence on cap/runner loss.

29. [operation] Reuse only immutable public input bytes and prior component facts under a new request, never invoke consumed old operators or native/scientific cases — this is new provider-free transport/preparation — cost if wrong: provenance could be confused with an old run, so request/source/producer identities remain separate.

30. [operation] Keep the observed failure as loopback RTM_NEWADDR/EPERM identified by exact public-source/errno hash agreement, not a claim that user namespaces are wholly unsupported — the helper reached network setup — cost if wrong: the exact host policy remains unidentified; no retry or privilege/capability relaxation is authorized by this evidence.

31. [operation] Record a separate latent capability-probe defect: its capture call passes the root FD but omits the build FD; the observed EPERM occurs earlier in bubblewrap and is not explained by this later mount defect — do not conflate causal diagnosis with an additional source issue — cost if wrong: future supported backends could still fail until a separately verified source-only correction is made.

32. [operation] Permanently consume request01 and preserve its terminal loopback failure; complete evidence publication and then a separate source-only FD handoff correction, with no new live namespace/target retry — the additional defect is safe to repair with trusted owned-child fixtures but does not remove the observed backend blocker — cost if wrong: extra source/test/CI work without a built wheel; any future actual execution still requires a new reviewed protocol.

33. [source-only FD] Correct only the separate latent PF1 FD propagation defect through an owned trusted-child regression, without actual namespace/target execution or a new request — user continuous authorization covers safe source repair; observed loopback EPERM remains terminal and is not attributed to PF1 — cost if wrong: additional code/test/CI work will not resolve the actual backend blocker.

34. [source-only FD] Review this separate source delta once with fresh context and retain old source/evidence hashes as historical producer identities — source correction must not rewrite or reclassify consumed request01 — cost if wrong: an extra narrowly scoped review adds effort; no independent rereview of the original whole-source fix pass is requested.

35. [source-only FD] Defer FD-M1 historical review/CI wording; preserve reviewed315 checkpoint and publish actual review/CI records through the planned audit/PR — minor status phrasing does not change code or admission — cost if wrong: readers inspecting an intermediate checkpoint may overread completion.

36. [source-only FD] Review decline — Additional FD exposure: accept because only the intended build FD is added and close_fds remains true — cost if wrong: a future broader tuple change would need renewed isolation checks.

37. [source-only FD] Review decline — FD reuse masking: accept because both device and inode are compared while parent descriptors remain owned — cost if wrong: this does not certify malicious same-user interference resistance.

38. [source-only FD] Review decline — No unrelated-FD sentinel/exact tuple test: accept because the real regression covers this omission and the call visibly passes only two FDs — cost if wrong: future isolation expansions may need broader negative coverage.

39. [source-only FD] Review decline — Identities derived from argv: accept because the test isolates transport of unchanged selected descriptors — cost if wrong: upstream selection mistakes are outside this unchanged path.

40. [source-only FD] Review decline — Python substituted for namespace command: accept because owned-child isolation is required to avoid forbidden live probes — cost if wrong: actual namespace support remains unproven.

41. [source-only FD] Review decline — Non-executable helper and metadata stubs: accept because the fixture helper is never launched and real child uses isolated installed Python — cost if wrong: real helper option integration is not re-certified by this fixture.

42. [source-only FD] Review decline — Closed FD/ownership concerns: accept because caller owns the validated build FD and probe still closes only its root FD — cost if wrong: misuse by uncontrolled future callers can still fail.

43. [source-only FD] Review decline — Historical binding differs from corrected source: accept because request01 and producer bytes remain immutable and cannot be reused — cost if wrong: future execution needs new source binding/protocol rather than old-request replay.

44. [source-only FD] Review decline — Nullable audit fields: accept because they truthfully describe pending work at review time — cost if wrong: readers must follow exact final PR evidence rather than infer CI success from a placeholder.

45. [source-only FD] Review decline — Unchanged M6/M7: accept because existing external provenance binding and controlled180s callers remain the scoped mitigations — cost if wrong: review-SHA overinterpretation and longer arbitrary SDK deadlines remain possible.

46. [source-only FD] Review decline — Actual backend/build compatibility: accept because this source-only delta cannot establish network-policy support or target runtime behavior — cost if wrong: the genuine loopback EPERM blocker and absent wheel remain unresolved.
