"""Launch one independent sampler process; validate even Xvfb cleanup status 5."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from scripts.compare_native_pssm_cross_process import SEEDS, SCENES
from scripts.compare_native_shadow_sampler import ARMS, validate_sampler_trial


def run_trial(*, seed: int, scene: str, arm: str, out: Path) -> int:
    if seed not in SEEDS or scene not in SCENES or arm not in ARMS:
        raise ValueError('unknown sampler trial configuration')
    if out.exists():
        raise ValueError('preexisting output cannot prove a fresh native process')
    out.parent.mkdir(parents=True, exist_ok=True)
    mode, enabled = ARMS[arm]
    command = ['xvfb-run', '-a', sys.executable, '-m', 'scripts.native_raw_pixel_clock',
               '--seed', str(seed), '--scenario', scene, '--fraction', '0.12',
               '--mode', 'perceive_sequential', '--ablation', 'baseline',
               '--frames', '10', '--warmup', '2', '--shadow-sampler-mode', mode,
               '--out', str(out)]
    if enabled:
        command.append('--terminal-shadow-probe')
    status = subprocess.run(command).returncode
    if status not in (0, 5):
        return status
    validate_sampler_trial(json.loads(out.read_text()), seed, scene, arm)
    if status == 5:
        print('XVFB_CLEANUP_STATUS_5_WITH_VALIDATED_FRESH_SAMPLER_RECEIPT', out, flush=True)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed', type=int, choices=SEEDS, required=True)
    p.add_argument('--scene', choices=SCENES, required=True)
    p.add_argument('--arm', choices=ARMS, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(argv)
    return run_trial(seed=a.seed, scene=a.scene, arm=a.arm, out=a.out)


if __name__ == '__main__':
    raise SystemExit(main())
