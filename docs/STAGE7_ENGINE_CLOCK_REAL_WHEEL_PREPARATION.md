# Stage7 실제 wheel 검증·파생 입력 증거

공식 게시 hash와 일치하는 MetaDrive0.4.3 wheel을 한 번 다운로드하고, 고정된 metadata 변환기로 파생 wheel을 만들었다. **로컬 package-input 단계이며 Task3 전체·이미지·native 준비 완료가 아니다.** Root의 byte/RECORD 검증은 통과했고 독립 검토가 남아 있다.

실제 실행 source HEAD는 `63ee25b469c7f11cc901f4e0f8feed7219304866`, 변환기 source 기준은 PR44의 `de30d68027162b4058e029b9687c5a198f1339b2`다. 이후 증거·검토 commit HEAD를 실제 실행 source로 바꾸지 않는다. 사용자 기준 실행 시작은 **2026-11-13 10:03:16 KST**다. 실제 도구 Python은3.11.17이며, 미래 image의 Python3.11.18 준비 증거로 표시하지 않는다.

| 항목 | 실제 측정 |
| --- | --- |
| 원본 wheel | 55,128,766bytes / SHA256 `c6f8a42baac939a0af53a8e1cd9d48ec2bf0051917e7c19083e156a6506493d9` |
| 파생 wheel | 72,968,610bytes / SHA256 `f949e89ff4bc32b72c8d09f5c61446bbc2b1f9b415b99a077c02b8df77c217f7` |
| ZIP member | 원본1431개 → 파생1432개 |
| 변경 대상 밖 보존 | 1428개 / 72,484,277 decoded bytes, bytes·attribute 일치 |
| 실행 | 전체8.682869s, 변환1.048556s, controller 자기 process peak RSS145540KiB |
| 별도 root 검사 | 약0.779833s, 실제 파생 RECORD1432파일 검증 |

원본 METADATA는 실제 sidecar SHA `4fb69fa54bb0e8118315aecdc482597af69798e17e47df3c57fbca50d4e7bcf6`와 일치한다. Metadata 요청3건·wheel 요청1건은 모두 HTTP200/curl exit0/TLS verify result0/redirect0이며 application retry는0이다. 이는 설정된 TLS 경로에서 게시 pin이 일치한 사실이며 publisher 서명·upstream endorsement·독립 host 증명이나 Actions run/artifact 인증은 아니다.

변경은 정확한 METADATA dependency, WHEEL Generator·Build1headless, RECORD와 새 provenance다. Name/Version0.4.3 및 그 밖의 runtime·asset·license bytes와 원본 attribute를 유지한다. 파생물은 공식 upstream wheel이 아니다. 압축 stream/layout·CRC·RECORD 검사는 변경하지 않은 PR44 변환기가 수행했고, root는 결과를 다시 변환하지 않고 member별 bytes/attribute와 실제 저장된 파일 hash를 별도로 확인했다. 추출·설치·package import·native 실행은 없다.

## 영수증과 소비 상태

- [실행 전 요청](evidence/STAGE7_ENGINE_CLOCK_REAL_WHEEL_REQUEST.json)과 [운영 명령 원본](evidence/STAGE7_ENGINE_CLOCK_REAL_WHEEL_OPERATOR.txt)은 실행 source의 bytes를 보존한다.
- [원본 실행 영수증](evidence/STAGE7_ENGINE_CLOCK_REAL_WHEEL_RECEIPT.json), [root 검증](evidence/STAGE7_ENGINE_CLOCK_REAL_WHEEL_ROOT_VERIFICATION.json), [입력 후보](evidence/STAGE7_ENGINE_CLOCK_REAL_WHEEL_INPUT.json), [audit](evidence/STAGE7_ENGINE_CLOCK_REAL_WHEEL_AUDIT.json)에 실제 hash·크기·단계·출처 한계를 기록한다.
- [별도 소비 기록](evidence/STAGE7_ENGINE_CLOCK_REAL_WHEEL_CONSUMED.json)의 요청은 **CONSUMED_SUCCESS**이며 추가 실행 승인은false다. 원래 REQUEST를 고쳐 미소비 요청처럼 만들지 않는다. Local journal과 소비 기록은 독립적인 전역 anti-replay attestation이 아니다. 운영 명령은 이력이며 재사용 transport API가 아니다.

원본·파생 wheel과 metadata/journal/receipt 등8파일 128,148,435bytes를 `output/stage7-real-wheel-preparation/wheel-input-20261113-e369b2c18129`에 보존한다. Git에 대용량 wheel을 추가하거나 별도 artifact를 업로드하지 않았다. Raw 경로·snapshot·review/controller workspace를 삭제하지 않는다.

## 한계와 다음 단계

이 package 작업의 저장공간 최소치는1GiB다. Root의 실행 전 free snapshot은60,879,122,432bytes였고 operator가 최소치를 확인했으나 정확한 그 순간 값은 저장하지 않아 null로 기록한다. 미래 image의16GiB 조건을 대체하지 않는다. 자기 process peak RSS는 curl·전체 host 메모리 합계가 아니다. 로컬 시간·메모리·파일 측정은 이미지 규모 비용이나 observer 중립성 증거가 아니다.

다음은 파생 wheel hash를 명시적으로 묶은 완전한 Python/base/deb/asset dependency lock과 비활성 image adapter 설계다. 설치 환경·OpenCV runtime 호환성, image/config/rootfs·installed inventory·API/launch 인증은 미완료다. 현재 image 준비16참조null/nativeallowance0/Task3incomplete를 유지한다.

Producer70/workflows44/registry8·Task1/2·변환기 코드/시험/policy·비활성 proposal은 그대로다. 새 공식 모델·weights·ORT/provider/engine/Xvfb/GPU/clock·image build/pull/load/run은0이며 기본 생성 SMALL ONNX CI는 별도다. 새 raw/canvas/I420/first-divergence 측정은 없다. 과거 ABBA terminal FAIL/7null/4case·6비교 NOT_RUN, strict FAIL/expanded NOT_RUN/geometry·optics·full-S 한계/Stage7 INCOMPLETE를 유지한다. Cloud 게시와 main 병합은 하지 않는다.
