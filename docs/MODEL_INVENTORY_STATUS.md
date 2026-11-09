# 대형 주행 ONNX 모델 확보·실행 검증 현황 (2026-11-09)

이 저장소는 **대형모델의 순수 종·횡방향 판단을 가상 MetaDrive에서 비교**한다. CD210, 실차, 특정 차량의 동역학, Carrot MPC/Params 튜닝은 영구 제외한다.

## 실제 공식 ONNX 추론 증거

| 후보 | 실제 ONNX SHA256 | 확인한 범위 | 확정하지 않은 것 |
|---|---|---|---|
| MD-V3 | `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199` | 공식 파일 해시+연속 실행, MetaDrive S자 12스텝 영상 폐루프, 선행차 영상 26스텝 | 실도로 영상 동등성, S자 전체 완주, 모델 종/횡 성능 순위 |
| Light Speed 2 | `909a140019050a9d7f00db22dd4f4085928d2af9474a82244672ddab964f95a8` | 공식 파일 해시+연속 실행, MD-V3와 같은 곡선에서 12스텝 | 동일 조건 장시간 반복/성능 순위 |
| Light Speed | `6274eb4a3f3eb7ad1ab341d222bbba2ba709b06645dbbd15ac4971d6cb22ab21` | 공식 파일 해시+MetaDrive 도식적이지 않은 영상 입력으로 5스텝 | 곡선·램프 평가 및 다른 모델과의 비교 |
| N16 Nav | `01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a` (카탈로그 명세) | `nav_map`, `navigation` 및 추가 재귀 상태 명세 확인 | **실제 모델 다운로드·실행 미검증**; 공정한 지도 입력 어댑터 없음 |

기준은 공개된 `model_specs/*.json`의 원본 코드 카탈로그 명세다. 검증 기록:
- [MD-V3 / Light Speed 2 네이티브 12스텝](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42583866722)
- [Light Speed 5스텝](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585073433)
- [MD-V3 가상 선행차 영상 26스텝](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585288256)

## 실행 가능한 읽기 전용 사전 점검

```bash
python -m scripts.model_preflight --spec-dir model_specs --out output/model-inventory.json
```

현재 후보 목록 조회는 `MANIFEST_ONLY_MODEL_WEIGHTS_NOT_VERIFIED`를 반환한다. 위의 실제 실행 증거는 **별도 CI에서 특정 파일 SHA256과 ONNX 세션을 검증했다는 사실**이며, 단순 manifest preflight에 그 결과를 자동 대입하지 않는다.

N16처럼 지도·내비 입력을 요구하는 경우 모델 구조 검사만으로 실주행 판단을 평가할 수 없다. **임의의 0 입력을 내비게이션 신호로 위장하거나 CD210으로 폴백해서 실행하지 않는다.**

## 추가 확대 게이트

1. ONNX 경로/파일 크기/SHA256과 모델 라이선스 확인.
2. `new_img`, `state_* → next_state_*`, `action`, `plan`을 그래프와 직접 대조.
3. 영상/내비 입력 계약에 대한 **정상 의미의 입력 소스**가 없으면 실행 적격 보류.
4. 같은 가상 시나리오를 초기화한 후 모델별 독립 recurrent state 유지.
5. 영상 재현성(현재 [원인 조사](REPRODUCIBILITY_FINDINGS.md))이 확보되기 전에는 모델별 성능 순위를 발표하지 않음.
6. 비교가 가능해도 MetaDrive 가상 영상으로 평가한 결과만 명시하고 실도로 성능으로 일반화하지 않음.

공식 공개 ONNX 파일은 Hugging Face `commaai/openpilot_driving_models` 저장소에서 **필요한 파일만** 내려받아 검증한다. 사용자 개인 Hugging Face에 가중치를 재업로드할 필요는 아직 없다. 모델 파일·실주행 로그는 GitHub 공개 저장소에 저장하지 않는다.
