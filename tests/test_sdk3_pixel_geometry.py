"""CPU-only geometry and observer ordering; no native SDK or rendering."""
import unittest,numpy as np
from scripts import sdk3_pixel_geometry as g

class CPUCandidateMath(unittest.TestCase):
    def test_pixel_centers_and_corners_use_top_left_origin(self):
        rows=g.pixel_samples(964,604,596,494)
        self.assertEqual([r['name'] for r in rows],['center','top_left','top_right','bottom_right','bottom_left'])
        self.assertEqual(rows[0]['ndc'],[229/964,-385/604])
        self.assertEqual(rows[1]['ndc'],[228/964,-384/604])
        self.assertEqual(rows[3]['ndc'],[230/964,-386/604])
        for args in [(964,604,-1,0),(964,604,964,0),(0,604,0,0)]:
            with self.assertRaises(ValueError):g.pixel_samples(*args)

    def test_front_hits_have_world_distance_and_barycentrics(self):
        triangles=np.array([[[-1,3,-1],[1,3,-1],[0,3,1]],[[-1,2,-1],[1,2,-1],[0,2,1]]],float)
        rows=g.intersect_triangles([0,0,0],[0,4,0],triangles,10)
        self.assertEqual([r['triangle_index'] for r in rows],[1,0])
        self.assertEqual([r['distance'] for r in rows],[2.,3.])
        self.assertEqual(rows[0]['barycentric'],[.25,.25,.5])
        self.assertEqual(rows[0]['position'],[0.,2.,0.])
        self.assertEqual(g.intersect_triangles([0,0,0],[0,1,0],triangles,1),[])

    def test_parallel_degenerate_behind_and_outside_triangles_do_not_hit(self):
        triangles=np.array([[[-1,-2,-1],[1,-2,-1],[0,-2,1]],[[0,0,0],[0,1,0],[0,2,0]],[[4,2,4],[6,2,4],[5,2,6]],[[-1,-1,4],[1,-1,4],[0,1,4]]],float)
        self.assertEqual(g.intersect_triangles([0,0,0],[0,1,0],triangles,10),[])

    def test_nonfinite_and_zero_direction_are_rejected(self):
        triangle=np.array([[[-1,2,-1],[1,2,-1],[0,2,1]]],float)
        for origin,direction,data,distance in [([0,0,0],[0,0,0],triangle,10),([float('nan'),0,0],[0,1,0],triangle,10),([0,0,0],[0,1,0],triangle*np.nan,10),([0,0,0],[0,1,0],triangle,float('inf'))]:
            with self.assertRaises(ValueError):g.intersect_triangles(origin,direction,data,distance)

    def test_box_filter_keeps_inside_and_rejects_parallel_outside(self):
        self.assertTrue(g.ray_box([0,0,0],[0,1,0],[-1,2,-1],[1,4,1],10))
        self.assertFalse(g.ray_box([2,0,0],[0,1,0],[-1,2,-1],[1,4,1],10))
        self.assertFalse(g.ray_box([0,0,0],[0,-1,0],[-1,2,-1],[1,4,1],10))

class PostReadObserver(unittest.TestCase):
    def test_reads_once_and_inspects_only_after_target_read_then_restores(self):
        events=[];value=object()
        class Sensor:
            def get_rgb_array_cpu(self):events.append('read');return value
        sensor=Sensor()
        with g.post_read_observer(sensor,lambda rgb:events.append('inspect'),target_call=7) as state:
            for _ in range(8):self.assertIs(sensor.get_rgb_array_cpu(),value)
            self.assertEqual(state,dict(read_attempts=8,reads=8,inspection_attempts=1,inspections=1))
        self.assertEqual(events,['read']*7+['inspect','read'])
        self.assertNotIn('get_rgb_array_cpu',vars(sensor))

    def test_callback_failure_restores_existing_instance_getter(self):
        class Sensor:pass
        sensor=Sensor();getter=lambda:13;sensor.get_rgb_array_cpu=getter
        def broken(rgb):raise RuntimeError('CPU inspection failed')
        with self.assertRaises(RuntimeError):
            with g.post_read_observer(sensor,broken,target_call=1):sensor.get_rgb_array_cpu()
        self.assertIs(sensor.get_rgb_array_cpu,getter)


class ReferenceAndArchive(unittest.TestCase):
    def source(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]/'docs/evidence/sdk3-rgb-forensics-01/actual/full_rgb/bundle/pair'
        return [json.loads((root/f'run-{i}/run.json').read_text()) for i in (0,1)]

    def test_source_reference_and_exact_replay_qualification(self):
        a,b=self.source();ref=g.reference_from_reports(a,b)
        self.assertEqual(len(ref['previous_states']),6)
        self.assertEqual(ref['previous_states'][-1]['x'],67.79573787289344)
        captures=[]
        for i in range(7):
            captures.append(dict(step=i+1,pose=ref['previous_states'][i-1] if i else dict(t=0.,x=0.,y=0.,heading=0.,speed=8.),road_sha256=a['frames'][i]['source_road_rgb_sha256'],wide_sha256=a['frames'][i]['source_wide_rgb_sha256']))
        result=g.qualify_replay(captures,ref);self.assertTrue(result['source_images_match_reference']);self.assertEqual(result['known_target_branch'],0)
        captures[0]['road_sha256']='00'*32
        self.assertFalse(g.qualify_replay(captures,ref)['source_images_match_reference'])
        self.assertFalse(g.qualify_replay(captures[:6],ref)['source_images_match_reference'])
        b['frames'][5]['world_x_m']+=1
        with self.assertRaises(ValueError):g.reference_from_reports(a,b)

    def test_geometry_archive_roundtrip_and_forged_bytes_rejection(self):
        import tempfile
        from pathlib import Path
        triangles=np.array([[[-1,2,-1],[1,2,-1],[0,2,1]]],dtype='<f8');ids=np.array([[0,0,0,0,1,2]],dtype='<i8')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'geometry.npz';receipt=g.save_geometry_archive(p,triangles,ids);a,b=g.load_geometry_archive(p,receipt)
            self.assertEqual(a.tolist(),triangles.tolist());self.assertEqual(b.tolist(),ids.tolist())
            p.write_bytes(p.read_bytes()+b'extra')
            with self.assertRaises(ValueError):g.load_geometry_archive(p,receipt)

    def test_new_child_entry_never_dispatches_an_official_model_trial(self):
        from types import SimpleNamespace
        from scripts import sdk3_pixel_geometry_native as n
        args=SimpleNamespace(out='/out',nonce='ab'*16,repeat=1)
        cmd=n.owned_child_command(args,456)
        self.assertIn('--owned-child',cmd);self.assertIn('456',cmd)
        self.assertTrue(cmd[4].endswith('/scripts/sdk3_pixel_geometry_native.py'))
        self.assertNotIn('--model-trial',cmd);self.assertNotIn('--model-pair',cmd)
        self.assertEqual(cmd[-2:],['--repeat','1'])


class MatrixCalibration(unittest.TestCase):
    def test_row_vector_transform_and_pixel_reprojection(self):
        matrix=np.eye(4);matrix[3,:3]=[2,3,4]
        self.assertEqual(g.transform_points([[1,2,3]],matrix).tolist(),[[3.,5.,7.]])
        rays=[]
        for sample in g.pixel_samples(964,604,596,494):rays.append(dict(**sample,origin=[*sample['ndc'],-1.],direction=[0.,0.,1.],max_distance=2.))
        self.assertEqual(g.ray_projection_error(rays,np.eye(4),np.eye(4)),0.)
        rays[0]['origin'][0]+=1
        self.assertGreater(g.ray_projection_error(rays,np.eye(4),np.eye(4)),.9)


if __name__=='__main__':unittest.main()
