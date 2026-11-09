"""Synthetic route graph tests, never a real driving score."""
from __future__ import annotations
from types import SimpleNamespace
import unittest

from bigbench.native_route import (
    RouteContractError,NativeRouteProgress,forward_contiguous_chain
)


class Straight:
    def __init__(self,start,end,idx):
        self.start=float(start);self.length=float(end-start);self.index=idx
    def position(self,s,r):
        return (self.start+s,-r)
    def heading_theta_at(self,s):
        return 0.
    def width_at(self,s):
        return 3.5
    def local_coordinates(self,p):
        return (p[0]-self.start,-p[1])


class NativeRouteTests(unittest.TestCase):
    def test_unique_contiguous_route_transitions_at_link_end(self):
        a=Straight(0,10,('A','B',0))
        b=Straight(10,20,('B','C',0))
        c=Straight(20,30,('C','D',0))
        net=SimpleNamespace(graph={'A':{'B':[a]},'B':{'C':[b]},'C':{'D':[c]}})
        route=forward_contiguous_chain(net,a,str(c.index))
        self.assertEqual(len(route),3)
        traveler=NativeRouteProgress(route)
        traveler.evaluate(9.8,0.,0.)
        self.assertEqual(traveler.active_index,0)
        traveler.evaluate(10.1,0.,0.)
        self.assertEqual(traveler.active_index,1)
        traveler.evaluate(20.1,0.,0.)
        self.assertEqual(traveler.active_index,2)
        with self.assertRaises(RouteContractError):
            traveler.evaluate(32.,0.,0.)

    def test_branching_requires_predeclared_route(self):
        a=Straight(0,10,('A','B',0))
        b=Straight(10,20,('B','C',0))
        c=Straight(10,20,('B','D',1))
        net=SimpleNamespace(graph={'A':{'B':[a]},'B':{'C':[b],'D':[c]}})
        with self.assertRaisesRegex(RouteContractError,'explicit route required'):
            forward_contiguous_chain(net,a,str(b.index))

    def test_discontinuous_route_fails(self):
        a=Straight(0,10,('A','B',0))
        b=Straight(25,35,('B','C',0))
        net=SimpleNamespace(graph={'A':{'B':[a]},'B':{'C':[b]}})
        with self.assertRaises(RouteContractError):
            forward_contiguous_chain(net,a,str(b.index))

if __name__=='__main__':unittest.main()
