# SDK3 절차적 지형 셰이더 경로 감사 결과

PR138의 CPU 후보·캐시 검사가 포함하지 못한 별도 지형 경로를 원본 소스로 확인했다. **픽셀 원인이나 수정을 입증한 결과는 아니다.** 공식 행렬은 **3/4 PASS, 전체 FAIL**, Stage7=false를 유지한다.

## 확인한 경로

RGB 카메라의 `rgb` 태그 상태는 `TERRAIN`에 `Terrain.make_render_state`를 연결한다. `AssetLoader`의 기준 `assets`에 `../shaders`를 결합하므로 실제 파일은 **`metadrive/shaders/terrain.vert.glsl` 및 `terrain.frag.glsl`**이다. 별도로 존재하는 `assets/shaders/terrain.*` 샘플과는 바이트가 다르다.

지형은 `ShaderTerrainMesh`로 구성된다. 공식 Panda3D1.10.13 헤더의 상속 대상은 **PandaNode**이다. 앞선 CPU 기하 검사는 `**/+GeomNode`만 탐색했고 실제 보존 후보는 Skybox와 sidewalk 두 메시였다. 지형 정점 셰이더는 인스턴스 데이터와 높이 텍스처로 위치를 계산한다. 따라서 기존 CPU 삼각형·재질의 동일성으로 지형의 실제 GPU 표면까지 동일했다고 단정할 수 없다.

지형 프래그먼트에는 bounds 조건과 **0.01 < attribute.r < 0.11**일 때 `yellow_tex`를 선택하는 분기가 있다. 원본 생성값은 **RGB(1,200/255,0)**이다. 이 경로는 노란색 후보를 설명할 수 있지만, 실제 attribute 샘플·광원·그림자·fog와 픽셀 소유자는 관찰되지 않았다. 깊이 충돌이나 유일 원인으로 결론 내리지 않는다.

## 이전 실제 기록과 비교

실제 run43985158042의 카메라 태그 키는 `rgb`로 원본과 일치한다. 당시 캐시3프로그램/6단계의 원본 바이트 어느 것도 별도 지형의 예상 Panda 전처리 정점·프래그먼트와 일치하지 않는다. PR138에서 확인한6단계 일치는 해당 수집 집합에만 유효하다. **지형이 실행되지 않았다는 뜻은 아니다.** 카메라의 실제 TERRAIN 태그 상태와 shader priority가 수집되지 않아 활성 적용 여부는 남아 있다.

예상 지형 정점 SHA256: `74fe5c4b1dfeb80ecf3f200ff2236aaff76cc802b3cc956a3f4be0ff80a857c3`.
예상 지형 프래그먼트 SHA256: `2c1104ff463d5cb6f0170dcd0a0efec6da1234faa611ce5fe6291a93a0bb9404`.

## 검증과 범위

고정 이미지 tarSHA4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698의11레이어를 순서대로 읽고 각 blob SHA를 확인했다. 선택한8원본을 보존했고 관련 whiteout은 없었다. Panda 공식 태그와 고정 커밋470e352ab87ceae6e30429720e4690c8371f5a55로 읽은 헤더도 바이트가 같았다. 감사 입력18개/128460B는 코드에 고정한 인덱스 SHA로 검증한다. 원본을 import/실행하지 않으며 실제 캐시 바이트를 정규화하지 않는다.

새 테스트18개 RED→GREEN 및 관련 회귀80개 PASS. 전체 canonical push/PR CI와 독립 리뷰는 아래 완료 기록에 추가한다. 보존 원본의 CRLF는 해시 유지를 위해 변경하지 않았으며 whitespace 검사는 명령별 `core.whitespace=cr-at-eol`로 수행한다.

이번 단계의 새 native 렌더러/모델 실행은 **0/0**이다. GPU readback·추가 render/task·셰이더나 런타임 변경이 없다. 다음 실측에서 필요한 관찰은 원래 Road7 CPU-read 경계의 절차적 지형 노드, 카메라 TERRAIN 태그 상태와 shader 우선순위, heightfield/attribute 입력이다. 실제 GPU 픽셀 소유자와 HDR 색은 여전히 별도 증거가 필요하다.

재현: `python -I -B scripts/sdk3_terrain_route.py`.

근거: [audit.json](evidence/sdk3-terrain-route-01/audit.json), [원본 검증](evidence/sdk3-terrain-route-01/image-source-verification.json), [입력 인덱스](evidence/sdk3-terrain-route-01/input-index.json), [Panda 헤더 출처](evidence/sdk3-terrain-route-01/panda-reference/index.json).
