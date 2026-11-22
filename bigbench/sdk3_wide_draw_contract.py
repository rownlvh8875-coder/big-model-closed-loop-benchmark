"""Local, bounded no-model original draw comparison for the exact historical wide pixel."""
from bigbench.sdk3_wide_msaa_contract import BASE_CAMERA_SHA, CASE, POSES, TRIALS, VARIANT

MODE='CLOUD_LOCAL_WIDE_STEP44_ORIGINAL_DRAW_TRACE'
REQUEST='docs/requests/sdk3-wide-draw-local-20261122-02.json'
LIMITS=dict(captures_per_process=44,camera_processes=4,actual_pairs=8,
            seconds_per_process=420,models=0,inferences=0,captured_draw_calls_per_focus=128)
