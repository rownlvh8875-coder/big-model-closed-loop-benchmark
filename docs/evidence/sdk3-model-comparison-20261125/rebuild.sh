#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 3 ]]; then
    printf 'Usage: bash rebuild.sh RAW_INPUT_ROOT PYTHON NEW_OUTPUT_DIRECTORY\n' >&2
    exit 2
fi
here=$(cd -- "$(dirname -- "$0")" && pwd)
evidence=$(realpath -- "$1")
checkout=$(git -C "$here" rev-parse --show-toplevel)
python=$(realpath -s -- "$2")
output=$(realpath -m -- "$3")
cd "$evidence"
sha256sum --quiet -c "$here/inputs.SHA256SUMS"
cd "$checkout"
"$python" -B -m scripts.build_sdk3_benchmark_dashboard \
  --md-v3 "$evidence/inputs/md-v3-full-s/models" \
  --light-speed-2 "$evidence/inputs/fixed/light-speed-2" \
  --longitudinal "$evidence/inputs/longitudinal/baseline" \
  --ramps "$evidence/inputs/ramps/baseline" \
  --extra-full-s fairy-tale "$evidence/inputs/fixed/fairy-tale" \
  --extra-longitudinal fairy-tale "$evidence/inputs/longitudinal/fairy-tale" \
  --extra-ramps fairy-tale "$evidence/inputs/ramps/fairy-tale" \
  --extra-full-s light-speed "$evidence/inputs/fixed/light-speed" \
  --extra-longitudinal light-speed "$evidence/inputs/longitudinal/light-speed" \
  --extra-ramps light-speed "$evidence/inputs/ramps/light-speed" \
  --integrated-full-s md-v3 "$evidence/inputs/integrated/md-v3" \
  --integrated-full-s light-speed-2 "$evidence/inputs/integrated/light-speed-2" \
  --integrated-full-s fairy-tale "$evidence/inputs/integrated/fairy-tale" \
  --integrated-full-s light-speed "$evidence/inputs/integrated/light-speed" \
  --out "$output"
