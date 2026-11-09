"""Offline manifest-only large-model eligibility report; no model download."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from bigbench.model_eligibility import scan_candidates


def main(argv=None):
    p=argparse.ArgumentParser(description='Local SHA-pinned ONNX catalog preflight, no download')
    p.add_argument('--spec-dir',type=Path,default=Path('model_specs'))
    p.add_argument('--out',type=Path,default=Path('output/model-inventory.json'))
    a=p.parse_args(argv)
    report=scan_candidates(a.spec_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('MODEL_MANIFEST_PREFLIGHT',report['candidate_count'],
          'navigation_required',','.join(report['navigation_required']))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
