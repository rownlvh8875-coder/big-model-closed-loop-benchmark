from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
root=Path('/workspace/big-model-closed-loop-benchmark');sys.path.insert(0,str(root))
from scripts.gl_trace_reader import file_sha,TRACE_PINS
base='1555e3096afbb9c1e177eb6cbc5659341101b4f7'
out=root/sys.argv[1];out.mkdir(parents=True,exist_ok=True)
def git(*args,**kw):return subprocess.check_output(['git',*args],cwd=root,**kw)
rows=[]
for line in git('ls-tree','-r','-z',base).split(b'\0'):
    if not line:continue
    meta,path=line.split(b'\t',1);mode,kind,blob=meta.decode().split();assert kind=='blob'
    rows.append(dict(path=path.decode(),mode=mode,blob=blob))
p=subprocess.run(['git','hash-object','--stdin-paths'],input=('\n'.join(r['path'] for r in rows)+'\n').encode(),cwd=root,capture_output=True,check=True)
observed=p.stdout.decode().splitlines();assert len(observed)==len(rows)
assert all(r['blob']==sha for r,sha in zip(rows,observed))
assert all((root/r['path']).is_file() for r in rows)
q=json.loads((root/'docs/evidence/renderer-pipeline-sealed-01/source/qualified.json').read_text())
assert len(q['request']['source_closure'])==299
assert all(file_sha(root/p)==h for p,h in q['request']['source_closure'].items())
originals=[]
for name,(size,sha) in TRACE_PINS.items():
    path=root/'output/apitrace-draw-pilot-v2'/name;assert path.stat().st_size==size and file_sha(path)==sha
    originals.append(dict(path=str(path.relative_to(root)),nbytes=size,sha256=sha))
idx=json.loads((root/'docs/evidence/gl-read-provenance-01/proof-index.json').read_text())
for item in idx['full_graphs_retained_not_in_git']:
    path=Path(item['retained_path']);assert path.stat().st_size==item['nbytes'] and file_sha(path)==item['sha256'];originals.append(item)
for name,size,sha in [
 ('artifact-14113011109.zip',339390427,'123e060848fb7d7b5dd8f221d5434209da7455cd008d6c6e4be7c38b72bc9211'),
 ('artifact-14112987413.zip',406827081,'ef743f9a20ee67379faa64bf98151e2fae2165b61351f05bc78ac92ef344972f'),
 ('attestation.zip',1276,'1cff11d1ace1f0b017f0c64421dd82fbcad12014deac00134fc70ecc55ffbcac'),
 ('attestor-diagnostics.zip',437500,'148dac33cbe21cfa6736d3a0774088560d41346523c38ac32b35535cea10605c')]:
    folder=root/'output/stage7-renderer-pipeline-sealed-01'
    candidates=[p for p in folder.rglob('*.zip') if p.stat().st_size==size]
    assert len(candidates)==1,(name,[str(p) for p in candidates]);path=candidates[0];assert file_sha(path)==sha
    originals.append(dict(path=str(path.relative_to(root)),nbytes=size,sha256=sha))
old={416199727:[43251145868,43249493437],417996810:[43554149287],418007872:[43555898389,43556701512],418051491:[43563102068],418069748:[43565472170],418107188:[43571004531],418206888:[43584877011],418257705:[43591877488]}
prefix='repos/rownlvh8875-coder/big-model-closed-loop-benchmark/'
def api(path):
    p=subprocess.run(['gh','api',prefix+path],cwd=root,capture_output=True,text=True,timeout=45,check=True);return json.loads(p.stdout)
routes={'main':'git/ref/heads/main','prior-pr111':'pulls/111','prior-pr110':'pulls/110','prior-pr109':'pulls/109','prior-pr108':'pulls/108','prior-pr107':'pulls/107','prior-pr106':'pulls/106','prior-pr105':'pulls/105','prior-pr104':'pulls/104','prior-pr103':'pulls/103','prior-pr102':'pulls/102'}
routes.update({'native-'+str(k):f'actions/workflows/{k}/runs?per_page=100' for k in old})
with ThreadPoolExecutor(max_workers=6) as pool:proofs=dict(zip(routes,pool.map(api,routes.values())))
assert proofs['main']['object']['sha']=='48e79a7ed5aedf6daa5a62ff68d2225af7955ef1'
for wid,ids in old.items():
    p=proofs['native-'+str(wid)];assert p['total_count']==len(ids) and sorted(x['id'] for x in p['workflow_runs'])==sorted(ids)
for number,head in [(111,base),(110,'55ab312dcded2a55640a560441010f8f2737531d'),(109,'5aefbd5ca54557de79d00c67282c086e8a6bca61'),(108,'93475a36e8a68889aa632182dccd4cdc3dde39c0'),(107,'c06a3a3eb8e215a8e40054433cf4c6c4c1d42bdc'),(106,'868f65e368bcb811bce64f61c988a27bbed612f2'),(105,'a0e072e450cf6591b9da686711196d56eb9165a1'),(104,'f8994f1d6c0f4cb6c6348d50c8c6f25d6b4628c0'),(103,'3555a133ed3ae999cdcb86ab3867fe3f5005530e'),(102,'09ad7e3272713ec86031ab8158e3f9fdf0cf245d')]:
    p=proofs['prior-pr'+str(number)];assert p['head']['sha']==head and p['draft'] and not p['merged'] and p['state']=='open'
for name,p in proofs.items():(out/(name+'.json')).write_text(json.dumps(p,indent=2)+'\n')
result=dict(schema='panda-adapter-sdk-preservation-v1',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),
    base_sha=base,base_files_preserved=len(rows),base_file_git_blob_identities=rows,old_source_pins_preserved=299,
    preserved_originals=originals,old_native_history_unchanged={str(k):v for k,v in old.items()},main_unchanged=proofs['main']['object']['sha'],
    prior_drafts_unmerged=True,new_native_runs=0,consumed_native_allowance_remaining=0,new_gl_calls=0,new_provider_runs=0,new_model_runs=0,new_official_ort_runs=0)
(out/'preservation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(base_files_preserved=len(rows),old_source_pins_preserved=299,original_files_checked=len(originals),old_native_history_unchanged=True,main_unchanged=True)))
