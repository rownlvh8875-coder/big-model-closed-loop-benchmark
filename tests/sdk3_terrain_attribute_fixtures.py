"""Execute the real new snapshot with a sparse2.03GB attribute CPU buffer."""
from types import SimpleNamespace
import json,mmap,struct
from tests.sdk3_terrain_state_fixtures import fixture as prior_fixture
from tests.test_sdk3_terrain_attribute import NoWholeCopyMap,EXTENT
from scripts import sdk3_terrain_state as terrain

def fixture(folder,native,*,absent=False,resident=True,interrupt=False):
    with NoWholeCopyMap(-1,EXTENT,access=mmap.ACCESS_WRITE) as mapping:
        view=memoryview(mapping).toreadonly()
        def snapshot(core,engine,sensor,geometry,out,nonce,journal):
            texture=engine.terrain.semantic_tex
            texture.getXSize=lambda:22528;texture.getYSize=lambda:22528;texture.getExpectedRamImageSize=lambda:EXTENT;texture.getRamImage=lambda:view
            if not absent and not interrupt:
                samples=terrain.candidate_samples(geometry['hits'],[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]],engine.terrain._elevation_texture_ratio)
                for sample in samples:
                    for x,y in terrain.footprint([22528,22528],sample['attribute_uv'],'repeat','repeat'):struct.pack_into('=f',mapping,(y*22528+x)*4,.1)
            return native.snapshot_terrain(core,engine,sensor,geometry,out,nonce,journal)
        adapter=SimpleNamespace(p=native.p,os=native.os,time=native.time,snapshot_terrain=snapshot)
        try:dest,ref,nonce,result=prior_fixture(folder,adapter,absent=absent,resident=resident,interrupt=interrupt)
        finally:view.release()
    path=dest/'command.json';command=json.loads(path.read_text());index=command['argv'].index('/work/repo/scripts/sdk3_terrain_state_native.py');command['argv'][index]='/work/repo/scripts/sdk3_terrain_attribute_native.py';path.write_text(json.dumps(command)+'\n');return dest,ref,nonce,result
