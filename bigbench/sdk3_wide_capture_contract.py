"""Registered, zero-model camera sampling at the two historical runs' shared poses."""

BASE = '374884c8c7c776a17e6292cd30e190bcc14367de'
BRANCH = 'diagnostic/sdk3-wide-step44-20261122-01'
WORKFLOW = '.github/workflows/sdk3-wide-step44-20261122.yml'
APPROVAL = 'docs/approvals/sdk3-wide-step44-20261122-01.json'
REQUEST = 'docs/requests/sdk3-wide-step44-20261122-01.json'
POSES = 'docs/diagnostics/sdk3-wide-step44-poses.json'
MODE = 'WIDE_STEP44_TIMING_NO_MODEL'
OUTPUT = 'sdk3-wide-step44-20261122'
CASE = (20261110, 's_curve_left_right')
TRIALS = {'immediate-a': 0, 'immediate-b': 0, 'one-second-a': 1, 'one-second-b': 1}
LIMITS = dict(models=0,inferences=0,camera_processes=4,
              captures_per_process=46,seconds_per_process=540,
              total_pairs=184,memory=10*1024**3,cpus=2,pids=128)
BASE_CAMERA_SHA = '23d90c3d12894f855ae64d4607c03f3bf34e31e28dd7f5ce82bd0ddc7b37faf5'
VARIANT = 'source_yuv_nearest_even'
