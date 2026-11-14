# MetaDrive × MD-V3 — 승인된03 시계·픽셀의 CPU 분석

**관측된 엔진 카운트와 Texture 값만으로 RGB를 구분할 수 없는 사례를 확인했다.**
C와 각각의 ON 사이 네 호출에서 숫자 서명이 같고 RGB가 달랐다. 저장된 raw의
작은 차이는 CPU 변환에서 소실되기도, I420 여러 값으로 전파되기도 했다.
렌더러의 최초 원인은 아직 특정하지 못했다. **strict0/4 FAIL·Stage7 INCOMPLETE**다.

## 출처와 재구성

기존 [03 원본 승인](STAGE7_ENGINE_CLOCK_HELD_ABBA_V3_RESULT.md)의 C/A ZIP을
직접 읽었다. 새 다운로드·압축 해제·렌더링·provider·GPU 읽기·clock getter·
공식 모델·ORT 호출은 모두0이다. 이전5provider/30쌍/528getter 허용량은 재사용하지 않았다.

- 원래 생산 소스60f6d7fbadf9c0cdbeb087f6452d7b07ea77abd5,
  실제 checkout fd57f5efab90c7b410b699250a47603f364aace5,
  별도 A제어498647977af799ba0b765440d44985565eee7d13.
- [실행43571004531](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43571004531),
  attempt1/workflow418107188/hostjob132375169212. C와 A의 실제 원본 SHA·요청SHA·
  context·recorded runtime/pose/intrinsics·다섯 processUUID·261생산파일을 검증했다.
  261파일은 생산Git blob과 현재 작업파일 모두 일치한다.
- C원본14104039420/339057032B,
  SHA1484ea8be64763afa10b6cce1053f09790390ce3580adf1bfa90525b279606e7.
  A원본14103669668/405545950B,
  SHAcf1a03b478e15bc9c0533ef4bc2e8e644cb2a16df20ad3f6f341c409b6ea7505.
- Python3.11 CPU 전용 환경, NumPy2.4.6/opencv-python-headless5.0.0.93.
  30쌍/60raw를 originalPNG→RGB→canvas→derivedI420까지 전부 재구성해 원본과 일치했다.
  논리 raw 보관104806080B/128MiB이며 RSS한도가 아니다.
- [분석 JSON](evidence/STAGE7_ENGINE_CLOCK_PIXEL_FORENSICS_03.json)은264966B/2MiB,
  SHA556410b01b38e03741989e98c130f6fc37962ddf9e576ec10a545d44dc040136.
  분석기 SHA0ad2cd9ca258466e9255ae144f4f9eb28b048d5f62bc1cb6c462a6383649ff9c.
  이는 고정 ZIP 바이트의 오프라인 인증이며 새로운 liveAPI/물리호스트 인증이 아니다.

## 시계·Texture와 RGB

모든5프로세스는 Texture를 관찰했다. OFF0/OFF1은 **시계만** 읽지 않았으며,
시계 비교 결과는 null이다. 총10프로세스쌍 중 C/ON0/ON1의3쌍만 시계 비교가 가능하다.
세 쌍의36호출 비교 모두 네 경계의 숫자 count와 Texture 값은 같고, time은 달랐다.

| 비교 | 같은count+Texture / 다른RGB 호출 | 같은RGB / 다른time 호출 수 |
| --- | --- | ---: |
| C_ON–ON0 | 4,8,11,12 | 8/12 |
| C_ON–ON1 | 4,8,11,12 | 8/12 |
| ON0–ON1 | 없음 | 12/12 |

아래 count순서는 before_perceive/before_ram_method/after_ram_method/after_perceive다.
두 C비교에 같은 네 서술적 반례가 있다. 합계8은 프로세스쌍별 비교 행의 수이며,
독립적인8개 원인 실험을 의미하지 않는다.

| 호출 | capture/camera | 네 경계 count | Texture 전/후 |
| --- | --- | --- | --- |
| 4 | 2/wide | 13,14,14,14 | 15/15 |
| 8 | 4/wide | 17,18,18,18 | 19/19 |
| 11 | 6/road | 20,21,21,21 | 22/22 |
| 12 | 6/wide | 21,22,22,22 | 23/23 |

예를 들어 호출4의 before→RAM time은 C36.109928→38.382655,
ON0 30.352883→32.565020초다. 별도 프로세스의 같은 숫자 count는 같은 물리적
렌더프레임이 아니다. C와 A는 같은 기록상 호스트·이미지지만 별도 컨테이너이며
시작·부하·실시간이 다르다. time이 다른데 RGB가 같은28행도 time의 인과적
무관성을 증명하지 않는다. 현재 관측에는 절대time까지 같은 반례가 없다.

## 전체 RGB 상태를 유지한 결과

상태ID는 각 pose/camera 내 SHA정렬 바이트 동등류이며, 패널 간 의미가 없다.
capture1–4는 t0,5–6은 t0.05의 같은 기록상 pose다. 첫 capture를 삭제하지 않았다.

| 기록 pose시간 | camera | 완전RGB 상태 수 | 상태 사이 변경 픽셀 수 |
| --- | --- | ---: | --- |
| 0.00 | road | 3 | 24899,24898,1 |
| 0.00 | wide | 3 | 3196,3197,1 |
| 0.05 | road | 2 | 3 |
| 0.05 | wide | 2 | 1 |

전체30쌍의 같은capture끼리만 sparse64픽셀 상한을 적용했다. pose/camera별
서로 다른 좌표 합집합은6곳: road(254,363),wide(544,352), 다음pose의
road(130,351)/(552,438)/(718,512),wide(431,315). 큰 첫 상태 차이는
이 sparse상한으로 거르지 않았다. 좌표가 과거 연구와 겹친다는 사실만으로
같은 물리프레임·shader·그림자·모델step 또는 원인을 주장하지 않는다.

## OFF0→ON0 차이의 정확한 CPU 전파

모든 subset은 저장된 raw의 **사본** 안에서만 교체했다. 변경 픽셀은 capture별
최대3개이며,6capture 전체16subset을 열거했다. 원본·실제 graphfeed·renderer는
바꾸지 않았다. I420은(2,6,128,256)uint8이며 actual_input_sha256은 null이다.

| capture | 원래 raw 차이 (x,y), RGB A→B | subset 수 | 실제 두 endpoint I420 차이 |
| --- | --- | ---: | --- |
| 1 | 없음 | 1 | 0 |
| 2 | road(254,363),192/183/130→196/185/91 | 2 | 0 |
| 3 | wide(544,352),83/90/26→97/100/61 | 2 | 14값,합+43,max9 |
| 4 | wide(544,352),97/100/61→83/90/26 | 2 | 14값,합−43,max9 |
| 5 | road3곳, 아래 참조 | 8 | 5값,합−21,max7 |
| 6 | 없음 | 1 | 0 |

capture2의 canvas2픽셀은 달랐지만 양자화 뒤 I420은 같았다. 최초 raw차이와
최초 I420차이는 각각2와3으로 다르다. capture5의 세 raw픽셀은
(130,351)195/185/93→199/187/0,
(552,438)124/119/104→114/109/88,
(718,512)122/119/106→109/109/86이다. 각각 I4201/1/3값,합−4/−7/−10으로
전파되며, 세 곳을 모두 바꾼 mask7만 B의 I420을 정확히 재현한다.
capture2는 빈 subset도 B와 같고,3/4는 유일한 변경 픽셀이 필요하다.
이 표의 합·최대는 각 capture의 signed uint8값 차이를 int로 계산한 값이다.
이 여섯 예에서 관측한 가산성을 다른 픽셀/장면의 일반 성질로 확장하지 않는다.

기존 A의 OFF0–ON0는 raw6+canvas29=35변경 픽셀/8559936 비교픽셀이다.
ON0/ON1/OFF1은 세 단계 바이트가 동일하다. 작은 차이를 통과로 바꾸거나,
그래프 출력·재귀 상태·조향의 변화량을 추정하지 않는다. 이번에는 모델을 실행하지 않았다.

## 검증·판정과 다음 실험의 조건

새10시험은 모듈 부재로 RED를 확인했고, 기존33CPU시험을 포함한43개가 PASS했다.
전체시험·독립검토·정확한 HEAD CI와 Draft정보는 이 문서의 closeout 및
[ledger](STAGE7_ENGINE_CLOCK_PIXEL_FORENSICS_LEDGER.md)에 이어 기록한다.

현재 증거로 count/Texture를 강제하거나 임의 warmup·frame삭제·pixel수정·평균을
적용할 근거는 없다. 다음 네이티브 설계는 실제 PSSM.update/MainCamera._chase_task의
호출 경계·행렬/pose 및 shadow/HDR→최종 RGB 경로를 분리해 관찰해야 한다.
기존03을 재실행하는 대신 별도 소스 검토·새 허용량·동일호스트·독립프로세스
observer ON/OFF 대조와 원래 렌더러 의미 보존 조건이 필요하다.
현 시계+Texture 관측만으로 어느 경로를 수정할지 결정할 수 없다.
검증된 원인·수정 전에는 공식 모델 strict 재실행을 성공 판정으로 대체하지 않는다.

geometry·physical optics·determinism·driving performance는 별개 판정이다.
현재 원래 strict0/4FAIL,Stage7INCOMPLETE와 기존geometry/fullS 제한을 유지한다.
main병합·Cloud/registry게시·원본/소모 요청 재작성은 없었다.

## 코드·증거 검토 closeout

분석 구현fc2255c 및 결과57ce8b52b1b2ba26e9e6fc5206752c066fd9d3ca를 기준으로
전체1209시험: 실패0/오류0/기존7skip/111.217초를 확인했다.
[root수치교차확인](evidence/ENGINE_CLOCK_PIXEL_FORENSICS_03_ROOT_CHECK.json)도 PASS다.
한 명의 fresh-context gpt-6-astra/medium 검토자는 두 ZIP 전체와261파일,
30endpoint·16subset·카탈로그·시계 비교를 독립 재계산했다.
[검토 기록](evidence/ENGINE_CLOCK_PIXEL_FORENSICS_03_REVIEW.md): Critical0/Important0,
검토시점의 마감 문구 Minor1건(CP-M1)은 해당 historicalHEAD의 제한으로 보존했다.
소스 수정·추가 검토는 없으며 후속 커밋은 문서·증거만 추가한다.

원격 반영 대상은 evidence/engine-clock-held-abba-03 위의
analysis/engine-clock-pixel-forensics-03 소유 브랜치 Draft다.
[해당 Draft 검색](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pulls?q=is%3Apr+head%3Aanalysis%2Fengine-clock-pixel-forensics-03)의
본문에 최종 HEAD·정확한 push/PR CI run/job·미병합 판정을 기록한다.
API원본과 최종 검증 영수증은 로컬
output/stage7-engine-clock-pixel-forensics-03/closeout에 보존한다.
이 버전 문서의 계산·시험·검토 권위와 나중 원격CI 권위를 구분한다.
일반 CI의 생성 SMALL ONNX시험은 공식 MD-V3 모델 호출이 아니다.

재현 명령(현재 CPU 전용 환경에서 fresh --out 필요):

```bash
/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B \
  -m scripts.engine_clock_pixel_forensics \
  --canary-archive output/stage7-held-abba-root/held-abba-20261114-03/canary/engine-clock-held-abba-20261114-03-canary.original.zip \
  --abba-archive output/stage7-held-abba-root/held-abba-20261114-03/abba/engine-clock-held-abba-20261114-03-abba.original.zip \
  --out output/stage7-engine-clock-pixel-forensics-03/new-report.json
```
