"""Render MetaDrive map lane geometry and compare it to actual painted RGB pixels.

Never imports or evaluates a driving model. No real vehicle. No lane-following
score can be produced until this independent image/ground-truth check passes.

Usage: xvfb-run -a python -m scripts.metadrive_lane_audit --out output/lane-audit
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from bigbench.kinematics import AgentState
from bigbench.lane_reprojection import (
    draw_lane_alignment, evaluate_visible_lane_paint, map_boundary_landmarks,
    project_panda_camera_points,
)
from bigbench.metadrive_camera import MetaDriveOpticalRig, NativeMetaDriveProvider
from bigbench.optical_calibration import intrinsics_from_panda_lens, reference_model


def _project_while_borrowed(provider, state: AgentState, points, kind: str):
    """Recreate EXACTLY the MetaDrive BaseCamera.perceive borrowed transform.

    After actual RGB capture, BaseCamera.perceive restores its camera parent.
    We reapply the same camera pose to map world points through the Panda3D
    scene graph. We do not fit projected points to observed RGB markings.
    """
    env = provider.env
    if env is None:
        raise RuntimeError('provider closed')
    sensor=env.engine.sensors['bigbench_road' if kind=='road' else 'bigbench_wide']
    node=sensor.get_cam()
    original_parent=node.getParent()
    original_pos=node.getPos()
    original_hpr=node.getHpr()
    try:
        node.reparentTo(env.vehicle.origin)
        node.setPos(-float(state.y),float(state.x),provider.height_m)
        node.setHpr(math.degrees(float(state.heading)),0.0,0.0)
        width,height=provider.source_width,provider.source_height
        src=intrinsics_from_panda_lens(sensor.get_lens(),width,height)
        return project_panda_camera_points(node,env.engine.origin,points,width,height,src,reference_model(kind))
    finally:
        node.reparentTo(original_parent)
        node.setPos(original_pos)
        node.setHpr(original_hpr)


def audit_native_lanes(*, output: Path, seed: int = 20261109,
                       max_median_error_px: float = 7.0,
                       min_match_fraction: float = .45,
                       strict: bool = True) -> dict:
    """Pinhole pixel alignment diagnostic with actual rendered road paint.

    On insufficient paint, status is INCONCLUSIVE; never a silent PASS.
    """
    provider=NativeMetaDriveProvider(seed=seed)
    rig=MetaDriveOpticalRig(provider)
    output.mkdir(parents=True,exist_ok=True)
    try:
        vehicle=provider.env.vehicle
        lanes=tuple(vehicle.navigation.current_ref_lanes)
        origin_xy=(float(vehicle.position[0]),float(vehicle.position[1]))
        map_graph=provider.env.current_map.road_network
        landmarks=map_boundary_landmarks(map_graph,origin_xy)
        print('MAP_LANE_WORLD_MARKINGS',len(landmarks),'current_ref_lanes',len(lanes),flush=True)
        poses=(('baseline',AgentState(0.0,0.0,0.0,0.0,0.0)),
               ('shifted',AgentState(0.05,1.0,0.25,0.012,0.0)))
        records={}
        all_ok=True
        for label,pose in poses:
            raw_road,raw_wide,_,_=provider.capture(pose)
            lens={name:provider.env.engine.sensors['bigbench_'+name].get_lens() for name in ('road','wide')}
            from bigbench.optical_calibration import intrinsics_from_panda_lens
            raw_k={name:intrinsics_from_panda_lens(lens[name],provider.source_width,provider.source_height)
                   for name in ('road','wide')}
            paired,audit=rig.rectifier.rectify_pair(raw_road,raw_wide,
                        road_intrinsics=raw_k['road'],wide_intrinsics=raw_k['wide'])
            posesummary={}
            for kind in ('road','wide'):
                frame=getattr(paired,kind)
                predicted=_project_while_borrowed(provider,pose,landmarks,kind)
                measured=evaluate_visible_lane_paint(frame,predicted)
                # Wrongly offset projected points must NOT score equivalently.
                control=[]
                for p in predicted:
                    q=dict(p)
                    q['model_uv']=[p['model_uv'][0]+27.0,p['model_uv'][1]]
                    control.append(q)
                shifted_control=evaluate_visible_lane_paint(frame,control)
                errors=(measured['median_pixel_error_px'],measured['p90_pixel_error_px'])
                # This is a thresholded optical diagnostic, not model-quality scoring.
                passed=(len(predicted)>=8 and measured['matched_count']>=5 and
                        measured['matched_fraction']>=min_match_fraction and
                        errors[0] is not None and errors[0]<=max_median_error_px and
                        shifted_control['matched_fraction'] < measured['matched_fraction'])
                posesummary[kind]={
                    'status':'PASS_PAINTER_GEOMETRY_DIAGNOSTIC' if passed else 'INCONCLUSIVE_OR_MISMATCH',
                    'world_projected_points':len(predicted),
                    'paint_measurement':{k:v for k,v in measured.items() if k!='points'},
                    'shifted_27px_negative_control':{k:v for k,v in shifted_control.items() if k!='points'},
                    'camera_source_intrinsics':raw_k[kind].__dict__,
                    'warp_audit':audit[kind].to_dict(),
                    'visible_samples':measured['points'],
                }
                all_ok=all_ok and passed
                frame.save_png(output/f'{kind}_{label}.png')
                draw_lane_alignment(frame,measured).save_png(output/f'{kind}_{label}_reprojection.png')
            records[label]=posesummary
        if not all_ok:
            status='INCONCLUSIVE_OR_MISMATCH'
        else:
            status='PASS_VIRTUAL_METADRIVE_LANE_PIXEL_ALIGNMENT_DIAGNOSTIC'
        report={
            'status':status,
            'scope':'NATIVE_METADRIVE_3D_LANE_POINTS_VS_RENDERED_RGB_PAINT',
            'optics':'IDEAL_VIRTUAL_PINHOLE_ONLY_NOT_REAL_COMMA',
            'model_score_allowed':False,
            'actual_vehicle_test':False,
            'carrot_params_or_cd210_used':False,
            'seed':seed,
            'map_lane_count':len(lanes),
            'map_origin_xy':origin_xy,
            'candidate_world_markings':len(landmarks),
            'camera_pose_note':'MetaDrive camera is borrowed relative to env.vehicle.origin; Panda3D global xy is MetaDrive global xy',
            'notes':'Color thresholding of rendered paint is a diagnostic, subject to terrain/lighting false positives. Not physical-lens calibration or autonomous driving validation.',
            'poses':records,
        }
        (output/'lane_reprojection_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
        print(json.dumps({**{k:v for k,v in report.items() if k!='poses'},
                          'summaries':{pose:{kind:{'status':v['status'],
                              'projected':v['world_projected_points'],
                              'matched':v['paint_measurement']['matched_count'],
                              'fraction':v['paint_measurement']['matched_fraction'],
                              'median_error':v['paint_measurement']['median_pixel_error_px'],
                              'negative_fraction':v['shifted_27px_negative_control']['matched_fraction']}
                              for kind,v in rows.items()} for pose,rows in records.items()}},indent=2))
        if strict and not all_ok:
            raise RuntimeError('MetaDrive lane-pixel reprojection NOT verified: see lane_reprojection_report.json')
        return report
    finally:
        rig.close()


def main(argv=None):
    ap=argparse.ArgumentParser(description='Real MetaDrive 3D lane boundary/pixel optical diagnostic only')
    ap.add_argument('--out',type=Path,default=Path('output/metadrive-lanes'))
    ap.add_argument('--seed',type=int,default=20261109)
    ap.add_argument('--allow-inconclusive',action='store_true')
    args=ap.parse_args(argv)
    audit_native_lanes(output=args.out,seed=args.seed,strict=not args.allow_inconclusive)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
