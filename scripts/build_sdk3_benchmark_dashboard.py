"""Independently verify local SDK3 benchmark receipts and write an offline report."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from bigbench.benchmark_results import MODELS, build_comparison, build_integrated_comparison
from bigbench.benchmark_dashboard import render_benchmark_dashboard


def additional_roots(pairs, *, include_baseline=False):
    roots = {}
    allowed = MODELS.keys() if include_baseline else MODELS.keys() - {'md-v3', 'light-speed-2'}
    for model, path in pairs:
        if model not in allowed or model in roots:
            raise ValueError(f'expected a distinct permitted model, found {model!r}')
        roots[model] = Path(path)
    return roots


def ramp_inputs(gate):
    return [(case['seed'], case['scenario'],
             [(probe['context'], probe['rows']) for probe in case['probes']])
            for case in gate['cases']]


def add_ramp_cohort(report, model, evidence, baseline_gate):
    from scripts.verify_sdk3_ramps import camera_gate, model_pair, portable_camera_gate

    gate_bytes = (evidence / 'camera-gate.json').read_bytes()
    gate = json.loads(gate_bytes)
    rebuilt = camera_gate(evidence / 'probes')
    if not rebuilt['all_cases_admitted'] or portable_camera_gate(gate) != portable_camera_gate(rebuilt):
        raise ValueError(f'{model}: raw ramp camera admission did not reproduce the supplied gate')
    if ramp_inputs(gate) != ramp_inputs(baseline_gate):
        raise ValueError(f'{model}: ramp camera context or input differs from the baseline')
    digest = sha256(gate_bytes).hexdigest()
    cases = [model_pair(evidence / 'models', model, case, digest) for case in gate['cases']]
    runs = [run for case in cases for run in case['runs']]
    report['ramp']['models'][model] = dict(
        cases=cases,
        model_process_bounds=[sum(run['model_process_bounds'][i] for run in runs) for i in range(2)],
        inference_bounds=[sum(run['inference_bounds'][i] for run in runs) for i in range(2)],
        verified_runs=sum('error' not in run for run in runs),
        traversal_passed=sum(case['traversal_passed'] is True for case in cases),
        strict_repeat_passed=sum(case['strict_repeat_passed'] is True for case in cases),
    )
    report['ramp'].setdefault('additional_gate_sha256', {})[model] = digest
    report['model_sha256'][model] = MODELS[model]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--md-v3', type=Path, required=True)
    parser.add_argument('--light-speed-2', type=Path, required=True)
    parser.add_argument('--longitudinal', type=Path, required=True)
    parser.add_argument('--ramps', type=Path, help='baseline ramp evidence directory with camera-gate.json, probes and models')
    parser.add_argument('--extra-full-s', nargs=2, metavar=('MODEL', 'ROOT'), action='append', default=[])
    parser.add_argument('--extra-longitudinal', nargs=2, metavar=('MODEL', 'ROOT'), action='append', default=[])
    parser.add_argument('--extra-ramps', nargs=2, metavar=('MODEL', 'EVIDENCE'), action='append', default=[])
    parser.add_argument('--integrated-full-s', nargs=2, metavar=('MODEL', 'ROOT'), action='append', default=[],
                        help='model root with registered per-condition 55 m and 45 m integrated pair receipts')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        extra_ramps = additional_roots(args.extra_ramps)
        if extra_ramps and args.ramps is None:
            raise ValueError('--extra-ramps requires a baseline --ramps archive')
        report = build_comparison(args.md_v3, args.light_speed_2, args.longitudinal,
                                  extra_lateral=additional_roots(args.extra_full_s),
                                  extra_longitudinal=additional_roots(args.extra_longitudinal))
        if args.ramps is not None:
            from scripts.verify_sdk3_ramps import verify_campaign

            gate_path = args.ramps / 'camera-gate.json'
            report['ramp'] = verify_campaign(args.ramps / 'models', gate_path, probe_root=args.ramps / 'probes')
            if extra_ramps:
                baseline_gate = json.loads(gate_path.read_bytes())
                for model, evidence in extra_ramps.items():
                    add_ramp_cohort(report, model, evidence, baseline_gate)
        if args.integrated_full_s:
            integrated = additional_roots(args.integrated_full_s, include_baseline=True)
            report.update(build_integrated_comparison(integrated))
            report['model_sha256'].update({model: MODELS[model] for model in integrated})
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))

    args.out.mkdir(parents=True, exist_ok=False)
    with (args.out / 'comparison.json').open('x', encoding='utf-8') as output:
        json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write('\n')
    with (args.out / 'index.html').open('x', encoding='utf-8') as output:
        output.write(render_benchmark_dashboard(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
