# 기록기와 full-S worker 본체 연결

이 단계는 기존 기록기를 원래 모델·카메라 생성 경로와 연결한 별도 Linux SDK3
worker 본체입니다. 기존 과학 코드와 기록기 구현을 변경하지 않습니다. 사용자가
별도 「공식 모델 full-S 클라우드 실행 및 실패 분석」 작업의 상태를 모른다고
답했으므로 실제 모델 실행·새 활성화 요청/워크플로는 추가하지 않았습니다.
저장소 Actions 목록에 진행 중인 대응 작업이 없다는 사실만으로 다른 Codex
작업이 끝났다고 판단하지 않습니다.

## 모델 없이 실행할 수 있는 검사

두 명령 모두 새 출력 폴더를 사용합니다. 표준 라이브러리만 필요하며 Windows에서도
동작합니다. 모델·SDK·GPU·CARLA를 실행하거나 다운로드하지 않습니다.

```bash
python -I -S -B scripts/full_s_recorded_worker.py preflight --out output/recorded-worker-preflight-01
python -I -S -B scripts/full_s_recorded_worker.py process-check --out output/recorded-worker-process-01
```

preflight는 별도 작업 상태를`NOT_OBSERVED`, 실행 활성화를false로 기록합니다.
process-check는 실제 같은 진입점의 자식 프로세스를 실행해 정확한 PID·부모·nonce·
조건·모드·가상환경 경로를 확인하고 자식을 회수합니다. Python은`-I -S -B`로 시작해
시작 hook을 차단합니다. Windows venv에서는 공용 base-interpreter 실행 방식을
사용합니다. Popen 인터럽트로 핸들을 받지 못하면 생성 여부를 미확인으로 유지합니다.
`PROCESS_CHECK_PASS`는 소유권 검사이며 native 카메라/모델 통과가 아닙니다.

## 향후 별도 부모 실행기에 연결할 본체

`run_recorded_trial(args)`는 원래`full_trial`과 같은 out/nonce/seed/scenario 인자를
받습니다. out은 **부모 로그/소유권 파일 폴더와 다른 새 전용 하위 폴더**를 지정합니다.
부모의 소스·artifact 출처·모델 SHA·자원·PID 승인, frozen core/SDK bootstrap,
Xvfb/컨테이너/9000초 제한은 호출 전에 원래 실행기가 수행해야 합니다. 이 함수는
그 검사를 대신하거나 자체 수행했다고 주장하지 않습니다. 실행 CLI에는 이 본체를
호출하는 명령이 없습니다.
기존 full-S 수신기는 관찰기가 없는 원래 cohort를 검사하므로 이 새 receipt를
그대로 받는 경로가 아닙니다. 실제 실행 시에는 별도 부모/수신기가 이 worker의
소유권·lifecycle·recording 결과를 함께 확인해야 합니다.

```python
from types import SimpleNamespace
from pathlib import Path
from bigbench.full_s_recorded_worker import run_recorded_trial

# 별도 승인된 부모가 기존 사전 검사와 SDK bootstrap을 마친 이후에만 연결
body_args = SimpleNamespace(
    out=Path(args.out) / 'observed-trial',
    nonce=args.nonce, seed=args.seed, scenario=args.scenario,
)
receipt = run_recorded_trial(body_args)
```

본체는 원래 AuditedOfficialOnnx를 한 번 만들고, 단일 WorldFramePolicyAdapter와
원래 `_world`/terrain·lane 구성 및 NativeWorldCamera를 사용합니다. 원래 렌즈의
CPU getter로 intrinsics를 읽고 기존 capture_full_s(max_steps=600)를 호출합니다.
원래8m/s·dt0.05·초기12%·원시 조향·차선 침범 기준은 그대로이며 추가 capture,
추론, reset, GT 보정이나 전역 함수 교체가 없습니다. 입력/상태 복사에 따른 시간·
할당 영향은 별도 진단의 한계로 남습니다.

생성한 provider는 종료 경로에서 한 번 정리합니다. 추론 실패가 먼저 발생하고
정리가 실패해도 첫 오류를 유지하고 정리 오류를 secondary_errors에 남깁니다.
원래 기록기의 보고서·추론 범위는 바꾸지 않고 별도 lifecycle/trial 영수증을 씁니다.
생성 실패는 추론0회로, 미완료 호출은 원래 보수적 범위로 남깁니다. 최종 영수증
쓰기나 source/runtime metadata 수집이 실패해도 TrialFailure.report와
TrialFailure.inference_bounds에서 확보한 원래 결과를 받을 수 있습니다.

파일 구성은 다음과 같습니다.

| 파일 | 의미 |
|---|---|
| recorded-trial-lifecycle.json | 생성·진행·정리·실패 상태와 추론 범위 |
| recorded-trial.json | 별도 관찰 사실, driver/session/source 정보와 정리 결과 |
| recording/report.json | 기존 full-S 기록기가 저장한 원래 보고서 |
| recording/manifest.json 및 step-* | 첫/마지막 구간 픽셀·상태와 전체 해시 |

기록기 출력은 원래 [기록기 가이드](FULL_S_FAILURE_CAPTURE.md)의 offline verify로
검사합니다. mock/injected와 실제 ORT session 정보는 구분해서 기록하되, 그 값이나
로컬 파일 일관성 검사만으로 실제 외부 실행의 출처를 인증하지 않습니다.
새 worker source 지문은 onnx_contract.py/lane_truth.py도 포함한 선택 목록이며
전체 의존성 closure나 설치 바이너리 동등성의 인증은 아닙니다.

Linux 본체의 단위 검사는 원래 loop/adapter/policy와 기록기를 사용하고 외부
world/camera/graph만 CPU fixture로 대체합니다. 그 결과는 실제 모델/카메라 증거가
아닙니다. Windows CI에서는 portable preflight·실제 자식·빈 venv만 검사하며 Linux
SDK3 본체 검사는 건너뜁니다. 기존 Windows native 모델 실행기와는 별도입니다.

현재 모든 native/모델 카메라/RTX/물리 광학/CARLA qualification은false입니다.
기존 완주0/4·엄격 반복4/4를 바꾸지 않습니다. 다음 실제 실행의 승인된 부모 연결과
출처 인증은 별도 작업의 결과 확인 뒤에 다뤄야 합니다. 환경 게시/main 병합은 없습니다.
