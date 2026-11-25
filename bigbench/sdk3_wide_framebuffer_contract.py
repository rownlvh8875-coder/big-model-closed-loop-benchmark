"""Registered no-model comparison of the final framebuffer and native RAM."""

from bigbench.sdk3_wide_capture_contract import BASE_CAMERA_SHA, CASE, POSES, VARIANT

BASE = '872c84e31ab466abbe955e6b1ff579adf8f375f9'
BRANCH = 'diagnostic/sdk3-wide-framebuffer-20261122-01'
WORKFLOW = '.github/workflows/sdk3-wide-framebuffer-20261122.yml'
APPROVAL = 'docs/approvals/sdk3-wide-framebuffer-20261122-01.json'
REQUEST = 'docs/requests/sdk3-wide-framebuffer-20261122-01.json'
MODE = 'WIDE_STEP44_POST_PROCESS_FBO_VS_RAM'
OUTPUT = 'sdk3-wide-framebuffer-20261122'
TRIALS = ('control','framebuffer')
LIMITS = dict(models=0,inferences=0,camera_processes=2,captures_per_process=44,total_pairs=88,
              seconds_per_process=540,explicit_gl_reads=1,memory=10*1024**3,cpus=2,pids=128)
