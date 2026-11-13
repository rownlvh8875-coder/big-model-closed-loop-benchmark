# Stage7 실행 환경·설치 바이너리 계약 설계

이 문서는 **설계·비활성 제안과 순수 메타데이터 검증기(Task1)의 과거 체크포인트**다. 후속 Task2는 [설치 파일 검증기](STAGE7_ENGINE_CLOCK_RUNTIME_INVENTORY.md)에 별도 기록한다. 아래 Task1 시점의 범위·시험 수치를 현재 Task2로 바꾸지 않는다. 실제 image/archive/config digest와 설치 파일 manifest는 아직 없다. Collector·Dockerfile·워크플로·요청을 만들거나 image를 build/pull/load/run/publish하지 않았다. Native/provider/공식 모델/ORT/추가 GPU·clock 호출은 모두0이다. 기존 기본 CI의 생성 SMALL ONNX는 별도다.

Base `d7774ce40d62a19176ea2f5239edfc6644cf51ef`/PR40에서 `design/engine-clock-runtime-contract` 브랜치를 만들었다. 이전 producer70/all44workflows/소비된 request·acceptance8개와 raw/controller 이력을 보존한다. 기존 canary와 ABBA는 재실행하지 않는다.

## 확인한 사실

기존 실제 canary43249493437은 승인됐고, 직접 자식 ABBA43251145868은 acceptance 단계에서 종료됐다. 저장된 runtime 값의 유일한 차이는 ImageVersion C=`20261111.370.1`, A=`20261101.360.1`이다. 기존 계약은 version metadata와 전체 runtime equality를 검사하며, 설치 바이너리 동등성을 주장하지 않는다. 실패의7개 집계는 null,4case·6비교 미실행 상태를 그대로 유지한다. [원래 결과](STAGE7_ENGINE_CLOCK_NATIVE.md)를 이 설계의 실제 실행 증거로 바꾸지 않는다.

공식 runner-images 문서는 이미지 배포가 보통2–3일 걸리며 각 job의 setup 로그에서 사용 버전을 확인하라고 안내한다. `ubuntu-24.04`만으로 특정 ImageVersion을 고정할 수 있다는 증거는 없다. 이는 이전 두 job의 정확한 배포·스케줄링 원인을 입증하지 않는다. Docker 문서는 mutable tag와 digest pinning을 구분한다. OCI descriptor도 hash가 가리키는 개별 객체를 구분한다. 공식 자료 snapshot/hash 및 source anchors는 [audit](evidence/STAGE7_ENGINE_CLOCK_RUNTIME_CONTRACT_AUDIT.json)에 기록한다.

## 선택한 제안

향후 dependency image를 한 번 준비하고 **인증된 Actions Docker-save archive**로 전달한다. ZIP/내부 tar 해시, Docker image config digest, 순서가 있는 rootfs diffIDs, 실제 설치 파일·모드·symlink manifest를 각각 검증한다. 별도 registry 게시를 요구하지 않는다. Archive/config hash를 OCI registry manifest digest라고 표시하지 않는다.

그 안에서도 host kernel·CPU profile·Docker/runtime 버전과 허용된 환경·mount 정보를 관측하고 엄격히 비교한다. Container는 이 host 요소들을 고정하지 못하므로 새로운 runtime도 mismatch로 중단될 수 있다. 실제 GL library 선택·GPU 동작·물리적 host 동일성은 설치 파일 해시만으로 증명하지 못한다.

새 계약에서 outer ImageVersion은 provenance에 계속 남긴다. 동일한 인증 image와 host profile이 확인되는 경우에만 그 차이를 새 계약의 equality 대상에서 분리한다. 기존 `_runtime`/`_gate`의 전체 ImageVersion 비교는 변경하지 않는다. 기존 record의 키를 제거하거나 옛 canary를 재승인하는 방식은 금지한다.

PID·nonce·container ID·실행 HEAD·시간처럼 매번 달라지는 값은 별도 실행 증거로 인증한다. 고정 image identity에 섞어 모든 비교가 항상 실패하게 만들지 않는다. 반대로 kernel/CPU/library/config 변화는 진단 항목으로 밀어내지 않고 거부한다. 실제 library import·GL probe·driver query는 이번에 실행하지 않는다.

## 비활성 상태와 준비 조건

[Proposal](evidence/STAGE7_ENGINE_CLOCK_RUNTIME_CONTRACT_PROPOSAL.json)은 `INACTIVE_DESIGN_ONLY`, `execution_authorized=false`, `image_preparation_ready=false`, `native_admission_ready=false`다. 실제 preparation·image·lock·launch 증거16개는 null이며 native allowance는0이다. Null을 예시 digest나 가짜 artifact ID로 채우지 않는다.

실제 image 준비에는 완전한 base/Python/wheel/deb/asset lock, authenticated build/workflow/artifact, closed installed manifest, Docker compatibility와 disk/hash/load 비용 검증이 필요하다. 제안된 cap은 tar/ZIP 각2GiB, 설치 content3GiB, inventory4GiB/100000entries/16MiB/180초, file512MiB, identity128KiB, download300초, 가용 저장공간16GiB다. 아직 측정한 성능이 아니며 기존 native1320/270초를 자동 연장하지 않는다.

[계획 Task1](superpowers/plans/2026-11-12-engine-clock-runtime-contract.md)의 [순수 검증기](../scripts/engine_clock_runtime_contract.py)와 [회귀 시험](../tests/test_engine_clock_runtime_contract.py)을 구현했다. 표준 라이브러리로 proposal/identity를 파싱·비교하며 합성 identity match도 `native_admission=false`를 반환한다. 파일 inventory·Docker/API 실행·native import는 Task1에 포함하지 않는다. 이후 collector와 image 준비는 각각 별도 검토 단계다.

## 판단과 비용

1. 기존70source/44workflow/8registry를 동결하고 새 설계 namespace를 쓴다. 비용은 별도 구현·검증이며 이전 실패를 재사용하지 못한다.
2. Sealed userspace와 별도 host profile을 제안한다. Container가 kernel/CPU/실제 GL 선택까지 고정하지 못하고, 엄격한 host 비교로 다시 거부될 수 있다.
3. 현재 설계만 완료하고 실제 참조와 native allowance를 비활성으로 둔다. Image 준비나 native 실행을 이 문서만으로 시작할 수 없다.
4. Registry 대신 Actions image archive를 선택한다. 전송·load·저장공간 비용이 추가되고 archive/config/OCI digest의 차이를 별도로 검증해야 한다.

## 검증 범위와 후속

검증은 proposal의 비활성/null/zero 의미, identity의 타입·필드·self-hash·일치/불일치·최대64개 경로 차이, source·workflow·registry 보존, 문서 링크와 공식 reference snapshot을 다룬다. 17개 집중 시험이 통과했다. 구현하지 않은 manifest/collector에 시험 통과 수치를 만들지 않는다. 독립 builder/design 검토가 발견한 해시 객체 종류의 인증 한계를 수정했다. 같은 형식의 가짜 hash도 파싱될 수 있으며 실제 객체를 인증하지 않는다. 다음은 Task2의 bounded installed-file collector이며 아직 구현하지 않았다. 전체 변경 독립 검토와 기존 baseline CI 결과는 review/audit 및 Draft PR에 기록한다. Review 대상 HEAD와 이후 review/status-only HEAD는 구분한다.

실제 새 raw/canvas/I420/ONNX/clock trace/run/artifact는 없다. 원래 모델 step2의 first divergence와 이전 clock canary 결과는 과거 증거로 유지한다. Strict FAIL, expanded NOT_RUN, geometry/physical-optics/production-ISP/full-S 미검증, Stage7 INCOMPLETE, main 공식 호출0, Cloud 설정 변경·게시·main merge0, Draft 유지다. Raw와 controller workspace를 삭제하지 않는다.

실행 예: `python -m scripts.engine_clock_runtime_contract validate-proposal --proposal docs/evidence/STAGE7_ENGINE_CLOCK_RUNTIME_CONTRACT_PROPOSAL.json`은 `INACTIVE_PROPOSAL_VALIDATED`와 `execution_authorized=false`를 반환한다. `compare-identity --left FILE --right FILE`은 메타데이터 차이의 경로만 반환하고 실제 archive/API/Docker/installed tree를 검사하지 않는다. 두 가짜 identity가 같아도 실제 준비·실행·binary selection 증거가 아니다.

Task1 실제 로컬 전체 CPU 시험:661tests/73.571s/선택 의존성7skip, focused17/0.498s. 최초17개 missing-feature RED와 guard fixture 수정 로그를 보존했다. 같은 code/test의 독립 최종 검토와 최종 HEAD 기본 CI는 후속 영수증 및 Draft PR에서 구분해 기록한다.

독립 최종 검토: a2317468e3a3b4bf1a6e81a6c3d40c92e08331e3에서 Critical0/Important0/문서Minor1, 원래 설계I1 closed. [검토 원본](evidence/STAGE7_ENGINE_CLOCK_RUNTIME_CONTRACT_REVIEW.md)의 M1에 따라 완료 문구와 실제 provenance 거부 시험 설명을 정정했다. 후속 변경은 문서·검토 영수증뿐이며 code/test byte는 그대로다. 검토 JSON SHA256 `771e987e1f802f1ed8c48eaa2fed385f2e9b0beb4395d29fc6c386e2ba7030a8`; 최종 HEAD 및 이후 기본 CI는 Draft PR에 기록한다.


## Task3 continuation — builder source checkpoint (2026-11-13)

PR49 input closure now has new staging/open-FD verification, mandatory namespace launcher/owned driver, strict wheel validator and inactive one-use remote template. See [builder source result](STAGE7_ENGINE_CLOCK_BUILDER_STAGING.md).74new focused/full800tests passed with7optional skips; actual remote preparation follows source review/basic CI under a separate request. Local trusted-host true failed readonly UID mapping, so no downloaded local runtime/source execution occurred. Task3 is incomplete: actual wheel/full lock/main installed/image identity remain unavailable;16old refsnull/nativeallowance0. User continuous instruction authorizes proceeding through safe preparation without another step menu, preserving old44workflows and all old evidence/gates.

Builder source review96e97dc returned C0/I5/M2; root single TDD fix9aaca760 closed Important findings (88focused/814full CPUtests PASS,7optional skips), with no independent rereview. Actual source-before/source-after maps and bounded available-workspace retention now have concrete implementations; M6/M7 remain deferred. Source CI/registered provider-free operation still precede actual build claims. No old native or image admission follows.

Final same-pass I5 refinement: available host disk>=1073741824bytes is measured and recorded before component input transport, with failure facts retained. Qualified code `843fb749abe5c672d65d534fac150c90ec1ac3d3` follows initial fix `9aaca76095e611f6ec1bf73700bb1f6a2e33254c`;89focused/815full CPUtests PASS/7optional skips (full74.276s). Preliminary3ee2954 CI4jobs passed/814unit+1SMALL per event/artifacts0, but is historical; exact final source CI is recorded separately in Draft PR50. No target execution or second independent review occurred.
