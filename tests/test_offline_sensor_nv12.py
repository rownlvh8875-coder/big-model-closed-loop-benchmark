from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from bigbench.offline_sensor_nv12 import decode_nv12, verify_sensor_capture


class OfflineSensorNV12Tests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def file(self, name, payload):
        (self.root / name).write_bytes(payload)
        return {'file': name, 'sha256': sha256(payload).hexdigest()}

    def manifest(self, data):
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def fixture(self):
        # Hand-written unit-test vectors. No camera frames are used here.
        camera = dict(width=4, height=2, y_stride=6, uv_stride=8, y_offset=1, uv_offset=16,
                      chroma_order='UV', color_range='limited', color_matrix='BT.709',
                      sensor_model='fixture', calibration_and_mount=self.file('calibration.txt', b'fixture'))
        road = bytearray([255] * 24)
        road[1:5] = bytes([11, 12, 13, 14])
        road[7:11] = bytes([21, 22, 23, 24])
        road[16:20] = bytes([100, 150, 110, 160])
        wide = bytearray(road)
        wide[1] = 31
        return dict(schema='offline-sensor-nv12-v1', capture_origin='SENSOR_NATIVE_NV12',
                    capture_history=self.file('capture.txt', b'unit-test fixture'),
                    cameras={'road': camera, 'wide': camera.copy()},
                    pairs=[dict(
                        road=dict(self.file('road.nv12', road), nbytes=len(road), frame_id=7, timestamp_ns=1000),
                        wide=dict(self.file('wide.nv12', wide), nbytes=len(wide), frame_id=8, timestamp_ns=1100),
                    )])

    def test_decode_separate_strides_offsets_and_uv_order(self):
        data = self.fixture()
        y, u, v = decode_nv12((self.root / 'road.nv12').read_bytes(), data['cameras']['road'])
        np.testing.assert_array_equal(y, [[11, 12, 13, 14], [21, 22, 23, 24]])
        np.testing.assert_array_equal(u, [[100, 110]])
        np.testing.assert_array_equal(v, [[150, 160]])

    def test_overlapping_active_planes_and_wrong_fourcc_are_rejected(self):
        data = self.fixture()
        raw = (self.root / 'road.nv12').read_bytes()
        with self.assertRaisesRegex(ValueError, 'overlap'):
            decode_nv12(raw, dict(data['cameras']['road'], uv_offset=10))
        with self.assertRaisesRegex(ValueError, 'UV'):
            decode_nv12(raw, dict(data['cameras']['road'], chroma_order='VU'))

    def test_records_source_checksums_and_declared_timing_without_physical_pass(self):
        result = verify_sensor_capture(self.manifest(self.fixture()))
        self.assertEqual(result['status'], 'LAYOUT_VERIFIED')
        self.assertEqual(result['pairs'][0]['wide_minus_road_ns'], 100)
        self.assertIsNone(result['pairs'][0]['reference_comparison'])
        self.assertFalse(result['physical_optics_validated'])
        self.assertFalse(result['sensor_provenance_authenticated'])

    def test_destination_sampling_checks_literal_reference_and_localizes_first_difference(self):
        data = self.fixture()
        calibration = self.file('map-source.txt', b'unit-test map source')
        # Map every output coordinate to source luma (0,0), and source UV (0,0).
        fixed = [[0., 0., 0.], [0., 0., 0.], [0., 0., 1.]]
        data['warp'] = dict(road=fixed, wide=fixed, source=calibration)
        expected = np.zeros((2, 6, 128, 256), dtype=np.uint8)
        expected[0] = np.array([11, 11, 11, 11, 100, 150], dtype=np.uint8)[:, None, None]
        expected[1] = np.array([31, 31, 31, 31, 100, 150], dtype=np.uint8)[:, None, None]
        data['pairs'][0]['reference_tensor'] = self.file('reference.bin', expected.tobytes())
        result = verify_sensor_capture(self.manifest(data))
        self.assertEqual(result['status'], 'REFERENCE_MATCH')
        expected[1, 4, 2, 3] = 99
        data['pairs'][0]['reference_tensor'] = self.file('reference-mismatch.bin', expected.tobytes())
        result = verify_sensor_capture(self.manifest(data))
        self.assertEqual(result['status'], 'REFERENCE_MISMATCH')
        comparison = result['pairs'][0]['reference_comparison']
        self.assertEqual(comparison['changed_bytes'], 1)
        self.assertEqual(comparison['first_difference'],
                         {'camera': 'wide', 'plane': 'U', 'row': 2, 'column': 3,
                          'actual': 100, 'reference': 99})

    def test_mutated_source_or_reference_without_warp_is_rejected(self):
        data = self.fixture()
        data['pairs'][0]['road']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
            verify_sensor_capture(self.manifest(data))
        data = self.fixture()
        data['pairs'][0]['reference_tensor'] = self.file('invalid-reference.bin', b'bytes')
        with self.assertRaisesRegex(ValueError, 'reference requires'):
            verify_sensor_capture(self.manifest(data))

    def test_without_capture_manifest_reports_blocked(self):
        result = verify_sensor_capture(None)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['official_inferences'], 0)
