# 센서 NV12 원본 수신과 오프라인 비교

`python -B -m scripts.verify_sensor_nv12 --manifest /path/to/manifest.json --out /path/to/new-receipt.json`
을 실행합니다. 출력은 새 파일이어야 합니다. 레이아웃과 선택적 파생 텐서 검사는
NumPy를 사용합니다. 기존 카메라 검증과 같은 NumPy 2.4.6을 사용하면
투영 샘플링을 같은 라이브러리 버전에서 재현할 수 있습니다.

## 매니페스트

`schema`는 `offline-sensor-nv12-v1`, `capture_origin`은
`SENSOR_NATIVE_NV12`입니다. 센서가 기록한 8비트 NV12 버퍼를 사용합니다.
상대 파일 참조는 공통으로 `file`, 그 파일 전체의 `sha256`을 포함합니다.

| 필드 | 값 |
|---|---|
| `capture_history` | 장비·수집 경로·시간 기준·기준 텐서가 있으면 그 출처를 기록한 파일의 참조 |
| `cameras.road`, `cameras.wide` | 각 센서의 `sensor_model`, 짝수 `width`·`height`, `y_stride`·`uv_stride` 및 `y_offset`·`uv_offset` 바이트 값, `chroma_order: "UV"`, `color_range: "limited"` 또는 `"full"`, 수집 장치의 선언 `color_matrix`, 보정·장착 데이터의 `calibration_and_mount` 파일 참조 |
| `pairs[]` | 동일 장면의 `road`와 `wide` 원본 파일 참조. 각 참조에 `nbytes`, `frame_id`, `timestamp_ns`를 추가 |
| `warp` (선택) | `road`·`wide`별 목적지→원본 3×3 투영 행렬과 그 출처 및 적용 좌표계를 기록한 `source` 파일 참조 |
| `pairs[].reference_tensor` (선택) | 동일 프레임의 독립적으로 보존된 `uint8[2,6,128,256]` 원본 텐서 파일 참조. `warp`가 필요 |

파일은 매니페스트가 있는 디렉터리 아래에 둡니다. `nbytes`와 SHA‑256은
행 패딩과 끝 패딩을 포함한 **파일 전체**에 적용합니다. 활성 Y·UV 영역은
선언한 stride와 offset으로 읽습니다. 메타데이터 파일과 매니페스트는
각 128 KiB, 프레임 버퍼는 각 128 MiB까지 읽습니다.

## 판정 범위

레이아웃 검사에서는 원본과 활성 Y·U·V 바이트의 해시, 프레임 ID, 선언된
시간 차이를 기록합니다. 시간 차이의 허용 기준이나 색상 변환은 적용하지
않습니다. 선택적 투영은 기존 Linux 벤치마크의 최근접 짝수 반올림과
경계 좌표 제한을 사용해 `[road, wide]`의 `[Y00,Y10,Y01,Y11,U,V]`
텐서를 만듭니다. 이 샘플러는 원본 평면 축이 최대 4096인 경우를 지원합니다.
렌즈 왜곡이 있는 경우 별도의 왜곡 보정 경로와 측정 대응이 필요합니다.

`LAYOUT_VERIFIED`는 저장 구조를 읽은 결과입니다. `WARP_RECONSTRUCTED`는
기존 벤치마크 행렬로 텐서를 계산한 결과입니다. 모든 쌍에서 제공된 기준과
바이트가 일치해야 `REFERENCE_MATCH`입니다. 기준이 일부 쌍에만 있으면
`REFERENCE_PARTIAL`이며, 차이가 있으면 `REFERENCE_MISMATCH`에 카메라별·
평면별 차이 수와 최초 차이 좌표를 기록합니다. 자료 부재는 `BLOCKED`,
입력 오류는 `INPUT_ERROR`입니다. 종료 코드 1은 기준 불일치, 2는
자료 부재 또는 입력 오류입니다.

원본 촬영 이력은 제공자가 선언합니다. 이 도구의 결과는 생산 카메라의
ISP·워프·동기화나 물리 광학 인증과 별개입니다. 센서에 연결하거나 모델
세션을 만들지 않으므로 공식 추론 수는 항상 0입니다.
