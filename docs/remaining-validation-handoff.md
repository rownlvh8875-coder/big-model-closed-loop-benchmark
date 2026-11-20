# 남은 실제 검증: 로컬 Codex 인계

클라우드 실험 소스 브랜치 `feature/preprocess-four-track-v1`의 문서입니다.
기존 작업 디렉터리와 증거 파일을 유지하고 별도 worktree에서 실행하세요.
main 병합, 환경 게시, 이전 실행 요청 재활성화, 기존 결과 덮어쓰기는 하지 않습니다.
현재 클라우드에는 아래 장비/자료 접속이 없습니다. 이 문서는 검증 완료 증거가 아닙니다.

## Windows RTX 3050 Ti: 카메라 장면 + 공식 모델

RTX3050Ti Laptop GPU의 기존 통과 증거는 8×8 프레임버퍼/4×MSAA입니다.
장면 렌더링이나 모델 실행 통과를 의미하지 않습니다. 이 경로는 NVIDIA가
카메라 렌더링을 담당하고 공식 모델은 ORT1.20.1 **CPU**로 실행합니다.
GPU VRAM4GB에 모델을 올리는 CUDA 경로는 검증 대상이 아닙니다.
Windows x64/Python3.11/MetaDrive0.4.3/Panda1.10.13/NumPy2.4.6/
OpenCV5.0.0.93 설치 여부와 실제 NVIDIA 렌더러를 먼저 확인합니다.
이미 설치된 지정 Python의 절대 경로를 사용하세요.

```powershell
$py = 'C:\실제경로\python.exe'
& $py -I -B scripts/validate_laptop_environment.py --out output/rtx-readiness-01.json
& $py -I -S -B scripts/run_laptop_validation.py --mode process-check --out output/rtx-owned-process-01
```

가용 RAM **8GiB 이상**, 빈 디스크4GiB 이상이어야 모델을 시작합니다.
이전 관측 가용 RAM4.24GB는 부족했습니다. 프로그램을 닫은 뒤 실제 값을
재측정하고 부족하면 `BLOCKED`를 유지합니다. 제한을 낮추거나 실패 뒤
자동 재시도하지 않습니다. 공식 모델 파일이 이미 있다면 다음을 실행합니다.
모델768750198B/SHA256
`35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`
검사를 통과해야 하며, 이 명령은 다운로드하지 않습니다.

```powershell
$model = 'D:\실제경로\big_driving_supercombo.onnx'
& $py -I -B scripts/run_laptop_validation.py --mode full-s --model $model --out output/rtx-full-s-01
```

이 기존 실행기는 GPU canary→4조건 실제 카메라/렌즈/위치 probe→
4조건×2독립 모델 실행(최대8모델/4800추론)을 수행합니다. 과거 결과와
새 결과를 섞지 말고 성공/탈선/오류/정리 상태를 모두 보관하세요.
NVIDIA 장면/모델 통합 관측, 동일 입력 재현성, full-S 완주 여부를 각각
보고합니다. 원본 Linux SDK3/물리 광학 검증으로 확대하지 않습니다.

## 실측 광학 및 진짜 NV12 자료

현재 실측 자료가 없습니다. 합성 체크보드, 기존 가상 RGB를 NV12로
변환한 자료, 홀드아웃에서 맞춘 자세는 실측 통과 증거로 사용할 수 없습니다.

기존 공간 보정 검사는 `bigbench/offline_camera_validation.py`의
`offline-camera-holdout-v1` 계약입니다. road/wide 각각 실제 보정 학습
이미지 최소3장과 별도 홀드아웃 최소3장, 실측 보드 치수, 각 홀드아웃의
독립 측정 보드→카메라 자세, PINHOLE_BROWN5 K/왜곡 계수, 원본 파일과
SHA256이 필요합니다. 홀드아웃 오차 기준은 RMS1px/최대2px 고정입니다.

```powershell
& $py -I -B scripts/run_laptop_validation.py --mode physical --calibration 'D:\실측자료\manifest.json' --out output/physical-holdout-01
```

이 검사는 공간 재투영 범위의 `SCOPED_PASS`까지만 판정합니다.
노출/시간 동기/롤링셔터/장착/센서 입력 일치까지 인증하지 않습니다.
NV12 대조에는 동일 장면의 **센서가 출력한 원본 NV12**와 road/wide
역할·프레임 번호·시간·센서 모델·해상도·Y/UV stride·UV offset·UV 순서·
색 범위/행렬·캘리브레이션/장착 값·수집 이력·SHA256을 추가로 제공해야 합니다.
현재 RGB 대조 실험은 이 센서 자료를 대체하지 않습니다. 진짜 자료를
확보한 뒤 그 선언에 맞춘 별도 byte/warp 검증이 필요합니다.

## CARLA 실제 서버와 비교

CARLA0.9.16 클라이언트/서버가 정확히 일치해야 합니다. 전용 서버의
호스트/포트와 서버 변경 권한이 필요합니다. 다른 사용자가 쓰는 서버에서
실행하지 않습니다. 준비 검사는 서버 버전만 조회하고 world를 변경하지 않습니다.

```powershell
& $py -I -B scripts/run_laptop_validation.py --mode carla-readiness --carla-host '실제서버주소' --carla-port 2000 --dedicated-carla --out output/carla-readiness-01
```

`READY_FOR_PROBE`인 경우에만, 같은 공식 모델로 실제 카메라/등록 경로
probe 후4조건×2독립 실행을 진행합니다(최대8모델/4800추론).

```powershell
& $py -I -B scripts/run_laptop_validation.py --mode carla-full-s --carla-host '실제서버주소' --carla-port 2000 --dedicated-carla --model $model --out output/carla-full-s-01
```

센서 frame/ego pose/원본 RGB 해시/도로 기준과 정리 복구 영수증을 보관합니다.
동일 seed는 엔진 간 동일 영상의 증명이 아닙니다. 실제 궤적/기준 계약과
실패 위치를 비교하고, 엔진/렌더러 차이를 별도로 표시합니다.

## 결과 인계

새 출력 폴더 전체를 ZIP으로 전달하세요. 파일 해시와 실행 커밋·Python 경로·
종료 코드·실제 실행 횟수·단계별 범위·실패·정리 복구를 포함하고 모델 가중치와
비밀키는 ZIP에 넣지 않습니다. 출력 폴더가 이미 있으면 새 접미사를 사용하세요.
자료나 서버가 없다면 해당 항목을 `BLOCKED`로 남깁니다.
