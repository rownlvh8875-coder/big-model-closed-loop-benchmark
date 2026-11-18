# full-S 실패 구간 기록 준비

기존 source54의554개 기록을 분석했지만, 첫8입력 외546입력의 실제 픽셀과
전체 재귀 상태 배열은 남아 있지 않습니다. 새 `full_s_failure_capture`는 다음
진단에서 첫 입력과 실패 직전 구간을 보존하기 위한 도구입니다. 과거 자료를
복원하거나 현재 별도 클라우드 작업을 다시 실행하지 않습니다.

## 지금 실행할 수 있는 명령

저장 공간 계획은 표준 라이브러리만 사용합니다. 모델·시뮬레이터·GPU가 필요하지
않으며 실행을 활성화하지 않습니다. 출력 폴더는 새 경로여야 합니다.

```bash
python -I -S -B scripts/full_s_failure_capture.py plan --out output/failure-recording-plan-01
```

수신한 기록은 NumPy/OpenCV로 검사합니다. 기록한 환경과 같은 라이브러리 버전과
기록기의 source checkout을 사용합니다. 이 명령은 파일을 읽고 별도 결과를 쓰며
모델을 실행하지 않습니다.

```bash
python -I -B scripts/full_s_failure_capture.py verify --record-dir /path/to/recording --out output/failure-recording-check-01
```

실제 모델 실행용 CLI·워크플로·요청 파일은 추가하지 않았습니다. 현재 준비된
것은 CPU 기록기와 오프라인 수신기이며 실제 모델/카메라에 연결한 실행은 아직
검증하지 않았습니다.

## 보존 내용과 상한

- 첫 스텝과 마지막8스텝을 합쳐 최대9개 묶음을 보존합니다. 추론이 미완료이면
  그 시도의 입력·이전 상태가 마지막 구간에 포함됩니다. 최대600스텝의 해시는
  전부 남깁니다. 중간에 버린 배열은 해시에서 복구할 수 없습니다.
- 한 묶음은 기존964×604 road/wide source RGB, 실제512×256 보정 RGB,
  보정 영상으로 계산한 I420 입력, 모델 부모 객체의 이전/이후 재귀 상태,
  실제 FP32 원시 출력을 포함합니다. 완료한 스텝만 실제 입력 해시와 결합합니다.
- 추론 실패 시 이후 상태·출력을 만들어 내지 않습니다. 원래 실행의
  `[하한, 상한]` 추론 횟수와 실패 보고서를 유지합니다.
- **실패 이후 추가 주행은 없습니다.** '이후'는 중단 스텝이 만든 상태를 뜻하며
  차선 침범 뒤 별도 캡처·추론·이동을 추가하지 않습니다.
- 한 완전 묶음의 배열은25,391,024바이트입니다. observer의 보수적 배열·해시
  원장 예상량은 약295MiB이며, 모델/native 메모리와 Python 객체 부하는 포함하지
  않습니다. 전체 프로세스 RSS 상한을 뜻하지 않습니다.
- 출력은 보고서·manifest를 포함해 최대320MiB이며 시작 전에384MiB의 여유를
  요구합니다. 가상의8회 진단을 계획할 때는3GiB를 잡습니다. 실제 실행은 하지
  않았습니다. 모든 묶음은 원래 루프가 끝날 때 파일로 저장하며 오래된 증거를
  지우는 디스크 순환 방식은 사용하지 않습니다.

## 향후 실행기에 연결할 때

기존 부모의 플랫폼/자원/프로세스 소유권/공식 모델 SHA/SDK·카메라 사전 검사를
통과한 별도 진단 worker에서만 아래 library helper를 연결합니다. 이 helper는
모델·provider 생성이나 종료, 시간제한·자원 상한·소유권 검사와 복구를 대신하지
않습니다. 지금 그 부모 실행기에 연결하거나 자동 실행하지 않았습니다.

```python
from bigbench.full_s_failure_capture import capture_full_s

# policy: 원래 WorldFramePolicyAdapter(AuditedOfficialOnnx(...))
# camera: 원래 NativeWorldCamera(provider), raw_rgb_observer=None
# intrinsics: 원래 두 렌즈의 CPU getter로 측정한 PinholeIntrinsics
# lanes, seed, scene: 기존 등록된 조건; provider 정리는 기존 finally에서 수행
report = capture_full_s(
    policy, camera, lanes, intrinsics=intrinsics,
    out=fresh_private_output, seed=seed, scene=scene,
    max_steps=600, progress=existing_lifecycle_callback,
)
```

원래 `run_full_s`와 단일 좌표 변환 adapter, 카메라·모델·차량 이동 계산을 그대로
호출합니다. 카메라 proxy는 기존 캡처를 한 번만 전달하고 같은 road/wide 객체를
반환합니다. 기존 CPU 원본 영상 관찰 지점과 progress 이벤트에서 상태를 복사하며
추가 모델 호출이나 reset을 하지 않습니다. 이미 사용 중인 raw observer는 거부하고
연결한 observer는 `finally`에서 복구합니다. 원래 보고서는 payload 저장 전에
별도로 보존하며, 저장 실패는 예외로 남고 유효 manifest가 완성되지 않습니다.

intrinsics는 호출자가 제공한 측정값으로 표시합니다. 독립적으로 측정 장비의
출처를 인증하지 않습니다. 입력 I420는 실제 보정 영상으로 재계산한 배열이며,
완료한 스텝의 부모가 기록한 실제 graph-feed SHA와 정확히 일치할 때 결합합니다.
상태 배열은 step 호출 경계에서 관찰한 부모 상태입니다. ONNX 세션의 모든
입력 tensor를 직접 가로챈 결과라고 부르지 않습니다.

## 검사 결과의 의미

수신기는 크기·dtype·유한성·SHA·원본 보고서 결합·단계별 상태 연속성·선택한
첫/마지막 구간을 검사합니다. 보존된 source에서 원래 보정을 다시 계산하고
실제 canvas 및 I420와 바이트 단위로 대조합니다. symlink·경로 이탈·누락·중복
JSON 키·등록되지 않은 파일/폴더·큰 payload를 거부합니다. pickle이나 증거 속
코드를 실행하지 않습니다.

`recording_structure_valid`는 로컬 자료 구조와 바이트 결합의 결과입니다.
GitHub 원본 실행 출처·실제 모델 실행·하드웨어·물리 광학·CARLA·완주나 엄격
반복 통과를 인증하지 않으며 관련 qualification은 항상 false입니다. 출처
인증에는 향후 실제 실행의 API 메타데이터·artifact SHA·소스·lifecycle 대조가
별도로 필요합니다.

복사·해시 계산은 wall timing과 메모리 배치를 바꿀 수 있습니다. 기존 실행과
같은 실험으로 간주하지 말고 별도 진단으로 기록해야 합니다. 이번 단위 검사는
실제 원래 loop/adapter/policy 코드를 사용하되 외부 렌더러와 ONNX 세션만 CPU
fixture로 대체합니다. 생성된 영상과 상태는 실제 카메라/공식 모델 증거가 아닙니다.
기존 완주0/4·엄격 반복 일치4/4와 RTX8×8 MSAA 통과 범위는 그대로입니다.
