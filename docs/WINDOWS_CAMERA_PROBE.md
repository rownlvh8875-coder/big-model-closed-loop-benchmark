# Windows 원래 카메라 검사 — 모델 실행 없음

2026-11-18 KST. 대상은 기존 Windows x64/Python3.11, RTX3050Ti Laptop GPU입니다. [92fc0b4의 실제8×8 GPU/MSAA 검사](evidence/windows-camera-probe-20261118/README.md)는 통과했습니다. 다음은 별도 `probe_laptop_camera.py`로 **원래 MetaDrive 카메라의 가상 핀홀·영상 변환**을 검사합니다. 기존 full-S 실행 안에 묶인 사전검사를 모델 파일 없이 진행할 수 있습니다.

## 로컬 Codex 실행 지시

새 ZIP을 새 폴더에 풀고 기존 소스·가상환경·증거를 보존합니다. 이미 설치된 이전 가상환경의 Python 전체 경로를 사용합니다. 아래 첫 줄의 경로만 실제 경로로 바꿉니다.

```powershell
$probePython = 'C:\기존저장소\.venv-laptop\Scripts\python.exe'
& $probePython -I -B scripts\probe_laptop_camera.py --mode inventory --out output\windows-camera-inventory-01
```

설치된 패키지 버전은 numpy2.4.6, opencv-python5.0.0.93, panda3d1.10.13, metadrive-simulator0.4.3이어야 합니다. 사양 수집은 설치·다운로드·Panda/ORT import를 하지 않습니다. 자산 검사는 `assets/version.txt`의0.4.3과 MetaDrive의 갱신 판단에 쓰는 `textures/grass1/GroundGrassGreen002_COL_1K.jpg` 존재를 함께 확인합니다. 버전 표지만 있고 이 텍스처가 없으면 부분 설치로 `BLOCKED`됩니다. 출력 공간은 `--out`이 있는 드라이브에서 측정합니다.

`inventory.json`에서 asset 문제만 확인되면 아래 **명시적 자산 준비**를 한 번 진행합니다. MetaDrive0.4.3 자산 아카이브는 약134MB이며 가상환경의 `metadrive/assets`에 설치됩니다. 기존 자료의 해시를 먼저 보존하고, 기존 자산 폴더가 있으면 아래처럼 별도 이름으로 옮겨 보존한 뒤 새 자산 폴더를 준비합니다. `pull_asset`는 버전 표지만 있는 부분 설치를 건너뛸 수 있으므로 부분 폴더 위에 그대로 실행하지 않습니다. 완전한 자산0.4.3이 있으면 준비를 생략합니다. 모델 파일은 필요 없습니다.

```powershell
$cameraInventory = Get-Content output\windows-camera-inventory-01\inventory.json | ConvertFrom-Json
$assetDirectory = Split-Path $cameraInventory.assets_file -Parent
if (Test-Path -LiteralPath $assetDirectory) {
    $assetBackup = "$assetDirectory-before-camera-probe-01"
    if (Test-Path -LiteralPath $assetBackup) { throw '기존 자산 백업 이름이 있습니다. 새 이름을 정하세요.' }
    Move-Item -LiteralPath $assetDirectory -Destination $assetBackup
}
& $probePython -m metadrive.pull_asset
```

자산/버전 준비를 마치면 아래 **카메라 검사만 한 번** 실행합니다. 이미 사용한 출력 이름이면 새 이름을 사용하며 결과를 덮어쓰지 않습니다. 실패한 조건을 골라 재시도하지 않습니다.

```powershell
& $probePython -I -B scripts\probe_laptop_camera.py --mode probe --out output\windows-camera-probe-01
```

기존8×8 GPU 검사를 반복하거나 공식 모델/ORT 추론·full-S·CARLA를 실행하는 명령이 아닙니다. 카메라 명령은 자동 다운로드를 하지 않습니다. 자산 누락은 native 시작 전 `BLOCKED`; 실제 worker의 Python 네트워크·다운로드·추가 프로세스 시도는 거부됩니다. 필요한 자산 준비는 위 명령으로 분리했습니다.

## 실행·검증 범위

- seed20261109/20261110 × 좌→우/우→좌 S 방향, 총4개의 새 Windows 프로세스를 순서대로 실행합니다. 각각240초 제한, 소유 프로세스만 종료·회수하고 provider를 닫습니다. Windows 가상환경은 CPython multiprocessing과 같이 기본 인터프리터를 직접 실행하되 `__PYVENV_LAUNCHER__`로 기존 가상환경을 유지합니다. worker는 부모가 자신의 실제 PID를 기록한 뒤에만 native를 시작하며5초 내 확인되지 않으면 종료합니다. 시작 중 인터럽트는 시작 실패로 단정하지 않고 미확인으로 보존하며 나머지 조건을 시작하지 않습니다.
- 원래 `world()`/terrain priority/`NativeWorldCamera`/`PinholeRectifier`를 사용합니다. 첫 곡선의12% 지점과2m 전진한 지점에서 두 카메라를 캡처합니다. 전체8쌍, source16장과 canvas16장입니다. 별도 render/task tick을 추가하지 않고 이미 복사된 CPU RGB만 저장합니다.
- 원본964×604 RGB와 변환512×256 RGB, 실제 lens, 두 카메라의 NVIDIA 렌더러·코어/DLL·소스 해시를 기록합니다. 저장된 zlib RGB를 해독해 소스 해시와 warp/coverage를 정확히 재계산하고, 사례별 등록 기하·자세·새 worker 소유권·프레임 갱신을 검증합니다.
- 카메라만 실행하므로 full-S의 여유 RAM8GiB 조건은 적용하지 않습니다. 모델 실행의 기준은 그대로입니다. RAM이 충분하다고 인증하는 것은 아니며, 실제 메모리 부족·native 오류·시간 초과는 실패로 남깁니다. 출력 공간128MiB 이상이 필요합니다.

최종 `camera-summary.json`의 성공은 **`SCOPED_PASS` — Windows 가상 lens/source/warp/pose 검사만 통과**입니다. 실제 모델 입력의 시간 상태/I420/추론, 모델 카메라의 GL MSAA 샘플, Linux SDK3, 물리 카메라, full-S 완주, CARLA 또는7단계 전체 완료를 의미하지 않습니다. `model_camera_qualified`와 `all_four_validation_tracks_passed` 등은 false로 남습니다.

기존 공식 모델 full-S 결과는 source54의 완주0/4·반복 일치4/4이며 보존합니다. 별도 비공개 클라우드 모델 작업은 중복 실행하지 않습니다. 제어·속도·모델 입력·판정 기준을 완주에 맞춰 조정하지 않습니다.

## 결과 확인과 전달

`camera-summary.json`, `cohort.json`, `inventory.json`, 각 조건의 `inventory.json`/`owner.json`/`lifecycle.json`/`probe.json`/`stdout.log`/`stderr.log` 및 `*.rgb.zlib`를 같은 구조로 보존합니다. 실패 시 `error.json`/`failures.json`도 포함합니다. 하나의 cohort ID·부모 PID와 부모가 지정한 seed/시나리오를 각 worker/lifecycle과 대조하며 오류·실패 기록과 모순되는 결과는 통과시키지 않습니다. 이미지 파일명도 사례 폴더의 pose번호·카메라 역할에 고정해 서로 뒤바꾼 영상 할당을 거부합니다. 결과 폴더만 ZIP으로 전달하면 클라우드에서 GPU/모델 실행 없이 재검증할 수 있습니다. 모델·MetaDrive 자산·개인 촬영 원본은 넣지 않습니다. 출력 사양에는 로컬 경로가 있을 수 있으므로 공개 업로드 전에 확인합니다.

같은 소스와 정확한 NumPy/OpenCV 버전을 가진 환경에서는 저장 결과만 읽어 다시 검사할 수 있습니다.

```powershell
& $probePython -I -B scripts\probe_laptop_camera.py --mode verify --results output\windows-camera-probe-01 --out output\windows-camera-receiver-01
```

현재 클라우드의 순수/모의 테스트는 실제 Windows 카메라 검사를 대신하지 않습니다. 실제 Windows 카메라 실행은 이 문서 작성 시 **NOT_RUN**입니다.
