"""Real observer over CPU doubles; large RAM images are sparse mappings."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,mmap,struct
from tests.sdk3_terrain_attribute_fixtures import fixture as previous
from tests.test_sdk3_prepared_texture import EXTENT
from tests.test_sdk3_terrain_attribute import NoWholeCopyMap
from scripts import panda_sdk3_runtime as p,sdk3_terrain_state as terrain

def fixture(folder,native,*,mip_resident=True,missing_output=False,cap=16384,fail=False,rss_delta=0,absent=False):
    with NoWholeCopyMap(-1,EXTENT,access=mmap.ACCESS_WRITE) as mapping:
        view=memoryview(mapping).toreadonly()
        def snapshot(core,engine,sensor,geometry,out,nonce,journal):
            gsg=SimpleNamespace(this=2001,getPreparedObjects=lambda:SimpleNamespace(this=3001),getMaxTextureDimension=lambda:cap,getSupportsTexNonPow2=lambda:True,getMaxTextureStages=lambda:16)
            output=SimpleNamespace(getGsg=lambda:gsg);engine.win=None if missing_output else output;sensor.buffer=output;sensor.manager=SimpleNamespace(buffers=[output])
            samples=terrain.candidate_samples(geometry['hits'],[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]],engine.terrain._elevation_texture_ratio)
            for s in samples:
                for x,y in terrain.footprint([11264,11264],s['attribute_uv'],'repeat','repeat'):struct.pack_into('=f',mapping,(y*11264+x)*4,.25)
            for t in (engine.terrain.semantic_tex,engine.terrain.heightfield_tex,engine.terrain.yellow_lane_line):
                attribute=t is engine.terrain.semantic_tex
                t.getNumViews=lambda:1;t.getNumRamMipmapImages=lambda a=attribute:2 if a and mip_resident else 1
                t.getExpectedMipmapXSize=lambda n,t=t:max(1,t.getXSize()>>n);t.getExpectedMipmapYSize=lambda n,t=t:max(1,t.getYSize()>>n)
                t.getExpectedRamMipmapImageSize=lambda n,t=t:t.getExpectedMipmapXSize(n)*t.getExpectedMipmapYSize(n)*4
                t.hasRamMipmapImage=lambda n,a=attribute:n==0 or a and n==1 and mip_resident
                t.getRamMipmapImageSize=lambda n,t=t:t.getExpectedRamMipmapImageSize(n) if t.hasRamMipmapImage(n) else 0
                t.getRamMipmapImage=lambda n:view
                t.isPrepared=lambda p:True;t.getDataSizeBytes=lambda p,a=attribute:EXTENT if a else 24;t.getActive=lambda p:False;t.getResident=lambda p:False;t.wasImageModified=lambda p:True
                if fail and attribute:t.getNumViews=lambda:(_ for _ in ()).throw(RuntimeError('cache metadata interruption'))
            # The real attribute observer samples RSS twice, then prepared observer twice.
            with patch.object(native.resource,'getrusage',side_effect=[SimpleNamespace(ru_maxrss=v) for v in (100,100,100,100+rss_delta)]):return native.snapshot_terrain(core,engine,sensor,geometry,out,nonce,journal)
        adapter=SimpleNamespace(p=native.p,os=native.os,time=native.time,snapshot_terrain=snapshot)
        try:dest,ref,nonce,result=previous(folder,adapter,absent=absent)
        finally:view.release()
    q=dest/'prepared.json';x=json.loads(q.read_text());x.update(observer_finalized=True,terrain_sha256=p.digest(dest/'terrain.json'),material_sha256=p.digest(dest/'material.json'));q.write_text(json.dumps(x,indent=2)+'\n')
    q=dest/'command.json';c=json.loads(q.read_text());c['argv'][c['argv'].index('/work/repo/scripts/sdk3_terrain_attribute_native.py')]='/work/repo/scripts/sdk3_prepared_texture_native.py';q.write_text(json.dumps(c)+'\n');return dest,ref,nonce,x
