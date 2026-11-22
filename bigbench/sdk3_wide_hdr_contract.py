"""Identity and bounds of the no-model wide HDR texture diagnostic."""

from bigbench.sdk3_wide_framebuffer_contract import BASE_CAMERA_SHA, CASE, POSES, TRIALS, VARIANT

BASE = 'a3a0b1f5d070cd0d5a989f7b0e3e8413447806b3'
BRANCH = 'diagnostic/sdk3-wide-hdr-step44-20261122-01'
WORKFLOW = '.github/workflows/sdk3-wide-hdr-step44-20261122.yml'
APPROVAL = 'docs/approvals/sdk3-wide-hdr-step44-20261122-01.json'
REQUEST = 'docs/requests/sdk3-wide-hdr-step44-20261122-01.json'
MODE = 'WIDE_STEP44_BOUND_HDR_TEXTURE_VS_POSTPROCESS'
OUTPUT = 'sdk3-wide-hdr-step44-20261122'
LIMITS = dict(models=0,inferences=0,camera_processes=4,captures_per_process=44,total_pairs=92,
              seconds_per_process=540,explicit_gl_reads_per_probe=2,memory=10*1024**3,cpus=2,pids=128)
