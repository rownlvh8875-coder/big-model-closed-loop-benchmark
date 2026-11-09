"""Confirm an explicit connected native route from S-curve bend 1 to bend 2."""
from __future__ import annotations
import argparse,json
from pathlib import Path

from bigbench.curved_lane_scenarios import SCENARIOS,select_native_curve_lanes
from bigbench.metadrive_camera import NativeMetaDriveProvider
from bigbench.native_route import forward_contiguous_chain


def main(argv=None):
    ap=argparse.ArgumentParser(description='Route connectivity only, no model scoring')
    ap.add_argument('--scenario',choices=['s_curve_left_right','s_curve_right_left'],
                    default='s_curve_left_right')
    ap.add_argument('--seed',type=int,default=20261109)
    ap.add_argument('--out',type=Path,default=Path('output/native-s-route.json'))
    a=ap.parse_args(argv)
    case=SCENARIOS[a.scenario]
    provider=NativeMetaDriveProvider(seed=a.seed,map_config=case.map_config())
    try:
        bends=select_native_curve_lanes(provider.env.current_map,case)
        if len(bends)!=2:
            raise RuntimeError('need two native forward bends')
        route=forward_contiguous_chain(provider.env.current_map.road_network,
                                       bends[0],str(bends[1].index))
        ids=[str(l.index) for l in route]
        if len(route)<2 or ids[-1]!=str(bends[1].index):
            raise RuntimeError('S-curve route did not reach the second bend')
        data={'status':'PASS_EXPLICIT_NATIVE_S_ROUTE_GEOMETRY_ONLY',
              'scenario':a.scenario,'native_lane_ids':ids,
              'total_route_length_m':sum(float(l.length) for l in route),
              'model_scoring_allowed':False,'real_vehicle_testing':False}
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print('EXPLICIT_NATIVE_S_ROUTE_PASS',a.scenario,len(ids),flush=True)
    finally:
        provider.close()
    return 0


if __name__=='__main__':
    raise SystemExit(main())
