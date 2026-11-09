"""Atomic, deterministic CSV/JSON output for mock simulation diagnostics."""
from __future__ import annotations
import csv
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from .runner import BenchmarkRun


def write_run(outdir: Path, run: BenchmarkRun) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / 'frames.csv'
    rows = [asdict(frame) for frame in run.frames]
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    run.first_frame.save_png(outdir / 'first_camera.png')
    run.last_frame.save_png(outdir / 'last_camera.png')
    report = {'model_name':run.model_name, 'scenario_name':run.scenario_name,
              'evidence_class':run.classification, 'summary':run.summary,
              'csv_sha256':sha256(csv_path.read_bytes()).hexdigest(),
              'note':'Schematic-camera + mock-policy integration only; NOT big ONNX benchmark results.'}
    (outdir / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report
