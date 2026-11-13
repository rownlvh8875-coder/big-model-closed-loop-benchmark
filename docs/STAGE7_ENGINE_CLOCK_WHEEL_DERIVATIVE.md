# Stage7 MetaDrive metadata 파생 wheel 변환기

이 문서는 PR44의 합성 변환기 체크포인트다. 후속 [실제 wheel 검증·파생 입력](STAGE7_ENGINE_CLOCK_REAL_WHEEL_PREPARATION.md)은 별도 단계이며 Task3 전체·이미지·native 준비 완료가 아니다.

Task3 입력 충돌의 후속으로 합성 wheel을 처리하는 순수 bytes 변환기를 구현한다. Base `b9812ae4a7d795c22fc277036064e57ae8cfd3dd`/PR43, 브랜치 `feature/engine-clock-wheel-derivative`다. 실제 MetaDrive wheel을 다운로드·변환·설치하거나 지원되는 image를 준비한 결과가 아니다. Task3 전체는 미완료다.

## 범위와 정책

[변환기](../scripts/engine_clock_wheel_derivative.py)는 immutable bytes·예상 SHA·deadline을 받아 메모리에서만 처리한다. CLI·파일·network·process IO나 package import는 없다. [상세 계약](superpowers/specs/2026-11-13-engine-clock-wheel-derivative-design.md)과 [실행 계획](superpowers/plans/2026-11-13-engine-clock-wheel-derivative.md)에 한도와 실패 조건을 명시했다.

Name/Version은 metadrive-simulator/0.4.3으로 유지한다. METADATA의 정확한 unconditional `opencv-python` 요구 한 줄만 `opencv-python-headless==5.0.0.93`으로 바꾼다. WHEEL의 Generator·Build1headless, 새 provenance, 재작성 RECORD로 파생물임을 표시한다. 허용된 세 파일 외에는 runtime·asset·license·entry point와 directory/attribute를 보존한다. 서명된 원본은 서명을 지우지 않고 거부한다.

동일한 입력은 동일한 ZIP_STORED 출력 bytes를 만든다. 원래 archive의 압축·시간·순서는 달라지며, 보존 주장은 개별 member의 비압축 bytes와 attribute에 한정한다. Caller가 만든 가짜 wheel과 가짜 예상 hash도 일치할 수 있다. 성공은 metadata 변환 결과일 뿐 upstream/API/Git/구현 인증이 아니며, `source_origin_authenticated`, `implementation_authenticated`, `official_distribution`, `execution_authorized`, `image_preparation_ready`, `native_admission`은 모두false다. Policy hash는 구현 source hash가 아니다.

## 검증과 한계

합성 ZIP의 실제 bytes·RECORD·CRC·local/central 구조를 검사한다. 중앙 디렉터리 한도는 stdlib 파서가 ZipInfo 목록을 할당하기 전에 확인한다. Resource/deadline 실패와 외부 예외는 partial bytes·완전 보존 hash를 반환하지 않으며 raw 예외 문자열을 남기지 않는다. 원본은 immutable bytes여서 변경하지 않는다.

Input64MiB/expanded256MiB/member64MiB/metadata1MiB/20000members(추가 marker 자리 포함)/output·읽기512MiB/경로4096bytes/180초 cooperative deadline이다. Classic contiguous ZIP만 지원하고 ZIP64·descriptor·extras·comments 등은 거부한다. 정당한 실제 wheel도 이 제한에 걸릴 수 있다. 수백 MiB 메모리를 쓸 수 있으며 실제 wheel 호환성·대규모 비용·hard realtime·observer 중립성을 측정한 결과는 아니다. 미래 multi-GiB image 전송 도구와 구분한다.

수정 후 집중34개/0.099초와 전체CPU726개/70.128초/7skip으로 통과했다. 최초720개와 검토 전721개 시험은 각각 수정 전 과거 결과다. 합성 원본/파생 hash·보존 검사는 [audit](evidence/STAGE7_ENGINE_CLOCK_WHEEL_DERIVATIVE_AUDIT.json)와 [fixture 영수증](evidence/STAGE7_ENGINE_CLOCK_WHEEL_DERIVATIVE_FIXTURE.json)에 기록한다. 구현이 없을 때의 RED, 실제 수정 RED와 초기 시험 fixture 오류를 포함한 원본 로그를 보존한다. 독립 검토 HEAD와 후속 영수증 HEAD/기본 CI는 구분한다.

## 다음 단계와 보존

현재 시험에 사용한 실제 upstream 자료는 이전에 저장된 METADATA sidecar이며 carrier wheel/runtime/asset/license는 합성이다. 실제 공식 wheel hash나 실제 파생 wheel hash로 표시하지 않는다. 다음은 별도 검토된 bounded 실제 wheel 검증·파생과 measured hash 증거다. 그 뒤에도 완전한 base/Python/wheel/deb lock, recipe, API/launch adapter와 이미지 준비 검토가 필요하다.

Producer70/workflows44/registry8·Task1/2·비활성 proposal·과거 증거/raw/controller 이력을 보존한다. Preparation16refsnull/readinessfalse/nativeallowance0이다. 이번 새 공식 모델·native·GPU·clock·image 실행은0이며 기본 생성 SMALL ONNX CI는 별도다. 과거 ABBA terminal FAIL/7null/4case·6비교 NOT_RUN, strict FAIL/expanded NOT_RUN/geometry·optics·full-S 한계/Stage7 INCOMPLETE를 유지한다. Cloud 게시와 main 병합은 하지 않는다.

독립 검토는 `a4684d46d4e9fde9d9a32ec0b07428dbc93bc2eb`에서 Critical0/ImportantR1·R2/Minor0이다. [검토 원본](evidence/STAGE7_ENGINE_CLOCK_WHEEL_DERIVATIVE_REVIEW.md)을 보존한다. 압축 범위의 후행 bytes 무시와 provenance 경로 충돌을 실제 재현 RED→GREEN으로 한 차례 수정했다. 수정 후 독립 재검토를 했다고 표시하지 않는다. 검토 범위 밖12항목의 root 판단·비용은 audit에 기록한다.
