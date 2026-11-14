import json
from types import SimpleNamespace as NS
import threading
import unittest
try:
    from scripts import readback_camera_registry as registry
except ImportError:
    registry=None
NONCE=bytes(range(1,33))
class Buffer:
    def __init__(self,address,gsg):self.this=address;self.gsg=gsg;self.calls=0;self.hook=None
    def getGsg(self):
        self.calls+=1
        if self.hook:self.hook()
        return self.gsg
def provider():
    gsg=NS(this=0xabcdef123456)
    road=NS(copy_texture=NS(this=0x111122223333),buffer=Buffer(0x111133334444,gsg))
    wide=NS(copy_texture=NS(this=0x555566667777),buffer=Buffer(0x555577778888,gsg))
    return NS(env=NS(engine=NS(sensors={'bigbench_road':road,'bigbench_wide':wide})))
class CameraRegistryTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(registry,'provider-owned readback registry required')
    def test_native_handles_are_private_and_roles_are_independent_of_requester(self):
        p=provider();r=registry.CameraRegistry(p,NONCE);r.guard(1,1);r.guard(2,2)
        self.assertEqual(r.native_binding(),(0x111122223333,0x555566667777,0xabcdef123456))
        d=r.descriptor();self.assertEqual(d['roles'],{'road':1,'wide':2});self.assertEqual(d['guards_returned'],2)
        self.assertEqual((d['getter_attempts'],d['getter_returns']),(6,6))
        self.assertFalse(d['native_admission_proven']);self.assertFalse(d['driver_state_proven'])
        self.assertNotIn(str(0x111122223333),json.dumps(d));self.assertNotIn(str(0xabcdef123456),json.dumps(d))
    def test_owner_changes_reject_before_any_more_gsg_getters(self):
        for mutate in (lambda p:setattr(p,'env',None),lambda p:setattr(p.env,'engine',NS()),
                       lambda p:setattr(p.env.engine,'sensors',{}),lambda p:setattr(p.env.engine.sensors['bigbench_road'],'copy_texture',NS(this=4)),
                       lambda p:setattr(p.env.engine.sensors['bigbench_wide'],'buffer',Buffer(9,NS(this=3)))):
            p=provider();r=registry.CameraRegistry(p,NONCE);mutate(p)
            with self.assertRaises(registry.RegistryError):r.guard(1,1)
            self.assertEqual(r.descriptor()['getter_attempts'],2)
            with self.assertRaises(registry.RegistryError):r.native_binding()
    def test_changed_native_handle_and_shared_native_owner_are_rejected(self):
        for change in ('texture','buffer','duplicate'):
            p=provider();s=p.env.engine.sensors
            if change=='duplicate':s['bigbench_wide'].copy_texture.this=s['bigbench_road'].copy_texture.this
            if change=='duplicate':
                with self.assertRaises(registry.RegistryError):registry.CameraRegistry(p,NONCE)
            else:
                r=registry.CameraRegistry(p,NONCE)
                if change=='texture':s['bigbench_road'].copy_texture.this=123
                else:s['bigbench_wide'].buffer.this=456
                with self.assertRaises(registry.RegistryError):r.guard(1,1)
                self.assertEqual(r.descriptor()['getter_attempts'],2)
    def test_two_buffers_must_return_same_nonzero_gsg_handle(self):
        p=provider();p.env.engine.sensors['bigbench_wide'].buffer.gsg=NS(this=8)
        with self.assertRaises(registry.RegistryError):registry.CameraRegistry(p,NONCE)
        p=provider();r=registry.CameraRegistry(p,NONCE);p.env.engine.sensors['bigbench_wide'].buffer.gsg=NS(this=8)
        with self.assertRaises(registry.RegistryError):r.guard(1,1)
        with self.assertRaises(registry.RegistryError):r.guard(1,1)
    def test_guard_budget_is_checked_before_getters(self):
        p=provider();r=registry.CameraRegistry(p,NONCE,max_windows=2);r.guard(1,1);r.guard(2,2)
        with self.assertRaises(registry.RegistryError):r.guard(3,1)
        self.assertEqual(r.descriptor()['getter_attempts'],6)
    def test_wrong_sequence_and_typed_config_reject(self):
        for args in ((b'bad',12),(bytes(32),12),(NONCE,13),(NONCE,True)):
            with self.assertRaises(registry.RegistryError):registry.CameraRegistry(provider(),args[0],max_windows=args[1])
        for call,camera in ((2,2),(1,2),(True,1)):
            r=registry.CameraRegistry(provider(),NONCE)
            with self.assertRaises(registry.RegistryError):r.guard(call,camera)
            self.assertEqual(r.descriptor()['getter_attempts'],2)
    def test_wrong_thread_and_reentrant_getter_poison_binding(self):
        r=registry.CameraRegistry(provider(),NONCE);errors=[]
        def work():
            try:r.guard(1,1)
            except registry.RegistryError:errors.append(True)
        t=threading.Thread(target=work);t.start();t.join();self.assertEqual(errors,[True])
        with self.assertRaises(registry.RegistryError):r.native_binding()
        p=provider();r=registry.CameraRegistry(p,NONCE)
        def nested():
            try:r.guard(1,1)
            except registry.RegistryError:pass
        p.env.engine.sensors['bigbench_road'].buffer.hook=nested
        with self.assertRaises(registry.RegistryError):r.guard(1,1)
        self.assertEqual(r.descriptor()['guards_returned'],0)
    def test_closed_provider_and_registry_cannot_supply_handles(self):
        p=provider();r=registry.CameraRegistry(p,NONCE);r.close()
        with self.assertRaises(registry.RegistryError):r.native_binding()
        r=registry.CameraRegistry(p,NONCE);p.env=None
        with self.assertRaises(registry.RegistryError):r.guard(1,1)
    def test_invalid_handle_and_foreign_getter_fail_before_native_reads(self):
        for value in (0,-1,True,2**64,'0xabc'):
            p=provider();p.env.engine.sensors['bigbench_road'].copy_texture.this=value
            with self.assertRaises(registry.RegistryError):registry.CameraRegistry(p,NONCE)
        p=provider();b=p.env.engine.sensors['bigbench_road'].buffer;b.getGsg=lambda:NS(this=7)
        with self.assertRaises(registry.RegistryError):registry.CameraRegistry(p,NONCE)
    def test_full_twelve_window_budget_has_only26_named_getters(self):
        r=registry.CameraRegistry(provider(),NONCE)
        for i in range(1,13):r.guard(i,1 if i%2 else 2)
        self.assertEqual(r.descriptor()['getter_attempts'],26)
    def test_handle_descriptor_cannot_reenter_private_binding(self):
        class Handle:
            hook=None
            @property
            def this(self):
                if self.hook:self.hook()
                return 0x111122223333
        p=provider();h=Handle();p.env.engine.sensors['bigbench_road'].copy_texture=h
        r=registry.CameraRegistry(p,NONCE)
        def nested():
            h.hook=None
            try:r.guard(1,1)
            except registry.RegistryError:pass
        h.hook=nested
        with self.assertRaises(registry.RegistryError):r.native_binding()
        self.assertEqual(r.descriptor()['guards_returned'],0)

if __name__=='__main__':unittest.main()
