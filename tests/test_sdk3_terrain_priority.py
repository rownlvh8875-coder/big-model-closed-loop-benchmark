"""Adapter contracts use a tiny independent LESS-depth raster reference, no SDK."""
from types import SimpleNamespace
import unittest
try:from bigbench import sdk3_terrain_priority as h
except ImportError:h=None
class Attr:
    serial=100
    def __init__(self,*args):self.value=args;Attr.serial+=1;self.this=Attr.serial
class Shader:
    @staticmethod
    def getClassSlot():return 1
class Bin:
    @staticmethod
    def getClassSlot():return 2
    @staticmethod
    def make(name,order):return Attr(name,order)
class State:
    serial=200
    def __init__(self,items):self.items=dict(items);State.serial+=1;self.this=State.serial
    def getAttrib(self,slot):return self.items.get(slot,(None,0))[0]
    def getOverride(self,slot):return self.items.get(slot,(None,0))[1]
    def addAttrib(self,attr,priority):return State(dict(self.items,**{})|{2:(attr,priority)})
    def removeAttrib(self,slot):return State({k:v for k,v in self.items.items() if k!=slot})
    def __eq__(self,other):return isinstance(other,State) and self.items==other.items
class Camera:
    serial=300
    def __init__(self,key='rgb',fail=False):Camera.serial+=1;self.this=Camera.serial;self.key=key;self.states={'terrain':State({1:(Attr('shader'),0),9:(Attr('unchanged'),5)}),'other':State({9:(Attr('other'),9)})};self.fail=fail
    def node(self):return self
    def getTagStateKey(self):return self.key
    def getTagState(self,label):return self.states.get(label)
    def setTagState(self,label,state):
        self.states[label]=state
        if self.fail:self.fail=False;raise RuntimeError('update failed after mutation')
def fixture():
    road,wide,shadow=Camera(),Camera(),Camera('shadow');return SimpleNamespace(sensors={'bigbench_road':SimpleNamespace(cam=road),'bigbench_wide':SimpleNamespace(cam=wide)},shadow=shadow),SimpleNamespace(CullBinAttrib=Bin,ShaderAttrib=Shader)
def render(camera,order,terrain_depth=1065153572,geometry_depth=1065153572):
    attr=camera.getTagState('terrain').getAttrib(2);priority=10 if attr and attr.value==('background',-1) else 20
    commands=[(priority if kind=='terrain' else 20,i,kind) for i,kind in enumerate(order)];depth=1065353216;color='clear'
    for _,_,kind in sorted(commands):
        value=terrain_depth if kind=='terrain' else geometry_depth
        if value<depth:depth=value;color=kind
    return color
class TerrainPriority(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'cause-specific priority adapter is missing')
    def apply(self,engine,core):return h.install_rgb_terrain_priority(engine,terrain_label='terrain',tag_key='rgb',core=core)
    def test_measured_equal_depth_order_dependence_becomes_fixed_terrain_priority(self):
        e,c=fixture();cam=e.sensors['bigbench_road'].cam;orders=[['geometry','terrain'],['terrain','geometry']];self.assertEqual([render(cam,o) for o in orders],['geometry','terrain']);r=self.apply(e,c);self.assertEqual([render(cam,o) for o in orders],['terrain','terrain']);self.assertEqual(r['repair_id'],h.REPAIR_ID)
    def test_strictly_closer_geometry_still_occludes_farther_terrain(self):
        e,c=fixture();self.apply(e,c);cam=e.sensors['bigbench_road'].cam
        for order in (['geometry','terrain'],['terrain','geometry']):
            self.assertEqual(render(cam,order,geometry_depth=1065153571),'geometry');self.assertEqual(render(cam,order,terrain_depth=1065153571),'terrain')
    def test_only_two_rgb_bins_change_with_original_shaders_and_other_attributes(self):
        e,c=fixture();old={name:dict(s.cam.states) for name,s in e.sensors.items()};shadow=dict(e.shadow.states);r=self.apply(e,c);self.assertEqual(len(r['cameras']),2);self.assertEqual(e.shadow.states,shadow)
        for name,s in e.sensors.items():
            current=s.cam.getTagState('terrain');self.assertEqual(current.removeAttrib(2),old[name]['terrain']);self.assertIs(current.getAttrib(1),old[name]['terrain'].getAttrib(1));self.assertIs(s.cam.states['other'],old[name]['other']);self.assertEqual(current.getOverride(2),1000)
    def test_invalid_wide_preflight_leaves_road_unmodified(self):
        e,c=fixture();old=e.sensors['bigbench_road'].cam.getTagState('terrain');e.sensors['bigbench_wide'].cam.key='wrong'
        with self.assertRaises(ValueError):self.apply(e,c)
        self.assertIs(e.sensors['bigbench_road'].cam.getTagState('terrain'),old)
    def test_update_failure_rolls_back_both_cameras_even_if_second_mutated(self):
        e,c=fixture();old={name:s.cam.getTagState('terrain') for name,s in e.sensors.items()};e.sensors['bigbench_wide'].cam.fail=True
        with self.assertRaises(RuntimeError):self.apply(e,c)
        for name,s in e.sensors.items():self.assertIs(s.cam.getTagState('terrain'),old[name])
    def test_existing_unknown_bin_is_rejected_before_any_update(self):
        e,c=fixture();old=e.sensors['bigbench_road'].cam.getTagState('terrain');wide=e.sensors['bigbench_wide'].cam;wide.states['terrain']=wide.states['terrain'].addAttrib(Bin.make('fixed',7),10)
        with self.assertRaises(ValueError):self.apply(e,c)
        self.assertIs(e.sensors['bigbench_road'].cam.getTagState('terrain'),old)
if __name__=='__main__':unittest.main()
