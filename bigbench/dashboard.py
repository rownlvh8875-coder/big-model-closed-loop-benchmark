"""Standalone, zero-network HTML report for native synthetic model diagnostics.

No score is inferred from a raw action or from pinhole-only imagery.
Only human-readable, escaped text and deterministic inline SVG are produced.
"""
from __future__ import annotations

from html import escape
from math import isfinite
from pathlib import Path
from typing import Any
import json


def _number(x: Any, *, digits: int = 3) -> str:
    if x is None:
        return '미측정'
    try:
        val=float(x)
    except (ValueError,TypeError):
        return '유효하지 않음'
    return f'{val:.{digits}f}' if isfinite(val) else '유효하지 않음'


def _trajectory_svg(receipts: list[dict], *, width: int = 760, height: int = 340) -> str:
    lines=[]
    for receipt in receipts:
        coords=[]
        for row in receipt.get('frames',[]):
            x,y=row.get('world_x_m'),row.get('world_y_m')
            if isinstance(x,(int,float)) and isinstance(y,(int,float)) and isfinite(x) and isfinite(y):
                coords.append((float(x),float(y)))
        lines.append(coords)
    all_points=[xy for line in lines for xy in line]
    if not all_points:
        return '<p>유효한 가상 주행 궤적 데이터가 없습니다.</p>'
    xs=[p[0] for p in all_points];ys=[p[1] for p in all_points]
    minx,maxx=min(xs),max(xs);miny,maxy=min(ys),max(ys)
    spreadx=max(.01,maxx-minx);spready=max(.01,maxy-miny)
    inner_w=width-40;inner_h=height-40
    scale=min(inner_w/spreadx,inner_h/spready)
    def path(points):
        return ' '.join(f'{20+(x-minx)*scale:.2f},{height-20-(y-miny)*scale:.2f}' for x,y in points)
    colors=('#0c7a82','#b76708','#7c3aed','#bd2567')
    paths=[]
    for i,pts in enumerate(lines):
        if not pts:
            continue
        color=colors[i%len(colors)]
        paths.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.2" points="{path(pts)}"/>')
        x,y=pts[0];sx=20+(x-minx)*scale;sy=height-20-(y-miny)*scale
        paths.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="4" fill="{color}"/>')
    return (f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="가상 세계 좌표상의 모델별 궤적">'
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="#f7f8fa"/>'
            +''.join(paths)+'</svg>')


def render_diagnostic_dashboard(receipts: list[dict], *,
                                comparison: dict | None = None) -> str:
    if not receipts:
        raise ValueError('dashboard needs at least one diagnostic receipt')
    for receipt in receipts:
        if not isinstance(receipt,dict) or not isinstance(receipt.get('frames'),list):
            raise ValueError('invalid diagnostic receipt')
    def cell(value):
        return '<td>'+escape(str(value))+'</td>'
    rows=[]
    for r in receipts:
        m=r.get('lane_truth') or {}
        rows.append('<tr>'+''.join(map(cell,(
            r.get('model_label','미확인'),
            r.get('model_sha256','미검증'),
            r.get('status','미확인'),
            r.get('completed_steps',0),
            _number(m.get('absolute_lateral_error_max_m')),
            _number(m.get('intrusion_depth_max_m')),
            str(m.get('intrusion_count','미측정')),
        )))+'</tr>')
    labels=''.join(f'<span class="legend"><i style="background:{color}"></i>{escape(str(r.get("model_label","모델 미확인")))}</span>'
                   for color,r in zip(('#0c7a82','#b76708','#7c3aed','#bd2567'),receipts))
    scene=escape(str(receipts[0].get('scenario','unknown')))
    status=escape(str(comparison.get('classification','NOT_PAIRED') if comparison else 'NOT_PAIRED'))
    # Fixed safe HTML, no scripts, no external CDN, no user-controlled attributes.
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Big Model Closed-Loop · 가상환경 기술 진단</title>
<style>
body{{font:15px/1.55 system-ui,-apple-system,sans-serif;max-width:1050px;margin:30px auto;padding:0 16px;color:#1f2730}}
h1{{font-size:27px}}h2{{font-size:18px;margin-top:28px}}
.warning{{background:#f6f6f6;padding:15px;border-left:3px solid #777}}
svg{{width:100%;height:auto;border:1px solid #dde2e5}}
table{{width:100%;border-collapse:collapse;font-size:13px;overflow-wrap:anywhere}}
th,td{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}th{{background:#f6f6f6}}
.legend{{margin-right:20px;white-space:nowrap}}.legend i{{display:inline-block;width:11px;height:11px;margin-right:6px}}
footer{{font-size:12px;color:#58626c}}
</style></head><body>
<h1>대형 ONNX 모델 · 가상 폐루프 기술 진단</h1>
<p><b>가상도로:</b> {scene} · <b>분류:</b> {status}</p>
<p class="warning"><b>모델 성능 순위 아님.</b> MetaDrive의 이상적 핀홀 카메라와 합성 정답 차선만 검증했습니다.
실제 comma 카메라/실도로 안전성·주행 품질을 입증하지 않으며, 실차 테스트를 실시하지 않습니다.
CD210이나 Carrot 고유 튜닝을 사용하지 않습니다.</p>
<h2>가상 세계 궤적 (X/Y)</h2>{_trajectory_svg(receipts)}<p>{labels}</p>
<h2>동일 조건 기술 진단표</h2><table>
<thead><tr><th>모델</th><th>체크포인트 SHA256</th><th>실행 상태</th><th>추론 스텝</th>
<th>최대 중심편차(m)</th><th>최대 침범 깊이(m)</th><th>침범 이벤트</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>검증 제한사항</h2><p>수치는 모델 평가에 관한 판정이 아닌 단기 기하 진단값입니다.
주행영상의 광학 도메인 적합성과 전체 곡선/램프 시나리오 완주를 별도로 증명해야 합니다.</p>
<footer>오프라인 파일 기반 HTML · 외부 네트워크/스크립트 없음 · 차종 독립 가상 운동학</footer>
</body></html>"""


def save_diagnostic_dashboard(output: Path, receipts: list[dict],
                              comparison: dict | None = None) -> Path:
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(render_diagnostic_dashboard(receipts,comparison=comparison),
                      encoding='utf-8')
    return output
