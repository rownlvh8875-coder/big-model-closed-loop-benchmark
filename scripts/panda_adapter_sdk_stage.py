"""Stage a single-image activity/cache SDK; actual Panda is never loaded."""
import argparse,hashlib,json,os,stat,sys
from pathlib import Path
from scripts import panda_source_dispatch as base
from scripts.build_panda_source_dispatch import git_tree,blob_id,UPSTREAM_TREE
from scripts.panda_dispatch_coverage import read_input
ROOT=Path(__file__).resolve().parents[1]
REVISION=base.REVISION
BUILD='makepanda/makepanda.py'
BUILD_SHA='6a84de4ad91ade0cde328117c4b0352b3ee546238fcad1a6cae90c66b898ad67'
BASE_MANIFEST='.source-dispatch-base.json'
NATIVE_PINS={'panda_source_dispatch.h': 'f2e869a8c7a2719d6a7eb7fbc1a350873793265fb1c1a7a32aa0e43e00eca7e9', 'panda_source_dispatch.cxx': '50bb0428619654444f050d2c9f88b4a81d6d3411748050335d2c4ca59be7a8d7', 'panda_source_activity.h': 'dc9a35ebacf684e022b28ef5a7b5bf565a8e57d309708d97b96fab614590a962', 'panda_source_activity.cxx': 'fb6a4445386cfc950e475d7dc7b93f208f1abb58e6febf70ac39451dbc5ff9f6', 'panda_cache_adapter.h': 'ad598c1edecdcaaf2b0663091d9560b2e64f9d739a902c5ca5cec2c2eae8e3bc', 'panda_cache_adapter.cxx': 'a36415a418cba4f3dedbbe45a9f7ce8c15a0fd02411ff21f715c26d179bf9db6', 'readback_command_state.h': '4c64a2059cd722fa9a35d6e4ed81ac80bd4c89bdd8bac8ff73b00213b81db2b8', 'readback_command_state.c': '49e986eca295519f180e6b96477ab1752f6bd0996bdf9f9f535bcfc5c17e3bc2', 'readback_return_core.h': '1a78841638968a7c9d08fe845b1d0b3b7976ab0808edcc22ff6cfd631e0ee58f'}
need=base.need
canonical=base.canonical

def native_files():
    files={name:read_input(canonical(ROOT/'native'/name),1024*1024) for name in NATIVE_PINS}
    need(all(hashlib.sha256(data).hexdigest()==NATIVE_PINS[name] for name,data in files.items()),'immutable native source pin mismatch')
    return files

def transform(sources,makepanda):
    need(type(makepanda) is bytes and hashlib.sha256(makepanda).hexdigest()==BUILD_SHA,'exact upstream makepanda required')
    changed,manifest=base.transform_sources(sources)
    key='glGraphicsStateGuardian_src.cxx'
    changed[key]=base.once(changed[key].decode(),'#include "panda_source_dispatch.cxx"','#include "panda_source_activity.cxx"').encode()
    anchor="  TargetAdd('libpandagl.dll', input='p3glxdisplay_composite1.obj')"
    addition="""
  # Pinned command adapter: C cache and C++ observer in the same GLX image.
  PCA_OPTS=['DIR:panda/src/glstuff', 'BUILDING:PANDAGL', 'NOHIDDEN']
  TargetAdd('pca_command_state.obj', opts=PCA_OPTS, input='readback_command_state.c')
  TargetAdd('pca_adapter.obj', opts=PCA_OPTS, input='panda_cache_adapter.cxx')
  TargetAdd('libpandagl.dll', input=['pca_command_state.obj', 'pca_adapter.obj'])"""
    build=base.once(makepanda.decode(),anchor,anchor+addition).encode()
    manifest.update(schema='panda-adapter-sdk-stage-v1',native_admitted=False,source_activity_required=True,
                    build_original_sha256=BUILD_SHA,build_candidate_sha256=hashlib.sha256(build).hexdigest())
    for name,data in changed.items():manifest['files'][name]['candidate_sha256']=hashlib.sha256(data).hexdigest();manifest['files'][name]['candidate_nbytes']=len(data)
    return changed,build,manifest

def stage(upstream,dest):
    upstream,dest=canonical(upstream),canonical(dest);files=native_files()
    need(not dest.exists(),'existing SDK stage preserved')
    # The base stager verifies exact clean upstream and archives only that commit.
    baseline=base.stage(upstream,dest)
    old=dest/'source-dispatch-manifest.json';baseline_hash=hashlib.sha256(old.read_bytes()).hexdigest();old.rename(dest/BASE_MANIFEST)
    sources={name:read_input(ROOT/'docs/evidence/panda-dispatch-coverage-01/source'/name,1024*1024) for name in base.MEMBERS}
    changed,build,manifest=transform(sources,read_input(dest/BUILD,1024*1024))
    for name,data in changed.items():(dest/base.MEMBERS[name]).write_bytes(data)
    (dest/BUILD).write_bytes(build)
    for name,data in files.items():
        path=dest/'panda/src/glstuff'/name
        if path.exists():need(name in ('panda_source_dispatch.h','panda_source_dispatch.cxx') and path.read_bytes()==data,'native staging collision')
        path.write_bytes(data)
    manifest.update(upstream_tree=UPSTREAM_TREE,baseline_manifest_sha256=baseline_hash,native_sha256=dict(NATIVE_PINS),source_tree=base.tree_records(dest))
    manifest['source_tree_files']=len(manifest['source_tree'])
    (dest/'adapter-sdk-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    need(verify_stage(dest)==manifest,'new SDK stage verification failed');return manifest

def verify_stage(path):
    path=canonical(path);manifest=json.loads(read_input(path/'adapter-sdk-manifest.json',16*1024*1024))
    need(manifest.get('schema')=='panda-adapter-sdk-stage-v1' and manifest.get('upstream_revision')==REVISION and manifest.get('upstream_tree')==UPSTREAM_TREE and manifest.get('runtime_admission_ready') is False and manifest.get('native_admitted') is False,'pinned non-admitting SDK manifest required')
    records=[r for r in base.tree_records(path) if r['path']!='adapter-sdk-manifest.json']
    need(records==manifest.get('source_tree'),'SDK source tree changed/partial')
    need(hashlib.sha256(read_input(path/BASE_MANIFEST,16*1024*1024)).hexdigest()==manifest.get('baseline_manifest_sha256'),'baseline manifest drift')
    sources={name:read_input(ROOT/'docs/evidence/panda-dispatch-coverage-01/source'/name,1024*1024) for name in base.MEMBERS}
    original_build=read_input(ROOT/'docs/evidence/panda-adapter-sdk-01/source/makepanda.py.data',1024*1024)
    changed,build,_=transform(sources,original_build);files=native_files()
    reverse={member:name for name,member in base.MEMBERS.items()};native={'panda/src/glstuff/'+name:name for name in files};entries=[]
    need(manifest.get('native_sha256')==NATIVE_PINS,'native SDK profile mismatch')
    for row in records:
        relative=row['path'];file=path/relative
        if relative==BASE_MANIFEST:continue
        if relative in native:need(file.read_bytes()==files[native[relative]],'native stage bytes changed');continue
        if row['kind']=='symlink':mode,data='120000',os.fsencode(os.readlink(file))
        else:mode,data=('100755' if file.stat().st_mode&stat.S_IXUSR else '100644'),file.read_bytes()
        if relative in reverse:
            name=reverse[relative];need(data==changed[name],'SDK source hook bytes changed');data=sources[name]
        elif relative==BUILD:need(data==build,'SDK build graph changed');data=original_build
        entries.append((relative,mode,blob_id(data)))
    need(git_tree(entries)==UPSTREAM_TREE,'SDK reconstructed upstream tree mismatch');return manifest

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--upstream',required=True);parser.add_argument('--out',required=True);args=parser.parse_args(argv)
    try:
        r=stage(args.upstream,args.out);print(json.dumps(dict(source_files=r['source_tree_files'],out=args.out,native_admitted=False)));return 0
    except (ValueError,OSError) as exc:print('adapter SDK source rejected: '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
