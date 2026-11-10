"""Aggregate three independent MetaDrive HDR/PSSM process receipts, fail closed."""
import argparse
import json
from pathlib import Path

from scripts.metadrive_hdr_trace import ABLATIONS, compare_reports


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    records = {name: json.loads((args.root / (name + ".json")).read_text(encoding="utf-8"))
               for name in ABLATIONS}
    result = compare_reports(records)
    (args.root / "hdr_comparison.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")
    print("PSSM_HDR_COMPARISON", json.dumps({
        "status": result["status"], "seed": result["seed"], "pose": result["pose_id"],
        "bit_exact_after_warmup": result["after_warmup_bit_exact"],
    }, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
