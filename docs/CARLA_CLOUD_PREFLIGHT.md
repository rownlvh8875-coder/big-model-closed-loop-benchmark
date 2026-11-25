# 전용 Ubuntu GPU VM에서 CARLA 0.9.16 사전검증

CARLA 서버와 Python 검증기를 같은 전용 VM에서 실행합니다. 설치
후보는 x86-64 Ubuntu 22.04, NVIDIA GPU, Python 3.11입니다.
CARLA 공식 문서의 GPU 권장 기준은 VRAM 8 GB 이상입니다.
서버·모델·증거를 같은 VM에 두는 경우 RAM 32 GiB와 여유가 있는
영구 디스크를 출발점으로 잡을 수 있습니다. GPU와 디스크 수치는
VM에서 직접 확인하세요.
[CARLA 설치 요건](https://carla.readthedocs.io/en/0.9.16/start_quickstart/)

## 서버 배포본과 준비 검사

Ubuntu VM에 NVIDIA 드라이버, Docker, NVIDIA Container Toolkit을
설치한 뒤 실제 GPU가 표시되는지 확인합니다. 아래 명령은 전용 VM의
격리된 네트워크에서 사용합니다. 서버의 기본 포트 2000과 2001은 VM
내부에서 사용합니다. 프로젝트의 실측 카메라 검사는 렌더링을 켠
`-RenderOffScreen`을 사용합니다.
[CARLA Docker 실행 지침](https://carla.readthedocs.io/en/0.9.16/build_docker/)

```bash
nvidia-smi
df -h .
image=carlasim/carla@sha256:aaf1df22702780ece072069e23d03c4879b002ae028c79744b09c4c7ddbae953
docker pull "$image"
docker run -d --name carla-0916 --runtime=nvidia --network=host \
  --env NVIDIA_VISIBLE_DEVICES=all --env NVIDIA_DRIVER_CAPABILITIES=all \
  "$image" bash CarlaUE4.sh -RenderOffScreen -nosound
```

위 다이제스트는 공개 레지스트리에서 공식 `carlasim/carla:0.9.16`
태그의 Linux amd64 매니페스트로 관측한 값입니다. 압축 레이어
합계는 8,642,319,304바이트입니다. 풀린 이미지와 출력에는 추가
공간이 필요합니다.

소스 체크아웃에서 새 가상 환경에 CARLA 클라이언트를 설치합니다.
아래는 카메라 사전검사에 필요한 의존성입니다.

```bash
python3.11 -m venv .venv-carla
py=.venv-carla/bin/python
"$py" -m pip install --only-binary=:all: carla==0.9.16 numpy==2.4.6 opencv-python-headless==5.0.0.93
output=$(mktemp -d "$PWD/carla-0916-output.XXXXXX")
"$py" -I -B scripts/run_laptop_validation.py --mode carla-readiness \
  --carla-host 127.0.0.1 --carla-port 2000 --dedicated-carla --out "$output/readiness"
```

`readiness/carla-readiness.json`의 `READY_FOR_PROBE`는 정확히 0.9.16인
클라이언트와 서버의 응답을 뜻합니다. 준비 검사는 월드를 변경하지
않습니다. 전용 서버에서만 아래 네 조건의 카메라·경로 검사를
실행합니다. 전용 서버의 지도는 잠시 바뀌며, 소유 센서 정리와
원래 월드 복구 기록을 남깁니다. 기존 동적 액터가 있으면 작업을
중단합니다.

```bash
"$py" -I -B scripts/run_laptop_validation.py --mode carla-probe \
  --carla-host 127.0.0.1 --carla-port 2000 --dedicated-carla --out "$output/camera"
docker logs carla-0916 > "$output/server.log" 2>&1
```

`camera/carla-probe-summary.json`에서 `PROBES_MEASURED`와 4조건을
확인합니다. 모델·추론 수는 모두 0입니다. 실제 경로 일치, 도로·와이드
센서의 프레임 ID와 반환 자세, 종료 후 복구 상태는 각 조건의
`probe.json`, `owner.json`, `lifecycle.json`, stdout/stderr에
보관됩니다. 정리 오류와 부분 결과도 같은 새 경로에 남습니다.
공식 모델 단계는 기존 `carla-full-s` 경로의 별도 실행입니다.
[남은 검증 인계](remaining-validation-handoff.md)
