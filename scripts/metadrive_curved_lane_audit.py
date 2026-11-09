"""Audit native MetaDrive S-bend and in/out-ramp 3D paint vs RGB pixels.

This is a camera/road geometry diagnostic, NOT an ONNX driving benchmark.
No real vehicles, vehicle-specific dynamic models or CD210 are involved.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from bigbench.camera import RGBFrame
from bigbench.curved_lane_scenarios import (
    SCENARIOS, CurveCase, ScenarioGeometryError,
    select_native_curve_lanes, world_camera_pose,
)
from bigbench.lane_reprojection import (
    draw_lane_alignment, evaluate_visible_lane_paint,
    lane_boundary_landmarks, map_boundary_landmarks,
    project_panda_camera_points,
)
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.optical_calibration import intrinsics_from_panda_lens, reference_model


def _camera_capture_and_projection(provider, pose_world, landmarks, kind):
    """Use identical *WORLD* Panda3D pose for image acquisition and projection.

    Unlike existing baseline road test, no vehicle-local angle is guessed.
    The camera is borrowed into the engine origin, so MetaDrive vehicle
    dynamics are never stepped or used to synthesize ego control authority.
    """
    env = provider.env
    if env is None:
        raise RuntimeError('MetaDrive environment was closed')
    node = env.engine.sensors['bigbench_' + kind].get_cam()
    sensor = env.engine.sensors['bigbench_' + kind]
    x, y, z, heading = pose_world
    position = (x, y, z)
    hpr = (heading, 0, 0)
    raw = sensor.perceive(to_float=False,
                          new_parent_node=env.engine.origin,
                          position=position, hpr=hpr)
    if not isinstance(raw, np.ndarray):
        raw = raw.get()
    original_parent = node.getParent()
    original_pos = node.getPos()
    original_hpr = node.getHpr()
    try:
        node.reparentTo(env.engine.origin)
        node.setPos(*position)
        node.setHpr(*hpr)
        src = intrinsics_from_panda_lens(sensor.get_lens(),provider.source_width, provider.source_height)
        pred = project_panda_camera_points(node, env.engine.origin, landmarks,
                                            provider.source_width,provider.source_height,
                                            src,reference_model(kind))
    finally:
        node.reparentTo(original_parent)
        node.setPos(original_pos)
        node.setHpr(original_hpr)
    return np.asarray(raw), pred, src


def _focus_marks(lane, origin_xy, radius_m=90.0):
    """Use actual native painted sides, not a synthetic centerline overlay."""
    length = float(lane.length)
    step = 0.65
    stations = np.arange(0.5, max(0.5, length - 0.3), step)
    base, _ = lane.local_coordinates(origin_xy)
    distances = tuple(float(s - base) for s in stations)
    return [p for p in lane_boundary_landmarks((lane,),origin_xy,
            distances_m=distances) if math.hypot(p.world_x_m-origin_xy[0],p.world_y_m-origin_xy[1]) <= radius_m]


def _compare(frame, projected, focus_ids, *, search_radius_px=12):
    observed = evaluate_visible_lane_paint(frame,projected,search_radius_px=search_radius_px)
    shifted = []
    for point in projected:
        q = dict(point)
        q['model_uv'] = [q['model_uv'][0] + 27.0, q['model_uv'][1]]
        shifted.append(q)
    shifted_control = evaluate_visible_lane_paint(frame,shifted,search_radius_px=search_radius_px)
    focal_projection = [p for p in projected if p['road_id'] in focus_ids]
    observed_focus = evaluate_visible_lane_paint(frame,focal_projection,search_radius_px=search_radius_px)
    control_focus = [p for p in shifted if p['road_id'] in focus_ids]
    observed_focus_shift = evaluate_visible_lane_paint(frame,control_focus,search_radius_px=search_radius_px)
    a = observed
    b = observed_focus
    # Do not score a matched few pixels as a statistically valid complete frame.
    world_ok = (a['total_visible_candidates'] >= 8 and a['matched_count'] >= 5 and
                a['matched_fraction'] >= 0.45 and a['median_pixel_error_px'] is not None and
                a['median_pixel_error_px'] <= 7.0 and
                shifted_control['matched_fraction'] < a['matched_fraction'])
    # Require positive evidence on this specific curved/ramp road, not merely
    # unrelated straight lane paint somewhere else in the same camera view.
    focus_ok = (b['total_visible_candidates'] >= 5 and b['matched_count'] >= 3 and
                b['matched_fraction'] >= 0.35 and b['median_pixel_error_px'] is not None and
                b['median_pixel_error_px'] <= 7.0 and
                observed_focus_shift['matched_fraction'] < b['matched_fraction'])
    summary = {
        'status':'PASS_CURVED_LANE_PAINT_ALIGNMENT' if world_ok and focus_ok else 'INCONCLUSIVE_OR_MISMATCH',
        'global_diagnostic':{k:v for k,v in observed.items() if k!='points'},
        'global_negative_27px':{k:v for k,v in shifted_control.items() if k!='points'},
        'focus_diagnostic':{k:v for k,v in observed_focus.items() if k!='points'},
        'focus_negative_27px':{k:v for k,v in observed_focus_shift.items() if k!='points'},
        'native_world_geometry_tested':bool(focal_projection),
        'global_candidate_points':len(projected),
        'curved_or_ramp_candidate_points':len(focal_projection),
        'raw_observations':observed['points'],
    }
    return summary,observed


def audit_one(*, case: CurveCase, seed: int, output: Path) -> dict:
    provider = NativeMetaDriveProvider(seed=seed,map_config=case.map_config())
    output.mkdir(parents=True,exist_ok=True)
    result = {'scenario':case.name,'seed':seed, 'status':'INCONCLUSIVE_OR_MISMATCH',
              'map_config_requested':case.map_config(),
              'real_vehicle_testing':False, 'specific_vehicle_dynamics':False,
              'cd210_used':False, 'carrot_mpc_used':False,
              'driving_model_scoring_allowed':False,
              'optics':'VIRTUAL_ZERO_DISTORTION_PINHOLE_ONLY_NOT_REAL_COMMA',
              'poses':{}, 'errors':[]}
    try:
        roadmap = provider.env.current_map
        curved_lanes = select_native_curve_lanes(roadmap,case)
        result['native_curves']=[{'lane_index':str(getattr(l,'index','unknown')),
                                   'radius_m':float(l.radius),'length_m':float(l.length),
                                   'direction':float(getattr(l,'direction',0))} for l in curved_lanes]
        if case.expected_curve_directions and len(curved_lanes) != 2:
            raise ScenarioGeometryError('S-curve requires two distinct native forward bends')
        samples = [(f'bend_{i+1}',lane,0.13 if i%2==0 else 0.40)
                   for i,lane in enumerate(curved_lanes[:2])]
        if len(samples) < 2:
            # Ramps may expose one circular connector; inspect TWO poses on that
            # native connector instead of inventing a second geometry segment.
            samples.append(('bend_1_later',curved_lanes[0],0.50))
        all_pass=True
        for label,lane,fraction in samples:
            world_pose = world_camera_pose(lane,fraction,height_m=provider.height_m)
            point_xy = (world_pose[0],world_pose[1])
            marks = map_boundary_landmarks(roadmap.road_network,point_xy,
                                           max_radius_m=85.0,sample_step_m=1.0)
            focus = _focus_marks(lane,point_xy)
            # Sub-meter native-boundary samples are included in the image audit;
            # identifiers are used to prevent cross-road paint masquerading as
            # verified curve paint.
            allmarks = marks + focus
            focus_ids = {p.road_id for p in focus}
            pose_report = {'world_pose_xyzh':list(world_pose),
                           'native_lane_index':str(getattr(lane,'index','unknown')),
                           'native_focus_markings':len(focus), 'images':{}}
            for kind in ('road','wide'):
                raw, predicted, src = _camera_capture_and_projection(provider,world_pose,allmarks,kind)
                dest = reference_model(kind)
                from bigbench.optical_calibration import PinholeRectifier
                rect = PinholeRectifier(source_width=provider.source_width,
                                         source_height=provider.source_height)
                frame, warp = rect._rectify(kind,raw,src)
                audit,obs = _compare(frame,predicted,focus_ids)
                frame.save_png(output/f'{label}_{kind}.png')
                draw_lane_alignment(frame,obs).save_png(output/f'{label}_{kind}_reprojection.png')
                audit['source_intrinsics']=src.__dict__
                audit['warp_valid_fraction']=warp.fraction_valid_source_pixels
                pose_report['images'][kind]=audit
                all_pass=all_pass and audit['status']=='PASS_CURVED_LANE_PAINT_ALIGNMENT'
            result['poses'][label]=pose_report
        result['status']=('PASS_NATIVE_CURVE_RAMP_PIXEL_ALIGNMENT_DIAGNOSTIC'
                          if all_pass else 'INCONCLUSIVE_OR_MISMATCH')
    except (ScenarioGeometryError,ValueError,RuntimeError) as exc:
        result['status']='INCONCLUSIVE_OR_MISMATCH'
        result['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        provider.close()
        (output/'curved_lane_report.json').write_text(
            json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Native MetaDrive S-curve/ramp world-to-RGB reprojection diagnostic (SIM ONLY)')
    ap.add_argument('--out',type=Path,default=Path('output/metadrive-curved-lanes'))
    ap.add_argument('--seed',type=int,default=20261109)
    ap.add_argument('--scenarios',nargs='+',choices=sorted(SCENARIOS),
                    default=list(SCENARIOS))
    ap.add_argument('--strict',action='store_true',help='exit nonzero unless every named case passes')
    args = ap.parse_args(argv)
    rows={}
    for name in args.scenarios:
        print('NATIVE_CURVED_SCENARIO_START',name,flush=True)
        try:
            row=audit_one(case=SCENARIOS[name],seed=args.seed,output=args.out/name)
        except Exception as exc:
            # Even unexpected native engine initialization errors must be
            # recorded as non-PASS evidence, then surfaced in strict mode.
            row={'scenario':name,'status':'INCONCLUSIVE_OR_MISMATCH',
                 'errors':[f'{type(exc).__name__}: {exc}'],
                 'real_vehicle_testing':False,'driving_model_scoring_allowed':False}
        rows[name]=row
        print('NATIVE_CURVED_SCENARIO_RESULT',name,row['status'],row.get('errors'),flush=True)
    summary={'scenario_statuses':{k:v['status'] for k,v in rows.items()},
             'all_pass':all(v['status']=='PASS_NATIVE_CURVE_RAMP_PIXEL_ALIGNMENT_DIAGNOSTIC' for v in rows.values()),
             'real_vehicle_testing':False,'model_scoring_allowed':False}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'curved_lane_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    return int(args.strict and not summary['all_pass'])


if __name__=='__main__':
    raise SystemExit(main())
