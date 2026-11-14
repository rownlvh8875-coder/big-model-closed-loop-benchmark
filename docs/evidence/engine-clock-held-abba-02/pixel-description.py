"""Descriptive CPU differences only, after authenticated original case replay."""
from pathlib import Path
import itertools,json,sys
import numpy as np
import cv2
root=Path('/workspace/big-model-closed-loop-benchmark');sys.path.insert(0,str(root))
from scripts import engine_clock_held_abba_v2 as n
out=root/'output/stage7-held-abba-root'/n.ID/'abba'
accept=n.image.parse((out/'root-acceptance.json').read_bytes());assert accept['status']=='AUTHENTICATED_TERMINAL_MEMBER_CAP_WITH_FOUR_CASE_DIAGNOSTICS'
base=out/'root-selected';comparisons=[]
for a,b in itertools.combinations(range(4),2):
 rows=[]
 for index in range(1,7):
  for boundary in ('raw','canvas'):
   for camera in ('road','wide'):
    name='capture_%02d/%s_%s.png'%(index,boundary,camera)
    left=cv2.imread(str(base/('case_%02d'%a)/name),cv2.IMREAD_COLOR)
    right=cv2.imread(str(base/('case_%02d'%b)/name),cv2.IMREAD_COLOR)
    assert left is not None and right is not None and left.shape==right.shape
    diff=np.abs(left.astype(np.int16)-right.astype(np.int16));changed=int(np.count_nonzero(np.any(diff,axis=2)))
    rows.append(dict(capture=index,boundary=boundary,camera=camera,width=int(left.shape[1]),height=int(left.shape[0]),changed_pixels=changed,total_pixels=int(left.shape[0]*left.shape[1]),absolute_channel_difference_mean=float(diff.mean()),absolute_channel_difference_max=int(diff.max())))
 comparisons.append(dict(left=a,right=b,rows=rows,total_changed_pixels=sum(r['changed_pixels'] for r in rows),total_pixels=sum(r['total_pixels'] for r in rows)))
report=dict(schema='held-abba-descriptive-pixel-differences-v1',status='REJECTED_PHASE_DESCRIPTIVE_CPU_RGB_DIAGNOSTICS_ONLY',artifact_sha256=accept['artifact_zip_sha256'],opencv_version=cv2.__version__,numpy_version=np.__version__,comparisons=comparisons,causal_effect_proven=False,gpu_freshness_proven=False,observer_neutrality_proven=False,scientific_result_promoted=False,official_model_calls=0,ort_sessions=0)
with (out/'pixel-differences.json').open('xb') as f:f.write(n.canonical(report))
print(json.dumps(dict(status=report['status'],comparisons=[{k:v for k,v in r.items() if k!='rows'} for r in comparisons])))
