"""Read-only fake/pure review reproductions, never actual GPU/CARLA evidence."""
from pathlib import Path
import tempfile,unittest
from unittest.mock import Mock,patch
from bigbench import carla_validation as c
from scripts import run_laptop_validation as l
class LaptopReviewRegressions(unittest.TestCase):
 def test_normal_carla_cleanup_refuses_new_foreign_actor(self):
  owner=c.DedicatedCarlaWorld.__new__(c.DedicatedCarlaWorld);owner.closed=False;owner.actors=[];owner.client=Mock();owner.mutated=True;owner.restored=False;owner.on_state=None;owner.original=dict(map_name='Town01',xodr='old',weather='old',settings='old');owner.client.get_world.return_value.get_actors.return_value=[Mock(id=99,type_id='vehicle.foreign')]
  with self.assertRaises(RuntimeError):owner.close()
  owner.client.load_world.assert_not_called();owner.client.generate_opendrive_world.assert_not_called()
 def test_failed_popen_does_not_reset_an_untouched_carla_server(self):
  lease=Mock();lease.recover.return_value={'restored':True}
  with tempfile.TemporaryDirectory() as tmp,patch.object(c,'CarlaParentLease',return_value=lease),patch.object(l.subprocess,'Popen',side_effect=OSError('no launch')):
   with self.assertRaises(OSError):l.launch_worker(dest=Path(tmp)/'owned',seed=20261109,scene='s_curve_left_right',probe=True,model=None,backend='carla',carla_host='127.0.0.1')
  lease.recover.assert_not_called()
 def test_interrupted_wait_reaps_child_before_carla_recovery(self):
  events=[];child=Mock(pid=42,returncode=-9);child.poll.return_value=None
  def kill():events.append('kill');child.poll.return_value=-9
  child.kill.side_effect=kill;calls=[0]
  def wait(**kw):
   events.append('wait');calls[0]+=1
   if calls[0]==1:raise KeyboardInterrupt()
   return -9
  child.wait.side_effect=wait;lease=Mock();lease.recover.side_effect=lambda ids:(events.append('recover') or {'restored':True})
  with tempfile.TemporaryDirectory() as tmp,patch.object(c,'CarlaParentLease',return_value=lease),patch.object(l.subprocess,'Popen',return_value=child):
   with self.assertRaises(KeyboardInterrupt):l.launch_worker(dest=Path(tmp)/'owned',seed=20261109,scene='s_curve_left_right',probe=True,model=None,backend='carla',carla_host='127.0.0.1')
  self.assertEqual(events,['wait','kill','wait','recover'])
 def test_owner_write_failure_after_spawn_still_reaps_child(self):
  child=Mock(pid=42,returncode=-9);child.poll.return_value=None;child.kill.side_effect=lambda:setattr(child.poll,'return_value',-9);original=l.write;calls=[0]
  def write(path,value):
   if path.name=='owner.json':
    calls[0]+=1
    if calls[0]==2:raise OSError('post-spawn receipt disk failure')
   return original(path,value)
  with tempfile.TemporaryDirectory() as tmp,patch.object(l.subprocess,'Popen',return_value=child),patch.object(l,'write',side_effect=write):
   with self.assertRaises(OSError):l.launch_worker(dest=Path(tmp)/'owned',seed=20261109,scene='s_curve_left_right',probe=True,model=None)
  child.kill.assert_called_once();child.wait.assert_called_once()
 def test_matching_sensor_frame_with_offset_image_transform_is_rejected(self):
  import queue
  from types import SimpleNamespace as NS
  from bigbench.kinematics import AgentState
  from bigbench.optical_calibration import PinholeRectifier,reference_source
  camera=c.CarlaWorldCamera.__new__(c.CarlaWorldCamera);camera.owner=NS(carla=Mock(),world=Mock());camera.owner.world.tick.return_value=5;camera.sensors={role:Mock() for role in ('road','wide')};camera.queues={};camera.intrinsics={role:reference_source(role) for role in ('road','wide')};camera.rectifier=PinholeRectifier();camera.sensor_frames=[];camera.last_source_rgb_sha256={}
  for role in ('road','wide'):
   image=NS(frame=5,timestamp=.25,width=964,height=604,raw_data=bytes(964*604*4),transform=NS(location=NS(x=1.5,y=-2.,z=1.22),rotation=NS(yaw=-.5*180/c.math.pi,pitch=0.,roll=0.)));q=queue.Queue();q.put(image);camera.queues[role]=q
  with self.assertRaisesRegex(ValueError,'pose'):camera.capture(AgentState(0.,1.,2.,.5,8.))
 def test_receiver_rejects_returned_sensor_pose_despite_matching_frame_hashes(self):
  pose=dict(t=0.,x=1.,y=2.,heading=.5,speed=8.);actual=c.carla_pose(1.,2.,.5);actual['z']+=.1;metadata=dict(frame=5,timestamp=.25,source_sha256='a'*64,transform=actual);frames=[dict(world_frame=5,pre_step_state=pose,cameras=dict(road=metadata,wide=metadata))]
  with self.assertRaisesRegex(ValueError,'pose'):c.validate_sensor_bindings(frames,[pose],[dict(road='a'*64,wide='a'*64)])
 def test_report_failure_after_restoration_does_not_reset_server_twice(self):
  import json
  lease=Mock();child=Mock(pid=42,returncode=0);child.poll.return_value=0;child.wait.return_value=0
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)/'owned'
   def popen(*args,**kwargs):(dest/'lifecycle.json').write_text(json.dumps(dict(world_mutation_entered=True,world_restored=True)));return child
   with patch.object(c,'CarlaParentLease',return_value=lease),patch.object(l.subprocess,'Popen',side_effect=popen):
    with self.assertRaises(FileNotFoundError):l.launch_worker(dest=dest,seed=20261109,scene='s_curve_left_right',probe=True,model=None,backend='carla',carla_host='127.0.0.1')
  lease.recover.assert_not_called()
 def test_parent_removes_owned_sensor_without_reloading_already_restored_world(self):
  from types import SimpleNamespace as NS
  lease=c.CarlaParentLease.__new__(c.CarlaParentLease);lease.client=Mock();world=lease.client.get_world.return_value;sensor=Mock(id=1,type_id='sensor.camera.rgb');sensor.destroy.return_value=True;world.get_actors.return_value=[sensor];world.get_map.return_value=NS(name='Town01',to_opendrive=lambda:'old');settings=NS(synchronous_mode=False);weather=NS(cloudiness=0.);world.get_settings.return_value=settings;world.get_weather.return_value=weather;lease.original=dict(map_name='Town01',xodr='old',settings=settings,weather=weather)
  result=lease.recover([1]);self.assertTrue(result['restored']);self.assertFalse(result['reset_performed']);sensor.destroy.assert_called_once();lease.client.load_world.assert_not_called()
if __name__=='__main__':unittest.main()


