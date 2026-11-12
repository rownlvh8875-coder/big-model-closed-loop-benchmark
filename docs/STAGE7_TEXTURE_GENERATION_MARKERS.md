[확인 기록] MetaDrive × MD-V3 7단계 개발 결과

고정 카메라 재생의 첫 ON canary를 완료했다. 공식 모델/ORT 호출 없이12번의 기존 RGB CPU 복사 주변에서24번의 CPU Texture generation 표식을 읽었다. 각 복사 직전·직후 값은 모두 같았다. 이 값은 GPU 완료 fence가 아니며 원래 네 픽셀 차이의 원인을 판정하지 않는다.

## A. 변경과 원본 연결

저장소 `rownlvh8875-coder/big-model-closed-loop-benchmark`, 브랜치 `diagnostic/texture-generation-markers`, [Draft PR37](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/37)은 PR36 위에 쌓였다. canary source는 `0a98918e746fe7df9d5502e21db91c3e5cd15396`다. 기존62 producer/protected13/baseline43/42workflow/소비된요청을 변경하지 않았다. 새 script/test/workflow를 포함한65개 producer closure는 mutable request와 분리한다. ABBA는 accepted source의 직접 자식에서 request·acceptance·문서만 바꾸고65개 producer와 runtime을 고정한다.

## B. 실제 canary

[run43177564313](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43177564313), workflow415702769/job131045412519/attempt1 SUCCESS. Artifact13925041858 `stage7-texture-marker-canary`: ZIP14,605,800bytes, SHA256 `6a8c7a2e3495a5115938d17aee1da8c4e27f4e2ebc1b6350001e0f1090ee1994`;33members/15,795,803uncompressedbytes. 원본ZIP API digest·크기·head 연결과 한번 추출한 모든 바이트를 대조했다.

Parent/launcher/native PID는 root 원본 보고서에 보존한다. 실제 native child3024, launcher/group3012;1provider/6pairs/12observed RGB copies/24sequence readings, 총53.433267887초, 정상 close·exit0·group gone/reaped·cleanup오류0. Constructor의 startup sensor activity는 observed counts 밖이다. 각 sequence reading은 get_image_modified와 get_seq를 각각1번 호출하므로48getter invocations다. 공식 모델/ORT/추가GPU read는0.

Road pre/post trace는12/14/16/18/20/22, Wide는13/15/17/19/21/23이며 모든12행의pre=post다. 저장된 raw→실제 lens canvas12개, derived I4206개가 정확히 재구성됐다. I420는 모델에 공급하지 않은 DERIVED_ONLY다. 새 isolated Mesa 경로는 빈 상태에서50files/1,661,172bytes로 채워졌으나 개별 cache hit를 입증하지 않는다. Retained logical payload28,039,104bytes, frozen write reservation38,171,904bytes가 각각32MiB memory/40MiB disk 한도 안에 있다. 일시 memory 추정치는32,319,072bytes다.

실제 runtime은 Ubuntu24/ImageVersion20261101.360.1/Python3.11.18 GCC13.3/NumPy2.4.6/OpenCVheadless5.0.0.93(cv2 5.0.0)/Panda1.10.13/MetaDrive0.4.3/설치ORT없음이다. 모델을 호출한 이전 실험의 ORT1.31.1 환경과 구분한다.

## C. 사실과 한계

두 arm 모두 같은 raw retention과 얇은 wrapper를 쓴다. OFF는 marker OFF/raw retention ON이며 원래의 비계측 경로가 아니다. 동일 RAM method를 한번 호출하고 같은 array object를 반환한다. ON에서만 CPU 표식을 앞뒤로 읽는다. signed32의 같음·음수·wrap·초깃값은 유효 관측이며 값의 증가를 성공 조건으로 강제하지 않는다.

고정 입력은 과거 retained0의 첫 pose4회+두번째pose2회다. retained1의 첫 pose3회나 기존6/16/10 수렴 정책을 재현한 것이 아니다. 그래프 지연/공식 추론이 없으며 모든6쌍을 저장하고 각 process의 cache를 새로 시작하므로 이전 모델 실험과 시간·할당·cache 조건이 다르다. 추가 render/task/GPU readback/장벽은 없다. 같은 표식이 raw 일치나 freshness/observer neutrality를 보장한다는 결론은 내리지 않는다.

## D. 검증과 기존 게이트

Source 전체 검토 PASS와 T1-R1 scoped fix 검토 PASS. 복구 가능한 close 예외 후 이미 복사된 raw/canvas를 failure-only bounded CPU prefix로 보존하며 provider_closed=false를 유지한다. Hard kill의 미저장 RAM은 복구한다고 주장하지 않는다. 초기 source의 전체542테스트/선택7skip 기록과 수정 source의46covering·50optional integration 기록을 구분한다. 실제 current source 기본 push43177564041/PR43177608658의4jobs SUCCESS;unit544tests/선택7skip, 별도 generated SMALL ONNX1test이며 공식 추론과 별도다.

공식 strict **FAIL**, 확대 시나리오 미실행, 원래 renderer0/4·역사적 candidate12/12·geometry original2/4/candidate1/4·물리 optics/productionISP/fullS 미검증·Stage7미완료를 유지한다. Main공식호출0/Cloud미게시/PR33–37DRAFT·미병합이다.

## E. 다음 순서와 판단

원본 canary의 root+fresh 독립 raw 수락 후에만 직접 자식 metadata activation으로 OFF0/ON0/ON1/OFF1 네 개의 새 process를 한번 실행한다. 각6쌍, 전체 ABBA24쌍/48observed RGB copies/48sequence readings. canary 포함 최대5providers/30pairs/60copies/72sequence readings(144getter invocations),0official/ORT/extraGPU. 어느 phase도 retry/연장/남은 allowance 재사용을 하지 않는다. 실제 실패도 원본과 unknown bounds를 보존하고 중단한다. 각child270초/cleanup포함300초/phase1320초,192MiB dataset 한도를 유지한다.

Root raw 수락 SHA256 `63a9cc4faa23f0a13a02bb89c9aa5f55d22cf03110b923223be3ca9743b3bac0`, fresh 독립 수락 SHA256 `e57d9eb33411474013bda59566815e8d77f807e3c74d59e597a721a7b0f85390`이며 지적0개다. [Root 원본 검증](evidence/STAGE7_TEXTURE_MARKER_CANARY.json)과 [독립 검토](evidence/STAGE7_TEXTURE_MARKER_CANARY_REVIEW.json)를 브랜치 Git 기록에 보존한다. 이 metadata activation은 ABBA4case를 한번 등록하며 결과는 아직 미실행이다.
