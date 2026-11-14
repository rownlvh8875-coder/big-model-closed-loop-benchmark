"""Structural synthetic engines and source-data parsing, never native evidence."""
from copy import deepcopy
import importlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

try:
    binding=importlib.import_module('scripts.renderer_task_binding')
except ModuleNotFoundError as exc:
    if exc.name!='scripts.renderer_task_binding':raise
    binding=None


class Matrix:
    def assign(self,raw):self.values=deepcopy(raw)
    def getCell(self,i,j):return self.values[i][j]


class PSSM:
    def update(self,task):return task.cont


class Chase:
    def _chase_task(self,vehicle,task):return task.cont


class Node:
    def __init__(self):self.position=[1.,2.,3.];self.hpr=[4.,5.,6.]
    def getPos(self,parent):return self.position
    def getHpr(self,parent):return self.hpr


class Rig:
    def __init__(self):self.rows=[[[float(i==j) for j in range(4)] for i in range(4)] for _ in range(2)]
    def get_mvp_array(self):return self.rows


class RendererTaskBindingTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(binding,'structural binding/source audit required')
    def fixture(self):
        e=SimpleNamespace(camera=Node(),render=object(),pssm=PSSM(),main_camera=Chase())
        e.pssm.engine=e;e.pssm.num_splits=2;e.pssm.camera_rig=Rig()
        e.main_camera.engine=e;e.main_camera.camera=e.camera;e.main_camera.run_task=True
        return e
    def bind(self,e,**kw):
        return binding.bind_engine(e,pssm_class=PSSM,chase_class=Chase,matrix_class=Matrix,task_continue=1,**kw)

    def test_actual_self_code_binding_and_exact_named_getter_budget(self):
        e=self.fixture();b=self.bind(e);s=b['snapshot']()
        self.assertIs(b['targets']['PSSM.update'].__self__,e.pssm)
        self.assertIs(b['targets']['MainCamera._chase_task'].__self__,e.main_camera)
        self.assertEqual(s['pose'],dict(xyz_m=[1.,2.,3.],hpr_deg=[4.,5.,6.]))
        self.assertEqual(s['matrices'][0][0],[1.,0.,0.,0.])
        self.assertEqual(b['reader_counts']['named_getter_attempts'],35)
        self.assertEqual(b['reader_counts']['named_getter_returns'],35)
        self.assertEqual(b['reader_counts']['private_matrix_allocations'],2)
        self.assertEqual(b['reader_counts']['private_matrix_assignments'],2)
        self.assertEqual(b['reader_counts']['vector_component_reads'],6)
        self.assertFalse(b['native_admission_proven'])

    def test_private_matrix_and_pose_copies_do_not_alias_native_values(self):
        e=self.fixture();b=self.bind(e);s=b['snapshot']();e.camera.position[0]=99.;e.pssm.camera_rig.rows[0][0][0]=42.
        self.assertEqual(s['pose']['xyz_m'][0],1.);self.assertEqual(s['matrices'][0][0][0],1.)

    def test_foreign_owner_wrong_class_and_shared_camera_fail_before_reads(self):
        for mutate in (lambda e:setattr(e.pssm,'engine',object()),
                       lambda e:setattr(e.main_camera,'engine',object()),
                       lambda e:setattr(e.main_camera,'camera',Node()),
                       lambda e:setattr(e.pssm,'num_splits',3),
                       lambda e:setattr(e,'pssm',SimpleNamespace())):
            e=self.fixture();mutate(e)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):self.bind(e)

    def test_changed_owner_after_binding_is_rejected_before_getters(self):
        e=self.fixture();b=self.bind(e);e.main_camera=Chase()
        with self.assertRaises(ValueError):b['snapshot']()
        self.assertEqual(b['reader_counts']['named_getter_attempts'],0)

    def test_snapshot_cap_is_enforced_before_the_next_named_getter(self):
        e=self.fixture();b=self.bind(e,max_snapshots=2)
        b['snapshot']();b['snapshot']()
        with self.assertRaises(ValueError):b['snapshot']()
        self.assertEqual(b['reader_counts']['named_getter_attempts'],70)

    def test_split_layout_and_nonfinite_values_cannot_produce_a_snapshot(self):
        for mutate in (lambda e:setattr(e.pssm.camera_rig,'rows',[]),
                       lambda e:e.camera.position.__setitem__(0,float('nan')),
                       lambda e:e.pssm.camera_rig.rows[0][0].__setitem__(0,float('inf')),
                       lambda e:setattr(e.main_camera,'run_task',1)):
            e=self.fixture();b=self.bind(e);mutate(e)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):b['snapshot']()
            self.assertEqual(b['reader_counts']['snapshots_returned'],0)

    def test_exact_ast_method_is_located_without_executing_source(self):
        source='raise RuntimeError("MUST NOT EXECUTE")\nclass PSSM:\n    def update(self, task):\n        self.rig.update()\n        return task.cont\n'
        row=binding.method_receipt(source.encode(),'PSSM','update')
        self.assertEqual((row['lineno'],row['end_lineno']),(3,5))
        self.assertEqual(row['syntactic_calls'],['self.rig.update'])
        self.assertFalse(row['code_executed'])

    def test_missing_duplicate_or_syntax_invalid_target_is_rejected(self):
        for source in ('class PSSM: pass','class PSSM:\n def update(self):pass\n def update(self):pass',
                       'class PSSM:\n def update(self):pass\nclass PSSM:\n def update(self):pass','!!!'):
            with self.subTest(source=source),self.assertRaises(ValueError):
                binding.method_receipt(source.encode(),'PSSM','update')

    def test_foreign_archive_and_symlink_inputs_fail_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);wheel=root/'foreign.whl';wheel.write_bytes(b'foreign');manifest=root/'manifest.json';manifest.write_text('{}')
            out=root/'audit.json'
            with self.assertRaises(ValueError):binding.audit_sources(wheel,manifest,out)
            self.assertFalse(out.exists());link=root/'link.whl';link.symlink_to(wheel)
            with self.assertRaises(ValueError):binding.audit_sources(link,manifest,out)
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
