# Windows · RTX 3050 Ti Laptop GPU 실행 안내

2026-11-18 KST. 대상은 Windows x64, Python 3.11, NVIDIA GeForce RTX 3050 Ti Laptop GPU입니다. 노트북에 원격 접속한 상태가 아니므로 아래 현지 실행 결과가 필요합니다. 클라우드 실제 시험은 [결과 기록](evidence/four-validation-20261118/README.md)에 있습니다. **전체 S 경로 완주 0/4, 반복 일치 4/4**이며, Windows의 동작을 보증하는 결과는 아닙니다.

## 1. 먼저 설치 없이 사양 확인

host 수정본은 `feature/windows-msaa-host-v1` 브랜치입니다. 기존 `feature/sdk3-four-validation-v1`의 소스14297e2는 로컬 보고서에서 원본 GPU 검사가 실패했던 버전으로 보존합니다. 수정 브랜치 소스를 노트북에 받으세요. PowerShell에서 저장소 폴더로 이동합니다. Python이 없으면 [Python 3.11 Windows x64](https://www.python.org/downloads/windows/)를 설치합니다.

```powershell
py -3.11 scripts\run_laptop_validation.py --mode inventory --out output\laptop-inventory-01
```

이 명령은 RAM·여유 디스크·GPU/드라이버와 선택적 라이브러리 유무만 기록합니다. 모델, 서버, GPU 창을 실행하거나 설치·다운로드하지 않습니다. `inventory.json`의 `full_s`는 **기존 Linux SDK3 환경**의 준비 조건입니다. Windows 실행 조건은 별도 `windows-readiness.json`에 있습니다. 같은 출력 폴더를 덮어쓰지 않으므로 다음 실행에는 `-02`처럼 새 이름을 쓰세요.

NVIDIA GPU 메모리는 실제 `nvidia-smi` 응답으로 기록합니다. 이 GPU 이름만으로 VRAM 용량이나 CARLA 실행 가능 여부를 추정하지 않습니다. Windows full-S 사전 조건은 사용 가능 RAM 8 GiB, 디스크 4 GiB 이상이며 실제 실행 중 메모리 부족은 별도 실패로 남습니다.

## 2. 별도 Python 환경과 GPU 검사

```powershell
py -3.11 -m venv .venv-laptop
.\.venv-laptop\Scripts\python.exe -m pip install numpy==2.4.6 opencv-python==5.0.0.93 panda3d==1.10.13 metadrive-simulator==0.4.3 onnxruntime==1.20.1
.\.venv-laptop\Scripts\python.exe -m metadrive.pull_asset
.\.venv-laptop\Scripts\python.exe scripts\run_laptop_validation.py --mode gpu --out output\laptop-gpu-01
```

패키지와 MetaDrive asset 다운로드는 위 명시적 설치 명령에서 일어납니다. 가상환경 활성화나 PowerShell 실행 정책 변경은 필요하지 않습니다. `opencv-python`과 `opencv-python-headless`를 같은 가상환경에 함께 설치하지 마세요.

GPU 검사는 모델 없이 두 색상 화면과 MSAA를 켜고 끈 삼각형 경계 대조 화면을 각각 8×8 RGBA로 렌더링합니다. 활성 WGL 컨텍스트의 NVIDIA 렌더러, 실제 샘플 수, 전체 픽셀 읽기와 정리를 확인합니다. GL_MULTISAMPLE 상태와 실제 경계의 부분 커버리지도 확인하여 샘플 버퍼만 있고 MSAA가 꺼진 경우를 구별합니다. **MSAA 4를 요청했다는 사실만으로 통과하지 않습니다.** Optimus가 Intel GPU를 선택하면 Windows 설정 → 시스템 → 디스플레이 → 그래픽에서 이 가상환경의 `python.exe`를 추가하고 고성능 NVIDIA를 선택한 뒤 새 폴더로 재실행하세요.

이 결과의 범위는 해당 Windows stock-Panda 프레임버퍼입니다. Linux SDK3 `.so`를 Windows DLL로 사용하지 않으며, 모델 카메라의 MSAA나 실제 광학을 인증하지 않습니다. 현재 클라우드에서 이 실제 Windows GPU 검사는 **미실행**입니다.

## 3. 공식 모델의 Windows S 경로 시험

원하는 경우에만 공식 가중치를 내려받습니다(768,750,198 바이트). 인벤토리/GPU 명령은 이를 내려받지 않습니다.

```powershell
New-Item -ItemType Directory -Force models
Invoke-WebRequest -Uri 'https://huggingface.co/commaai/openpilot_driving_models/resolve/main/1365126a-e71e-4778-be00-8ab92dc82c09/12864/big_driving_supercombo.onnx' -OutFile models\md-v3.onnx
Get-FileHash models\md-v3.onnx -Algorithm SHA256
.\.venv-laptop\Scripts\python.exe scripts\run_laptop_validation.py --mode full-s --model models\md-v3.onnx --out output\laptop-full-s-01
```

필수 SHA256: `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`.

GPU와 네 조건의 무모델 원본 카메라 검사를 먼저 실행합니다. 통과하면 두 seed × 두 S 방향을 각각 두 개의 새 프로세스로 실행합니다. 공식 추론은 ORT 1.20.1 **CPU**이며 NVIDIA GPU는 렌더링에 사용합니다. 최대 8 모델 프로세스·4,800 추론·프로세스당 600스텝/9,000초입니다. 실제 DLL/라이브러리/소스 해시와 활성 카메라 드라이버를 기록합니다. Windows 모델 실행은 아직 실제 검증되지 않았으며 초기 호환성 오류도 그대로 보존됩니다.

속도 8 m/s, 간격 0.05 s, 기존 FRD→FLU 변환을 한 번 적용합니다. 차선 침범 즉시 실패로 종료하며 입력 재생·조향 구제·모델 조정은 없습니다. `case-results.json`의 `traversal_passed`와 `strict_repeat_passed`를 따로 확인하세요. 진단 프로그램의 종료 코드 0이나 `MEASURED`는 완주 통과를 뜻하지 않습니다. 오류·시간 초과는 원본 로그와 `lifecycle.json`/`owner.json`/`error.json`의 불확실한 추론 범위를 유지합니다.

## 4. 실제 카메라 자료가 있을 때만

```powershell
.\.venv-laptop\Scripts\python.exe scripts\run_laptop_validation.py --mode physical --calibration C:\private\camera-data\manifest.json --out output\laptop-optics-01
```

자료가 없으면 `BLOCKED`입니다. 촬영이나 차량 연결을 자동으로 수행하지 않습니다. 모든 원본 영상은 해당 로컬 폴더에 남습니다. 업로드 명령은 없습니다.

지원하는 계약은 **고정된 독립 보정값으로 검사하는 Brown5 체커보드 공간 투영**입니다. 전체 물리 광학·노출·시간 동기·롤링 셔터·장착 오차 인증은 아닙니다. 합성 영상이나 선언만으로 실제 촬영을 원격 인증할 수 없으므로 결과에 그 한계를 기록합니다. `SCOPED_PASS`여도 `physical_optics_validated`는 false입니다.

매니페스트 필수 필드:

- `schema: "offline-camera-holdout-v1"`, `provenance: "OFFLINE_MEASURED_CAMERA_CORRESPONDENCES"`, `pose_source: "INDEPENDENT_BOARD_POSE_NOT_FIT_ON_HOLDOUT"`.
- `calibration: {"file": "calibration.json", "sha256": "실제 파일 SHA256"}`. 보정 파일에는 `model: "PINHOLE_BROWN5"`, `cameras.road/wide` 각각 `width`, `height`, 3×3 `K`, `[k1,k2,p1,p2,k3]` `distortion`이 필요합니다.
- `board: {"inner_columns": 9, "inner_rows": 6, "square_size_m": 0.025}`처럼 실제 측정값을 지정합니다.
- 보정 파일의 `training_images`와 매니페스트의 `heldout`은 각각 road/wide별 최소 3장의 서로 다른 영상 레코드입니다. 각 레코드에는 `camera`, 상대 `file`, 실제 `sha256`이 필요합니다. 두 집합은 파일 SHA와 해독한 영상 픽셀 SHA 모두 겹칠 수 없습니다. 모든 학습 영상도 실제 해독과 해상도 검사를 통과해야 합니다.
- `heldout`의 각 레코드에 `board_to_camera: {"rotation": 3×3, "translation_m": [x,y,z]}`를 추가합니다. 이 자세는 홀드아웃 영상에 맞춰 피팅한 값이 아닌 독립 측정값이어야 합니다. 좌표는 광학 카메라의 오른쪽/아래/앞, 보드 점 순서는 OpenCV 체커보드 검출 순서입니다.

프로그램이 실제 영상을 해독하고 코너를 직접 검출합니다. 매니페스트의 `passed`나 임의 픽셀 좌표는 사용하지 않습니다. 고정 기준은 영상별 RMS ≤1 px, 최대 오차 ≤2 px입니다. 지원하지 않는 렌즈 모델·유효하지 않은 자세·검출 실패는 오류로 남습니다.

## 5. CARLA 전용 서버를 준비한 뒤

CARLA는 별도 서버 설치와 상당한 디스크/메모리를 요구합니다. 이 노트북에서의 가동 여부·속도는 아직 측정하지 않았습니다. 우선 MetaDrive/GPU 검사 결과를 확인하세요. [공식 CARLA 릴리스](https://github.com/carla-simulator/carla/releases/tag/0.9.16)에서 **0.9.16 서버**를 준비하고, 그 배포본의 실행 안내로 별도 인스턴스를 시작합니다. 다른 작업에 쓰는 서버를 지정하지 마세요.

```powershell
.\.venv-laptop\Scripts\python.exe -m pip install carla==0.9.16
.\.venv-laptop\Scripts\python.exe scripts\run_laptop_validation.py --mode carla-readiness --carla-host 127.0.0.1 --carla-port 2000 --dedicated-carla --out output\laptop-carla-ready-01
.\.venv-laptop\Scripts\python.exe scripts\run_laptop_validation.py --mode carla-full-s --carla-host 127.0.0.1 --carla-port 2000 --dedicated-carla --model models\md-v3.onnx --out output\laptop-carla-full-s-01
```

준비 검사는 버전만 확인하며 교차 엔진 검증 통과가 아닙니다. full-S 명령은 전용 서버의 지도를 임시로 바꿉니다. 기존 차량·보행자·센서·컨트롤러가 있으면 시작을 거부합니다. 클라우드에서 인증한 네 조건의 MetaDrive 기하를 OpenDRIVE로 만들고, 실제 CARLA waypoint 위치/방향 일치와 두 카메라의 프레임 ID, 반환된 영상의 실제 위치·높이·방향을 요청한 직전 이상적 자세와 대조합니다. 원본 지도·날씨·설정을 복원하고 소유 센서만 정리합니다. **서버 경과 시각은 복원할 수 없습니다.** 부모 프로세스는 자식 시간 초과 때도 복구를 시도하며, 외부 동적 액터를 발견하면 지도 재설정을 거부하고 복구 실패를 기록합니다.

CARLA도 별도 최대 8 모델·4,800 추론입니다. 두 로컬 백엔드를 모두 명시적으로 실행하면 합계 최대 16 모델·9,600 추론입니다. 동일 엔진의 두 실행만 픽셀 단위로 비교합니다. 엔진 간 영상 일치나 주행 품질 순위는 요구하지 않으며, 공통 기하·시계·카메라·동작 변환·이상적 운동 계약과 각 완주 결과를 따로 기록합니다. **실제 CARLA 실행은 아직 미실행**이고 이 어댑터는 순수 계약 테스트만 거쳤습니다.

처음에는 `inventory.json`, `windows-readiness.json`, `gpu.json`과 오류가 있으면 `error.json`만 확인하면 됩니다. 개인 촬영 원본이나 모델 파일을 공유할 필요는 없습니다.

## host 수정본 재검사

로컬 보고서에서 실패한 원본은 host/GSG 없이 MSAA 버퍼를 요청했습니다. 수정본은 샘플0의 비활성 offscreen host를 먼저 열고 그 GSG를 실제 요청 샘플 버퍼에 전달합니다. 샘플0은 컨텍스트 준비용이며 검사 대상의 샘플 기준을 낮추는 것이 아닙니다. 두 출력은 callback 복원 후 정리됩니다. 기존 원본 실패와 별도 메모리 실험은 그대로 보존합니다.

기존 환경·증거·로컬 변경을 보존한 뒤 로컬 Codex에서 새 수정 브랜치로 전환하고 다음 명령을 실행하세요. 이미 설치한 `.venv-laptop`을 그대로 사용하므로 이 GPU 재검사에는 자산/모델 다운로드가 필요하지 않습니다.

```powershell
.\.venv-laptop\Scripts\python.exe scripts\run_laptop_validation.py --mode gpu --out output\laptop-gpu-host-fix-01
```

출력은 새 `windows-panda-gpu-attempt-v2`이며 정상 측정 시 construction 표지가 `OWNED_ZERO_SAMPLE_OFFSCREEN_HOST_AND_REQUESTED_MSAA_FBO_V1`입니다. 실제 색상·경계·GL sample/state 기준은 기존 readback-v2와 같습니다. 소프트웨어/Linux API 검사나 모의 테스트의 통과가 이 실제 Windows 재검사를 대신하지 않습니다. 모델 카메라·물리광학·CARLA 검증도 별도입니다.

보고서 측정 당시 사용 가능 RAM은 약4.68GiB로 Windows full-S의8GiB 기준에 미달했습니다. 이 수정은 메모리 기준을 변경하지 않습니다. 별도 클라우드 full-S 작업의 결과는 해당 작업의 원본 기록이 전달돼야 확인할 수 있습니다.
