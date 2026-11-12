# Stage7 Task3 입력 호환성 사전 확인

**Task3는 입력 호환성 단계에서 차단됐다.** Python/필수 패키지 버전은 존재하지만, MetaDrive의 `opencv-python` 요구와 현재 계약의 고정 headless 패키지가 같은 `cv2` namespace를 사용한다. OpenCV는 이들을 함께 설치하지 말라고 안내한다. Pip resolver의 불가능성이나 과거 이미지 차이의 원인을 입증한 결과는 아니다.

브랜치 `design/engine-clock-image-inputs`, base `d54d43757eabc60d4f3f5b3d7e51f665bcc9f23e`/Draft PR42. Task1·2 구현과 시험은 그대로다. [설계 및 후속 정책 제안](superpowers/specs/2026-11-12-engine-clock-image-inputs-design.md), [audit](evidence/STAGE7_ENGINE_CLOCK_IMAGE_INPUTS_AUDIT.json)에 확인 범위와 미확인 항목을 기록한다.

## 실제로 확인한 내용

- 공식 release/index/core metadata에8번 요청했고 모두 HTTP200이다. 자동 재시도는 없다. Python3.11.18/NumPy2.4.6/OpenCVheadless5.0.0.93/Panda1.10.13/MetaDrive0.4.3 버전의 존재를 확인했다.
- MetaDrive wheel의 PEP658 metadata11,315bytes를 다운로드해 게시 SHA256 `4fb69fa54bb0e8118315aecdc482597af69798e17e47df3c57fbca50d4e7bcf6`과 일치하는지 확인했다. [원본 METADATA](evidence/engine-clock-image-inputs/metadrive-0.4.3.METADATA)에 unconditional `Requires-Dist: opencv-python`이 있다. Wheel payload는 다운로드하지 않았다.
- [OpenCV 안내 원문](evidence/engine-clock-image-inputs/opencv-package-guidance.txt)은 패키지 하나만 선택하라고 명시한다. 실제 중복 설치·파일 덮어쓰기·import를 실행하거나 측정하지 않았다.
- Wheel SHA는 upstream이 게시한 값이다. 실제 payload의 로컬 측정 SHA, 완성 dependency lock, 준비된 image나 실제 설치 파일 증거로 표시하지 않는다.

## 현재 멈춘 범위와 다음 작업

계획의 “지원되지 않는 입력이면 중단” 조건에 따라 complete lock·Dockerfile·준비 workflow·image preflight adapter를 만들지 않았다. Base/Python archive/전체 wheel·deb graph/실제 Docker 호환성과 disk/hash/load 비용은 미확인이다. Task3 완료 checkbox는 체크하지 않는다. 준비 참조16개는 null, readinessfalse/native allowance0이다.

다음 제안은 **MetaDrive 원본 runtime payload를 보존하고 dependency METADATA만 변경하는 재현 가능한 파생 wheel의 정책·변환기 설계**다. 아직 구현·다운로드·변환하지 않았다. 원본/변환 source/파생 hash, RECORD, 비메타데이터 바이트 보존과 hostile archive 시험을 별도 검토해야 한다. 이 제안은 upstream 공식 headless wheel이 있다는 주장이나 실제 이미지 준비 승인이 아니다. 두 OpenCV 배포판 동시 설치, headless pin 제거, `--no-deps`로 요구를 숨기는 방식은 채택하지 않았다.

## 보존과 상태

Producer70/workflows44/registry8 및 Task1·2 코드·시험·비활성 proposal을 보존한다. 원래 raw/extraction/controller 기록도 유지한다. 새 model/weights/ORT/provider/engine/Xvfb/GPU/clock/image build·pull·load·run은0이다. 기본 생성 SMALL ONNX CI는 별도다. Cloud 게시와 main 병합은 없다.

새 raw/canvas/I420/first-divergence 측정은 없다. 과거 ABBA terminal FAIL/7null/4case·6비교 NOT_RUN과 strict FAIL/expanded NOT_RUN/geometry·optics·full-S 한계/Stage7 INCOMPLETE를 유지한다. 입력 package 지원 문제를 과거 픽셀 차이의 원인으로 해석하지 않는다.
