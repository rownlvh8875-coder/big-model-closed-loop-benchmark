# Big Model Closed-Loop Benchmark

**Independent closed-loop benchmarking of large driving models**

comma 계열 대형 주행모델의 **원본 주행 판단**을 동일한 가상 환경에서 비교하는 프로젝트입니다. CD210과 carrotpilot 고유의 경로·속도 보정 로직을 비교에서 제외하고, 공통 제어기와 동일한 차량 물리 조건에서 모델별 차선 유지·급커브·S자 곡선·고속도로 램프 성능을 평가하는 것을 목표로 합니다.

> **현재 상태: 기획 단계 (구현·모델 실행·성능 검증 미착수)**  
> 이 저장소의 문서는 개발 계획이며, 폐루프 시험 성능이나 실제 도로 안전성을 입증한 결과가 아닙니다.

## 주요 목표

- 대형 ONNX 주행모델의 입력·출력 계약 및 순환 상태를 검증합니다.
- **오픈루프 원본 예측 비교**와 **폐루프 가상 주행 비교**를 명확히 분리합니다.
- 고정속도 조향 평가와 조향·가감속 통합 평가를 별도로 실시합니다.
- S자 곡선 및 진출입 램프의 **안쪽 차선 침범(코너 커팅)**을 정량화합니다.
- 모델별 동일 초기 조건·동일 제어기·동일 차량 물리·동일 랜덤 시드로 재현성을 확보합니다.
- 기존 openpilot/MetaDrive 연동 구조를 조사하고 필요 시 CARLA로 교차검증합니다.

## 개발 계획

**[PROJECT_PLAN.md](PROJECT_PLAN.md)** — 프로젝트 배경, 범위, 구조, 모델 실행 계약, 시험 시나리오, 성능 지표, 단계별 개발계획, 완료 기준 및 제약 사항.

## 프로젝트 원칙

- **CD210 제외:** 대형모델 실행 실패 시 CD210 자동 폴백 금지; 오류로 기록합니다.
- **브랜치 개입 분리:** carrotpilot 레인모드·MPC·경로 오프셋·커브 감속 등은 모델 성능 비교에 사용하지 않습니다.
- **폐루프 정의 준수:** 제어 결과로 차량 자세가 변하고 다음 카메라 관측이 달라져야 폐루프입니다. 기록 영상의 반복 재생은 오픈루프입니다.
- **실측과 추정 구분:** 모델·시뮬레이터 한계를 명시하고 실제 도로 성능을 보장하지 않습니다.
- **안전·개인정보:** 실제 차량 제어 및 CAN 송신 기능을 만들지 않고, 주행로그의 위치·식별 정보는 공개 저장소에 올리지 않습니다.

## 참고 프로젝트

- [carrotpilot (carrot-wip)](https://github.com/ajouatom/openpilot/tree/carrot-wip)
- [openpilot](https://github.com/commaai/openpilot)
- [commaai 대형 주행모델](https://huggingface.co/commaai/openpilot_driving_models/tree/main)
- [MetaDrive](https://github.com/metadriverse/metadrive)
- [CARLA](https://github.com/carla-simulator/carla)

*프로젝트 기획: 2026-11-09. 구체적인 모델 목록·실행 가능 여부·라이선스는 개발 착수 전 다시 확인합니다.*
