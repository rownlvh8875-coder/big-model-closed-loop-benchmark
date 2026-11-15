from pathlib import Path
import hashlib,io,json,os,tarfile,tempfile,time,unittest
from unittest.mock import patch
from scripts.engine_clock_runtime_inventory import BASE_ROOTS,RUNTIME_EXCLUSIONS
try:
    from scripts import panda_sdk_routes_archive as save_archive
except ImportError:save_archive=None
try:
    from scripts import panda_sdk_routes_image as image
except ImportError:image=None
class LocalImageBytesTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(image,'byte-only local image builder required')
    def manifest(self):return dict(schema='installed-files-v1',roots=list(BASE_ROOTS),runtime_exclusions=list(RUNTIME_EXCLUSIONS),entries=[dict(path='/usr/lib/link',kind='symlink',target='owned'),dict(path='/usr/lib/owned',kind='file',mode=0o755,nbytes=3,sha256=hashlib.sha256(b'new').hexdigest())])
    def tar(self,path,case='good'):
        with tarfile.open(path,'w') as t:
            for p in ('etc','lib','lib64','opt','opt/python','opt/venv','usr','usr/lib'):
                x=tarfile.TarInfo(p);x.type=tarfile.DIRTYPE;x.mode=0o755;t.addfile(x)
            x=tarfile.TarInfo('usr/lib/link');x.type=tarfile.SYMTYPE;x.linkname='missing' if case=='link' else 'owned';t.addfile(x)
            if case=='forward':
                x=tarfile.TarInfo('usr/lib/hard');x.type=tarfile.LNKTYPE;x.linkname='usr/lib/owned';x.mode=0o755;t.addfile(x)
            if case!='missing':
                x=tarfile.TarInfo('usr/lib/owned');x.mode=0o644 if case=='mode' else 0o755;x.size=3;t.addfile(x,io.BytesIO(b'bad' if case=='hash' else b'new'))
            if case in ('extra','escape','duplicate'):
                x=tarfile.TarInfo({'extra':'usr/extra','escape':'../outside','duplicate':'usr/lib/owned'}[case]);x.mode=0o755;x.size=1;t.addfile(x,io.BytesIO(b'X'))
    def test_stopped_export_file_modes_links_and_hashes_match(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'root.tar';self.tar(p);r=image.inspect_export(p,self.manifest(),time.perf_counter()+5);self.assertEqual(r['matched_entries'],2);self.assertFalse(r['native_admitted'])
    def test_other_file_changes_missing_extra_mode_and_escape_reject(self):
        with tempfile.TemporaryDirectory() as t:
            for case in ('hash','link','mode','missing','extra','escape','duplicate'):
                p=Path(t)/(case+'.tar');self.tar(p,case)
                with self.subTest(case=case),self.assertRaises(ValueError):image.inspect_export(p,self.manifest(),time.perf_counter()+5)
    def test_forward_hardlinks_are_data_only_and_cycles_reject(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'root.tar';self.tar(p,'forward');m=self.manifest();m['entries'].insert(0,dict(path='/usr/lib/hard',kind='file',mode=0o755,nbytes=3,sha256=hashlib.sha256(b'new').hexdigest()))
            r=image.inspect_export(p,m,time.perf_counter()+5);self.assertEqual(r['matched_entries'],3)
            p=Path(t)/'cycle.tar';self.tar(p)
            with tarfile.open(p,'a') as stream:
                x=tarfile.TarInfo('usr/lib/hard');x.type=tarfile.LNKTYPE;x.linkname='usr/lib/hard';x.mode=0o755;stream.addfile(x)
            with self.assertRaises(ValueError):image.inspect_export(p,m,time.perf_counter()+5)
    def test_oversized_pax_metadata_rejects_before_large_allocation(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'pax.tar';x=tarfile.TarInfo('pax');x.type=tarfile.XHDTYPE;x.size=32*1024**2;p.write_bytes(x.tobuf(format=tarfile.PAX_FORMAT))
            with self.assertRaises(ValueError):image.inspect_export(p,self.manifest(),time.perf_counter()+5)
    def test_activation_and_publication_docker_verbs_are_rejected(self):
        for args in (['run','image'],['start','id'],['exec','id','python'],['push','tag'],['pull','tag'],['system','prune'],['rm','--force','id']):
            with self.subTest(args=args),self.assertRaises(ValueError):image.validate_docker_arguments(args)
        image.validate_docker_arguments(['create','--entrypoint','/bin/false','tag'])
    def test_context_cannot_add_run_extra_files_or_symlinked_sdk(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);lib=p/'libpandagl.so';lib.write_bytes(b'SDK');lib.chmod(0o755);docker=p/'Dockerfile';docker.write_text(image.recipe('owned:base'));sha=hashlib.sha256(b'SDK').hexdigest();image.validate_context(p,'owned:base',sha,3)
            docker.write_text(image.recipe('owned:base')+'RUN echo forbidden\n')
            with self.assertRaises(ValueError):image.validate_context(p,'owned:base',sha,3)
            docker.write_text(image.recipe('owned:base'));(p/'secret').write_bytes(b'not sent')
            with self.assertRaises(ValueError):image.validate_context(p,'owned:base',sha,3)
            (p/'secret').unlink();lib.unlink();lib.symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):image.validate_context(p,'owned:base',sha,3)
    def test_existing_output_and_expired_inspection_preserve_inputs(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'keep').write_bytes(b'prior')
            with self.assertRaises(ValueError):image.assemble_image(p,p,p)
            f=p/'root.tar';self.tar(f)
            with self.assertRaises(ValueError):image.inspect_export(f,self.manifest(),time.perf_counter()-1)
            self.assertEqual((p/'keep').read_bytes(),b'prior')
    def test_cpu_child_boundary_filters_endpoint_and_bounds_timeout(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);fake=p/'handwritten-cpu-docker';fake.write_text('#!/usr/bin/python3\nimport os,sys,time\nassert sys.argv[1]=="--host=unix:///var/run/docker.sock"\nassert "DOCKER_HOST" not in os.environ\nassert os.environ["DOCKER_CONFIG"]=="cpu-config-sentinel"\nprint("CPU child only",flush=True)\nif sys.argv[2]=="info":time.sleep(5)\n');fake.chmod(0o755);out=p/'logs';out.mkdir()
            with patch.object(image,'DOCKER',str(fake)),patch.dict(os.environ,{'DOCKER_HOST':'bad-endpoint','DOCKER_CONFIG':'cpu-config-sentinel'}):
                d=image._Docker(out,time.perf_counter()+5);self.assertEqual(d.call(['version'],1).strip(),'CPU child only')
                with self.assertRaises(ValueError):d.call(['info'],1)
                self.assertIn('CPU child only',(out/'docker-1.stdout').read_text())
                with self.assertRaises(ValueError):d.call(['start','forbidden'])
    def test_unqualified_build_and_mismatched_coverage_reject_before_output(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);b=p/'build';b.mkdir();c=p/'coverage';c.mkdir();out=p/'fresh';(b/'receipt.json').write_text('{}');(c/'coverage.json').write_text('{}')
            with self.assertRaises(ValueError):image.assemble_image(b,c,out)
            self.assertFalse(out.exists())
    def test_legacy_copy_compatibility_metadata_binds_head_container_config(self):
        from tests.test_engine_clock_image_archive import make_save,rawjson,sha,TAG
        self.assertIsNotNone(save_archive,'separate bounded legacy COPY metadata profile required')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);_,_,c=make_save(p);container=dict(Cmd=['/bin/sh','-c','#(nop) COPY CPU bytes'],Env=['CPU only']);created='2026-11-15T06:36:45Z'
            root=dict(id='1'*64,created='1970-01-01T00:00:00Z',container_config={k:v for k,v in save_archive.EMPTY_COMPAT_CONTAINER.items() if k!='OnBuild'},os='linux')
            head=dict(id='2'*64,parent='1'*64,created=created,container_config=container,os='linux',architecture='amd64',config={k:v for k,v in {**save_archive.EMPTY_COMPAT_CONTAINER,**c['config']}.items() if k!='OnBuild'})
            for changed in (False,True):
                if changed:head['container_config']=dict(Cmd=['unbound mutation'])
                extra=[('blobs/sha256/'+sha(rawjson(r)),rawjson(r)) for r in (root,head)];f,_,_=make_save(p,layout='oci',config_patch=dict(created=created,container_config=container),extra=extra)
                if changed:
                    with self.assertRaises(ValueError):save_archive.inspect_save_archive(f,expected_tag=TAG,deadline=time.perf_counter()+5)
                else:
                    r=save_archive.inspect_save_archive(f,expected_tag=TAG,deadline=time.perf_counter()+5);self.assertEqual(r['compatibility_metadata_files'],2);self.assertFalse(r['native_admission'])
if __name__=='__main__':unittest.main()
