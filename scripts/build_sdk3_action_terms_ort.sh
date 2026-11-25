#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
evidence="$(realpath -m "$1")"
scratch="$(realpath -m "$2")"
mkdir -p "$evidence"
mkdir "$scratch"
export GIT_TERMINAL_PROMPT=0

(
  url="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["archive"]["url"])' \
    "$repo/scripts/sdk3_action_terms_source/pins.json")"
  curl --fail --silent --show-error --location --max-time 360 --max-filesize 177287156 \
    --output "$scratch/source.nar.xz" "$url"
  python -I -B "$repo/scripts/sdk3_materialize_ort_release.py" "$scratch/source.nar.xz" \
    "$scratch/ort-src" "$evidence/release-source.json"
  eigen="$scratch/eigen"
  git init -q "$eigen"
  git -C "$eigen" fetch --no-tags --depth 1 https://gitlab.com/libeigen/eigen.git e7248b26a1ed53fa030c5c459f7ea095dfd276ac
  git -C "$eigen" checkout --detach FETCH_HEAD
  test "$(git -C "$eigen" rev-parse HEAD)" = e7248b26a1ed53fa030c5c459f7ea095dfd276ac
  test "$(git -C "$eigen" rev-parse HEAD^{tree})" = 3142f2e6ec15a2cb94c6d1bb751953cbc5f1c948
  git -C "$eigen" fsck --full
  git -C "$eigen" show --no-patch --format='commit=%H tree=%T' HEAD > "$evidence/eigen-source.txt"
) >"$evidence/source.stdout.log" 2>"$evidence/source.stderr.log"

(
  python -m pip freeze > "$evidence/python-toolchain.txt"
  cmake --version > "$evidence/cmake.txt"
  ninja --version > "$evidence/ninja.txt"
  g++ --version > "$evidence/compiler.txt"
  cd "$scratch/ort-src"
  ./build.sh --config Release --build_dir "$scratch/build" --build_wheel \
    --skip_tests --parallel 3 --skip_submodule_sync --cmake_generator Ninja --compile_no_warning_as_error \
    --cmake_extra_defines onnxruntime_DEBUG_NODE_INPUTS_OUTPUTS=ON onnxruntime_BUILD_UNIT_TESTS=OFF \
    "FETCHCONTENT_SOURCE_DIR_EIGEN=$scratch/eigen"
) >"$evidence/build.stdout.log" 2>"$evidence/build.stderr.log"

(
  mkdir "$scratch/stock-wheel" "$evidence/canary"
  python -m pip download --no-deps --only-binary=:all: --dest "$scratch/stock-wheel" onnxruntime==1.20.1
  stock=("$scratch/stock-wheel/"onnxruntime-*.whl)
  debug=("$scratch/build/Release/dist/"onnxruntime-*.whl)
  test "${#stock[@]}" = 1
  test "${#debug[@]}" = 1
  printf '5eec64c0269dcdb8d9a9a53dc4d64f87b9e0c19801d9321246a53b7eb5a7d1bc  %s\n' "${stock[0]}" | sha256sum -c
  sha256sum "${stock[0]}" "${debug[0]}" > "$evidence/wheel-digests.txt"
  python -m pip install --no-index --no-deps --target "$scratch/stock-site" "${stock[0]}"
  python -m pip install --no-index --no-deps --target "$scratch/debug-site" "${debug[0]}"
  python -m pip install --no-deps --target "$scratch/canary-deps" numpy==2.4.6 onnx==1.23.2 \
    "protobuf==$(python -c 'import google.protobuf; print(google.protobuf.__version__)')" \
    "typing-extensions==$(python -c 'import importlib.metadata; print(importlib.metadata.version("typing-extensions"))')" \
    "ml-dtypes==$(python -c 'import importlib.metadata; print(importlib.metadata.version("ml-dtypes"))')"
  chmod -R a+rX "$scratch/debug-site" "$scratch/canary-deps"
  python -I -B "$repo/scripts/verify_ort_node_audit.py" "$scratch/stock-site" "$scratch/debug-site" "$evidence/canary"
  cd "$repo"
  python -B - "$scratch/debug-site" "${debug[0]}" "$evidence/runtime.json" <<'PY'
import json
from pathlib import Path
import sys
from bigbench.sdk3_action_terms import ORT_COMMIT, digest, native_libraries

site, wheel, receipt = map(Path, sys.argv[1:])
with receipt.open('x') as stream:
    json.dump(dict(ort_release_commit=ORT_COMMIT, native_libraries=native_libraries(site),
                   wheel_sha256=digest(wheel), wheel_bytes=wheel.stat().st_size), stream, indent=2)
    stream.write('\n')
PY
) >"$evidence/canary.stdout.log" 2>"$evidence/canary.stderr.log"

# Keep the verified mounted sites and all evidence. Release only this job's build scratch.
rm -rf -- "$scratch/build" "$scratch/ort-src" "$scratch/eigen"
rm -- "$scratch/source.nar.xz"
