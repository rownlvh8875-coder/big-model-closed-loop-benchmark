"""Read independent terminal-only MetaDrive PSSM/HDR snapshots (NO MODEL SCORING)."""
import argparse
import json
from pathlib import Path
from scripts.metadrive_terminal_hdr import CONDITIONS, compare_terminals


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    reports = {name: json.loads((args.root / (name + ".json")).read_text(encoding="utf-8"))
               for name in CONDITIONS}
    result = compare_terminals(reports)
    (args.root / "terminal_hdr_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n",
        encoding="utf-8")
    print("TERMINAL_HDR_AGGREGATE", json.dumps({
        "status": result["status"], "seed": result["seed"],
        "frames": result["frames"],
        "temporal": result["pre_terminal_frame_series"],
    }, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
