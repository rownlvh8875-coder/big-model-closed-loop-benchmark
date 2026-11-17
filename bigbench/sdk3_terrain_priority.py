"""Explicit RGB-only preference for terrain at equal quantized opaque depth."""
from pathlib import Path
import hashlib
REPAIR_ID='SDK3_RGB_TERRAIN_DEPTH_TIE_PRIORITY_V1'
BIN='background'
DRAW_ORDER=-1
OVERRIDE=1000

def need(value,message):
    if not value:raise ValueError(message)

def install_rgb_terrain_priority(engine,*,terrain_label,tag_key,core=None):
    if core is None:
        import panda3d.core as core
    need(isinstance(terrain_label,str) and terrain_label and isinstance(tag_key,str) and tag_key,'explicit existing RGB terrain tag')
    bin_slot=core.CullBinAttrib.getClassSlot();shader_slot=core.ShaderAttrib.getClassSlot();changes=[];cameras=[]
    for role in ('road','wide'):
        sensor=engine.sensors.get('bigbench_'+role);need(sensor is not None,'both original RGB sensors required');camera=sensor.cam.node();need(camera.getTagStateKey()==tag_key,'same original RGB tag-state key');original=camera.getTagState(terrain_label);need(original is not None and original.getAttrib(shader_slot) is not None and original.getAttrib(bin_slot) is None,'original terrain shader state without an existing bin')
        updated=original.addAttrib(core.CullBinAttrib.make(BIN,DRAW_ORDER),OVERRIDE);need(updated.removeAttrib(bin_slot)==original and updated.getOverride(bin_slot)==OVERRIDE and int(updated.getAttrib(shader_slot).this)==int(original.getAttrib(shader_slot).this),'only immutable terrain bin attribute changes')
        changes.append((camera,original,updated));cameras.append(dict(role=role,camera_pointer=int(camera.this),original_state_pointer=int(original.this),updated_state_pointer=int(updated.this),shader_attrib_pointer=int(original.getAttrib(shader_slot).this),shader_preserved=True,other_attributes_preserved=True))
    need(len({r['camera_pointer'] for r in cameras})==2,'distinct original RGB cameras');attempted=[]
    try:
        for camera,original,updated in changes:
            attempted.append((camera,original));camera.setTagState(terrain_label,updated)
    except BaseException:
        for camera,original in reversed(attempted):camera.setTagState(terrain_label,original)
        raise
    return dict(adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),adapter_path=str(Path(__file__).resolve()),protocol='sdk3-rgb-terrain-priority-v1',repair_id=REPAIR_ID,classification='MODIFIED_RGB_TERRAIN_PRIORITY_CANDIDATE',bin=BIN,draw_order=DRAW_ORDER,override=OVERRIDE,tag_key=tag_key,terrain_label=terrain_label,cameras=cameras,depth_function_changed=False,shader_replaced=False,extra_render_tasks=0,source_pixel_rewrite=False,historical_original_result_replaced=False,stage7_complete=False)
