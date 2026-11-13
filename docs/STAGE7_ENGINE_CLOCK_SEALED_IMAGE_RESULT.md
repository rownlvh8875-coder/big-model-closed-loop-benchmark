# MetaDrive × MD-V3: 모델을 실행하지 않는 의존성 이미지 준비 결과

의존성 이미지 준비와 별도 컨테이너의 설치 파일 검증을 완료했다. 원본 Actions API·아티팩트 ZIP·이미지 TAR·설치 목록·실행 전 코드/Python 복사본을 인증하고 대조했다. 이 결과는 설치된 파일과 격리 실행 조건에 관한 증거이며, 렌더러·GL·네이티브 ABI·MD-V3 추론·폐루프 성능 결과는 아니다. Stage7은 여전히 INCOMPLETE이다.

| 항목 | 실제 결과 |
| --- | --- |
| 검증된 소스 | 1af17fbe6bcaceb3ff7aa72ce869a0d1e3bae840 / Draft #80 |
| 소스 CI | push43511648616 / PR43511670793, 작업4개 성공, attempt1, 아티팩트0 |
| 준비 실행 | [43512140336](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43512140336), 성공, 작업4분35초 |
| 준비 본 작업 시간 | 211.692415초 |
| 독립 검증 실행 | [43514088919](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43514088919), 성공, 작업1분45초 |
| 독립 검증 본 작업 시간 | 93.875190초 |
| 이미지 아티팩트 | 14078483374, ZIP1,735,029,078B, SHA25662e09e31d565890a82b4965bafe855ad382e9a22794d12310fe0f06e695e920a |
| 실행 증거 아티팩트 | 14079975272, ZIP1,920,694,790B, SHAc315ec6301243f24c3b986a440ca00e152e9d721c3cbad7d753e9cd73b2277c6 |
| 독립 검증 아티팩트 | 14079832009, ZIP322,401,522B, SHAc6b065d08c6df430a70eec632954120e8c57f01b2dc5754c006aacb44b36db13 |
| 이미지 TAR | 1,726,678,016B, SHA256f69b8ece51bcc6911aaf118d5ea091ba4d6ace8418b480e408be5b9fd8cb2921 |
| 이미지 설정 digest | sha256:2b0854f1cf91e470994637f52f4e8c78c618ed00b1496a40bb05158290e01a37 |
| 설치 목록 | 44,232파일/심볼릭링크, 8,339,196B, SHA256f81fa5be38bc9853b6eff1d0ea524be97f3d1e92f5c1f0f9e1449a11b4c4b59f |
| 독립 검증 읽기 | 파일1,670,492,280B + Python 핵심23,107,322B =1,693,599,602B, 방문96,862회, 5.606337초 |
| 최종 CPU 테스트 | 1,067개 통과, 7개 건너뜀, 92.519초 |

이미지 TAR 해시, 설정 digest, archive-local OCI manifest/blob digest는 서로 다른 값이다. 로컬 태그와 OCI 이름 표기는 레지스트리 게시를 의미하지 않는다. 원본 이미지 아티팩트는 image.tar / preparation.json / installed-files.json 세 파일이다.

독립 실행은 정확한 이미지 ID, 읽기 전용 루트, 네트워크 없음, 모든 capability 제거, no-new-privileges, 메모리2GiB·CPU2·PID128·tmpfs64MiB 제한을 확인했다. 시작 전에 코드4파일51,729B, 원본 Python10,545항목305,721,228B, 실제 venv 실행 파일17,744B를 복사한 TAR에서 검증했다. 그 뒤 격리된 Python3.11.18의 표준 라이브러리로 저장된 설치 목록과 실제 파일 내용·모드·링크를 비교했다. 모델/렌더러 패키지를 import해 버전을 측정하지 않았다. 설치 METADATA의 NumPy2.4.6/OpenCV headless5.0.0.93/Panda3D1.10.13/MetaDrive0.4.3와 총53분포를 확인했다. ORT 분포와 onnxruntime 이름의 설치 항목은 없다. cv2 네이티브 API5.0.0은 고정된 기대값이며 import 관측값이 아니다.

준비와 독립 검증은 서로 다른 실제 CPU/커널 호스트에서 수행됐다. 각 컨테이너는 자기 호스트의 사전 관측과 일치했고 Docker 엔진 핵심은 같았다. 이것은 향후 엄격한 네이티브 C/A 호스트 일치나 성능 적격성을 증명하지 않는다. 후속 네이티브 프로토콜은 자체 소스·canary·실제 수락·예산·호스트 비교가 필요하다.

실제 입력의 자산 폴더 부재, Ubuntu 버전 라벨, usrmerge pager 별칭, 실행 목록의 초기 가시성, Docker28 저장 형식을 각각 확인해 반영했다. 입력 버전·바이트와 기존 검증기의 루트 범위를 유지했다. 새 effective policy8f214a1454557e588425d473cefa946c14e443e4cc47f85c1bfce02673d9552a는 pager 메타데이터 변환을 명시하며 이전1111정책은 보존했다. 요청001/002/004/005의 실제 실패 및 실행하지 않은003 등록은 보존했다. 이전 실패를 성공으로 바꾸거나 재실행하지 않았다.

공식 모델 호출0, native admission=false, scientific promotion=false, 레지스트리/Cloud 게시 없음, main 병합 없음. main48e79a7ed5aedf6daa5a62ff68d2225af7955ef1 및 과학 실험 workflow416199727의 기존 두 실행43251145868/43249493437은 유지됐다.

검증된 작은 권위 파일과 설치 목록은 [engine-clock-sealed-image-06](evidence/engine-clock-sealed-image-06/)에 있다. 최종 상태·전체 해시 목록은 [최종 JSON](evidence/STAGE7_ENGINE_CLOCK_SEALED_IMAGE_06_RESULT.json), 모든 실패·리뷰 판정·유보한 경미 항목과 비용은 [연속 작업 기록](STAGE7_ENGINE_CLOCK_CONTINUATION_LEDGER.md)에 남겼다. 원본 ZIP/TAR와 복사 TAR는 output/stage7-image-root-authentication/에 보존했고 Actions 보존 기간은30일이다.
