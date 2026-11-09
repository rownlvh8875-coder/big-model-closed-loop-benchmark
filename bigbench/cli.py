"""Offline-only command line interface. No vehicle or internet calls."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .onnx_inspect import inspect_onnx
from .policies import CameraLaneMock
from .report import write_run
from .runner import run_episode
from .scenario import get_scenario, SCENARIOS


def main(argv=None):
    ap = argparse.ArgumentParser(prog='bigbench', description='Offline big-model benchmark scaffolding')
    sub = ap.add_subparsers(dest='command', required=True)
    smoke = sub.add_parser('smoke', help='Run schematic camera closed-loop using MOCK camera policies (NOT ONNX)')
    smoke.add_argument('--scenario', choices=SCENARIOS, default='s_curve')
    smoke.add_argument('--out', type=Path, default=Path('output/mock_smoke'))
    smoke.add_argument('--policy', choices=('conservative','responsive'), default='conservative')
    smoke.add_argument('--integrated', action='store_true', help='Allow mock acceleration, not fixed speed')
    matrix = sub.add_parser('smoke-compare', help='Compare TWO MOCK camera controllers across synthetic scenarios; NOT ONNX benchmark')
    matrix.add_argument('--out', type=Path, default=Path('output/mock_comparison'))
    inspect = sub.add_parser('inspect-onnx', help='Inspect local ONNX file I/O and SHA256 (no inference)')
    inspect.add_argument('path', type=Path)
    args = ap.parse_args(argv)
    if args.command == 'inspect-onnx':
        print(json.dumps(inspect_onnx(args.path), ensure_ascii=False, indent=2))
        return 0
    if args.command == 'smoke-compare':
        rows = []
        for name in ('s_curve', 'ramp_left', 'ramp_right', 'lead_brake'):
            for variant, gain in (('conservative', 0.04), ('responsive', 0.085)):
                result = run_episode(get_scenario(name), CameraLaneMock(gain, name='MOCK_'+variant))
                report = write_run(args.out / name / variant, result)
                rows.append({'scenario':name,'mock_policy':variant, **report['summary']})
        overview = {'evidence_class':'SYNTHETIC_MOCK_ONLY',
                    'not_big_model_performance':True, 'results':rows,
                    'note':'ONLY mock image-conditioned policies; no real ONNX inference'}
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out / 'comparison.json').write_text(json.dumps(overview,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'evidence_class':overview['evidence_class'],'episodes':len(rows),
                          'output':str(args.out / 'comparison.json')},ensure_ascii=False))
        return 0
    if args.command == 'smoke':
        gain = 0.04 if args.policy == 'conservative' else 0.085
        policy = CameraLaneMock(gain, name='MOCK_'+args.policy)
        result = run_episode(get_scenario(args.scenario), policy, fixed_speed=not args.integrated)
        output = write_run(args.out, result)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    raise AssertionError('unhandled command')


if __name__ == '__main__':
    raise SystemExit(main())
