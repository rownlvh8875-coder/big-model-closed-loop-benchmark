"""Review regressions: isolated CPU bootstrap, bounded fake scene, safe NPY header."""
import hashlib,io,json,os,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import MagicMock,patch
import numpy as np
from scripts import sdk3_pixel_geometry as g,sdk3_pixel_geometry_native as n


def fake_scene(geoms=1,nodes=1,with_triangle=False,clock=None,jump_on_vertex=False):
    matrix=MagicMock();matrix.getCell.side_effect=lambda r,c:float(r==c)
    region=MagicMock();region.getLeft.return_value=region.getBottom.return_value=0.;region.getRight.return_value=region.getTop.return_value=1.
    cam=MagicMock();cam.getMat.return_value=matrix;cam.node().getDisplayRegion.return_value=region
    lens=MagicMock()
    def extrude(point,near,far):near[:]=[*point,-1.];far[:]=[*point,1.];return True
    lens.extrude.side_effect=extrude;lens.getProjectionMat.return_value=matrix;lens.getNear.return_value=.1;lens.getFar.return_value=100.
    buffer=MagicMock();buffer.getXSize.return_value=964;buffer.getYSize.return_value=604
    sensor=NS(cam=cam,buffer=buffer,get_lens=lambda:lens);paths=[]
    for _ in range(nodes):
        path=MagicMock();path.isHidden.return_value=False;path.getTightBounds.return_value=([-2.,-2.,-2.],[2.,2.,2.]);path.getMat.return_value=matrix
        node=path.node();node.getNumGeoms.return_value=geoms;geom=node.getGeom.return_value;geom.getNumPrimitives.return_value=int(with_triangle);geom.getVertexData().getNumRows.return_value=3 if with_triangle else 0
        primitive=geom.getPrimitive.return_value.decompose.return_value;primitive.getNumPrimitives.return_value=1;primitive.getPrimitiveStart.return_value=0;primitive.getPrimitiveEnd.return_value=3;primitive.getVertex.side_effect=lambda i:i;paths.append(path)
    world=MagicMock();world.findAllMatches.return_value=paths;engine=NS(render=world,origin=object());cam.getParent.return_value=engine.origin
    points=[[-1.,-1.,0.],[1.,-1.,0.],[0.,1.,0.]];readers=[]
    class Reader:
        def __init__(self,*args):self.count=0;readers.append(self)
        def getData3f(self):
            value=points[self.count];self.count+=1
            if jump_on_vertex:clock.value=100.
            return value
    core=NS(LPoint3f=lambda:[0.,0.,0.],LPoint2f=lambda *p:list(p),GeomVertexReader=Reader)
    return core,engine,sensor,readers


class BoundedSnapshot(unittest.TestCase):
    def test_one_node_cannot_exceed_512_meshes(self):
        core,engine,sensor,_=fake_scene(geoms=513)
        with patch.object(g,'save_geometry_archive',return_value={}),patch('time.monotonic',return_value=0.):report=n.snapshot_geometry(core,engine,sensor,Path('/unused'))
        self.assertLessEqual(len(report['meshes']),512);self.assertFalse(report['scan_finished_within_budget']);self.assertIn('mesh_budget',report['truncation_reasons'])

    def test_time_limit_is_checked_during_vertex_reads(self):
        clock=NS(value=0.);core,engine,sensor,readers=fake_scene(with_triangle=True,clock=clock,jump_on_vertex=True)
        with patch.object(g,'save_geometry_archive',return_value={}),patch('time.monotonic',side_effect=lambda:clock.value):report=n.snapshot_geometry(core,engine,sensor,Path('/unused'))
        self.assertFalse(report['scan_finished_within_budget']);self.assertIn('time_budget',report['truncation_reasons']);self.assertLess(readers[0].count,3)

    def test_exact_triangle_cap_with_remaining_geometry_is_incomplete(self):
        core,engine,sensor,_=fake_scene(nodes=2,with_triangle=True)
        with patch.object(g,'MAX_TRIANGLES',1),patch.object(g,'save_geometry_archive',return_value={}),patch('time.monotonic',return_value=0.):report=n.snapshot_geometry(core,engine,sensor,Path('/unused'))
        self.assertEqual(report['counts']['triangles_tested'],1);self.assertFalse(report['scan_finished_within_budget']);self.assertIn('triangle_budget',report['truncation_reasons'])


class IsolatedBootstrap(unittest.TestCase):
    def isolated(self,with_numpy):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out';out.mkdir();site=str(Path(np.__file__).resolve().parents[1]) if with_numpy else str(Path(tmp)/'empty');Path(site).mkdir(exist_ok=True)
            code=f'''import sys,os,json
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,{str(root)!r})
from scripts import sdk3_pixel_geometry_native as n,panda_sdk3_runtime as p
p.SITE={site!r}
class BlockNative:
 def find_spec(self,name,path=None,target=None):
  if name=='panda3d' or name.startswith('panda3d.'):
   raise RuntimeError('STOP_BEFORE_ANY_PANDA_OR_SDK')
sys.meta_path.insert(0,BlockNative())
try:n.run_native(SimpleNamespace(out={str(out)!r},server_owner=os.getppid(),nonce='ab'*16,repeat=0))
except BaseException as error:
 print(json.dumps(dict(error=str(error),numpy_loaded='numpy' in sys.modules,panda_loaded='panda3d.core' in sys.modules)))
'''
            result=subprocess.run([sys.executable,'-I','-S','-B','-c',code],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr);facts=json.loads(result.stdout.strip().splitlines()[-1]);report=out/'report.json';self.assertTrue(report.exists(),'missing failure receipt from isolated bootstrap');return facts,json.loads(report.read_text())

    def test_missing_numpy_retains_failure_receipt_before_sdk(self):
        facts,report=self.isolated(False);self.assertFalse(facts['numpy_loaded']);self.assertFalse(facts['panda_loaded']);self.assertEqual(report['status'],'FAILED');self.assertEqual(report['checkpoint'],'OWNED_BOOT')

    def test_pinned_site_precedes_numpy_import_and_native_import_is_blocked(self):
        facts,report=self.isolated(True);self.assertTrue(facts['numpy_loaded']);self.assertFalse(facts['panda_loaded']);self.assertEqual(facts['error'],'STOP_BEFORE_ANY_PANDA_OR_SDK');self.assertEqual(report['checkpoint'],'DEPENDENCIES_READY')


class NPYPreflight(unittest.TestCase):
    def test_huge_npy_shape_is_rejected_before_any_numpy_array_decoder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'malformed.npz';huge=io.BytesIO();np.lib.format.write_array_header_1_0(huge,dict(descr='<f8',fortran_order=False,shape=(10**12,3,3)));empty=io.BytesIO();np.save(empty,np.zeros((0,6),dtype='<i8'),allow_pickle=False)
            with zipfile.ZipFile(path,'w') as z:z.writestr('triangles.npy',huge.getvalue());z.writestr('ids.npy',empty.getvalue())
            receipt=dict(nbytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            with patch.object(np,'load',side_effect=AssertionError('array decoder reached before bounded header validation')):
                with self.assertRaises(ValueError):g.load_geometry_archive(path,receipt)

if __name__=='__main__':unittest.main()
