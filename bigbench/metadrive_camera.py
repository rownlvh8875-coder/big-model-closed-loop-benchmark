"""Optional MetaDrive dual RGB sensor -> comma model-canvas adapter.

Uses real MetaDrive/Panda3D RGB camera rendering when the optional dependency is
installed. Camera poses follow a virtual ego state; no Carrot controller, CAN,
actual vehicle plant, or real-world route data are imported.

This is a *geometric pinhole contract* smoke tool, NOT a validated comma sensor
replacement. In particular, lens distortion / optical center mounting / exposure
are not certified, and simulated map geometry isn't matched to bigbench Scenario.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Protocol

import numpy as np

from .camera_rig import SchematicPair
from .kinematics import AgentState, step_ideal
from .optical_calibration import (
    CameraWarpAudit, OpticalContractError, PinholeRectifier,
    intrinsics_from_panda_lens, reference_source,
)
from .policies import ModelObservation


class RGBProvider(Protocol):
    def capture(self, state: AgentState) -> tuple[np.ndarray, np.ndarray, Any, Any]: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class OpticalFrame:
    pair: SchematicPair
    audit: dict[str, CameraWarpAudit]


class MetaDriveOpticalRig:
    """Convert MetaDrive road/wide RGB arrays to zero-distortion model views."""
    def __init__(self, provider: RGBProvider, *, source_width: int = 964,
                 source_height: int = 604):
        self.provider = provider
        self.rectifier = PinholeRectifier(source_width=source_width, source_height=source_height)

    def capture(self, pose: AgentState) -> OpticalFrame:
        road, wide, road_lens, wide_lens = self.provider.capture(pose)
        road_k = intrinsics_from_panda_lens(road_lens, self.rectifier.expected['road'].width,
                                             self.rectifier.expected['road'].height)
        wide_k = intrinsics_from_panda_lens(wide_lens, self.rectifier.expected['wide'].width,
                                             self.rectifier.expected['wide'].height)
        pair, audit = self.rectifier.rectify_pair(road, wide,
                                                  road_intrinsics=road_k, wide_intrinsics=wide_k)
        return OpticalFrame(pair, audit)

    def close(self) -> None:
        self.provider.close()


def _metadrive_sensor_classes(width: int, height: int):
    """Build RAM-backed sensors after the *optional* simulator import.

    Based on the openpilot MetaDrive CopyRamRGBCamera approach, with focal lengths
    chosen from comma's published ideal-pinhole reference instead of 40/120 roundings.
    """
    try:
        from metadrive.component.sensors.rgb_camera import RGBCamera
        from panda3d.core import GraphicsOutput, Texture
    except ImportError as exc:
        raise RuntimeError('MetaDrive capture requires metadrive-simulator and Panda3D') from exc

    def one_camera(kind):
        class RAMCamera(RGBCamera):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # The reference focal is only a ZERO-DISTORTION pinhole stand-in.
                lens = self.get_lens()
                lens.setFov(reference_source(kind, width, height).fov_h_deg)
                lens.setNear(0.1)
                self.copy_texture = Texture()
                self.buffer.addRenderTexture(self.copy_texture, GraphicsOutput.RTMCopyRam)

            def get_rgb_array_cpu(self):
                texture = self.copy_texture
                data = np.frombuffer(texture.getRamImageAs('RGB').getData(), dtype=np.uint8)
                if data.size != width * height * 3:
                    raise OpticalContractError('MetaDrive camera RAM buffer missing or wrong size')
                return np.ascontiguousarray(data.reshape((height, width, 3))[::-1])
        RAMCamera.__name__ = 'BigBench' + kind.title() + 'Camera'
        return RAMCamera

    return one_camera('road'), one_camera('wide')


class NativeMetaDriveProvider:
    """Short bounded offscreen optical probe using MetaDrive's own rendered road.

    The camera is *borrowed* into a virtual reference pose for every capture;
    the vehicle is NOT used as a model plant or modified by steering commands.
    MetaDrive BaseCamera.perceive() supports new_parent_node / position / hpr,
    which updates Panda3D frames before reading its CPU buffer.

    Local forward-left-up -> Panda vehicle-local (-left, forward, up). This frame
    convention needs an independent pixel-landmark check for full optical fidelity.
    """
    def __init__(self, *, seed: int = 20261109, source_width: int = 964,
                 source_height: int = 604, height_m: float = 1.22):
        if not math.isfinite(height_m) or not 0.25 <= height_m <= 4:
            raise OpticalContractError('virtual camera height out of bounded probe range')
        self.source_width, self.source_height = source_width, source_height
        self.height_m = height_m
        self.seed = int(seed)
        self.env = None
        self.start()

    def start(self) -> None:
        try:
            from metadrive.envs.metadrive_env import MetaDriveEnv
        except ImportError as exc:
            raise RuntimeError('Install the optional metadrive-simulator dependency') from exc
        road_class, wide_class = _metadrive_sensor_classes(self.source_width, self.source_height)
        # Only use MetaDrive's scenery/camera; its vehicle dynamics do not
        # participate in the model policy or benchmark metrics.
        config = dict(
            use_render=False, image_observation=False, image_on_cuda=False,
            start_seed=self.seed, num_scenarios=1,
            random_traffic=False, traffic_density=0.0,
            sensors={'bigbench_road': (road_class, self.source_width, self.source_height),
                     'bigbench_wide': (wide_class, self.source_width, self.source_height)},
            map_config={'type': 'block_sequence', 'config': 'S', 'lane_width': 3.5, 'lane_num': 2},
            decision_repeat=1,
        )
        self.env = MetaDriveEnv(config)
        try:
            self.env.reset(seed=self.seed)
            # Some MetaDrive 0.4.x configurations do not auto-construct
            # custom cameras when image_observation=False. Use EngineCore's API.
            for key, klass in (('bigbench_road', road_class), ('bigbench_wide', wide_class)):
                if key not in self.env.engine.sensors:
                    self.env.engine.add_image_sensor(key, klass,
                                                     (self.source_width, self.source_height))
            if not all(name in self.env.engine.sensors for name in ('bigbench_road','bigbench_wide')):
                raise RuntimeError('MetaDrive camera registration failed; available: ' +
                                   repr(sorted(self.env.engine.sensors)))
        except BaseException:
            self.close()
            raise

    def capture(self, state: AgentState) -> tuple[np.ndarray, np.ndarray, Any, Any]:
        if self.env is None:
            raise RuntimeError('MetaDrive provider is closed')
        if not all(math.isfinite(v) for v in (state.x,state.y,state.heading,state.t,state.speed)):
            raise OpticalContractError('virtual pose must be finite')
        # Virtual camera is placed independently of MetaDrive built-in vehicle physics.
        position=(-float(state.y), float(state.x), self.height_m)
        hpr=(math.degrees(float(state.heading)), 0.0, 0.0)
        cams = self.env.engine.sensors
        frames=[]
        lenses=[]
        for name in ('bigbench_road', 'bigbench_wide'):
            cam = cams[name]
            raw = cam.perceive(to_float=False, new_parent_node=self.env.vehicle.origin,
                               position=position, hpr=hpr)
            if not isinstance(raw, np.ndarray):
                raw = raw.get()  # MetaDrive may return a GPU-backed array
            frames.append(np.asarray(raw))
            lenses.append(cam.get_lens())
        return frames[0], frames[1], lenses[0], lenses[1]

    def close(self) -> None:
        if self.env is not None:
            self.env.close()
            self.env = None


def probe_model_with_metadrive(policy: Any, rig: MetaDriveOpticalRig, *,
                               steps: int = 3, dt_s: float = 0.05,
                               initial_speed_mps: float = 12.0) -> tuple[dict, OpticalFrame]:
    """Optical/ONNX feedback wiring only. Never produces driving performance scores.

    No scripted ground-truth route from bigbench is paired with an unrelated
    MetaDrive map, and no lane-intrusion or model quality score is computed.
    """
    if type(steps) is not int or not 1 <= steps <= 20:
        raise ValueError('bounded MetaDrive optical probe requires 1..20 steps')
    if not 0 < dt_s <= 0.05 or not 0 <= initial_speed_mps <= 35:
        raise ValueError('invalid virtual timestep or initial speed')
    state = AgentState(0, 0, 0, 0, initial_speed_mps)
    policy.reset()
    hashes=[]
    records=[]
    last=None
    for _ in range(steps):
        last=rig.capture(state)
        hashes.append((last.pair.road.sha256,last.pair.wide.sha256))
        action=policy.step(ModelObservation(last.pair.road, state.speed, state.t,
                                            wide_frame=last.pair.wide))
        records.append(dict(t_s=state.t, x_m=state.x, y_m=state.y,
                            heading_rad=state.heading, speed_mps=state.speed,
                            target_curvature_1pm=action.curvature_1pm,
                            target_acceleration_mps2=action.acceleration_mps2,
                            road_sha256=hashes[-1][0], wide_sha256=hashes[-1][1]))
        state=step_ideal(state,action,dt_s)
    assert last is not None
    return {
        'classification': ('METADRIVE_REAL_RENDER_VIRTUAL_PINHOLE_UNCALIBRATED'
                           if isinstance(rig.provider, NativeMetaDriveProvider)
                           else 'CAMERA_PROVIDER_TEST_DOUBLE_NOT_METADRIVE'),
        'scoring_allowed': False, 'real_vehicle_testing': False,
        'cd210_fallback': False, 'steps': steps,
        'distinct_road_frames': len({a for a,b in hashes}),
        'distinct_wide_frames': len({b for a,b in hashes}),
        'camera_audit': {k:v.to_dict() for k,v in last.audit.items()},
        'records': records,
        'warning': 'Pinhole intrinsics only; MetaDrive/map geometry & actual camera distortion/extrinsics not validated',
    }, last
