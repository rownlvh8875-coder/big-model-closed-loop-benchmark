"""Fresh versioned source stage; no Panda library is loaded."""
import argparse,hashlib,json,os,stat
from pathlib import Path
from scripts import panda_adapter_sdk_stage as old
from scripts.panda_dispatch_coverage import read_input
ROOT=Path(__file__).resolve().parents[1]
need=old.need;canonical=old.canonical
MANIFEST='adapter-sdk-routes-manifest.json';PARENT='.adapter-sdk-v1.json'
PARENT_SHA='0725f7135392fb7ee26d2262936c7895d91016487b518a65eeeb658fe4bbd913'
NATIVE_PINS={'panda_cache_adapter.cxx':'6f672c0a3435adb70b796a8c839d9e791b630601beaae24d6750c2d822cfa893','panda_cache_adapter.h':'ad598c1edecdcaaf2b0663091d9560b2e64f9d739a902c5ca5cec2c2eae8e3bc','panda_source_activity.cxx':'fb6a4445386cfc950e475d7dc7b93f208f1abb58e6febf70ac39451dbc5ff9f6','panda_source_activity.h':'dc9a35ebacf684e022b28ef5a7b5bf565a8e57d309708d97b96fab614590a962','panda_source_dispatch.cxx':'914554cc7f645f4b6de938e3cf3150143b980d4483b7e5258fa31b96f6efa588','panda_source_dispatch.h':'c8175046824a9e2845f962df6572b8fb1426da622a46eb478080521fa3d89ede','readback_command_state.c':'49e986eca295519f180e6b96477ab1752f6bd0996bdf9f9f535bcfc5c17e3bc2','readback_command_state.h':'4c64a2059cd722fa9a35d6e4ed81ac80bd4c89bdd8bac8ff73b00213b81db2b8','readback_return_core.h':'1a78841638968a7c9d08fe845b1d0b3b7976ab0808edcc22ff6cfd631e0ee58f'}
def sha(data):return hashlib.sha256(data).hexdigest()
def native_files():
    result={name:read_input(canonical(ROOT/'native/panda_sdk_routes_v2'/name),1024**2) for name in NATIVE_PINS}
    need(all(sha(data)==NATIVE_PINS[name] for name,data in result.items()),'versioned native pin mismatch');return result

def expected_manifest(parent,records):
    result=dict(parent);result.update(schema='panda-sdk-routes-stage-v2',native_sha256=NATIVE_PINS,parent_sdk_manifest_sha256=PARENT_SHA,source_tree=records,source_tree_files=len(records),safe_cap=256,route_slots=64,new_native_runs=0);return result

def stage(upstream,out):
    out=canonical(out);need(not out.exists(),'existing stage preserved');files=native_files()
    old.stage(upstream,out);raw=read_input(out/'adapter-sdk-manifest.json',16*1024**2);need(sha(raw)==PARENT_SHA,'exact parent SDK stage required')
    (out/'adapter-sdk-manifest.json').rename(out/PARENT)
    for name,data in files.items():(out/'panda/src/glstuff'/name).write_bytes(data)
    result=expected_manifest(json.loads(raw),old.base.tree_records(out));(out/MANIFEST).write_text(json.dumps(result,indent=2)+'\n');need(verify_stage(out)==result,'new stage verify mismatch');return result

def verify_stage(path):
    path=canonical(path);m=json.loads(read_input(path/MANIFEST,16*1024**2));raw=read_input(path/PARENT,16*1024**2);need(sha(raw)==PARENT_SHA,'parent SDK manifest pin')
    parent=json.loads(raw);records=[r for r in old.base.tree_records(path) if r['path']!=MANIFEST];need(m==expected_manifest(parent,records),'source stage manifest drift')
    need(sha(read_input(path/old.BASE_MANIFEST,16*1024**2))==parent['baseline_manifest_sha256'],'base source manifest drift')
    sources={n:read_input(old.ROOT/'docs/evidence/panda-dispatch-coverage-01/source'/n,1024**2) for n in old.base.MEMBERS}
    original=read_input(old.ROOT/'docs/evidence/panda-adapter-sdk-01/source/makepanda.py.data',1024**2);changed,build,_=old.transform(sources,original)
    reverse={v:k for k,v in old.base.MEMBERS.items()};files=native_files();native={'panda/src/glstuff/'+n:n for n in files};entries=[]
    for row in records:
        name=row['path'];p=path/name
        if name in (PARENT,old.BASE_MANIFEST):continue
        if name in native:need(row['kind']=='file' and not p.is_symlink() and p.read_bytes()==files[native[name]],'versioned native stage drift');continue
        if row['kind']=='symlink':mode,data='120000',os.fsencode(os.readlink(p))
        else:mode,data=('100755' if p.stat().st_mode&stat.S_IXUSR else '100644'),p.read_bytes()
        if name in reverse:
            key=reverse[name];need(data==changed[key],'source hook drift');data=sources[key]
        elif name==old.BUILD:need(data==build,'build graph drift');data=original
        entries.append((name,mode,old.blob_id(data)))
    need(old.git_tree(entries)==old.UPSTREAM_TREE,'reconstructed upstream tree mismatch');return m

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--upstream',required=True);p.add_argument('--out',required=True);a=p.parse_args(argv)
    try:r=stage(a.upstream,a.out);print(json.dumps(dict(source_files=r['source_tree_files'],native_admitted=False)));return 0
    except (ValueError,OSError) as e:print('source rejected: '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
