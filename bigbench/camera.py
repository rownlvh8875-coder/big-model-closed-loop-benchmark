"""Deterministic schematic RGB scene renderer for loop plumbing tests.

Not photorealistic; NOT validated for real openpilot ONNX image inputs.
"""
from __future__ import annotations
import hashlib
import struct
import zlib
from dataclasses import dataclass
from math import cos, sin
from pathlib import Path
from .kinematics import AgentState
from .scenario import Scenario


@dataclass(frozen=True)
class RGBFrame:
    width: int
    height: int
    rgb: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.rgb).hexdigest()

    def rgb_at(self, x: int, y: int) -> tuple[int, int, int]:
        i = 3 * (y * self.width + x)
        return tuple(self.rgb[i:i + 3])

    def save_png(self, path: Path) -> None:
        def chunk(t: bytes, data: bytes) -> bytes:
            return struct.pack('!I', len(data)) + t + data + struct.pack('!I', zlib.crc32(t + data) & 0xffffffff)
        raw = b''.join(b'\0' + self.rgb[y * self.width * 3:(y + 1) * self.width * 3]
                       for y in range(self.height))
        png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', self.width, self.height, 8, 2, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress(raw, level=5)) + chunk(b'IEND', b''))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)


class SchematicCamera:
    def __init__(self, width: int = 160, height: int = 96):
        if width < 80 or height < 64:
            raise ValueError('camera output too small')
        self.width, self.height = width, height

    def _draw_segment(self, data: bytearray, x0: float, y0: float, x1: float, y1: float,
                      color: tuple[int, int, int], thickness: int = 2) -> None:
        n = max(1, round(max(abs(x1 - x0), abs(y1 - y0)) * 1.5))
        w, h = self.width, self.height
        for k in range(n + 1):
            x = round(x0 + (x1 - x0) * k / n)
            y = round(y0 + (y1 - y0) * k / n)
            for yy in range(max(0, y - thickness // 2), min(h, y + thickness // 2 + 1)):
                for xx in range(max(0, x - thickness // 2), min(w, x + thickness // 2 + 1)):
                    idx = 3 * (yy * w + xx)
                    data[idx:idx + 3] = bytes(color)

    def render(self, scenario: Scenario, state: AgentState, station: float) -> RGBFrame:
        w, h = self.width, self.height
        # Keep a stable landscape gradient so only road/actor geometry affects the hash.
        pixels = bytearray(w * h * 3)
        for y in range(h):
            color = (22, 38, 52) if y < 19 else (48, 54, 62)
            pixels[y * w * 3:(y + 1) * w * 3] = bytes(color) * w

        def project(x: float, y: float) -> tuple[float, float] | None:
            dx, dy = x - state.x, y - state.y
            fwd = cos(state.heading) * dx + sin(state.heading) * dy
            side = -sin(state.heading) * dx + cos(state.heading) * dy
            if fwd < 1.5 or fwd > 100:
                return None
            px = w / 2 - 190 * side / (fwd + 5)
            py = h - 6 - (h - 25) * fwd / (fwd + 26)
            return px, py

        # The same physical world point is reprojected after every ego move.
        lookahead = [2, 3, 4, 5, 7, 9, 12, 15, 18, 22, 27, 32, 39, 47, 57, 70, 85]
        for sign in (-1, 1):
            last = None
            for d in lookahead:
                p = scenario.road.at(station + d)
                lateral = sign * scenario.lane_width_m * 0.5
                dot = project(p.x - sin(p.heading) * lateral, p.y + cos(p.heading) * lateral)
                if dot is not None and last is not None:
                    self._draw_segment(pixels, *last, *dot, (242, 242, 242), 2)
                last = dot
        if scenario.lead:
            lead_s = scenario.lead.station(state.t)
            if lead_s > station:
                pos = scenario.road.at(lead_s)
                pt = project(pos.x, pos.y)
                if pt is not None:
                    x, y = pt
                    self._draw_segment(pixels, x - 4, y - 2, x + 4, y - 2, (247, 103, 58), 3)
                    self._draw_segment(pixels, x - 4, y + 2, x + 4, y + 2, (247, 103, 58), 3)
        return RGBFrame(w, h, bytes(pixels))
