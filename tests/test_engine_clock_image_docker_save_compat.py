"""Tiny owned Docker28 metadata fixtures; never call Docker or execute layer bytes."""
import copy,hashlib,io,json,tarfile,tempfile,time,unittest
from pathlib import Path
from test_engine_clock_image_archive import TAG,rawjson,sha,tarbytes,make_save
try:from scripts import engine_clock_image_archive_v2 as a
except ImportError:from scripts import engine_clock_image_archive as a
EMPTY={'Hostname':'','Domainname':'','User':'','AttachStdin':False,'AttachStdout':False,'AttachStderr':False,'Tty':False,'OpenStdin':False,'StdinOnce':False,'Env':None,'Cmd':None,'Image':'','Volumes':None,'WorkingDir':'','Entrypoint':None,'OnBuild':None,'Labels':None}
def docker28(root,mutation=None):
 p,cid,config=make_save(root,config_patch={'created':'2026-11-13T21:06:39Z'})
 with tarfile.open(p,'r:') as t:
  old=json.load(t.extractfile('manifest.json'))[0];cfg=t.extractfile(old['Config']).read();layers=[t.extractfile(n).read() for n in old['Layers']]
 cp='blobs/sha256/'+sha(cfg);lp=['blobs/sha256/'+sha(raw) for raw in layers]
 legacy=[{'id':'1'*64,'created':'1970-01-01T00:00:00Z','container_config':copy.deepcopy(EMPTY),'os':'linux'},{'id':'2'*64,'parent':'1'*64,'created':config['created'],'container_config':copy.deepcopy(EMPTY),'os':'linux','architecture':'amd64','config':{**copy.deepcopy(EMPTY),**config['config']}}]
 annotations={'io.containerd.image.name':'docker.io/library/'+TAG,'org.opencontainers.image.ref.name':TAG.rsplit(':',1)[1]}
 state={'legacy':legacy,'annotations':annotations,'extra':[]}
 if mutation:mutation(state)
 oci={'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json','config':{'digest':cid,'size':len(cfg),'mediaType':'application/vnd.oci.image.config.v1+json'},'layers':[{'digest':'sha256:'+sha(raw),'size':len(raw),'mediaType':'application/vnd.oci.image.layer.v1.tar'} for raw in layers]}
 im=rawjson(oci);entries=[(cp,cfg),*zip(lp,layers),('blobs/sha256/'+sha(im),im),('oci-layout',rawjson({'imageLayoutVersion':'1.0.0'})),('index.json',rawjson({'schemaVersion':2,'manifests':[{'digest':'sha256:'+sha(im),'size':len(im),'mediaType':oci['mediaType'],'annotations':annotations}]})),('manifest.json',rawjson([{'Config':cp,'RepoTags':[TAG],'Layers':lp}])),('repositories',rawjson({TAG.rsplit(':',1)[0]:{TAG.rsplit(':',1)[1]:lp[-1].split('/')[-1]}}))]
 for row in legacy:
  raw=rawjson(row);entries.append(('blobs/sha256/'+sha(raw),raw))
 entries+=state['extra'];p.write_bytes(tarbytes(entries));return p,cid
class DockerSaveCompatTests(unittest.TestCase):
 def test_owned_measured_docker28_tag_pair_and_compat_chain_are_cross_bound(self):
  with tempfile.TemporaryDirectory() as tmp:
   p,cid=docker28(Path(tmp));r=a.inspect_save_archive(p,expected_tag=TAG,deadline=time.perf_counter()+10)
   self.assertEqual(cid,r['config_digest']);self.assertEqual(2,r['compatibility_metadata_files']);self.assertFalse(r['native_admission'])
 def test_wrong_canonical_repository_or_tag_rejects(self):
  for key,value in [('io.containerd.image.name','docker.io/foreign/image:wrong'),('org.opencontainers.image.ref.name','wrong')]:
   with self.subTest(key=key),tempfile.TemporaryDirectory() as tmp:
    p,_=docker28(Path(tmp),lambda s:s['annotations'].__setitem__(key,value))
    with self.assertRaises(ValueError):a.inspect_save_archive(p,expected_tag=TAG,deadline=time.perf_counter()+10)
 def test_foreign_sidecar_commands_chain_top_config_or_extra_payload_reject(self):
  mutations=[lambda s:s['legacy'][0]['container_config'].__setitem__('Cmd',['never execute']),lambda s:s['legacy'][0].__setitem__('parent','2'*64),lambda s:s['legacy'][1]['config'].__setitem__('Env',['SECRET_SENTINEL']),lambda s:s['extra'].append(('unexpected',b'never execute'))]
  for change in mutations:
   with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
    p,_=docker28(Path(tmp),change)
    with self.assertRaisesRegex(ValueError,'^IMAGE_ARCHIVE_REJECTED$'):a.inspect_save_archive(p,expected_tag=TAG,deadline=time.perf_counter()+10)
if __name__=='__main__':unittest.main()
