"""Aggregate independent baseline/PSSM-off MetaDrive scene observations.

Strictly a static camera diagnostic; never promotes absence of drift to model PASS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.native_scene_ablation_sweep import compare_ablation


def main(argv=None) -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    args=p.parse_args(argv)
    reports={name: json.loads((args.root / (name+".json")).read_text(encoding="utf-8"))
             for name in ("baseline","shadow_off")}
    result=compare_ablation(reports["baseline"],reports["shadow_off"])
    (args.root/"comparison.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n",
        encoding="utf-8")
    print("NATIVE_MULTISCENE_ABLATION_COMPARISON",
          json.dumps(result,ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
