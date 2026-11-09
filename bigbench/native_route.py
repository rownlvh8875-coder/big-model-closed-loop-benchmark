"""Explicit native MetaDrive lane chain for eventual FULL S-curve traversal.

No nearest-lane fallback. At branches/ramps the route must be supplied
explicitly: a graph adjacency alone never authorizes choosing an arbitrary
turn or merging lane.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .lane_truth import LaneTruthError,evaluate_target_lane_by_id


class RouteContractError(ValueError):
    pass


def _point(lane,at_end):
    p=lane.position(float(lane.length) if at_end else 0.,0.)
    return float(p[0]),float(p[1])


def _heading(lane,at_end):
    return float(lane.heading_theta_at(float(lane.length) if at_end else 0.))


def _angle_difference(a,b):
    return math.atan2(math.sin(a-b),math.cos(a-b))


def _distance(a,b):
    return math.hypot(a[0]-b[0],a[1]-b[1])


def forward_contiguous_chain(road_network:Any,first_lane:Any,last_lane_id:str, *,
                             max_hops:int=16,join_tolerance_m:float=.35,
                             heading_tolerance_rad:float=.35)->tuple:
    """Follow only physically continuous unambiguous native road links.

    Does not drive the car; does not infer route choices from camera images.
    """
    graph=getattr(road_network,'graph',None)
    if not isinstance(graph,dict):
        raise RouteContractError('native road network graph required')
    if not last_lane_id or not 1<=max_hops<=50:
        raise RouteContractError('target lane ID and bounded hops required')
    current=first_lane
    route=[current]
    seen={str(getattr(current,'index',None))}
    if next(iter(seen))==last_lane_id:
        return tuple(route)
    for _ in range(max_hops):
        idx=getattr(current,'index',None)
        if not isinstance(idx,(list,tuple)) or len(idx)<2:
            raise RouteContractError('native road lane graph index missing')
        end_node=idx[1]
        end=_point(current,True)
        theta=_heading(current,True)
        eligible=[]
        for lanes in graph.get(end_node,{}).values():
            for lane in lanes:
                if not hasattr(lane,'position') or not hasattr(lane,'heading_theta_at'):
                    continue
                name=str(getattr(lane,'index',None))
                if name in seen:
                    continue
                if _distance(end,_point(lane,False))>join_tolerance_m:
                    continue
                if abs(_angle_difference(theta,_heading(lane,False)))>heading_tolerance_rad:
                    continue
                eligible.append(lane)
        if len(eligible)!=1:
            raise RouteContractError(f'explicit route required: {len(eligible)} native successors')
        current=eligible[0]
        route.append(current)
        seen.add(str(current.index))
        if str(current.index)==last_lane_id:
            return tuple(route)
    raise RouteContractError('end target not reached in native route hop limit')


@dataclass
class NativeRouteProgress:
    lanes: tuple
    active_index: int = 0

    def __post_init__(self):
        if not self.lanes:
            raise RouteContractError('explicit lane sequence is empty')
        ids=[str(getattr(l,'index',None)) for l in self.lanes]
        if len(ids)!=len(set(ids)):
            raise RouteContractError('repeated lane identities in route')

    def evaluate(self,x:float,y:float,heading:float,*,half_width_m:float=.9):
        """Advance ONLY to prescribed next segment when ego longitudinal s crossed."""
        lane=self.lanes[self.active_index]
        s,_=lane.local_coordinates((x,y))
        if not math.isfinite(s):
            raise RouteContractError('nonfinite native segment progress')
        while s>=float(lane.length) and self.active_index+1<len(self.lanes):
            self.active_index+=1
            lane=self.lanes[self.active_index]
            s,_=lane.local_coordinates((x,y))
            if not math.isfinite(s):
                raise RouteContractError('nonfinite successor segment progress')
        if s<0 or s>float(lane.length):
            raise RouteContractError('ego outside explicitly selected route; no nearest fallback')
        return evaluate_target_lane_by_id([lane],str(lane.index),x,y,heading,
                                          half_width_m=half_width_m)
