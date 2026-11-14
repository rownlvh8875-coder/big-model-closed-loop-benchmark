from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import sys
import numpy as np
import cv2

ROOT=Path('/workspace/big-model-closed-loop-benchmark');sys.path.insert(0,str(ROOT))
from scripts import renderer_tasks_sealed_v1 as n
from scripts import texture_marker_state_sequences as states
from scripts import first_divergence_pixel_forensics as forensic
from scripts.engine_clock_boundaries import BOUNDARIES
from bigbench.optical_calibration import PinholeIntrinsics
BASE=ROOT/'output/stage7-renderer-tasks-sealed-01'
states.require_cpu_runtime()

def load(root,desc,width,height):
    path=root/desc['path'];payload=path.read_bytes();assert sha256(payload).hexdigest()==desc['sha256'] and len(payload)==desc['nbytes']
    image=cv2.imdecode(np.frombuffer(payload,np.uint8),cv2.IMREAD_COLOR)
    assert image.shape==(height,width,3);image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
    assert sha256(image.tobytes()).hexdigest()==desc['rgb_sha256'];image.setflags(write=False)
    return image

def diff(a,b):
    d=b.astype(np.int16)-a.astype(np.int16);coords=np.argwhere(np.any(d!=0,axis=2));count=len(coords)
    return dict(changed_pixels=count,changed_values=int(np.count_nonzero(d)),max_abs=int(np.abs(d).max()),
        first_xy=coords[0][::-1].tolist() if count else None,
        points=[dict(xy=[int(x),int(y)],rgb_a=a[y,x].tolist(),rgb_b=b[y,x].tolist(),delta=d[y,x].tolist()) for y,x in coords] if count<=64 else None)

cases=[];retained=0
for role,i,label in [('canary',0,'C_ON'),('abba',0,'OFF0'),('abba',1,'ON0'),('abba',2,'ON1'),('abba',3,'OFF1')]:
    r=BASE/role/'root-selected/output'/f'case_{i:02d}';data=json.loads((r/'case.json').read_bytes());images=[]
    n.validate_callback_metadata(data)
    for row in data['accepted']:
        pair={cam:load(r,row['raw'][cam],964,604) for cam in ('road','wide')};retained+=sum(a.nbytes for a in pair.values());assert retained<=128*n.MIB
        images.append(pair)
    if cases:
        assert n.exact(data['runtime'],cases[0]['data']['runtime'])
        assert [r['pose'] for r in data['capture_rows']]==[r['pose'] for r in cases[0]['data']['capture_rows']]
        assert [r['intrinsics'] for r in data['accepted']]==[r['intrinsics'] for r in cases[0]['data']['accepted']]
    cases.append(dict(id=label,root=r,data=data,images=images))

clocks=[];pixel=[]
for l,r in combinations(cases,2):
    rows=[]
    for i in range(12):
        a,b=l['data'],r['data'];ca,cb=(x['clock_trace']['calls'][i] for x in (a,b));ma,mb=(x['markers'][i] for x in (a,b))
        observed=a['callback_enabled'] and b['callback_enabled']
        full=None;orders=None
        if observed:
            ea,eb=(x['callback_trace']['steps'][i]['events'] for x in (a,b))
            full=n.canonical([e['state'] for e in ea])==n.canonical([e['state'] for e in eb]);orders=[(e['callback'],e['event']) for e in ea]==[(e['callback'],e['event']) for e in eb]
        count_equal=[ca['snapshots'][k]['frame_count'] for k in BOUNDARIES]==[cb['snapshots'][k]['frame_count'] for k in BOUNDARIES]
        time_equal=[ca['snapshots'][k]['frame_time_s'] for k in BOUNDARIES]==[cb['snapshots'][k]['frame_time_s'] for k in BOUNDARIES]
        marker_equal=(ma['before'],ma['after'])==(mb['before'],mb['after']);raw_equal=ma['raw_sha256']==mb['raw_sha256']
        rows.append(dict(call=i+1,capture=i//2+1,camera=('road','wide')[i%2],raw_equal=raw_equal,clock_counts_equal=count_equal,clock_times_equal=time_equal,texture_pair_equal=marker_equal,
            callback_observed=observed,callback_states_equal=full,callback_orders_equal=orders,
            same_observed_signature_different_rgb=(count_equal and marker_equal and full and orders and not raw_equal) if observed else None))
    clocks.append(dict(left=l['id'],right=r['id'],rows=rows,same_full_signature_different_raw=[r['call'] for r in rows if r['same_observed_signature_different_rgb']]))
    if l['id']=='C_ON':continue
    changes=[];total=0;packed=[]
    for i in range(6):
        for cam in ('road','wide'):
            for boundary in ('raw','canvas'):
                if boundary=='raw':a,b=l['images'][i][cam],r['images'][i][cam]
                else:a,b=(load(x['root'],x['data']['accepted'][i]['canvas'][cam],512,256) for x in (l,r))
                d=diff(a,b);total+=d['changed_pixels'];changes.append(dict(capture=i+1,camera=cam,boundary=boundary,**d))
        vals=[np.frombuffer((x['root']/x['data']['accepted'][i]['packed']['path']).read_bytes(),np.uint8).astype(np.int16) for x in (l,r)]
        d=vals[1]-vals[0];packed.append(dict(capture=i+1,changed_values=int(np.count_nonzero(d)),signed_sum=int(d.sum()),max_abs=int(np.abs(d).max())))
    pixel.append(dict(left=l['id'],right=r['id'],aggregate_changed_pixels=total,aggregate_pixels=8559936,changes=changes,packed=packed))

catalogs=[]
for t,indices in ((0.,range(4)),(.05,range(4,6))):
    for cam in ('road','wide'):
        images=[c['images'][i][cam] for c in cases for i in indices]
        catalogs.append(dict(pose_time_s=t,camera=cam,samples=[dict(case=c['id'],capture=i+1) for c in cases for i in indices],**states.state_catalog(images)))

interventions=[]
for i in range(6):
    a,b=cases[1],cases[2];changed=sum(np.count_nonzero(np.any(a['images'][i][cam]!=b['images'][i][cam],axis=2)) for cam in ('road','wide'))
    if changed>4:interventions.append(dict(capture=i+1,status='NOT_RUN_RAW_PIXEL_CAP',changed_raw_pixels=int(changed)));continue
    lenses={cam:PinholeIntrinsics(**a['data']['accepted'][i]['intrinsics'][cam]) for cam in ('road','wide')}
    result=forensic.analyze_pair(a['images'][i],b['images'][i],lenses)
    assert result['baseline_packed_sha256']==a['data']['accepted'][i]['packed']['sha256'] and result['target_packed_sha256']==b['data']['accepted'][i]['packed']['sha256']
    interventions.append(dict(capture=i+1,status='COPIED_CPU_SUBSETS_ONLY',**result))

report=dict(schema='renderer-tasks-original-saved-analysis-v1',status='SAVED_ORIGINAL_CALLBACK_RGB_ANALYSIS',retained_raw_bytes=retained,
    provenance=[dict(role=role,artifact_id=(r:=json.loads((BASE/role/'root-acceptance.json').read_text()))['artifact_id'],artifact_sha256=r['artifact_sha256']) for role in ('canary','abba')],
    catalogs=catalogs,cross_process=clocks,abba_pixels=pixel,copied_array_interventions=interventions,
    campaign_providers=5,campaign_capture_pairs=30,campaign_named_observer_getters=5760,remaining_allowance=0,
    additional_native_calls=0,additional_model_calls=0,additional_ort_sessions=0,original_strict_pass=False,stage7_complete=False,
    limitation='Same observed CPU state/count/Texture signature across processes is not a shared physical frame or complete GPU state; time, light/HDR/shadow depths/igLoop order remain unproved. Private CPU subsets are derived input bytes, no model counterfactual. OFF callback states remain unobserved, all clocks/Texture ON. No observer neutrality or unique GPU cause.')
states.require_cpu_runtime();payload=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode();assert len(payload)<=2*n.MIB
with (BASE/'saved-analysis.json').open('xb') as f:f.write(payload)
print(json.dumps(dict(status=report['status'],raw_bytes=retained,report_bytes=len(payload),catalog_states=[len(c['states']) for c in catalogs],
    abba_pixel_totals=[(p['left'],p['right'],p['aggregate_changed_pixels']) for p in pixel],
    counterexamples=[(p['left'],p['right'],p['same_full_signature_different_raw']) for p in clocks if p['same_full_signature_different_raw']])))
