# MetaDrive × MD-V3 — 카메라 호출과 연결되는 제한된 PSSM/Chase 계측

**새 CPU 콜백 관측기와 실제 설치 소스 대조를 구현했다. 실제 네이티브 실행은
NOT_RUN이며, 원인 규명이나 renderer 수정 성공을 뜻하지 않는다.** 기존03의
시계+Texture 동등/RGB차이에서 다음 호출 경계로 좁히기 위한 준비다.
strict0/4FAIL·Stage7INCOMPLETE를 유지한다.

## 기존 증거와 새 범위

[과거 실제 PSSM/Chase 관측](STAGE7_PSSM_CHASE_POSE_LAG.md)은24프로세스/96틱에서
실제 PSSM→Chase 순서와 pose/MVP 변화를 측정했다. 당시 OFF/ON의 I420 시계열은
8비교 모두 불일치했고 CPU 계측의 중립성을 증명하지 못했다. 같은 연구를
재실행하거나 고정 pose의 미세 RGB 차이를 이미 해결했다고 주장하지 않는다.

[최신03 CPU 분석](STAGE7_ENGINE_CLOCK_PIXEL_FORENSICS.md)은 같은 count/Texture에도
다른 RGB를 확인했다. 새 관측기는 이 실험 형식의 각 road/wide 호출과 실제
PSSM.update/MainCamera._chase_task의 entry/exit를 직접 연결하도록 만들었다.
03의261생산파일·원본·소모 요청은 바꾸지 않았다.

## 구현과 실패 조건

- scripts/renderer_task_callbacks.py는 기존 clock scope **앞에서** taskMgr.step을
  감싼다. clock trace의 활성 camera/call과 task진입·RAM미진입 상태를 확인한다.
  원래 step의 인수·반환객체·예외·실행횟수를 유지하며, 태스크 함수·등록·정렬은
  바꾸지 않는다. 실제 code object와 self가 모두 일치하는 두 콜백만 기록한다.
- sys.setprofile은 원래 각 step 안에서만 설치한다. 최대12step/48state snapshot,
  JSON256KiB이다. 기존 hook은 거부·보존하고 own/inherited step 속성을 복원한다.
  두 callback의 실제 순서는 어느 쪽이 먼저여도 관측하며 가정으로 채우지 않는다.
- Python profile return 이벤트만으로 정상 반환을 판단하지 않는다. 등록된
  task.cont 반환값을 요구한다. 관측 실패는 원래 예외를 가리지 않도록 sticky로
  남기고 step 경계에서 거부한다. snapshot의 중단/종료/deadline은 즉시 전파한다.
  엔진이 오류를 잡더라도 빈 callback trace나 일부 snapshot이 성공할 수 없다.
- OFF는 callback owner/reader를 연결하거나 profile을 설치하지 않는다.
  events는 null/미측정이다. 공통 step wrapper는 남으므로 untouched 동작이나
  observer중립성을 주장하지 않는다. 향후 clock/Texture는 양 arm의 공통 관측이다.
- scripts/renderer_task_binding.py는 이미 승인된 caller가 제공하는 클래스로
  정확한 engine.pssm/main_camera/camera/render/rig 소유 관계를 연결한다.
  기존 두 split MVP를 private aligned matrix에 복사하고 WORLD position/HPR을
  읽는다. 이 모듈은 MetaDrive/Panda를 import하거나 provider를 만들지 않는다.

상태는 pose6float·2×4×4 MVP float·Chase run_task bool의 사본이다. 세 종류의
상태는 순차 조회이므로 atomic/동시 snapshot이 아니다. 추가 clock/GL/GPU/RAM
getter는 없다. 상태를 읽는 동안에도 CPU 시간과 lazy transform 계산이 영향을
받을 수 있으므로 후속 독립 OFF/ON 대조가 필요하다.

| 한 관측 프로세스의 최대6쌍 | 상한 |
| --- | ---: |
| 원래 taskMgr.step | 12 |
| PSSM/Chase entry+exit state snapshot | 48 |
| 명시한 getter 메서드/snapshot | 35 |
| 명시한 getter 메서드 합계 | 1680 |
| private aligned matrix 생성/assign 각각 | 96 |

35는 getPos/getHpr/get_mvp_array 3개와 getCell32개다. vector6성분 및 MVP-array
2인덱스 조회, 길이 확인·속성 접근·private 생성/assign은 별도로 취급하며 모든
C++ 호출의 총수라고 주장하지 않는다. 미래 네이티브 프로토콜의 예산에는 이
범위와 기본 clock/Texture 관측을 새로 명시해야 한다. 기존03의528getter 허용량은
재사용할 수 없다.

## 실제 소스의 데이터 검증

다운로드된 코드를 실행하지 않고 보존 wheel과 승인 image006의 설치 manifest를
SHA로 검증했다. [원본 감사 JSON](evidence/RENDERER_TASK_BOUNDARY_SOURCE_AUDIT.json):
SHA40bb1acd6b2ee14681f95527475fb90b35a0d14131c4b36610a56079452c5b78.

- Headless wheel72968610B,
  SHAf949e89ff4bc32b72c8d09f5c61446bbc2b1f9b415b99a077c02b8df77c217f7.
- 설치 manifest44232항목,
  SHAf81fa5be38bc9853b6eff1d0ea524be97f3d1e92f5c1f0f9e1449a11b4c4b59f.
- pssm.py/update80–102, main_camera.py/_chase_task221–273,
  base_camera.py/perceive132–200, base_engine.py/setup_main_camera629–635의
  원본 파일 전체 SHA/바이트 수가 설치 manifest와 일치했다.
  AST는 구문상 호출과 범위를 기록하며 실제 실행 순서의 증거가 아니다.

이 대조는 현재 프로세스의 실제 callback binding·loader·native binary 동등성·
GPU출력·물리호스트를 인증하지 않는다. 구조적 synthetic engine도 adapter 검사를
통과할 수 있으며 이 사실로 네이티브 실행 권위를 얻지 않는다.

## 검증과 남은 실제 실행 연결

모듈 부재 RED 및 예외 회귀 RED 뒤 새27시험+기존23clock시험50개가 통과했다.
fresh 검토에서 RT-I1 malformed행의 실패 기록 누락을 재현했고, 회귀1시험의
OFF/ON·비정상행4subcase RED→GREEN 수정 후 현재51PASS/0.210초다.
검토는 Critical0/Important1수정/Minor0, 추가 검토 없이 한 차례 수정했다.
[검토 원본·범위](evidence/RENDERER_TASK_BOUNDARIES_01_REVIEW.md).
전체 시험·fresh 검토·최종 Draft/CI의
실제 관측은 [ledger](STAGE7_RENDERER_TASK_BOUNDARIES_LEDGER.md)의 후속 closeout과
해당 소유 브랜치 Draft본문을 기준으로 한다.

실제 실행 전에는 다음 연결이 남아 있다.

1. 별도 sealed producer에서 새 observer를 삽입하고, callback trace와 clock/camera/
   원본RGB의 전체 association 및 실패 prefix를 검증하는 새 schema가 필요하다.
   기존03 case의 frozen exact schema에 필드를 억지로 추가할 수 없다.
2. 새 source closure·계측 ON/OFF schedule·명시적 getter/시간/파일 예산·이미지/호스트
   검증 및 canary→독립 원본 승인→ABBA lifecycle을 새 소스로 연결해야 한다.
3. 새 source 검토와 정확한 HEAD CI 이후, 고유 요청·허용량으로 실제 canary를
   실행해야 한다. 현재 source audit는 이 admission을 대체하지 않는다.

이 증분에서는 실행 요청·workflow activation을 추가하지 않았다. 실제 provider,
추가 frame/readback/getter, 공식 MD-V3 모델/ORT 호출은0이다. renderer/shader/default
변경·임의 warmup삭제·pixel보정·main병합·Cloud/registry게시는 없다.

## 코드 검증 마감

수정 소스76236ed14fcb412c6964ab554ccefaf81bc6d7b3에서 전체1237시험:
실패0/오류0/기존7skip/122.515초다.
[수정 후 검증](evidence/RENDERER_TASK_BOUNDARIES_01_POST_FIX_CHECK.json)은 표준
라이브러리만의 import와261생산파일 불변도 확인했다. 현재 관측기
SHA cb623b30cc5ed97dbb8b381866fa28f51e7cd0d4e2b031793a5cf747b37f37d2,
binding SHA889b79da9f41d3cde33a538846bb745f6b3582bd1cbb1509b9a4e5b3dff103ac다.
이후 수정은 문서·증거만 추가한다. 중요한 지적1건은 위 회귀 시험과 전체 시험으로
수정 검증했으며 독립 재검토를 받았다고 주장하지 않는다. 새 Minor보류는 없다.

[소유 브랜치 Draft 검색](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pulls?q=is%3Apr+head%3Adiagnostic%2Frenderer-task-boundaries-v1)의
최종 본문과 output/stage7-renderer-task-boundaries-01/closeout/final-verification.json에
정확한 최종 HEAD·push/PR CI run/job·Draft/미병합·main불변·기존 native실행 수를
검증해 남긴다. 일반 CI의 생성 SMALL ONNX시험은 공식 MD-V3 호출이 아니다.
