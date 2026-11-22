"""Identity and fixed bounds for the no-model scene MSAA sample diagnostic."""
from bigbench.sdk3_wide_hdr_contract import BASE_CAMERA_SHA, CASE, POSES, TRIALS, VARIANT

BASE = '854a3fc0eb17ca87b971f61012c7a8276e9d2f70'
BRANCH = 'diagnostic/sdk3-wide-msaa-step44-20261122-01'
WORKFLOW = '.github/workflows/sdk3-wide-msaa-step44-20261122.yml'
APPROVAL = 'docs/approvals/sdk3-wide-msaa-step44-20261122-01.json'
REQUEST = 'docs/requests/sdk3-wide-msaa-step44-20261122-01.json'
MODE = 'WIDE_STEP44_ORIGINAL_MSAA_SAMPLES_VS_RESOLVE'
OUTPUT = 'sdk3-wide-msaa-step44-20261122'
LIMITS = dict(models=0,inferences=0,camera_processes=4,captures_per_process=44,total_pairs=92,
              seconds_per_process=540,scene_sample_copies=1,extra_compute=1,
              private_blits_per_probe=1,explicit_readbacks_per_probe=4,memory=10*1024**3,cpus=2,pids=128)
