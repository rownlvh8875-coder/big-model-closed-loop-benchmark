"""Static pinned Panda source/ELF identity audit. Never load those shared objects.

Run as `python -B -m scripts.audit_readback_return_source --out DIR`.
This is an inactive handoff: ELF imports/source version do not prove a usable ABI.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
WHEEL=ROOT/'output/stage7-python-wheel-closure/python-lock-20261114-02/wheels/panda3d-1.10.13-cp311-cp311-manylinux2014_x86_64.whl'
MANIFEST=ROOT/'docs/evidence/engine-clock-sealed-image-06/installed-files.json'
CXX=Path('/workspace/.cloud-tools/stage7/glGraphicsStateGuardian-1.10.13.cxx')
WHEEL_SHA='68e9e215c4192ca14ab1304be79f86657f43d6d663b3dbe3af209caf8eb9793c'
MANIFEST_SHA='f81fa5be38bc9853b6eff1d0ea524be97f3d1e92f5c1f0f9e1449a11b4c4b59f'
CXX_SHA='a7ee480dbafa47f652bbab8b525606421cde6d9a15507422c423fe62128f2d6a'
MEMBERS={
 'panda3d/libpandagl.so':('f38e0734a5344eda9a11e3024695febf2cea0177aa80985b67ceef5837a088d7',913073),
 'panda3d/libpanda.so.1.10':('2750e15c1f171536fabaeb07e283b866930ba16dd51aa442f819d84240f1cd5f',18747689)}
GSG='_ZN23GLGraphicsStateGuardian23framebuffer_copy_to_ramEP7TextureiiPK13DisplayRegionRK12RenderBuffer'

def need(ok,message):
    if not ok:raise ValueError(message)

def digest(data):return hashlib.sha256(data).hexdigest()

def verified_member(wheel,member,entries,expected_sha,expected_size):
    """Compare zip bytes with one exact installed-file identity; no extraction/load."""
    with zipfile.ZipFile(wheel) as z:
        matches=[i for i in z.infolist() if i.filename==member]
        need(len(matches)==1 and matches[0].file_size==expected_size,'zip member identity/size')
        data=z.read(matches[0])
    need(len(data)==expected_size and digest(data)==expected_sha,'member hash')
    path='/opt/venv/lib/python3.11/site-packages/'+member
    rows=[e for e in entries if e.get('path')==path]
    need(len(rows)==1 and rows[0].get('kind')=='file' and rows[0].get('sha256')==expected_sha
         and type(rows[0].get('nbytes')) is int and rows[0]['nbytes']==expected_size,'installed member identity')
    return data

def probe_environment():
    from scripts import renderer_pipeline_sealed_v1 as sealed
    profile=sealed.environment_profile();sealed.check_environment(profile,'parent')
    rejected=False
    try:sealed.check_environment(dict(profile,LD_PRELOAD='/inactive/readback-return.so'),'parent')
    except ValueError:rejected=True
    need(rejected,'old runtime unexpectedly admits preload')
    return dict(baseline_accepted=True,added_preload_rejected=rejected,runtime_admission_ready=False,
                old_contract_modified=False,probe_kind='PURE_DICTIONARY_GUARD_NO_PROCESS_LAUNCH')

def inspect_elf(path):
    result={}
    for name,flags in (('symbols',['-WsW']),('relocations',['-rW']),('dynamic',['-dW'])):
        p=subprocess.run(['readelf',*flags,str(path)],capture_output=True,text=True,timeout=15,check=True)
        result[name]=p.stdout
    return result

def audit(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    wheel=WHEEL.read_bytes();manifest_bytes=MANIFEST.read_bytes();source=CXX.read_bytes()
    need(digest(wheel)==WHEEL_SHA and digest(manifest_bytes)==MANIFEST_SHA and digest(source)==CXX_SHA,'pinned input identity')
    manifest=json.loads(manifest_bytes);members={};elfs={}
    for member,(sha,size) in MEMBERS.items():
        data=verified_member(WHEEL,member,manifest['entries'],sha,size)
        path=out/Path(member).name;path.write_bytes(data);metadata=inspect_elf(path);elfs[member]=metadata
        files={}
        for kind,text in metadata.items():
            target=out/(Path(member).name+'.'+kind+'.txt');target.write_text(text)
            files[kind]=dict(path=target.name,nbytes=target.stat().st_size,sha256=digest(target.read_bytes()))
        members[member]=dict(sha256=sha,nbytes=size,installed_identity_matches=True,readelf_files=files)
    gl=elfs['panda3d/libpandagl.so'];panda=elfs['panda3d/libpanda.so.1.10']
    gl_import=[l.strip() for l in gl['symbols'].splitlines() if ' UND ' in l and l.split()[-1]=='glReadPixels']
    gsg=[l.strip() for l in gl['symbols'].splitlines() if GSG in l]
    read_reloc=[l.strip() for l in gl['relocations'].splitlines() if 'glReadPixels' in l]
    gsg_reloc=[l.strip() for l in gl['relocations'].splitlines() if GSG in l]
    size_symbols=[l.strip() for l in panda['symbols'].splitlines() if 'get_ram_image_size' in l and ' UND ' not in l]
    need(bool(gl_import) and bool(gsg) and len(read_reloc)==1 and len(gsg_reloc)==3,'read boundary ELF metadata')
    lines=source.decode().splitlines()
    excerpt='\n'.join(f'{i+1}: {lines[i]}' for i in range(7456,7495))+'\n'
    (out/'source-excerpt.txt').write_text(excerpt)
    result=dict(schema='readback-return-static-source-audit-v1',kind='STATIC_DATA_ONLY_NO_ELF_LOAD',
        wheel=dict(path=str(WHEEL.relative_to(ROOT)),nbytes=len(wheel),sha256=WHEEL_SHA),
        installed_manifest=dict(path=str(MANIFEST.relative_to(ROOT)),nbytes=len(manifest_bytes),sha256=MANIFEST_SHA),
        upstream_source=dict(path=str(CXX),nbytes=len(source),sha256=CXX_SHA,
            excerpt='source-excerpt.txt',original_read_line=7477,component_reordering_after_read=True,
            source_to_compiled_instruction_binding_proven=False),
        members=members,gl_read_import=gl_import,gsg_method=gsg,gl_read_relocations=read_reloc,gsg_relocations=gsg_reloc,
        standalone_ram_size_exports=size_symbols,environment_probe=probe_environment(),runtime_admission_ready=False,
        original_gpu_bytes_observed=False,new_native_runs=0,new_gl_calls=0,new_model_runs=0,new_official_ort_runs=0,
        inactive_gates=[
            'Qualified original GL dispatch ABI and actual instruction binding; no ambient symbol lookup assumption.',
            'Validated accessible borrowed RAM span from actual Texture/view/face state, including 2D offset and component type.',
            'Observed pre-call pack/PBO/read-FBO/context and producer camera identity; labels must not be inferred from requester/order.',
            'Same-process window nonce/host call binding and original post-return memory copy before Panda component reordering.',
            'New reviewed runtime/source/build/maps/environment contract; old sealed contract rejects preload and stays unchanged.',
            'Fresh bounded native canary allowance, ON/OFF control and raw evidence review before any new native collection.',
            'GPU write success/freshness and physical-frame association remain separate from void return or CPU byte equality.'])
    (out/'audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    args=parser.parse_args();result=audit(args.out)
    print(json.dumps(dict(runtime_admission_ready=result['runtime_admission_ready'],members=len(result['members']),out=args.out)))

if __name__=='__main__':main()
