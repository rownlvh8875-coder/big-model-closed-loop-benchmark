# SDK3 shader 경로 수집기 준비 기록

후속: [승인 후 실제 실행 결과](STAGE7_SDK3_SHADER_PATH_RESULT.md). 아래 내용은 원격 승인 전의 준비 기록이다.

2026-11-17 KST. **다음 진단의 로컬 구현과 단일 전체 변경 검토에서 찾은 세 문제의 회귀 수정을 완료했다.** 새 테스트16개와 관련 회귀132개,actionlint가 통과했다. 원격 푸시는 자동 승인 검토가 이전 “아무것도 게시하지 마” 지시와 충돌한다고 거부했다. 새 원격 브랜치·초안 PR·실제 렌더러는 만들거나 실행하지 않았다. 전체 CI와 실제 관측 결과는 아직 없으며,기존 공식 모델 행렬3/4PASS·전체FAIL,수리 미입증·Stage7 미완료를 유지한다.

기준은 PR136의`dacce23588e45dfd986f69f1ec00f23e0be051ed`다. 읽기 전용 고정 이미지 tar의 SHA`4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698`를 확인하고 실행 없이 MetaDrive Python/GLSL 텍스트931개·4,724,007B를 읽었다. 이 중12개 원본의 이미지 계층·크기·SHA와 원문을 보관했다. 패키지의 문자열 사전 shaders.py는 현재 로더에서 비활성이고,_load_shader_str는 별도GLSL 파일을 읽는다. 따라서 사전의 오래된 문자열을 실제 shader로 간주하지 않았다.

고정 소스에는 장면 shader와 Road 센서의 별도 톤매핑 shader가 있다. EngineCore는 simplepbr의 기본`use_normal_maps=False`를 유지하며,센서의 톤매핑 노출은1.0으로 설정된다. 이는 **소스 경로 관측**이며 실제 실행의 활성 define·입력·GPU 출력은 아직 수집하지 않았다. CPU 텍스처 연결만으로 노멀 계산 분기가 활성이라고 판단할 수 없다.

새 수집기는 원래 Road7 CPU 읽기 직후·카메라 복원 전 경계에서 다음을 읽도록 구현했다.

- 선택한 CPU 메시의 RenderState/ShaderAttrib/Shader 포인터와 실제 캐시 vertex/fragment 문자열.
- 원래 Road 톤매핑 quad와 scene_tex 입력의 객체 결합,exposure 입력,카메라 초기 상태·태그 문맥.
- 실제 simplepbr 플래그와 알려진 PSSM 입력8개. 배열을 공개 getter로 읽을 수 없으면 unavailable로 남기고,소유 rig의 캐시 배열은 GPU uniform 결합을 입증하지 않는 별도 필드로 기록.
- 고정 파일12개와 캐시 shader 문자열의 SHA·크기. 파일당256KiB·전체2MiB·shader8개·메시40개·관측20초의 제한.

기존 재질·기하·원본 이미지·프로세스 수명 주기 검증을 그대로 적용한 뒤 shader 문자열을 소스/define과 독립 비교한다. 실제 다른 문자열은 불일치로 보존하고 성공으로 바꾸지 않는다. GPU query/readback·shader 재컴파일·강제RAM reload·렌더/태스크/조명/시계/샘플러 변경은 없다. 기존 파일·프로토콜은 수정하지 않고 새 파일과 private function globals만 사용했다.

단일 read-only 검토의 Important3개는 회귀로 재현해 한 번의 수정 단계에서 처리했다: 실행 진입점의 argparse import 누락;파일을 읽을 때 줄바꿈을 정규화해 서로 다른 캐시 shader를 같다고 판정한 문제;fragment 크기 초과 또는 stage 사이 timeout에서 이미 저장한 vertex 파일을 manifest가 잃는 문제다. 실제 isolated --help subprocess,재해시한CRLF 변조,SDK 없는 CPU 객체로 실제 snapshot 함수의 두 부분 실패 경로를 검증했다. 재검토는 하지 않았다. Minor1개는 보류했다: 오프라인 tonemap 함수에1e308 같은 극단적 유한 값을 넣으면 중간 overflow로NaN이 나올 수 있다. 일반 수치 테스트는 통과하며 native 수신 검증에서는 이 함수를 호출하지 않는다.

로컬 전체 스위트는 통과하지 못했다. 첫 실행은2,012개/실패1·오류26·건너뜀7,수정 후 실행은1,997개/실패2·오류39·건너뜀7이다. setupClass 컴파일 실패로 일부 테스트가 실행되지 않아 개수가 감소했다. 기존 fixture가RUNNER_TEMP를/tmp로 고정하지만 이 환경의 쓰기 가능한 임시 공간은/dev/shm에 있으며,토큰 등을 제거한 컴파일 환경에서는가득 찬/tmp 때문에`Cannot create temporary file ... No space left on device`가 발생했다. 기존 GLX fixture는/dev/shm의 실행 매핑을 driver 공유 메모리로 판단해 거부한다. 기존 fork/timeout 테스트의 조기 종료 원인은 아직 완전히 확정하지 않았다. 실패한 모든 이름·예외와 원본 로그를 보존했으며,기존 검증 코드나 조건을 완화하지 않았다. **관련132개 통과를 전체 CI 통과로 대신하지 않는다.**

원본 체크아웃`2435bf438651916ff496c07d334ba264d56a71bc`과 주요6개 파일의 byte/mode pin,이전31개 디렉터리/3,846개 파일,PR136 본문·HEAD·상태와main`48e79a7ed5aedf6daa5a62ff68d2225af7955ef1`의 보존을 확인했다.

승인 후 제안한 작업은 새 feature 브랜치 푸시와 부모PR136을 기준으로 한 Draft PR 작성,정확한 소스의 canonical push/PR 네 CI 작업 확인,그 이후 버전이 고정된 요청 전용 브랜치로 단일 렌더러 실행이다. 기존600초 자식/630초 컨테이너/20분 job·2CPU/10GiB·읽기 전용 루트·network none을 유지하며,공식 모델0개·ONNX 추론0회다. 환경/레지스트리 게시와main 병합은 이 제안에 포함하지 않는다. 실제 실행 후 산출물 인증·원본 비교·독립 검증과 최종 결과 보고가 남아 있다.

근거: [구체적 실행 제안](proposals/sdk3-shader-path-execution.json),[로컬 검증](evidence/sdk3-shader-path-01/local-verification.json),[전체 스위트 실패 목록](evidence/sdk3-shader-path-01/whole-suite-failures.json),[검토·수정](evidence/sdk3-shader-path-01/wholebranch-review.md),[고정 소스 색인](evidence/sdk3-shader-path-01/frozen-source-index.json),[판단 장부](evidence/sdk3-shader-path-01/ledger.md),[실행 계획](superpowers/plans/2026-11-17-sdk3-shader-path.md).
