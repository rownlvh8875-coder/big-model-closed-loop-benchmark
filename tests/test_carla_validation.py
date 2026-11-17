"""Pure/fake CARLA contracts; no actual Unreal server or model evidence."""
import copy,unittest,xml.etree.ElementTree as ET
from unittest.mock import Mock
from tests.full_s_fakes import route as lanes
from bigbench.full_s_validation import validate_route
try:from bigbench import carla_validation as c
except ImportError:c=None
class CarlaContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(c,'dedicated CARLA adapter missing')
 def test_opendrive_centers_right_lane_on_reference_without_moving_route(self):
  rows=validate_route(lanes());root=ET.fromstring(c.opendrive(rows));road=root.find('road');self.assertEqual(len(road.findall('planView/geometry')),3);self.assertAlmostEqual(float(road.find('lanes/laneOffset').get('a')),rows[0]['width_m']/2);self.assertEqual(road.find('lanes/laneSection/right/lane').get('id'),'-1');self.assertEqual([g[0].tag for g in road.findall('planView/geometry')],['arc','line','arc'])
 def test_carla_transform_reflects_y_and_heading_once(self):
  self.assertEqual(c.carla_pose(1,2,.5),dict(x=1.,y=-2.,z=1.22,yaw_deg=-.5*180/c.math.pi,pitch_deg=0.,roll_deg=0.))
 def test_server_and_dynamic_ownership_gate_before_mutation(self):
  with self.assertRaises(ValueError):c.require_dedicated(False,'0.9.16','0.9.16',[])
  for actors in [['vehicle.tesla.model3'],['walker.pedestrian.0001'],['sensor.camera.rgb']]:
   with self.assertRaises(ValueError):c.require_dedicated(True,'0.9.16','0.9.16',actors)
  with self.assertRaises(ValueError):c.require_dedicated(True,'0.9.15','0.9.16',[])
 def test_actual_waypoint_gate_rejects_wrong_lane_offset_and_yaw(self):
  good=[dict(expected_x=1.,expected_y=2.,expected_heading_rad=.5,actual_x=1.,actual_y=-2.,actual_yaw_deg=-.5*180/c.math.pi,road_id=1,lane_id=-1)]
  self.assertTrue(c.verify_waypoints(good)['passed'])
  for key in ('actual_y','actual_yaw_deg'):
   bad=copy.deepcopy(good);bad[0][key]+=1
   with self.assertRaises(ValueError):c.verify_waypoints(bad)
 def test_parent_recovery_refuses_foreign_actors_before_world_reset(self):
  lease=c.CarlaParentLease.__new__(c.CarlaParentLease);lease.client=Mock();lease.client.get_world.return_value.get_actors.return_value=[Mock(type_id='vehicle.other',id=99)]
  with self.assertRaises(ValueError):lease.recover([1])
  lease.client.load_world.assert_not_called();lease.client.generate_opendrive_world.assert_not_called()
 def test_sensor_frames_join_by_actual_frame_not_arrival_order(self):
  import queue
  q=queue.Queue();q.put(Mock(frame=4));wanted=Mock(frame=5);q.put(wanted);self.assertIs(c.frame_for(q,5),wanted)
  q=queue.Queue();q.put(Mock(frame=6))
  with self.assertRaises(ValueError):c.frame_for(q,5)
 def test_carla_route_class_cannot_be_passed_off_as_native_metadrive(self):
  from bigbench.full_s_receipts import recorded_route
  rows=validate_route(lanes());wrapped=[c.RegisteredCarlaLane(r) for r in rows];carla_rows=validate_route(wrapped)
  with self.assertRaises(ValueError):recorded_route(carla_rows)
  self.assertEqual(len(recorded_route(carla_rows,geometry_context='carla-prescribed')),3)
if __name__=='__main__':unittest.main()
