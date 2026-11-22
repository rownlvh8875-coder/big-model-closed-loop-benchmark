"""Offline presentation for the verified SDK3 model comparison."""

from html import escape

from .dashboard import _number, _trajectory_svg


def _bench_table(headers, rows):
    def line(tag, values):
        return '<tr>'+''.join(f'<{tag}>{escape(str(value))}</{tag}>' for value in values)+'</tr>'
    return ('<table><thead>'+line('th',headers)+'</thead><tbody>'
            + ''.join(line('td',row) for row in rows)+'</tbody></table>')


def _verdict(value):
    return '통과' if value is True else '실패' if value is False else '미판정'


def render_benchmark_dashboard(report: dict) -> str:
    """Show per-model receipts and matching conditions from verified cohort data."""
    names = {'md-v3':'md-v3','light-speed-2':'Light Speed 2'}
    lateral = []
    for case in report['lateral']:
        rows = []
        traces = []
        for model,result in case['models'].items():
            runs = result['runs']
            run_labels = ' / '.join(
                f"{run['outcome']} ({run['steps']}스텝)" if run['steps'] is not None
                else f"{run['outcome']} · {run.get('error','상세 기록 참조')}" for run in runs) or '미판정'
            incursions = ' / '.join(_number(run.get('intrusion_m')) for run in runs) or '미측정'
            rows.append((names.get(model,model),run_labels,_verdict(result['traversal_passed']),
                         _verdict(result['strict_repeat_passed']),incursions))
            traces.extend(run for run in runs if run.get('frames'))
        label = escape(f"{case['seed']} · {case['scenario']}")
        headers = ('모델','실행 종료','완주','엄격 반복','최초 침범(m)')
        table = _bench_table(headers,rows)
        figure = _trajectory_svg(traces) if traces else ''
        lateral.append(f"<section><h3>{label}</h3><p>공통 기하·첫 입력 검증 {_verdict(case['comparable'])}</p>"
                       f"{table}{figure}</section>")
    longitudinal = []
    for case in report['longitudinal']:
        for model,result in case['models'].items():
            longitudinal.append((
                case['scenario'], names.get(model,model),
                ' · '.join(filter(None,(result.get('termination','미판정'),result.get('error')))),
                result.get('steps') if result.get('steps') is not None else '미측정',
                _number(result.get('minimum_synthetic_gap_m')),
                _number(result.get('minimum_ttc_s')), _number(result.get('ego_first_stop_s')),
                _number(result.get('ego_first_restart_s')), _number(result.get('maximum_abs_jerk_mps3')),
            ))
    longitudinal_headers = ('장면','모델','실행 종료','스텝','최소 중심 간격(m)','최소 TTC(s)',
                            '첫 정지(s)','첫 재출발(s)','최대 저크(m/s³)')
    return f"""<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>대형 ONNX 모델 비교</title>
<style>
body{{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#1f2730}}
section{{margin:0 0 1.6rem}}table{{border-collapse:collapse;width:100%;margin:.5rem 0 1rem}}
th,td{{padding:.5rem;border-bottom:1px solid #d9e0e5;text-align:left;overflow-wrap:anywhere}}
th{{background:#edf4f5}}svg{{width:100%;height:auto;max-height:340px}}
@media(max-width:640px){{table{{display:block;overflow-x:auto}}}}
</style>
<h1>대형 ONNX 모델 비교</h1>
<p>Linux SDK3 · 가상 핀홀 카메라 · 고정 조건의 시뮬레이션 결과</p>
<h2>횡방향 full-S</h2>{''.join(lateral)}
<h2>종방향</h2>{_bench_table(longitudinal_headers,longitudinal)}
</html>
"""
