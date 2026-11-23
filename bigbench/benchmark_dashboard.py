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


def _count_bounds(bounds):
    lower, upper = bounds
    return str(lower) if lower == upper else f'{lower}~{upper}'


def _ramp_section(ramp, names):
    summary = []
    conditions = {}
    for model, result in ramp['models'].items():
        name = names.get(model, model)
        summary.append((name, _count_bounds(result['model_process_bounds']),
                        _count_bounds(result['inference_bounds'])))
        for case in result['cases']:
            key = case['seed'], case['scenario']
            outcomes = []
            for run in case['runs']:
                if 'error' in run:
                    outcomes.append(f"미판정 · {run['error']}")
                else:
                    count = _count_bounds(run['inference_bounds'])
                    position = _number(run['route_progress_m'])
                    intrusion = _number(run['final_route']['intrusion_m'])
                    outcomes.append(f"{run['outcome']} ({count}회, 누적 {position} m, 침범 {intrusion} m)")
            conditions.setdefault(key, []).append((
                name, _verdict(case['traversal_passed']), _verdict(case['strict_repeat_passed']),
                ' / '.join(outcomes) or '미판정',
            ))
    sections = []
    scene_names = {'in_ramp': '진입 램프', 'out_ramp': '진출 램프'}
    for (seed, scene), rows in conditions.items():
        title = escape(f"{seed} · {scene_names.get(scene, scene)}")
        sections.append(f"<section><h3>{title}</h3>"
                        + _bench_table(('모델', '완주', '엄격 반복', '독립 실행'), rows) + '</section>')
    return ('<h2 id="ramps">진입·진출 램프</h2>'
            f"<p>카메라와 기하 사전검증 {ramp['camera_pairs_verified']}/4 조건. "
            "완주는 등록된 램프의 종점으로 판정합니다. 본선 차로 변경은 별도 검증 범위입니다.</p>"
            + _bench_table(('모델', '공식 프로세스', '실제 추론'), summary)
            + ''.join(sections))


def render_benchmark_dashboard(report: dict) -> str:
    """Show per-model receipts and matching conditions from verified cohort data."""
    names = {'md-v3':'md-v3','light-speed-2':'Light Speed 2'}
    ramp = _ramp_section(report['ramp'], names) if 'ramp' in report else ''
    ramp_link = '<a href="#ramps">진입·진출 램프</a> · ' if ramp else ''
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
nav{{margin-bottom:1.5rem}}section{{margin:0 0 1.6rem}}table{{border-collapse:collapse;width:100%;margin:.5rem 0 1rem}}
th,td{{padding:.5rem;border-bottom:1px solid #d9e0e5;text-align:left;overflow-wrap:anywhere}}
th{{background:#edf4f5}}svg{{width:100%;height:auto;max-height:340px}}
@media(max-width:640px){{table{{display:block;overflow-x:auto}}}}
</style>
<h1>대형 ONNX 모델 비교</h1>
<p>Linux SDK3 MetaDrive · 가상 핀홀 카메라 · ORT 1.20.1 CPU</p>
<p>CARLA 교차검증 · 선택 검증, 미실행</p>
<nav aria-label="시험 결과"><a href="#full-s">횡방향 full-S</a> · {ramp_link}<a href="#longitudinal">종방향</a> · <a href="comparison.json">결과 JSON</a></nav>
<h2 id="full-s">횡방향 full-S</h2>{''.join(lateral)}
{ramp}
<h2 id="longitudinal">종방향</h2>{_bench_table(longitudinal_headers,longitudinal)}
</html>
"""
