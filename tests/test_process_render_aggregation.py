"""Unit checks for process-isolated MetaDrive diagnostic aggregation."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.aggregate_render_causality import (
    combine_independent_processes,SCENES,MODES
)


def fixture(key,scene,mode,*,stable=True):
    s={'bit_exact_after_warmup':stable,'max_changed_pixels_after_warmup':0 if stable else 3}
    return {
        'status':'OBSERVED','condition':key,'scene':scene,'mode':mode,
        'seed':20261109,'frames':8,
        'scene_before':{'clock_frame_count':8,'clock_frame_time_s':.15},
        'scene_after':{'clock_frame_count':16,'clock_frame_time_s':.35},
        'model_frame_stability':{'road':dict(s),'wide':dict(s)},
        'source_frame_stability':{'road':dict(s),'wide':dict(s)},
        'cpu_readback':{'road':{'readback_bit_exact':True},
                        'wide':{'readback_bit_exact':True}},
        'onnx_packed_tensor_stability':{
            'after_warmup_bit_exact':stable,
            'max_changed_tensor_elements_after_warmup':0 if stable else 2},
        'pose_shift_positive_control':{'road':True,'wide':True},
        'real_vehicle_testing':False,'model_scoring_allowed':False,
    }


def write_fixture(root,scene,mode,**args):
    key=f'{scene}_{mode}'
    path=root/key
    path.mkdir(parents=True,exist_ok=True)
    (path/(key+'.json')).write_text(
        json.dumps(fixture(key,scene,mode,**args)),encoding='utf-8')


class ProcessAggregationTests(unittest.TestCase):
    def test_all_conditions_in_distinct_directories(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            for scene in SCENES:
                for mode in MODES:
                    write_fixture(root,scene,mode,stable=mode=='graphics_frame_pair')
            receipt=combine_independent_processes(root)
            self.assertTrue(receipt['all_conditions_valid'])
            self.assertEqual(receipt['independent_python_processes_expected'],6)
            self.assertEqual(len(receipt['per_condition']),6)
            self.assertFalse(receipt['model_scoring_allowed'])
            self.assertEqual(receipt['interpretation']['task_vs_graphics'],
                             'GRAPHICS_ONLY_STABLER_THAN_TASK_STEP_IN_THIS_SCENE')

    def test_missing_process_not_silently_accepted(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            write_fixture(root,'ego_hidden','task_step_pair')
            receipt=combine_independent_processes(root)
            self.assertFalse(receipt['all_conditions_valid'])
            self.assertEqual(receipt['status'],'INCONCLUSIVE_MISSING_OR_INVALID_PROCESS_EVIDENCE')
            self.assertTrue(receipt['invalid_conditions'])

    def test_wrong_condition_identity_rejected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            write_fixture(root,'ego_hidden','task_step_pair')
            name='ego_hidden_task_step_pair'
            file=root/name/(name+'.json')
            z=json.loads(file.read_text())
            z['condition']='different'
            file.write_text(json.dumps(z))
            receipt=combine_independent_processes(
                root,scenes=('ego_hidden',),modes=('task_step_pair',))
            self.assertFalse(receipt['all_conditions_valid'])
            self.assertIn('identity mismatch',str(receipt['invalid_conditions']))


if __name__=='__main__':
    unittest.main()
