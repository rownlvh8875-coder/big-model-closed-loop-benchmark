"""Opt-in model-body FRD to world-integrator body-FLU action boundary."""
from dataclasses import asdict
import math
from time import perf_counter

from .kinematics import ModelAction

SOURCE_ACTION_FRAME='MODEL_BODY_FRD'
APPLIED_ACTION_FRAME='INTEGRATOR_BODY_FLU_WORLD_CCW'
BODY_ROTATION=((1.,0.,0.),(0.,-1.,0.),(0.,0.,-1.))


def basis_receipt():
    return dict(source_action_frame=SOURCE_ACTION_FRAME,applied_action_frame=APPLIED_ACTION_FRAME,
                body_rotation=[list(row) for row in BODY_ROTATION],raw_outputs_rewritten=False)


class WorldFramePolicyAdapter:
    """Compose a policy; rotate only its returned action, leaving all evidence owned by it."""
    world_frame_adapter_applied=True
    applied_action_frame=APPLIED_ACTION_FRAME

    def __init__(self,inner,*,source_action_frame):
        if (source_action_frame!=SOURCE_ACTION_FRAME or getattr(inner,'world_frame_adapter_applied',False)
                or getattr(inner,'applied_action_frame',SOURCE_ACTION_FRAME)!=SOURCE_ACTION_FRAME):
            raise ValueError('explicit model-body FRD action required; repeated/world conversion prohibited')
        self.inner=inner
        self.bridge_receipts=[]
        self.adapter_reset_calls=0

    def __getattr__(self,name):
        return getattr(object.__getattribute__(self,'inner'),name)

    def reset(self):
        result=self.inner.reset()
        self.adapter_reset_calls+=1
        self.bridge_receipts.clear()
        return result

    def step(self,observation):
        parent=self.inner.step(observation)
        started=perf_counter()
        if (not isinstance(parent,ModelAction) or any(type(x) not in (int,float) or not math.isfinite(x)
                for x in (parent.curvature_1pm,parent.acceleration_mps2))):
            raise ValueError('finite parent ModelAction required at explicit body-frame boundary')
        applied=ModelAction(-parent.curvature_1pm,parent.acceleration_mps2)
        self.bridge_receipts.append(dict(step=len(self.bridge_receipts)+1,**basis_receipt(),
            parent_model_action=asdict(parent),applied_world_action=asdict(applied),bridge_audit_wall_s=perf_counter()-started))
        return applied
