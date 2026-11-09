"""Deterministic, vehicle-independent 2-D geometry for a synthetic road."""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from math import cos, sin, hypot, isfinite


@dataclass(frozen=True)
class CurveSection:
    length_m: float
    curvature_start: float
    curvature_end: float

    def __post_init__(self):
        if not (isfinite(self.length_m) and self.length_m > 0):
            raise ValueError('section length must be finite and positive')
        if not all(isfinite(x) for x in (self.curvature_start, self.curvature_end)):
            raise ValueError('curvature must be finite')


@dataclass(frozen=True)
class RoadPoint:
    s: float
    x: float
    y: float
    heading: float
    curvature: float


class Centerline:
    """Sample a curvature-by-station profile. No real-vehicle parameter enters."""

    def __init__(self, sections: tuple[CurveSection, ...], ds: float = 0.5):
        if not sections or ds <= 0 or not isfinite(ds):
            raise ValueError('sections required and ds must be positive')
        points = [RoadPoint(0.0, 0.0, 0.0, 0.0, sections[0].curvature_start)]
        x = y = heading = station = 0.0
        for section in sections:
            steps = max(1, round(section.length_m / ds))
            delta = section.length_m / steps
            for i in range(steps):
                t0 = i / steps
                t1 = (i + 1) / steps
                curvature = section.curvature_start + (section.curvature_end - section.curvature_start) * (t0 + t1) / 2
                new_heading = heading + curvature * delta
                middle_heading = 0.5 * (heading + new_heading)
                x += cos(middle_heading) * delta
                y += sin(middle_heading) * delta
                heading = new_heading
                station += delta
                target_curvature = section.curvature_start + (section.curvature_end - section.curvature_start) * t1
                points.append(RoadPoint(station, x, y, heading, target_curvature))
        self.points = tuple(points)
        self.stations = tuple(p.s for p in points)
        self.length_m = station
        self.ds = ds

    def at(self, station: float) -> RoadPoint:
        s = max(0.0, min(float(station), self.length_m))
        i = max(0, min(len(self.points) - 2, bisect_right(self.stations, s) - 1))
        a, b = self.points[i:i + 2]
        t = (s - a.s) / (b.s - a.s)
        return RoadPoint(s,
                         a.x + t * (b.x - a.x),
                         a.y + t * (b.y - a.y),
                         a.heading + t * (b.heading - a.heading),
                         a.curvature + t * (b.curvature - a.curvature))

    def project(self, x: float, y: float, station_hint: float | None = None) -> tuple[float, float, float]:
        """Return (station, signed lateral error, local road curvature)."""
        if not all(isfinite(v) for v in (x, y)):
            raise ValueError('pose must be finite')
        # Local search avoids snapping across different loops of an S-shaped road.
        if station_hint is None:
            first, last = 0, len(self.points) - 1
        else:
            lo = max(0.0, station_hint - 35.0)
            hi = min(self.length_m, station_hint + 90.0)
            first = max(0, bisect_right(self.stations, lo) - 1)
            last = min(len(self.points) - 1, bisect_right(self.stations, hi))
        best = (float('inf'), 0.0, 0.0, 0.0)
        for i in range(first, last):
            a, b = self.points[i], self.points[i + 1]
            vx, vy = b.x - a.x, b.y - a.y
            dx, dy = x - a.x, y - a.y
            norm = vx * vx + vy * vy
            t = min(1.0, max(0.0, (dx * vx + dy * vy) / norm))
            ex, ey = a.x + t * vx, a.y + t * vy
            squared = (x - ex)**2 + (y - ey)**2
            if squared < best[0]:
                lat = (-vy * (x - ex) + vx * (y - ey)) / hypot(vx, vy)
                best = (squared, a.s + t * (b.s - a.s), lat,
                        a.curvature + t * (b.curvature - a.curvature))
        if best[0] == float('inf'):
            raise RuntimeError('empty centerline projection range')
        return best[1], best[2], best[3]
