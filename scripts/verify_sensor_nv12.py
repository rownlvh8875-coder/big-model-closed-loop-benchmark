"""Offline inspection of declared native NV12 buffers and saved tensor references."""

import argparse
import json
from pathlib import Path

from bigbench.offline_sensor_nv12 import PROTOCOL, verify_sensor_capture


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--out', type=Path, required=True, help='new JSON receipt path')
    args = parser.parse_args(argv)
    with args.out.open('x', encoding='utf-8') as output:
        try:
            result = verify_sensor_capture(args.manifest)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
            result = dict(protocol=PROTOCOL, status='INPUT_ERROR', error=f'{type(exc).__name__}: {exc}',
                          sensor_provenance_authenticated=False, physical_optics_validated=False,
                          production_warp_validated=False, official_model_processes=0, official_inferences=0)
        json.dump(result, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write('\n')
    return {'BLOCKED': 2, 'INPUT_ERROR': 2, 'REFERENCE_MISMATCH': 1}.get(result['status'], 0)


if __name__ == '__main__':
    raise SystemExit(main())
